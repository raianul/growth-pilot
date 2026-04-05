from fastapi import Depends, HTTPException, status

from app.core.auth import get_current_user
from app.models.user import UserProfile

TIER_LEVELS = {"free": 0, "pro": 1, "enterprise": 2}


def require_tier(min_tier: str):
    """FastAPI dependency that enforces minimum subscription tier."""

    async def _check_tier(
        user: UserProfile = Depends(get_current_user),
    ) -> UserProfile:
        user_level = TIER_LEVELS.get(user.tier, 0)
        required_level = TIER_LEVELS.get(min_tier, 0)
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "upgrade_required",
                    "required_tier": min_tier,
                    "current_tier": user.tier,
                },
            )
        return user

    return _check_tier
