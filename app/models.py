from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, relationship
import enum


class Base(DeclarativeBase):
    pass


class ChoreStatus(str, enum.Enum):
    """Status of a chore submission."""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


class RewardRedemptionStatus(str, enum.Enum):
    """Status of a reward redemption request."""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


class Child(Base):
    """Child profile - supports multiple children in the future."""
    __tablename__ = "children"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    coins = Column(Float, default=0.0)
    goal_reward_id = Column(Integer, ForeignKey("rewards.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    chore_submissions = relationship("ChoreSubmission", back_populates="child")
    reward_redemptions = relationship("RewardRedemption", back_populates="child")
    goal_reward = relationship("Reward", foreign_keys=[goal_reward_id])


class Chore(Base):
    """A chore that can be assigned to children."""
    __tablename__ = "chores"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    room = Column(String(100), nullable=False, default="General")
    description = Column(String(500), default="")
    coin_value = Column(Float, default=1.0)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    submissions = relationship("ChoreSubmission", back_populates="chore")


class ChoreSubmission(Base):
    """A child submitting a completed chore for approval."""
    __tablename__ = "chore_submissions"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=False)
    chore_id = Column(Integer, ForeignKey("chores.id"), nullable=False)
    status = Column(SAEnum(ChoreStatus), default=ChoreStatus.PENDING)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)

    # Relationships
    child = relationship("Child", back_populates="chore_submissions")
    chore = relationship("Chore", back_populates="submissions")


class Reward(Base):
    """A reward that children can redeem with coins."""
    __tablename__ = "rewards"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(String(500), default="")
    coin_cost = Column(Float, default=0.0)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    redemptions = relationship("RewardRedemption", back_populates="reward")


class RewardRedemption(Base):
    """A child requesting to redeem a reward."""
    __tablename__ = "reward_redemptions"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=False)
    reward_id = Column(Integer, ForeignKey("rewards.id"), nullable=False)
    status = Column(SAEnum(RewardRedemptionStatus), default=RewardRedemptionStatus.PENDING)
    requested_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)

    # Relationships
    child = relationship("Child", back_populates="reward_redemptions")
    reward = relationship("Reward", back_populates="redemptions")
