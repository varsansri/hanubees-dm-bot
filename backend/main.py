import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database import engine, get_db, Base
from models import IGAccount, AutomationRule, DMLog
from oauth_handler import router as oauth_router
from webhook_handler import router as webhook_router
from rules_api import router as rules_router

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="Hanubees DM Bot", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────
app.include_router(oauth_router)
app.include_router(webhook_router)
app.include_router(rules_router)


# ── Dashboard Stats ──────────────────────────────────
@app.get("/api/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    accts_result = await db.execute(select(IGAccount))
    all_accounts = accts_result.scalars().all()
    acct_ids = [a.id for a in all_accounts]

    if not acct_ids:
        return {"accounts": 0, "rules": 0, "dms_sent_today": 0, "total_dms": 0}

    rules_count = await db.execute(
        select(func.count(AutomationRule.id)).where(AutomationRule.ig_account_id.in_(acct_ids))
    )
    total_dms = await db.execute(
        select(func.count(DMLog.id)).where(DMLog.ig_account_id.in_(acct_ids))
    )

    return {
        "accounts": len(all_accounts),
        "rules": rules_count.scalar() or 0,
        "dms_sent_today": total_dms.scalar() or 0,
        "total_dms": total_dms.scalar() or 0,
    }


# ── IG Accounts ──────────────────────────────────────
@app.get("/api/ig-accounts")
async def list_ig_accounts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(IGAccount))
    accounts = result.scalars().all()
    return [
        {
            "id": a.id,
            "ig_username": a.ig_username,
            "ig_user_id": a.ig_user_id,
            "is_active": a.is_active,
            "connected_at": str(a.connected_at),
        }
        for a in accounts
    ]


# ── DM Logs ──────────────────────────────────────────
@app.get("/api/dm-logs")
async def get_dm_logs(db: AsyncSession = Depends(get_db), limit: int = 50):
    result = await db.execute(
        select(DMLog)
        .order_by(DMLog.created_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    return [
        {
            "id": l.id,
            "from_username": l.from_username,
            "comment_text": l.comment_text,
            "dm_text": l.dm_text,
            "status": l.status,
            "created_at": str(l.created_at),
        }
        for l in logs
    ]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
