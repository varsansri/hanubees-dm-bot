"""
Token generator for Hanubees DM Bot.
Usage: python generate_token.py <APP_SECRET> <SHORT_TOKEN>
"""
import sys, httpx, asyncio

APP_ID = "1663530681618204"
API_VERSION = "v21.0"
BASE = f"https://graph.facebook.com/{API_VERSION}"

async def main():
    if len(sys.argv) < 3:
        print("Usage: python generate_token.py <APP_SECRET> <SHORT_TOKEN>")
        return

    app_secret = sys.argv[1]
    short_token = sys.argv[2]

    async with httpx.AsyncClient() as client:
        # Step 1: Exchange for long-lived token
        print("[1/5] Exchanging for long-lived token...")
        resp = await client.get(f"{BASE}/oauth/access_token", params={
            "grant_type": "fb_exchange_token",
            "client_id": APP_ID,
            "client_secret": app_secret,
            "fb_exchange_token": short_token,
        })
        if resp.status_code != 200:
            print(f"FAILED: {resp.status_code} - {resp.text}")
            return
        token = resp.json()["access_token"]
        print(f"  Token: {token}")

        # Step 2: Get Facebook Pages
        print("\n[2/5] Fetching Facebook Pages...")
        pages_resp = await client.get(f"{BASE}/me/accounts", params={"access_token": token})
        if pages_resp.status_code != 200:
            print(f"FAILED: {pages_resp.text}")
            return
        pages = pages_resp.json().get("data", [])
        print(f"  Found {len(pages)} pages")

        ig_username = None
        page_token = None
        ig_biz_id = None

        for page in pages:
            p_name = page.get("name", "Unknown")
            p_id = page["id"]
            p_token = page["access_token"]

            ig_resp = await client.get(f"{BASE}/{p_id}", params={
                "fields": "instagram_business_account{id,username}",
                "access_token": p_token,
            })
            if ig_resp.status_code != 200:
                print(f"  {p_name}: No access - {ig_resp.text[:100]}")
                continue

            ig_biz = ig_resp.json().get("instagram_business_account")
            if not ig_biz:
                print(f"  {p_name}: No IG account linked")
                continue

            ig_biz_id = ig_biz["id"]
            ig_username = ig_biz.get("username", "unknown")
            page_token = p_token
            print(f"  {p_name}: @{ig_username} ({ig_biz_id})")
            break

        if not ig_biz_id:
            print("\nFAILED: No Instagram business account linked to any page.")
            return

        # Step 3: Get IG info
        print(f"\n[3/5] IG account details...")
        info_resp = await client.get(f"{BASE}/{ig_biz_id}", params={
            "fields": "username,followers_count",
            "access_token": token,
        })
        if info_resp.status_code == 200:
            info = info_resp.json()
            print(f"  @{info.get('username')} - {info.get('followers_count', '?')} followers")

        # Step 4: Subscribe webhooks
        print(f"\n[4/5] Subscribing to webhooks (comments, messages)...")
        sub_resp = await client.post(f"{BASE}/{ig_biz_id}/subscribed_apps", params={
            "subscribed_fields": "comments,messages",
            "access_token": page_token,
        })
        if sub_resp.status_code == 200:
            print(f"  Subscribed: {sub_resp.json()}")
        else:
            print(f"  Failed: {sub_resp.text[:300]}")

        # Step 5: Output
        print(f"\n{'='*55}")
        print(f"IG_BUSINESS_ID = {ig_biz_id}")
        print(f"IG_USERNAME    = {ig_username}")
        print(f"PAGE_TOKEN     = {page_token}")
        print(f"LONG_TOKEN     = {token}")
        print(f"{'='*55}")

if __name__ == "__main__":
    asyncio.run(main())
