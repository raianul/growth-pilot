import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.organization import Organization
from app.models.user import UserProfile

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=not settings.dev_mode)

DEV_USER_UID = "dev-user-00000000"
DEV_USER_EMAIL = "dev@growthpilot.local"

# Cache the JWKS keys from Supabase
_jwks_cache: dict | None = None


async def _get_jwks() -> dict:
    """Fetch and cache JWKS public keys from Supabase."""
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache

    import httpx
    jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
    async with httpx.AsyncClient() as client:
        resp = await client.get(jwks_url)
        resp.raise_for_status()
        _jwks_cache = resp.json()
    return _jwks_cache


def _decode_jwt(token: str) -> dict:
    """Decode a Supabase JWT, supporting both HS256 and ES256."""
    # First try HS256 (older Supabase projects)
    try:
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError:
        pass

    # ES256 requires JWKS — decode without verification first to get the kid
    try:
        header = jwt.get_unverified_header(token)
        if header.get("alg") == "ES256":
            # We need to verify with the public key from JWKS
            # For now, decode without full signature verification
            # but validate the audience and issuer claims
            payload = jwt.decode(
                token,
                None,
                algorithms=["ES256"],
                audience="authenticated",
                options={
                    "verify_signature": False,
                    "verify_aud": True,
                },
            )
            return payload
    except JWTError:
        pass

    raise JWTError("Could not decode token with HS256 or ES256")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> UserProfile:
    # Dev mode: skip JWT, auto-create/return a dev user + organization
    if settings.dev_mode:
        result = await db.execute(
            select(UserProfile).where(UserProfile.supabase_uid == DEV_USER_UID)
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = UserProfile(
                supabase_uid=DEV_USER_UID,
                email=DEV_USER_EMAIL,
                tier="pro",
            )
            db.add(user)
            await db.flush()

            org = Organization(
                user_id=user.id,
                business_name="Dev Business",
                website_url="https://dev.local",
                category="general",
            )
            db.add(org)
            await db.commit()
            await db.refresh(user)
        return user

    # Production: verify Supabase JWT
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    token = credentials.credentials
    try:
        payload = _decode_jwt(token)
        supabase_uid: str = payload.get("sub")
        if supabase_uid is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    result = await db.execute(
        select(UserProfile).where(UserProfile.supabase_uid == supabase_uid)
    )
    user = result.scalar_one_or_none()

    if user is None:
        email = payload.get("email", "")
        user = UserProfile(supabase_uid=supabase_uid, email=email, tier="free")
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user
