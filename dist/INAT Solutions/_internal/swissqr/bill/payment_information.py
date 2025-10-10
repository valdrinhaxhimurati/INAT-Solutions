from pydantic import BaseModel
from typing import Optional
from .address import Address


class PaymentInformation(BaseModel):
    iban: str
    creditor: Address
    currency: str
    amount: float
    reference: Optional[str] = None
    unstructured_message: Optional[str] = None
