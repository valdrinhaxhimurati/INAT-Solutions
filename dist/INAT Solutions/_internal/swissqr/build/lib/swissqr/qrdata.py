from pydantic import field_validator, ConfigDict, BaseModel, model_validator
from enum import Enum
from typing import Union, Optional
from iso4217 import Currency
from pyban.iban import IBAN

from swissqr import PaymentParty, StandardViolation, AddressType


class ReferenceType(Enum):
    QRR = "QRR",
    SCOR = "SCOR",
    NON = "NON"


class QRData(BaseModel):
    # Mandatory fields
    iban: Union[IBAN, str]
    creditor: PaymentParty
    # Optional fields
    amount: Optional[float] = None
    currency: Union[Currency, str] = Currency.chf
    ultimate_debitor: PaymentParty = PaymentParty.get_empty()
    reference_type: ReferenceType = ReferenceType.NON
    reference: str = ""
    message: str = ""
    # Fixed fields
    qr_type: str = "SPC"
    version: str = "0200"
    coding_type: int = 1  # 1: utf8
    ultimate_creditor: PaymentParty = PaymentParty.get_empty()  # Empty, reserved for future use,
    trailer: str = "EPD"
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("qr_type")
    @classmethod
    def _validate_qr_type(cls, v: str):
        if v != "SPC":
            raise StandardViolation('QRType header must be "SPC"')
        return v

    @field_validator("version")
    @classmethod
    def _validate_version(cls, v: str):
        if v[:2] != "02":
            raise NotImplementedError("Only Version 2 is currently supported")
        if v[2:] != "00":
            raise StandardViolation("Version 2 does not allow sub-versioning")
        return v

    @field_validator("coding_type")
    @classmethod
    def _validate_coding_type(cls, v: int):
        if v != 1:
            raise StandardViolation("Coding type must be 1 (meaning UTF-8)")
        return v

    @field_validator("iban")
    @classmethod
    def _validate_iban(cls, v: Union[IBAN, str]):
        v = IBAN(v)
        if v.iban[:2] not in ["CH", "LI"]:
            raise StandardViolation("Standard only allows for IBANs with a CH or LI country code.")
        return v

    @field_validator("creditor")
    @classmethod
    def _validate_creditor(cls, v: PaymentParty):
        if v.address_type == AddressType.EMPTY:
            raise StandardViolation("Creditor address type must not be empty")
        return v

    @field_validator("ultimate_creditor")
    @classmethod
    def _validate_ultimate_creditor(cls, v: PaymentParty):
        if v != PaymentParty.get_empty():
            raise StandardViolation("Ultimate creditor must be empty (reserved for future use)")
        return v

    @field_validator("amount")
    @classmethod
    def _validate_amount(cls, v: Union[float, str]):
        if v is None:
            return v
        v = float(v)
        if not (0.01 <= v <= 999999999.99):
            raise StandardViolation("Payment amount is out of allowed range")
        return round(v, 2)

    @field_validator("currency")
    @classmethod
    def _validate_currency(cls, v: Union[str, Currency]):
        if isinstance(v, str):
            v = Currency(v.upper())
        if v not in [Currency.chf, Currency.eur]:
            raise StandardViolation("Standard allows only CHF or EURO")
        return v

    @model_validator(mode="before")
    @classmethod
    def _check_reference(cls, values):
        reftype, reference = values.get('reference_type'), values.get("reference")
        if reftype == ReferenceType.NON and reference != "":
            raise StandardViolation("Reference must be empty for type NON")
        if reftype == ReferenceType.QRR:
            if len(reference) != 27:
                raise StandardViolation("QR Reference must have a length of exactly 27")
            if not reference.isnumeric():
                raise StandardViolation("QR Reference must be numeric")
        # TODO: Mod10 Validation
        if reftype == ReferenceType.SCOR:
            if not (5 <= len(reference) <= 25):
                raise StandardViolation("SCOR Reference must be between 5 and 25 chars long")
            if not reference.isalnum():
                raise StandardViolation("SCOR Reference must be alphanumeric")
        # TODO: Mod97 Validation
        return values

    @field_validator("message")
    @classmethod
    def _validate_message(cls, v: str):
        if len(v) > 140:
            raise StandardViolation("Unstructured message must not be longer than 140 chars")
        return v

    @field_validator("trailer")
    @classmethod
    def _validate_trailer(cls, v: str):
        if v != "EPD":
            raise StandardViolation('Trailer string must be "EPD"')
        return v

    def __str__(self):
        if self.amount is None:
            amount_string = ""
        else:
            amount_string = "{:.2f}".format(self.amount)
        elements = [
            self.qr_type,
            self.version,
            str(self.coding_type),
            self.iban.iban,
            str(self.creditor),
            str(self.ultimate_creditor),
            amount_string,
            self.currency.code,
            str(self.ultimate_debitor),
            self.reference_type.value,
            self.reference,
            self.message,
            self.trailer
        ]
        return "\r\n".join(elements)
