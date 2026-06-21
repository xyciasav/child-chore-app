from fastapi import APIRouter, Request, Form, Depends, UploadFile, File
from fastapi.responses import RedirectResponse, JSONResponse
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
import json
router = APIRouter()

ADMIN_TABS = {
    "pending_chores": "/admin?tab=pending-chores",
    "manage_chores": "/admin?tab=manage-chores",
    "pending_rewards": "/admin?tab=pending-rewards",
    "manage_rewards": "/admin?tab=manage-rewards",
    "children": "/admin?tab=children",
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
    submission.child.game_tickets += 1

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
    # The daily Switch request is earned through its routine, never paid with coins.
    if (redemption.reward.title or "").strip().casefold() != "request switch":
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
    """Archive a chore so existing submission history remains intact."""
    redirect = check_admin_cookie(request)
    if redirect:
        return redirect

    chore_result = await db.execute(select(Chore).where(Chore.id == chore_id))
    chore = chore_result.scalar_one_or_none()
    if chore:
        chore.active = False
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

@router.post("/admin/reward/edit")
async def edit_reward(
    request: Request,
    reward_id: int = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    coin_cost: float = Form(0.0),
    active: bool = Form(False),
    db: AsyncSession = Depends(get_db)
):
    """Edit an existing reward."""
    redirect = check_admin_cookie(request)
    if redirect:
        return redirect

    reward_result = await db.execute(select(Reward).where(Reward.id == reward_id))
    reward = reward_result.scalar_one_or_none()

    if reward:
        reward.title = title
        reward.description = description
        reward.coin_cost = coin_cost
        reward.active = active
        await db.commit()

    return RedirectResponse(url=ADMIN_TABS["manage_rewards"], status_code=303)

@router.post("/admin/reward/delete")
async def delete_reward(
    request: Request,
    reward_id: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Archive a reward so existing redemption history remains intact."""
    redirect = check_admin_cookie(request)
    if redirect:
        return redirect

    reward_result = await db.execute(select(Reward).where(Reward.id == reward_id))
    reward = reward_result.scalar_one_or_none()
    if reward:
        reward.active = False
        await db.commit()
    return RedirectResponse(url=ADMIN_TABS["manage_rewards"], status_code=303)


@router.post("/admin/child/name")
async def update_child_name(
    request: Request,
    name: str = Form(...),
    child_id: int = Form(0),
    db: AsyncSession = Depends(get_db)
):
    """Create or update a child display name."""
    redirect = check_admin_cookie(request)
    if redirect:
        return redirect

    clean_name = name.strip() or "Child"
    child = None
    if child_id:
        child_result = await db.execute(select(Child).where(Child.id == child_id))
        child = child_result.scalar_one_or_none()

    if not child:
        child_result = await db.execute(select(Child))
        child = child_result.scalar_one_or_none()

    if child:
        child.name = clean_name
    else:
        db.add(Child(name=clean_name, coins=0.0))
    await db.commit()
    return RedirectResponse(url=ADMIN_TABS["children"], status_code=303)

@router.get("/admin/export")
async def export_admin_data(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Export chores and rewards as JSON."""
    redirect = check_admin_cookie(request)
    if redirect:
        return redirect

    chores_result = await db.execute(select(Chore).order_by(Chore.room, Chore.title))
    chores = chores_result.scalars().all()

    rewards_result = await db.execute(select(Reward).order_by(Reward.title))
    rewards = rewards_result.scalars().all()

    data = {
        "version": 1,
        "exported_at": datetime.utcnow().isoformat(),
        "chores": [
            {
                "title": chore.title,
                "room": chore.room or "General",
                "description": chore.description or "",
                "coin_value": chore.coin_value,
                "active": chore.active,
            }
            for chore in chores
        ],
        "rewards": [
            {
                "title": reward.title,
                "description": reward.description or "",
                "coin_cost": reward.coin_cost,
                "active": reward.active,
            }
            for reward in rewards
        ],
    }

    return JSONResponse(
        content=data,
        headers={
            "Content-Disposition": 'attachment; filename="chore-tracker-backup.json"'
        }
    )


@router.post("/admin/import")
async def import_admin_data(
    request: Request,
    backup_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Import chores and rewards from exported JSON."""
    redirect = check_admin_cookie(request)
    if redirect:
        return redirect

    try:
        raw = await backup_file.read()
        data = json.loads(raw.decode("utf-8"))
    except Exception:
        return RedirectResponse(url="/admin?tab=children", status_code=303)

    chores_data = data.get("chores", [])
    rewards_data = data.get("rewards", [])

    existing_chores_result = await db.execute(select(Chore))
    existing_chores = existing_chores_result.scalars().all()
    chores_by_key = {
        ((chore.title or "").strip().lower(), (chore.room or "General").strip().lower()): chore
        for chore in existing_chores
    }

    for item in chores_data:
        title = str(item.get("title", "")).strip()
        room = str(item.get("room", "General")).strip() or "General"

        if not title:
            continue

        key = (title.lower(), room.lower())
        chore = chores_by_key.get(key)

        if chore:
            chore.description = str(item.get("description", ""))
            chore.coin_value = float(item.get("coin_value", 1.0))
            chore.active = bool(item.get("active", True))
        else:
            db.add(Chore(
                title=title,
                room=room,
                description=str(item.get("description", "")),
                coin_value=float(item.get("coin_value", 1.0)),
                active=bool(item.get("active", True)),
            ))

    existing_rewards_result = await db.execute(select(Reward))
    existing_rewards = existing_rewards_result.scalars().all()
    rewards_by_key = {
        (reward.title or "").strip().lower(): reward
        for reward in existing_rewards
    }

    for item in rewards_data:
        title = str(item.get("title", "")).strip()

        if not title:
            continue

        key = title.lower()
        reward = rewards_by_key.get(key)

        if reward:
            reward.description = str(item.get("description", ""))
            reward.coin_cost = float(item.get("coin_cost", 1.0))
            reward.active = bool(item.get("active", True))
        else:
            db.add(Reward(
                title=title,
                description=str(item.get("description", "")),
                coin_cost=float(item.get("coin_cost", 1.0)),
                active=bool(item.get("active", True)),
            ))

    await db.commit()
    return RedirectResponse(url=ADMIN_TABS["children"], status_code=303)


@router.post("/admin/coins/reset")
async def reset_all_coins(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Reset all child coin balances to zero."""
    redirect = check_admin_cookie(request)
    if redirect:
        return redirect

    children_result = await db.execute(select(Child))
    children = children_result.scalars().all()

    for child in children:
        child.coins = 0.0

    await db.commit()
    return RedirectResponse(url=ADMIN_TABS["children"], status_code=303)


@router.post("/admin/coins/award")
async def award_coins(
    request: Request,
    child_id: int = Form(...),
    amount: float = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Give a child bonus coins for something outside the chore list."""
    redirect = check_admin_cookie(request)
    if redirect:
        return redirect

    child_result = await db.execute(select(Child).where(Child.id == child_id))
    child = child_result.scalar_one_or_none()
    if child and amount > 0:
        child.coins += amount
        await db.commit()

    return RedirectResponse(url=ADMIN_TABS["children"], status_code=303)

@router.post("/admin/logout")
async def admin_logout(request: Request):
    """Logout admin."""
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie(key="admin_auth")
    return response
