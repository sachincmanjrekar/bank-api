from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Account, Transaction, TransactionType
from app.routers.accounts import get_owned_account
from app.schemas import TransactionOut, TransferIn
from app.security import CurrentUser

router = APIRouter(prefix="/transfers", tags=["transfers"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transfer(body: TransferIn, current_user: CurrentUser, db: DbSession):
    source = get_owned_account(db, body.from_account_id, current_user)
    destination = (
        db.query(Account).filter(Account.account_number == body.to_account_number).first()
    )
    if destination is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Destination account not found")
    if destination.id == source.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot transfer to the same account")

    # Lock both rows, always in id order. If two transfers run A->B and B->A at the
    # same time and each locked "its" source first, each would wait for the other
    # forever (a deadlock). A fixed order makes the second one simply wait its turn.
    # populate_existing=True re-reads the balance now that we hold the lock.
    for account_id in sorted([source.id, destination.id]):
        db.get(Account, account_id, with_for_update=True, populate_existing=True)

    if source.balance < body.amount:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Insufficient funds")

    source.balance -= body.amount
    destination.balance += body.amount

    debit = Transaction(
        account_id=source.id,
        type=TransactionType.TRANSFER_OUT,
        amount=body.amount,
        balance_after=source.balance,
        description=body.description or f"Transfer to {destination.account_number}",
    )
    credit = Transaction(
        account_id=destination.id,
        type=TransactionType.TRANSFER_IN,
        amount=body.amount,
        balance_after=destination.balance,
        description=body.description or f"Transfer from {source.account_number}",
    )
    db.add_all([debit, credit])
    db.commit()  # both balances + both rows saved together, or nothing is
    db.refresh(debit)

    # Only the sender's side goes back: the receiver's balance is none of their business.
    return debit
