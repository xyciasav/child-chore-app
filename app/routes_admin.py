from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.database import get_db
from app.models import (
    Child, Chore, ChoreSubmission, Reward, RewardRedemption,
    ChoreStatus, RewardRedemptionStatus
)
from app.core import templates
from app.auth import check_admin_passcode

router = APIRouter()

ADMIN_TABS = {
    "pending_chores": "/admin?tab=pending-chores",
    "manage_chores": "/admin?tab=manage-chores",
    "pending_rewards": "/admin?tab=pending-rewards",
    "manage_rewards": "/admin?tab=manage-rewards",
}


@router.get("/admin/login")
async def admin_login_page(request: Request):
    """Admin login page."""
    # If already authenticated, redirect to admin dashboard
    if request.cookies.get("admin_auth"):
        return RedirectResponse(url="/admin", status_code=303)
    return templates.TemplateResponse("admin_login.html", {
        "request": request,
        "error": request.query_params.get("error", "")
    })


@router.post("/admin/login")
async def admin_login(
    request: Request,
    passcode: str = Form(...)
):
    """Handle admin login."""
    if check_admin_passcode(passcode):
        response = RedirectResponse(url="/admin", status_code=303)
        response.set_cookie(key="admin_auth", value="true", max_age=86400, httponly=True)
        return response
    return RedirectResponse(url="/admin/login?error=invalid", status_code=303)


def check_admin_cookie(request: Request):
    """Check if user is authenticated as admin via cookie."""
    if not request.cookies.get("admin_auth"):
        return RedirectResponse(url="/admin/login", status_code=303)
    return None


@router.get("/admin")
async def admin_dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    """Admin dashboard - approve chores, manage chores/rewards."""
    redirect = check_admin_cookie(request)
    if redirect:
        return redirect

    # Get pending chore submissions
    pending_chores_result = await db.execute(
        select(ChoreSubmission)
        .where(ChoreSubmission.status == ChoreStatus.PENDING)
        .options(
            selectinload(ChoreSubmission.child),
            selectinload(ChoreSubmission.chore)
        )
    )
    pending_chores = pending_chores_result.scalars().all()

    # Get all chores
    chores_result = await db.execute(select(Chore).order_by(Chore.room, Chore.title))
    chores = chores_result.scalars().all()

    # Get all rewards
    rewards_result = await db.execute(select(Reward))
    rewards = rewards_result.scalars().all()

    # Get pending reward redemptions
    pending_rewards_result = await db.execute(
        select(RewardRedemption)
        .where(RewardRedemption.status == RewardRedemptionStatus.PENDING)
        .options(
            selectinload(RewardRedemption.child),
            selectinload(RewardRedemption.reward)
        )
    )
    pending_rewards = pending_rewards_result.scalars().all()

    # Get all children
    children_result = await db.execute(select(Child))
    children = children_result.scalars().all()

    chore_history_result = await db.execute(select(ChoreSubmission))
    chore_history = chore_history_result.scalars().all()

    reward_history_result = await db.execute(select(RewardRedemption))
    reward_history = reward_history_result.scalars().all()

    metrics = {
        "total_coins": sum(child.coins for child in children),
        "active_chores": sum(1 for chore in chores if chore.active),
        "inactive_chores": sum(1 for chore in chores if not chore.active),
        "active_rewards": sum(1 for reward in rewards if reward.active),
        "pending_chores": len(pending_chores),
        "pending_rewards": len(pending_rewards),
        "approved_chores": sum(1 for submission in chore_history if submission.status == ChoreStatus.APPROVED),
        "denied_chores": sum(1 for submission in chore_history if submission.status == ChoreStatus.DENIED),
        "approved_rewards": sum(1 for redemption in reward_history if redemption.status == RewardRedemptionStatus.APPROVED),
    }

    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "pending_chores": pending_chores,
        "chores": chores,
        "rewards": rewards,
        "pending_rewards": pending_rewards,
        "children": children,
        "metrics": metrics,
    })


