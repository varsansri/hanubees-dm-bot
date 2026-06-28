from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from database import get_db
from models import AutomationRule, IGAccount

router = APIRouter(prefix="/api/rules", tags=["rules"])


class RuleCreate(BaseModel):
    ig_account_id: str
    keyword: str
    reply_message: str
    match_type: str = "exact"  # exact, contains, starts_with


class RuleUpdate(BaseModel):
    keyword: str | None = None
    reply_message: str | None = None
    match_type: str | None = None
    is_active: bool | None = None


@router.post("")
async def create_rule(data: RuleCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(IGAccount).where(IGAccount.id == data.ig_account_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Instagram account not found")

    rule = AutomationRule(
        ig_account_id=data.ig_account_id,
        keyword=data.keyword.strip(),
        reply_message=data.reply_message.strip(),
        match_type=data.match_type,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return {"status": "ok", "rule": {"id": rule.id, "keyword": rule.keyword, "dm_count": rule.dm_count}}


@router.get("")
async def list_rules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AutomationRule))
    rules = result.scalars().all()
    return [
        {
            "id": r.id,
            "ig_account_id": r.ig_account_id,
            "keyword": r.keyword,
            "reply_message": r.reply_message,
            "match_type": r.match_type,
            "is_active": r.is_active,
            "dm_count": r.dm_count,
        }
        for r in rules
    ]


@router.put("/{rule_id}")
async def update_rule(rule_id: str, data: RuleUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AutomationRule).where(AutomationRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "Rule not found")

    if data.keyword is not None:
        rule.keyword = data.keyword
    if data.reply_message is not None:
        rule.reply_message = data.reply_message
    if data.match_type is not None:
        rule.match_type = data.match_type
    if data.is_active is not None:
        rule.is_active = data.is_active

    await db.commit()
    return {"status": "ok"}


@router.delete("/{rule_id}")
async def delete_rule(rule_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AutomationRule).where(AutomationRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "Rule not found")

    await db.delete(rule)
    await db.commit()
    return {"status": "ok"}
