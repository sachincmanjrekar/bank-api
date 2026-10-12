from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """What the client sends to register."""

    email: EmailStr
    full_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    """What we send back about a user. Deliberately has no password field."""

    model_config = ConfigDict(from_attributes=True)  # allows building it from a SQLAlchemy object

    id: int
    email: EmailStr
    full_name: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AccountOut(BaseModel):
    """What we send back about a bank account."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    account_number: str
    balance: Decimal  # sent as a string like "0.00" in JSON, so no float rounding
    created_at: datetime
