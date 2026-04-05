import httpx
from app.core.config import settings

httpx_client = httpx.AsyncClient(timeout=10.0)

async def send_telegram_message(chat_id: str, text: str) -> bool:
    response = await httpx_client.post(
        f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
    )
    return response.status_code == 200
