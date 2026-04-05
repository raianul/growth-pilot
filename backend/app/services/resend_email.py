import httpx
from app.core.config import settings

httpx_client = httpx.AsyncClient(timeout=10.0)
RESEND_API = "https://api.resend.com/emails"

async def send_audit_ready_email(email: str, brand_name: str, week_number: int, score: int) -> bool:
    response = await httpx_client.post(
        RESEND_API,
        headers={"Authorization": f"Bearer {settings.resend_api_key}"},
        json={
            "from": "GrowthPilot <noreply@growthpilot.com>",
            "to": email,
            "subject": f"Week {week_number} missions ready — Score: {score}",
            "html": f"""
                <h2>Your Week {week_number} audit is complete!</h2>
                <p><strong>{brand_name}</strong> scored <strong>{score}/100</strong> this week.</p>
                <p>3 new missions are waiting for you.</p>
                <a href="{settings.app_url}/dashboard"
                   style="display:inline-block;background:#0037b0;color:white;padding:12px 24px;border-radius:12px;text-decoration:none;font-weight:600;">
                    View Dashboard
                </a>
            """,
        },
    )
    return response.status_code == 200
