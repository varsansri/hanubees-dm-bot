import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database import engine, get_db, Base
from models import User, IGAccount, AutomationRule, DMLog
from auth import hash_password, verify_password, create_access_token, get_current_user
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


# ── Auth Endpoints ───────────────────────────────────
class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/api/register")
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Email already registered")

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_access_token(user.id)
    return {"status": "ok", "token": token, "user": {"id": user.id, "email": user.email}}


@app.post("/api/login")
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(401, "Invalid email or password")

    token = create_access_token(user.id)
    return {"status": "ok", "token": token, "user": {"id": user.id, "email": user.email, "plan": user.plan}}


@app.get("/api/me")
async def get_me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "full_name": user.full_name, "plan": user.plan}


# ── Dashboard Stats ──────────────────────────────────
@app.get("/api/stats")
async def get_stats(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Get user's IG accounts
    accts_result = await db.execute(select(IGAccount).where(IGAccount.user_id == user.id))
    accounts = accts_result.scalars().all()
    acct_ids = [a.id for a in accounts]

    if not acct_ids:
        return {"accounts": 0, "rules": 0, "dms_sent_today": 0, "total_dms": 0}

    rules_count = await db.execute(
        select(func.count(AutomationRule.id)).where(AutomationRule.ig_account_id.in_(acct_ids))
    )
    total_dms = await db.execute(
        select(func.count(DMLog.id)).where(DMLog.ig_account_id.in_(acct_ids))
    )

    return {
        "accounts": len(accounts),
        "rules": rules_count.scalar() or 0,
        "dms_sent_today": 0,  # TODO: filter by today
        "total_dms": total_dms.scalar() or 0,
    }


# ── IG Accounts ──────────────────────────────────────
@app.get("/api/ig-accounts")
async def list_ig_accounts(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(IGAccount).where(IGAccount.user_id == user.id))
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
async def get_dm_logs(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db), limit: int = 50):
    result = await db.execute(
        select(DMLog)
        .join(IGAccount)
        .where(IGAccount.user_id == user.id)
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
