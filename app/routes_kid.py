from collections import OrderedDict
from datetime import datetime, time
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.database import get_db
from app.models import Child, Chore, ChoreSubmission, DailyRoutineReset, Reward, RewardRedemption, ChoreStatus, RewardRedemptionStatus
from app.core import templates

router = APIRouter()

SWITCH_REWARD_TITLE = "request switch"
PACIFIC_TIMEZONE = ZoneInfo("America/Los_Angeles")
SWITCH_AVAILABLE_TIME = time(hour=9)
DAILY_SWITCH_REQUIREMENTS = (
    ("Brush teeth", lambda title: "teeth" in title),
    ("Eat breakfast", lambda title: "breakfast" in title),
    ("Take snack trash downstairs", lambda title: "snack" in title and "trash" in title),
)


def is_switch_reward(reward: Reward) -> bool:
    """Return whether a reward is the special daily-routine Switch request."""
    return (reward.title or "").strip().casefold() == SWITCH_REWARD_TITLE


def daily_switch_requirements(
    approved_chores: list[ChoreSubmission],
    reset_at: datetime | None = None,
) -> list[dict]:
    """Build today's approved-routine checklist for the Switch request."""
    today = datetime.now(PACIFIC_TIMEZONE).date()
    today_titles = [
        (submission.chore.title or "").casefold()
        for submission in approved_chores
        if (
            submission.submitted_at
            and submission.submitted_at.date() == today
            and (reset_at is None or submission.submitted_at > reset_at)
            and submission.chore
        )
    ]
    return [
        {"label": label, "complete": any(matches(title) for title in today_titles)}
        for label, matches in DAILY_SWITCH_REQUIREMENTS
    ]


def switch_is_available_now() -> bool:
    """Keep Switch requests unavailable before 9:00 AM Pacific time."""
    return datetime.now(PACIFIC_TIMEZONE).time() >= SWITCH_AVAILABLE_TIME


