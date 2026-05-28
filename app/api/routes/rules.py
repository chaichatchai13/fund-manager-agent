import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.rule import SellPutRule
from app.schemas.rule import SellPutRuleCreate, SellPutRuleResponse, SellPutRuleUpdate

router = APIRouter(prefix="/api/rules", tags=["rules"])


@router.get("", response_model=list[SellPutRuleResponse])
async def list_rules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SellPutRule).order_by(SellPutRule.created_at))
    return result.scalars().all()


@router.post("", response_model=SellPutRuleResponse, status_code=201)
async def create_rule(body: SellPutRuleCreate, db: AsyncSession = Depends(get_db)):
    rule = SellPutRule(**body.model_dump())
    rule.symbols = [s.model_dump() for s in body.symbols]
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.get("/{rule_id}", response_model=SellPutRuleResponse)
async def get_rule(rule_id: str, db: AsyncSession = Depends(get_db)):
    rule = await db.get(SellPutRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.put("/{rule_id}", response_model=SellPutRuleResponse)
async def update_rule(rule_id: str, body: SellPutRuleUpdate, db: AsyncSession = Depends(get_db)):
    rule = await db.get(SellPutRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    updates = body.model_dump(exclude_unset=True)
    if "symbols" in updates and updates["symbols"] is not None:
        updates["symbols"] = [s.model_dump() if hasattr(s, "model_dump") else s for s in updates["symbols"]]
    for field, value in updates.items():
        setattr(rule, field, value)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(rule_id: str, db: AsyncSession = Depends(get_db)):
    rule = await db.get(SellPutRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    await db.delete(rule)
    await db.commit()


@router.patch("/{rule_id}/toggle", response_model=SellPutRuleResponse)
async def toggle_rule(rule_id: str, db: AsyncSession = Depends(get_db)):
    rule = await db.get(SellPutRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    rule.enabled = not rule.enabled
    await db.commit()
    await db.refresh(rule)
    return rule


@router.post("/{rule_id}/retry", response_model=SellPutRuleResponse)
async def retry_rule(rule_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Clear last_error and immediately trigger a scan for this rule."""
    rule = await db.get(SellPutRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    if not rule.enabled:
        raise HTTPException(status_code=400, detail="Rule is disabled — enable it first")

    # Clear the error so the UI updates immediately
    rule.last_error = None
    rule.last_error_at = None
    await db.commit()
    await db.refresh(rule)

    # Run a scan for this rule in the background so the HTTP response returns fast
    async def _run():
        from app.services.scan_service import scan_service
        await scan_service.run_scan(rule_id=rule_id)

    background_tasks.add_task(asyncio.ensure_future, _run())

    return rule
