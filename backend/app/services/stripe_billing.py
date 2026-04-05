import stripe
from app.core.config import settings

stripe.api_key = settings.stripe_secret_key

def create_checkout_session(customer_id: str, price_id: str, success_url: str, cancel_url: str) -> str:
    session = stripe.checkout.Session.create(
        customer=customer_id, mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url, cancel_url=cancel_url,
    )
    return session.url

def create_portal_session(customer_id: str, return_url: str) -> str:
    session = stripe.billing_portal.Session.create(customer=customer_id, return_url=return_url)
    return session.url

def create_customer(email: str) -> str:
    customer = stripe.Customer.create(email=email)
    return customer.id
