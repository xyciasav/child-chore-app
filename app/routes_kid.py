from collections import OrderedDict

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Child, Chore, ChoreSubmission, Reward, RewardRedemption, ChoreStatus, RewardRedemptionStatus
from app.core import templates

router = APIRouter()


@router.get("/kid")
async def kid_dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    """Child dashboard - shows chores, rewards, and coin balance."""
    # Get or create default child
    result = await db.execute(select(Child))
    child = result.scalar_one_or_none()
    if not child:
        child = Child(name="Child", coins=0.0)
        db.add(child)
        await db.commit()
        await db.refresh(child)

    # Get active chores
    chores_result = await db.execute(
        select(Chore)
        .where(Chore.active == True)
        .order_by(Chore.room, Chore.title)
    )
    chores = chores_result.scalars().all()
    chore_groups_by_room = OrderedDict()
    for chore in chores:
        room = (chore.room or "General").strip() or "General"
        chore_groups_by_room.setdefault(room, []).append(chore)
    chore_groups = [
        {"room": room, "chores": grouped_chores}
        for room, grouped_chores in chore_groups_by_room.items()
    ]

    # Get active rewards
    rewards_result = await db.execute(select(Reward).where(Reward.active == True))
    rewards = rewards_result.scalars().all()

    # Get pending chore submissions for this child
    pending_chores_result = await db.execute(
        select(ChoreSubmission)
        .where(ChoreSubmission.child_id == child.id)
        .where(ChoreSubmission.status == ChoreStatus.PENDING)
        .options(selectinload(ChoreSubmission.chore))
    )
    pending_chores = pending_chores_result.scalars().all()

    # Get pending reward redemptions for this child
    pending_rewards_result = await db.execute(
        select(RewardRedemption)
        .where(RewardRedemption.child_id == child.id)
        .where(RewardRedemption.status == RewardRedemptionStatus.PENDING)
        .options(selectinload(RewardRedemption.reward))
    )
    pending_rewards = pending_rewards_result.scalars().all()

    return templates.TemplateResponse("kid_dashboard.html", {
        "request": request,
        "child": child,
        "chores": chores,
        "chore_groups": chore_groups,
        "rewards": rewards,
        "pending_chores": pending_chores,
        "pending_rewards": pending_rewards,
    })


@router.post("/kid/chore/submit")
async def submit_chore(
    chore_id: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Submit a chore completion for approval."""
    # Get default child
    result = await db.execute(select(Child))
    child = result.scalar_one_or_none()
    if not child:
        child = Child(name="Child", coins=0.0)
        db.add(child)
        await db.commit()

    # Get the chore
    chore_result = await db.execute(select(Chore).where(Chore.id == chore_id))
    chore = chore_result.scalar_one_or_none()
    if not chore:
        return RedirectResponse(url="/kid", status_code=303)

    # Create submission
    submission = ChoreSubmission(
        child_id=child.id,
        chore_id=chore.id,
        status=ChoreStatus.PENDING
    )
    db.add(submission)
    await db.commit()

    return RedirectResponse(url="/kid", status_code=303)


@router.post("/kid/reward/request")
async def request_reward(
    reward_id: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Request a reward redemption."""
    # Get default child
    result = await db.execute(select(Child))
    child = result.scalar_one_or_none()
    if not child:
        child = Child(name="Child", coins=0.0)
        db.add(child)
        await db.commit()

    # Get the reward
    reward_result = await db.execute(select(Reward).where(Reward.id == reward_id))
    reward = reward_result.scalar_one_or_none()
    if not reward:
        return RedirectResponse(url="/kid", status_code=303)

    # Check if child has enough coins
    if child.coins < reward.coin_cost:
        return RedirectResponse(url="/kid", status_code=303)

    # Create redemption request
    redemption = RewardRedemption(
        child_id=child.id,
        reward_id=reward.id,
        status=RewardRedemptionStatus.PENDING
    )
    db.add(redemption)
    await db.commit()

    return RedirectResponse(url="/kid", status_code=303)
