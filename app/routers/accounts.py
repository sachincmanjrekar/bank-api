import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Account, Transaction, TransactionType, User
from app.schemas import AccountOut, AmountIn, TransactionOut
from app.security import CurrentUser

router = APIRouter(prefix="/accounts", tags=["accounts"])

DbSession = Annotated[Session, Depends(get_db)]


def generate_account_number(db: Session) -> str:
    """Random 12-digit number, retried in the (very rare) case it's already taken."""
    while True:
        number = "".join(str(secrets.randbelow(10)) for _ in range(12))
        if not db.query(Account).filter(Account.account_number == number).first():
            return number


def get_owned_account(db: Session, account_id: int, user: User, lock: bool = False) -> Account:
    """Load an account that belongs to `user`, or raise 404.

    Someone else's account also gives 404 (not 403), so users can't
    discover which account ids exist by guessing.

    lock=True locks the row until commit (SELECT ... FOR UPDATE), so two
    requests can't change the same balance at once. PostgreSQL honours it;
    SQLite ignores it (it locks the whole file on write instead).
    """
    account = db.get(Account, account_id, with_for_update=lock)
    if account is None or account.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found")
    return account


@router.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(current_user: CurrentUser, db: DbSession):
    account = Account(account_number=generate_account_number(db), owner_id=current_user.id)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("", response_model=list[AccountOut])
def list_accounts(current_user: CurrentUser, db: DbSession):
    return db.query(Account).filter(Account.owner_id == current_user.id).order_by(Account.id).all()


@router.get("/{account_id}", response_model=AccountOut)
def get_account(account_id: int, current_user: CurrentUser, db: DbSession):
    return get_owned_account(db, account_id, current_user)


@router.get("/{account_id}/transactions", response_model=list[TransactionOut])
def list_transactions(
    account_id: int,
    current_user: CurrentUser,
    db: DbSession,
    type: TransactionType | None = None,  # optional filter, e.g. ?type=deposit
    limit: Annotated[int, Query(ge=1, le=100)] = 20,  # page size, capped so nobody can ask for 1 million rows
    offset: Annotated[int, Query(ge=0)] = 0,  # how many rows to skip (page 2 = offset 20)
):
    """The account statement, newest first."""
    get_owned_account(db, account_id, current_user)  # only for the ownership check / 404

    query = db.query(Transaction).filter(Transaction.account_id == account_id)
    if type is not None:
        query = query.filter(Transaction.type == type)
    # Order by id, not created_at: rows in the same second would tie, and the order must be stable for paging.
    return query.order_by(Transaction.id.desc()).offset(offset).limit(limit).all()


@router.post(
    "/{account_id}/deposit", response_model=TransactionOut, status_code=status.HTTP_201_CREATED
)
def deposit(account_id: int, body: AmountIn, current_user: CurrentUser, db: DbSession):
    account = get_owned_account(db, account_id, current_user, lock=True)
    account.balance += body.amount
    txn = Transaction(
        account_id=account.id,
        type=TransactionType.DEPOSIT,
        amount=body.amount,
        balance_after=account.balance,
        description=body.description,
    )
    db.add(txn)
    db.commit()  # balance change and transaction row are saved together, or not at all
    db.refresh(txn)
    return txn


@router.post(
    "/{account_id}/withdraw", response_model=TransactionOut, status_code=status.HTTP_201_CREATED
)
def withdraw(account_id: int, body: AmountIn, current_user: CurrentUser, db: DbSession):
    account = get_owned_account(db, account_id, current_user, lock=True)
    if account.balance < body.amount:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Insufficient funds")
    account.balance -= body.amount
    txn = Transaction(
        account_id=account.id,
        type=TransactionType.WITHDRAWAL,
        amount=body.amount,
        balance_after=account.balance,
        description=body.description,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn
