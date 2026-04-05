import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.subscription import Subscription
from app.models.user import UserProfile
from app.schemas.billing import CheckoutRequest, CheckoutResponse, PortalResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["billing"])

stripe.api_key = settings.stripe_secret_key

TIER_BY_PRICE: dict[str, str] = {}

def _build_tier_map() -> None:
    if settings.stripe_pro_price_id:
        TIER_BY_PRICE[settings.stripe_pro_price_id] = "pro"
    if settings.stripe_agency_price_id:
        TIER_BY_PRICE[settings.stripe_agency_price_id] = "enterprise"

_build_tier_map()


async def _get_or_create_customer(user: UserProfile, db: AsyncSession) -> str:
    """Return existing Stripe customer ID or create a new one."""
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    sub = result.scalar_one_or_none()

    if sub is not None:
        return sub.stripe_customer_id

    customer = stripe.Customer.create(email=user.email, metadata={"user_id": str(user.id)})
    new_sub = Subscription(
        user_id=user.id,
        stripe_customer_id=customer["id"],
        plan="free",
        status="active",
    )
    db.add(new_sub)
    await db.commit()
    await db.refresh(new_sub)
    return customer["id"]


@router.post("/billing/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    payload: CheckoutRequest,
    user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CheckoutResponse:
    customer_id = await _get_or_create_customer(user, db)

    try:
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": payload.price_id, "quantity": 1}],
            mode="subscription",
            success_url=f"{settings.app_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.app_url}/billing/cancel",
            metadata={"user_id": str(user.id)},
        )
    except stripe.StripeError as exc:
        logger.exception("Stripe checkout error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create checkout session",
        )

    return CheckoutResponse(checkout_url=session["url"])


@router.post("/billing/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except stripe.SignatureVerificationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook signature"
        )
    except Exception as exc:
        logger.exception("Webhook payload error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload"
        )

    event_type = event["type"]

    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        customer_id = session.get("customer")
        price_id = None

        # Retrieve price_id from line items if not embedded
        try:
            line_items = stripe.checkout.Session.list_line_items(session["id"])
            if line_items["data"]:
                price_id = line_items["data"][0]["price"]["id"]
        except Exception:
            pass

        new_tier = TIER_BY_PRICE.get(price_id, "pro") if price_id else "pro"

        if customer_id:
            result = await db.execute(
                select(Subscription).where(Subscription.stripe_customer_id == customer_id)
            )
            sub = result.scalar_one_or_none()
            if sub:
                sub.plan = new_tier
                sub.stripe_subscription_id = session.get("subscription")

                # Update user tier
                user_result = await db.execute(
                    select(UserProfile).where(UserProfile.id == sub.user_id)
                )
                user = user_result.scalar_one_or_none()
                if user:
                    user.tier = new_tier

                await db.commit()

    elif event_type == "customer.subscription.deleted":
        subscription_obj = event["data"]["object"]
        customer_id = subscription_obj.get("customer")

        if customer_id:
            result = await db.execute(
                select(Subscription).where(Subscription.stripe_customer_id == customer_id)
            )
            sub = result.scalar_one_or_none()
            if sub:
                sub.plan = "free"
                sub.status = "cancelled"
                sub.stripe_subscription_id = None

                user_result = await db.execute(
                    select(UserProfile).where(UserProfile.id == sub.user_id)
                )
                user = user_result.scalar_one_or_none()
                if user:
                    user.tier = "free"

                await db.commit()

    return {"received": True}


@router.post("/billing/portal", response_model=PortalResponse)
async def create_portal_session(
    user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortalResponse:
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No billing record found for this account",
        )

    try:
        session = stripe.billing_portal.Session.create(
            customer=sub.stripe_customer_id,
            return_url=f"{settings.app_url}/settings/billing",
        )
    except stripe.StripeError as exc:
        logger.exception("Stripe portal error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create portal session",
        )

    return PortalResponse(portal_url=session["url"])