@router.post("/admin/chore/approve")
async def approve_chore(
    request: Request,
    submission_id: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Approve a chore submission - award coins to child."""
    redirect = check_admin_cookie(request)
    if redirect:
        return redirect

    submission_result = await db.execute(
        select(ChoreSubmission)
        .where(ChoreSubmission.id == submission_id)
        .options(
            selectinload(ChoreSubmission.child),
            selectinload(ChoreSubmission.chore)
        )
    )
    submission = submission_result.scalar_one_or_none()
    if not submission:
        return RedirectResponse(url=ADMIN_TABS["pending_chores"], status_code=303)

    submission.status = ChoreStatus.APPROVED
    submission.reviewed_at = datetime.utcnow()
    submission.child.coins += submission.chore.coin_value

    await db.commit()
    return RedirectResponse(url=ADMIN_TABS["pending_chores"], status_code=303)


@router.post("/admin/chore/deny")
async def deny_chore(
    request: Request,
    submission_id: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Deny a chore submission - no coins awarded."""
    redirect = check_admin_cookie(request)
    if redirect:
        return redirect

    submission_result = await db.execute(
        select(ChoreSubmission)
        .where(ChoreSubmission.id == submission_id)
    )
    submission = submission_result.scalar_one_or_none()
    if not submission:
        return RedirectResponse(url=ADMIN_TABS["pending_chores"], status_code=303)

    submission.status = ChoreStatus.DENIED
    submission.reviewed_at = datetime.utcnow()

    await db.commit()
    return RedirectResponse(url=ADMIN_TABS["pending_chores"], status_code=303)


@router.post("/admin/reward/approve")
async def approve_reward(
    request: Request,
    redemption_id: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Approve a reward redemption - deduct coins from child."""
    redirect = check_admin_cookie(request)
    if redirect:
        return redirect

    redemption_result = await db.execute(
        select(RewardRedemption)
        .where(RewardRedemption.id == redemption_id)
        .options(
            selectinload(RewardRedemption.child),
            selectinload(RewardRedemption.reward)
        )
    )
    redemption = redemption_result.scalar_one_or_none()
    if not redemption:
        return RedirectResponse(url=ADMIN_TABS["pending_rewards"], status_code=303)

    redemption.status = RewardRedemptionStatus.APPROVED
    redemption.reviewed_at = datetime.utcnow()
    redemption.child.coins -= redemption.reward.coin_cost

    await db.commit()
    return RedirectResponse(url=ADMIN_TABS["pending_rewards"], status_code=303)


@router.post("/admin/reward/deny")
async def deny_reward(
    request: Request,
    redemption_id: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Deny a reward redemption - coins remain with child."""
    redirect = check_admin_cookie(request)
    if redirect:
        return redirect

    redemption_result = await db.execute(
        select(RewardRedemption)
        .where(RewardRedemption.id == redemption_id)
    )
    redemption = redemption_result.scalar_one_or_none()
    if not redemption:
        return RedirectResponse(url=ADMIN_TABS["pending_rewards"], status_code=303)

    redemption.status = RewardRedemptionStatus.DENIED
    redemption.reviewed_at = datetime.utcnow()

    await db.commit()
    return RedirectResponse(url=ADMIN_TABS["pending_rewards"], status_code=303)


@router.post("/admin/chore/add")
async def add_chore(
    request: Request,
    title: str = Form(...),
    room: str = Form("General"),
    description: str = Form(""),
    coin_value: float = Form(1.0),
    db: AsyncSession = Depends(get_db)
):
    """Add a new chore."""
    redirect = check_admin_cookie(request)
    if redirect:
        return redirect

    chore = Chore(
        title=title,
        room=room.strip() or "General",
        description=description,
        coin_value=coin_value,
        active=True
    )
    db.add(chore)
    await db.commit()
    return RedirectResponse(url=ADMIN_TABS["manage_chores"], status_code=303)


@router.post("/admin/chore/delete")
async def delete_chore(
    request: Request,
    chore_id: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Delete a chore."""
    redirect = check_admin_cookie(request)
    if redirect:
        return redirect

    chore_result = await db.execute(select(Chore).where(Chore.id == chore_id))
    chore = chore_result.scalar_one_or_none()
    if chore:
        await db.delete(chore)
        await db.commit()
    return RedirectResponse(url=ADMIN_TABS["manage_chores"], status_code=303)


@router.post("/admin/chore/edit")
async def edit_chore(
    request: Request,
    chore_id: int = Form(...),
    title: str = Form(...),
    room: str = Form("General"),
    description: str = Form(""),
    coin_value: float = Form(1.0),
    active: bool = Form(False),
    db: AsyncSession = Depends(get_db)
):
    """Edit an existing chore."""
    redirect = check_admin_cookie(request)
    if redirect:
        return redirect

    chore_result = await db.execute(select(Chore).where(Chore.id == chore_id))
    chore = chore_result.scalar_one_or_none()
    if chore:
        chore.title = title
        chore.room = room.strip() or "General"
        chore.description = description
        chore.coin_value = coin_value
        chore.active = active
        await db.commit()
    return RedirectResponse(url=ADMIN_TABS["manage_chores"], status_code=303)


@router.post("/admin/reward/add")
async def add_reward(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    coin_cost: float = Form(0.0),
    db: AsyncSession = Depends(get_db)
):
    """Add a new reward."""
    redirect = check_admin_cookie(request)
    if redirect:
        return redirect

    reward = Reward(
        title=title,
        description=description,
        coin_cost=coin_cost,
        active=True
    )
    db.add(reward)
    await db.commit()
    return RedirectResponse(url=ADMIN_TABS["manage_rewards"], status_code=303)


@router.post("/admin/reward/delete")
async def delete_reward(
    request: Request,
    reward_id: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Delete a reward."""
    redirect = check_admin_cookie(request)
    if redirect:
        return redirect

    reward_result = await db.execute(select(Reward).where(Reward.id == reward_id))
    reward = reward_result.scalar_one_or_none()
    if reward:
        await db.delete(reward)
        await db.commit()
    return RedirectResponse(url=ADMIN_TABS["manage_rewards"], status_code=303)


@router.post("/admin/logout")
async def admin_logout(request: Request):
    """Logout admin."""
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie(key="admin_auth")
    return response
