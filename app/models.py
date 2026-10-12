import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Money is stored as an exact decimal with 2 places, never as a float:
# 0.1 + 0.2 == 0.30000000000000004 in floating point.
Money = Numeric(12, 2)

# IDs are BIGINT because Aurora DSQL's auto-numbering (identity columns) only
# supports BIGINT. SQLite only auto-numbers a column declared exactly INTEGER,
# hence the variant.
Id = BigInteger().with_variant(Integer, "sqlite")


def id_column() -> Mapped[int]:
    # CACHE 1: DSQL requires CACHE to be 1 or >= 65536; 1 keeps numbers close to
    # creation order, which suits account/reference numbers.
    return mapped_column(Id, Identity(cache=1), primary_key=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = id_column()
    # unique=True becomes a UNIQUE constraint inside CREATE TABLE (DSQL can't
    # build a separate index synchronously).
    email: Mapped[str] = mapped_column(String(255), unique=True)
    full_name: Mapped[str] = mapped_column(String(100))
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    accounts: Mapped[list["Account"]] = relationship(back_populates="owner")


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = id_column()
    account_number: Mapped[str] = mapped_column(String(20), unique=True)
    owner_id: Mapped[int] = mapped_column(Id, ForeignKey("users.id"))
    balance: Mapped[Decimal] = mapped_column(Money, default=Decimal("0.00"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner: Mapped[User] = relationship(back_populates="accounts")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="account")


class TransactionType(enum.StrEnum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"


class Transaction(Base):
    """One row per money movement: the account's audit trail / statement."""

    __tablename__ = "transactions"

    id: Mapped[int] = id_column()
    account_id: Mapped[int] = mapped_column(Id, ForeignKey("accounts.id"), index=True)
    # native_enum=False: stored as VARCHAR, because DSQL has no CREATE TYPE.
    # Python still only accepts the four TransactionType values.
    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, native_enum=False, length=20)
    )
    amount: Mapped[Decimal] = mapped_column(Money)
    balance_after: Mapped[Decimal] = mapped_column(Money)
    description: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    account: Mapped[Account] = relationship(back_populates="transactions")
