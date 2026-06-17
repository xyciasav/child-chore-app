from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# --- Child Schemas ---
class ChildBase(BaseModel):
    name: str
    coins: float = 0.0


class ChildCreate(ChildBase):
    pass


class ChildUpdate(BaseModel):
    name: Optional[str] = None
    coins: Optional[float] = None


class Child(ChildBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- Chore Schemas ---
class ChoreBase(BaseModel):
    title: str
    room: str = "General"
    description: str = ""
    coin_value: float = 1.0
    active: bool = True


class ChoreCreate(ChoreBase):
    pass


class ChoreUpdate(BaseModel):
    title: Optional[str] = None
    room: Optional[str] = None
    description: Optional[str] = None
    coin_value: Optional[float] = None
    active: Optional[bool] = None


class Chore(ChoreBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- Chore Submission Schemas ---
class ChoreSubmissionBase(BaseModel):
    status: str


class ChoreSubmission(ChoreSubmissionBase):
    id: int
    child_id: int
    chore_id: int
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Reward Schemas ---
class RewardBase(BaseModel):
    title: str
    description: str = ""
    coin_cost: float = 0.0
    active: bool = True


class RewardCreate(RewardBase):
    pass


class RewardUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    coin_cost: Optional[float] = None
    active: Optional[bool] = None


class Reward(RewardBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- Reward Redemption Schemas ---
class RewardRedemptionBase(BaseModel):
    status: str


class RewardRedemption(RewardRedemptionBase):
    id: int
    child_id: int
    reward_id: int
    requested_at: datetime
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
