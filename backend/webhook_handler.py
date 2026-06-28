import json
import logging
from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import IGAccount, AutomationRule, DMLog
from config import WEBHOOK_VERIFY_TOKEN, META_APP_ID, META_APP_SECRET, META_API_VERSION
from dm_sender import send_instagram_dm

logger = logging.getLogger("hanubees.webhook")
router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.get("")
async def verify_webhook(request: Request):
    """Meta hits this to verify webhook ownership."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == WEBHOOK_VERIFY_TOKEN:
        return int(challenge)
    raise HTTPException(403, "Verification failed")


async def process_comment(ig_account: IGAccount, change: dict, db: AsyncSession):
    """Process a single comment event."""
    value = change.get("value", {})
    comment_id = value.get("id", "")
    text = value.get("text", "").strip()
    media_id = value.get("media", {}).get("id", "") if value.get("media") else ""
    commenter_id = value.get("from", {}).get("id", "")
    commenter_name = value.get("from", {}).get("username", "")

    logger.info(f"Comment from @{commenter_name}: {text}")

    # Find matching rules
    result = await db.execute(
        select(AutomationRule).where(
            AutomationRule.ig_account_id == ig_account.id,
            AutomationRule.is_active == True,
        )
    )
    rules = result.scalars().all()

    for rule in rules:
        matched = False
        if rule.match_type == "exact":
            matched = text.lower() == rule.keyword.lower()
        elif rule.match_type == "contains":
            matched = rule.keyword.lower() in text.lower()
        elif rule.match_type == "starts_with":
            matched = text.lower().startswith(rule.keyword.lower())

        if matched:
            logger.info(f"Rule matched: {rule.keyword} → sending DM")
            success = await send_instagram_dm(
                ig_business_id=ig_account.ig_user_id,
                access_token=ig_account.access_token,
                recipient_ig_user_id=commenter_id,
                message=rule.reply_message,
            )

            rule.dm_count += 1

            log = DMLog(
                ig_account_id=ig_account.id,
                rule_id=rule.id,
                from_username=commenter_name,
                from_user_id=commenter_id,
                comment_text=text,
                dm_text=rule.reply_message,
                post_id=media_id,
                status="sent" if success else "failed",
            )
            db.add(log)
            return


@router.post("")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Receive webhook events from Meta."""
    body = await request.json()
    logger.info(f"Webhook received: {json.dumps(body, indent=2)[:2000]}")

    entries = body.get("entry", [])
    for entry in entries:
        for change in entry.get("changes", []):
            field = change.get("field", "")
            if field != "comments":
                continue

            ig_business_id = entry.get("id", "")
            if not ig_business_id:
                continue

            # Find the IG account in our DB
            result = await db.execute(
                select(IGAccount).where(
                    IGAccount.ig_user_id == ig_business_id,
                    IGAccount.is_active == True,
                )
            )
            ig_account = result.scalar_one_or_none()
            if not ig_account:
                logger.warning(f"No IG account found for {ig_business_id}")
                continue

            # Process in background so Meta gets 200 OK fast
            background_tasks.add_task(process_comment, ig_account, change, db)

    return {"status": "ok"}


@router.post("/setup-subscription")
async def setup_webhook_subscription(db: AsyncSession = Depends(get_db)):
    """Subscribe to comment webhooks for all connected IG accounts."""
    result = await db.execute(select(IGAccount).where(IGAccount.is_active == True))
    accounts = result.scalars().all()

    results = []
    for account in accounts:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://graph.facebook.com/{META_API_VERSION}/{account.ig_user_id}/subscribed_apps",
                params={
                    "subscribed_fields": "comments",
                    "access_token": account.access_token,
                },
            )
            results.append({
                "ig_username": account.ig_username,
                "success": resp.status_code == 200,
                "response": resp.text[:200],
            })

    return {"status": "ok", "results": results}
