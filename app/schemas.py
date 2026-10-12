from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import TransactionType


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


class AmountIn(BaseModel):
    """What the client sends to deposit or withdraw."""

    # gt=0: no zero or negative amounts. decimal_places=2: no fractions of a paisa/cent.
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    description: str | None = Field(default=None, max_length=255)


class TransferIn(AmountIn):
    """What the client sends to transfer money. Inherits amount + description."""

    from_account_id: int  # must be one of your own accounts
    to_account_number: str = Field(pattern=r"^\d{12}$")  # anyone's account, like a real payee


class TransactionOut(BaseModel):
    """One line of an account's statement."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    type: TransactionType
    amount: Decimal
    balance_after: Decimal
    description: str | None
    created_at: datetime