@router.get("/kid")
async def kid_dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    """Child dashboard - shows chores, rewards, and coin balance."""
    # Get or create default child
    result = await db.execute(
        select(Child).options(joinedload(Child.goal_reward))
    )
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
    daily_routine_chores = [
        {
            "label": label,
            "chore": next(
                (chore for chore in chores if matches((chore.title or "").casefold())),
                None,
            ),
        }
        for label, matches in DAILY_SWITCH_REQUIREMENTS
    ]

        # Get active rewards
    rewards_result = await db.execute(
        select(Reward)
        .where(Reward.active == True)
        .order_by(Reward.coin_cost, Reward.title)
    )
    rewards = rewards_result.scalars().all()

    switch_reward = next((reward for reward in rewards if is_switch_reward(reward)), None)
    standard_rewards = [reward for reward in rewards if not is_switch_reward(reward)]

    affordable_rewards = [
        reward for reward in standard_rewards
        if child.coins >= reward.coin_cost
    ]

    almost_rewards = [
        reward for reward in standard_rewards
        if child.coins < reward.coin_cost and reward.coin_cost - child.coins <= 25
    ]

    save_up_rewards = [
        reward for reward in standard_rewards
        if child.coins < reward.coin_cost and reward.coin_cost - child.coins > 25
    ]

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
    switch_requested = any(
        redemption.reward and is_switch_reward(redemption.reward)
        for redemption in pending_rewards
    )

        # Build automatic badges from approved chores and current coins
    approved_chores_result = await db.execute(
        select(ChoreSubmission)
        .where(ChoreSubmission.child_id == child.id)
        .where(ChoreSubmission.status == ChoreStatus.APPROVED)
        .options(selectinload(ChoreSubmission.chore))
    )
    approved_chores = approved_chores_result.scalars().all()
    daily_reset_result = await db.execute(
        select(DailyRoutineReset)
        .where(DailyRoutineReset.child_id == child.id)
        .where(DailyRoutineReset.routine_date == datetime.now(PACIFIC_TIMEZONE).date())
    )
    daily_reset = daily_reset_result.scalar_one_or_none()
    switch_requirements = daily_switch_requirements(
        approved_chores,
        daily_reset.reset_at if daily_reset else None,
    )
    switch_available = switch_is_available_now()
    switch_ready = (
        bool(switch_reward)
        and switch_available
        and not switch_requested
        and all(item["complete"] for item in switch_requirements)
    )

    approved_chore_count = len(approved_chores)
    bathroom_count = sum(
        1 for submission in approved_chores
        if submission.chore and (submission.chore.room or "").lower() == "bathroom"
    )
    toy_count = sum(
        1 for submission in approved_chores
        if submission.chore and "toy" in (submission.chore.title or "").lower()
    )
    teeth_count = sum(
        1 for submission in approved_chores
        if submission.chore and "teeth" in (submission.chore.title or "").lower()
    )
    sock_count = sum(
        1 for submission in approved_chores
        if submission.chore and "sock" in (submission.chore.title or "").lower()
    )
    plant_count = sum(
        1 for submission in approved_chores
        if submission.chore and "plant" in (submission.chore.title or "").lower()
    )

    badges = []

    if approved_chore_count >= 1:
        badges.append({
            "icon": "⭐",
            "title": "First Chore",
            "description": "Completed your first approved chore."
        })

    if approved_chore_count >= 10:
        badges.append({
            "icon": "🏆",
            "title": "10 Chores Complete",
            "description": "Completed 10 approved chores."
        })

    if child.coins >= 100:
        badges.append({
            "icon": "💰",
            "title": "100 Coin Club",
            "description": "Saved up 100 coins."
        })

    if bathroom_count >= 5:
        badges.append({
            "icon": "🧼",
            "title": "Bathroom Helper",
            "description": "Completed 5 bathroom chores."
        })

    if toy_count >= 5:
        badges.append({
            "icon": "🧸",
            "title": "Toy Tamer",
            "description": "Completed 5 toy chores."
        })

    if teeth_count >= 5:
        badges.append({
            "icon": "🦷",
            "title": "Toothbrush Champion",
            "description": "Brushed teeth 5 approved times."
        })

    if sock_count >= 5:
        badges.append({
            "icon": "🧦",
            "title": "Sock Hunter",
            "description": "Found lots of socks."
        })

    if plant_count >= 3:
        badges.append({
            "icon": "🌱",
            "title": "Plant Helper",
            "description": "Helped water plants 3 times."
        })

    locked_badges = [
        {
            "icon": "❓",
            "title": "Mystery Badge",
            "description": "Keep doing chores to unlock this."
        },
        {
            "icon": "🔥",
            "title": "Rage Clean Jr.",
            "description": "A special helper badge."
        },
        {
            "icon": "🐉",
            "title": "Dragon Level 1",
            "description": "Keep leveling up."
        }
    ]

    goal_reward = child.goal_reward if child and child.goal_reward and child.goal_reward.active else None
    goal_progress_percent = 0

    if goal_reward and goal_reward.coin_cost > 0:
        goal_progress_percent = min(100, int((child.coins / goal_reward.coin_cost) * 100))

    return templates.TemplateResponse("kid_dashboard.html", {
        "request": request,
        "child": child,
        "chores": chores,
        "chore_groups": chore_groups,
        "daily_routine_chores": daily_routine_chores,
        "rewards": rewards,
        "affordable_rewards": affordable_rewards,
        "almost_rewards": almost_rewards,
        "save_up_rewards": save_up_rewards,
        "goal_reward": goal_reward,
        "goal_progress_percent": goal_progress_percent,
        "badges": badges,
        "locked_badges": locked_badges,
        "pending_chores": pending_chores,
        "pending_rewards": pending_rewards,
        "game_tickets": child.game_tickets or 0,
        "treasure_high_score": child.treasure_high_score or 0,
        "switch_reward": switch_reward,
        "switch_requirements": switch_requirements,
        "switch_ready": switch_ready,
        "switch_requested": switch_requested,
        "switch_available": switch_available,
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


@router.post("/kid/game/start")
async def start_game(db: AsyncSession = Depends(get_db)):
    """Spend one approval-earned play pass to launch a game round."""
    result = await db.execute(select(Child))
    child = result.scalar_one_or_none()

    if not child or (child.game_tickets or 0) < 1:
        return RedirectResponse(url="/kid?tab=games", status_code=303)

    child.game_tickets -= 1
    await db.commit()
    return RedirectResponse(url="/kid?tab=games&play=1", status_code=303)


@router.post("/kid/game/treasure-score")
async def save_treasure_score(
    score: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Keep each child's best Treasure Dash score."""
    result = await db.execute(select(Child))
    child = result.scalar_one_or_none()
    if not child:
        return JSONResponse({"high_score": 0, "is_new_high_score": False})

    safe_score = max(0, min(score, 999))
    previous_high_score = child.treasure_high_score or 0
    is_new_high_score = safe_score > previous_high_score
    if is_new_high_score:
        child.treasure_high_score = safe_score
        await db.commit()

    return JSONResponse({
        "high_score": child.treasure_high_score or 0,
        "is_new_high_score": is_new_high_score,
    })

@router.post("/kid/reward/goal")
async def set_reward_goal(
    reward_id: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Set a reward as the child's current saving goal."""
    result = await db.execute(select(Child))
    child = result.scalar_one_or_none()

    if not child:
        child = Child(name="Child", coins=0.0)
        db.add(child)
        await db.commit()
        await db.refresh(child)

    reward_result = await db.execute(
        select(Reward)
        .where(Reward.id == reward_id)
        .where(Reward.active == True)
    )
    reward = reward_result.scalar_one_or_none()

    if reward:
        child.goal_reward_id = reward.id
        await db.commit()

    return RedirectResponse(url="/kid?tab=rewards", status_code=303)


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

    if is_switch_reward(reward):
        if not switch_is_available_now():
            return RedirectResponse(url="/kid", status_code=303)

        existing_request_result = await db.execute(
            select(RewardRedemption.id)
            .where(RewardRedemption.child_id == child.id)
            .where(RewardRedemption.reward_id == reward.id)
            .where(RewardRedemption.status == RewardRedemptionStatus.PENDING)
            .limit(1)
        )
        if existing_request_result.scalar_one_or_none() is not None:
            return RedirectResponse(url="/kid", status_code=303)

        approved_result = await db.execute(
            select(ChoreSubmission)
            .where(ChoreSubmission.child_id == child.id)
            .where(ChoreSubmission.status == ChoreStatus.APPROVED)
            .options(selectinload(ChoreSubmission.chore))
        )
        daily_reset_result = await db.execute(
            select(DailyRoutineReset)
            .where(DailyRoutineReset.child_id == child.id)
            .where(DailyRoutineReset.routine_date == datetime.now(PACIFIC_TIMEZONE).date())
        )
        daily_reset = daily_reset_result.scalar_one_or_none()
        if not all(
            item["complete"]
            for item in daily_switch_requirements(
                approved_result.scalars().all(),
                daily_reset.reset_at if daily_reset else None,
            )
        ):
            return RedirectResponse(url="/kid?tab=rewards", status_code=303)
    # Standard rewards require enough coins. The Switch request is always free.
    elif child.coins < reward.coin_cost:
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
