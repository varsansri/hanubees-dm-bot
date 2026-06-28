import httpx
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import IGAccount, User
from auth import get_current_user
from config import META_APP_ID, META_APP_SECRET, META_REDIRECT_URI, META_API_VERSION

router = APIRouter(prefix="/oauth", tags=["oauth"])

OAUTH_URL = "https://www.facebook.com/{version}/dialog/oauth"
TOKEN_URL = "https://graph.facebook.com/{version}/oauth/access_token"
GRAPH_URL = "https://graph.facebook.com/{version}"


@router.get("/connect")
def start_oauth():
    """Step 1: Redirect influencer to Meta login."""
    params = {
        "client_id": META_APP_ID,
        "redirect_uri": META_REDIRECT_URI,
        "scope": "instagram_basic,instagram_manage_messages,pages_messaging,pages_show_list,pages_read_engagement",
        "response_type": "code",
        "state": "connect_ig",  # Should be dynamic in production
    }
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    url = OAUTH_URL.format(version=META_API_VERSION) + "?" + qs
    return RedirectResponse(url)


@router.get("/callback")
async def oauth_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """Step 2: Meta redirects here with ?code=... Exchange for tokens."""
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(400, "Missing authorization code")

    # Exchange code for short-lived access token
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            TOKEN_URL.format(version=META_API_VERSION),
            params={
                "client_id": META_APP_ID,
                "client_secret": META_APP_SECRET,
                "redirect_uri": META_REDIRECT_URI,
                "code": code,
            },
        )
    if resp.status_code != 200:
        raise HTTPException(400, f"Token exchange failed: {resp.text}")

    data = resp.json()
    short_token = data.get("access_token")

    # Exchange for long-lived token (60 days)
    async with httpx.AsyncClient() as client:
        ll_resp = await client.get(
            f"https://graph.facebook.com/{META_API_VERSION}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": META_APP_ID,
                "client_secret": META_APP_SECRET,
                "fb_exchange_token": short_token,
            },
        )
    if ll_resp.status_code != 200:
        raise HTTPException(400, f"Long-lived token exchange failed: {ll_resp.text}")

    ll_data = ll_resp.json()
    long_lived_token = ll_data["access_token"]
    expires_seconds = ll_data.get("expires_in", 5184000)

    # Get Instagram accounts linked to this FB Page
    async with httpx.AsyncClient() as client:
        pages_resp = await client.get(
            f"https://graph.facebook.com/{META_API_VERSION}/me/accounts",
            params={"access_token": long_lived_token},
        )
    if pages_resp.status_code != 200:
        raise HTTPException(400, f"Failed to get pages: {pages_resp.text}")

    pages = pages_resp.json().get("data", [])
    if not pages:
        return {"status": "ok", "message": "Connected! But no Pages found. Link your IG Professional account to a Facebook Page first."}

    for page in pages:
        page_token = page["access_token"]
        page_id = page["id"]

        async with httpx.AsyncClient() as client:
            ig_resp = await client.get(
                f"https://graph.facebook.com/{META_API_VERSION}/{page_id}",
                params={"fields": "instagram_business_account", "access_token": page_token},
            )
        if ig_resp.status_code != 200:
            continue

        ig_data = ig_resp.json()
        ig_biz = ig_data.get("instagram_business_account")
        if not ig_biz:
            continue

        ig_biz_id = ig_biz["id"]

        # Get IG username
        async with httpx.AsyncClient() as client:
            user_resp = await client.get(
                f"https://graph.facebook.com/{META_API_VERSION}/{ig_biz_id}",
                params={"fields": "username", "access_token": long_lived_token},
            )
        ig_username = "unknown"
        if user_resp.status_code == 200:
            ig_username = user_resp.json().get("username", "unknown")

        # Store in DB - for now we store without a user (anonymous flow)
        # In production, track via state param and link to logged-in user
        existing = await db.execute(
            select(IGAccount).where(IGAccount.ig_user_id == ig_biz_id)
        )
        account = existing.scalar_one_or_none()
        if account:
            account.access_token = long_lived_token
            account.long_lived_token = long_lived_token
        else:
            account = IGAccount(
                ig_user_id=ig_biz_id,
                ig_username=ig_username,
                access_token=long_lived_token,
                long_lived_token=long_lived_token,
            )
            db.add(account)

    await db.commit()

    return {
        "status": "ok",
        "message": "Instagram connected successfully!",
        "ig_username": ig_username,
    }
