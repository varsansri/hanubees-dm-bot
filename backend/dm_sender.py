import logging
import httpx
from config import META_API_VERSION

logger = logging.getLogger("hanubees.dm")

GRAPH_URL = f"https://graph.facebook.com/{META_API_VERSION}"


async def send_instagram_dm(
    ig_business_id: str,
    access_token: str,
    recipient_ig_user_id: str,
    message: str,
) -> bool:
    """
    Send a DM via Instagram Graph API.
    Uses the Instagram Messaging API endpoint.
    """
    url = f"{GRAPH_URL}/{ig_business_id}/messages"

    payload = {
        "recipient": {"id": recipient_ig_user_id},
        "message": {"text": message},
        "access_token": access_token,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload)

        if resp.status_code == 200:
            logger.info(f"DM sent to {recipient_ig_user_id}")
            return True
        else:
            logger.error(f"DM failed ({resp.status_code}): {resp.text}")
            return False

    except Exception as e:
        logger.error(f"DM error: {e}")
        return False
