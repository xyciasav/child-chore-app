from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import (
    Child, Chore, ChoreSubmission, Reward, RewardRedemption,
    ChoreStatus, RewardRedemptionStatus
)
from app.schemas import (
    Child as ChildSchema,
    Chore as ChoreSchema,
    ChoreSubmission as ChoreSubmissionSchema,
    Reward as RewardSchema,
    RewardRedemption as RewardRedemptionSchema,
)

router = APIRouter(prefix="/api", tags=["API"])


# =============================================================================
# Home Assistant Integration Points
# =============================================================================
# These endpoints are designed to be consumed by Home Assistant REST sensors.
# They return clean JSON with no authentication (for local network use).
#
# To expand later:
# - Add API key authentication via header
# - Add WebSocket support for real-time updates
# - Add MQTT integration for Home Assistant
# - Add REST command endpoints to trigger actions from HA automations
# =============================================================================


@router.get("/children")
async def get_children(db: AsyncSession = Depends(get_db)):
    """Get all children with their coin balances."""
    result = await db.execute(select(Child))
    children = result.scalars().all()
    return [ChildSchema.model_validate(child) for child in children]


@router.get("/children/{child_id}/balance")
async def get_child_balance(child_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get a specific child's coin balance.
    
    Home Assistant REST sensor example:
    ```yaml
    - platform: rest
      resource: http://localhost:8000/api/children/1/balance
      value_template: '{{ value_json.coins }}'
      json_attributes:
        - name
        - coins
    ```
    """
    result = await db.execute(select(Child).where(Child.id == child_id))
    child = result.scalar_one_or_none()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    return {"name": child.name, "coins": child.coins}


@router.get("/chores")
async def get_chores(db: AsyncSession = Depends(get_db)):
    """Get all active chores."""
    result = await db.execute(select(Chore).where(Chore.active == True))
    chores = result.scalars().all()
    return [ChoreSchema.model_validate(chore) for chore in chores]


@router.get("/chores/pending")
async def get_pending_chore_submissions(db: AsyncSession = Depends(get_db)):
    """
    Get all pending chore submissions.
    
    Home Assistant REST sensor example:
    ```yaml
    - platform: rest
      resource: http://localhost:8000/api/chores/pending
      value_template: '{{ value_json | length }}'
      json_attributes: true
    ```
    """
    result = await db.execute(
        select(ChoreSubmission)
        .where(ChoreSubmission.status == ChoreStatus.PENDING)
        .options(
            selectinload(ChoreSubmission.child),
            selectinload(ChoreSubmission.chore)
        )
    )
    submissions = result.scalars().all()
    return [
        {
            "id": sub.id,
            "child_name": sub.child.name,
            "chore_title": sub.chore.title,
            "coin_value": sub.chore.coin_value,
            "submitted_at": sub.submitted_at.isoformat(),
        }
        for sub in submissions
    ]


@router.get("/chores/history")
async def get_chore_history(db: AsyncSession = Depends(get_db)):
    """Get all approved/denied chore submissions (completed history)."""
    result = await db.execute(
        select(ChoreSubmission)
        .where(ChoreSubmission.status != ChoreStatus.PENDING)
        .options(
            selectinload(ChoreSubmission.child),
            selectinload(ChoreSubmission.chore)
        )
    )
    submissions = result.scalars().all()
    return [
        {
            "id": sub.id,
            "child_name": sub.child.name,
            "chore_title": sub.chore.title,
            "status": sub.status.value,
            "reviewed_at": sub.reviewed_at.isoformat() if sub.reviewed_at else None,
        }
        for sub in submissions
    ]


@router.get("/rewards")
async def get_rewards(db: AsyncSession = Depends(get_db)):
    """Get all active rewards."""
    result = await db.execute(select(Reward).where(Reward.active == True))
    rewards = result.scalars().all()
    return [RewardSchema.model_validate(reward) for reward in rewards]


@router.get("/rewards/pending")
async def get_pending_reward_redemptions(db: AsyncSession = Depends(get_db)):
    """
    Get all pending reward redemption requests.
    
    Home Assistant REST sensor example:
    ```yaml
    - platform: rest
      resource: http://localhost:8000/api/rewards/pending
      value_template: '{{ value_json | length }}'
      json_attributes: true
    ```
    """
    result = await db.execute(
        select(RewardRedemption)
        .where(RewardRedemption.status == RewardRedemptionStatus.PENDING)
        .options(
            selectinload(RewardRedemption.child),
            selectinload(RewardRedemption.reward)
        )
    )
    redemptions = result.scalars().all()
    return [
        {
            "id": red.id,
            "child_name": red.child.name,
            "reward_title": red.reward.title,
            "coin_cost": red.reward.coin_cost,
            "requested_at": red.requested_at.isoformat(),
        }
        for red in redemptions
    ]


@router.get("/rewards/history")
async def get_reward_history(db: AsyncSession = Depends(get_db)):
    """Get all approved/denied reward redemptions (completed history)."""
    result = await db.execute(
        select(RewardRedemption)
        .where(RewardRedemption.status != RewardRedemptionStatus.PENDING)
        .options(
            selectinload(RewardRedemption.child),
            selectinload(RewardRedemption.reward)
        )
    )
    redemptions = result.scalars().all()
    return [
        {
            "id": red.id,
            "child_name": red.child.name,
            "reward_title": red.reward.title,
            "status": red.status.value,
            "reviewed_at": red.reviewed_at.isoformat() if red.reviewed_at else None,
        }
        for red in redemptions
    ]


@router.get("/summary")
async def get_summary(db: AsyncSession = Depends(get_db)):
    """
    Get a summary of all data.
    
    Useful for Home Assistant to get an overview in a single request.
    """
    # Get first child (MVP: single child)
    child_result = await db.execute(select(Child))
    child = child_result.scalar_one_or_none()

    # Get pending counts
    pending_chores = await db.execute(
        select(ChoreSubmission).where(ChoreSubmission.status == ChoreStatus.PENDING)
    )
    pending_chore_count = len(pending_chores.scalars().all())

    pending_rewards = await db.execute(
        select(RewardRedemption).where(RewardRedemption.status == RewardRedemptionStatus.PENDING)
    )
    pending_reward_count = len(pending_rewards.scalars().all())

    return {
        "child": {
            "name": child.name if child else "No child",
            "coins": child.coins if child else 0,
            "game_tickets": child.game_tickets if child else 0,
        } if child else None,
        "pending_approvals": {
            "chores": pending_chore_count,
            "rewards": pending_reward_count,
        },
    }
