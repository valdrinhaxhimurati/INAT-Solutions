from .types import AddressType
from pydantic import BaseModel


class Address(BaseModel):
    type: AddressType
    name: str
    street: str
    house_no: str
    postal_code: str
    city: str
    country: str

