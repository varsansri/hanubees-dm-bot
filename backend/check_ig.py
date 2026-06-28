import httpx, asyncio

async def main():
    token = "EAAXoZBOtZAzxwBR9n7WISA7th717spRSJcX7r5vr3lNF7cDCNR8xsZAMQzlz1p1YAybat1Xb13iPtXiOwpgEtVqkM9RcafIcSTFHZCedQekalsE4w9MlVTGeKl9qDpZASace3grmqfDtZB7HPrFUuNnAhfIAasC1t3Jq6TYwCA5hVIYvRZBgxZCJUVoyFQIz"
    BASE = "https://graph.facebook.com/v21.0"

    async with httpx.AsyncClient() as c:
        resp = await c.get(f"{BASE}/me/accounts", params={
            "fields": "name,id,username,instagram_business_account{id,username}",
            "access_token": token,
        })
        print(resp.text)

asyncio.run(main())
