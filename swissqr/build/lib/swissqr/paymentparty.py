from enum import Enum
import pycountry
from copy import copy
from pydantic import field_validator, BaseModel, model_validator

from swissqr import StandardViolation


class AddressType(Enum):
    EMPTY = ""
    S = "S"
    K = "K"


class PaymentParty(BaseModel):
    name: str
    street: str = ""
    street_no: str = ""
    addrline1: str = ""
    addrline2: str = ""
    zipcode: str = ""
    city: str = ""
    country: str
    address_type: AddressType = AddressType.S  # S: structured address, more compatible with NF1

    @classmethod
    def get_empty(cls):
        return cls(name="", street="", street_no="", zipcode="", city="", country="", address_type=AddressType.EMPTY)

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if len(v) > 70:
            raise StandardViolation("Name must be shorter than 71 chars")
        return v

    @field_validator("street")
    @classmethod
    def validate_street(cls, v: str):
        if len(v) > 70:
            raise StandardViolation("Street must be shorter than 71 chars")
        return v

    @field_validator("street_no")
    @classmethod
    def validate_street_no(cls, v: str):
        if len(v) > 16:
            raise StandardViolation("Street number must be shorter than 17 chars")
        return v

    @field_validator("addrline1")
    @classmethod
    def validate_addrline1(cls, v: str):
        if len(v) > 70:
            raise StandardViolation("Address line 1 must be shorter than 71 chars")
        return v

    @field_validator("addrline2")
    @classmethod
    def validate_addrline2(cls, v: str):
        if len(v) > 70:
            raise StandardViolation("Address line 2 must be shorter than 71 chars")
        return v

    @field_validator("zipcode")
    @classmethod
    def validate_zipcode(cls, v):
        if len(v) > 16:
            raise StandardViolation("Zip code must be shorter than 17 chars")
        # TODO: How to check if country code is NOT in zip code? A lot of countries use alphanumeric zip codes...
        return v

    @field_validator("city")
    @classmethod
    def validate_city(cls, v):
        if len(v) > 35:
            raise StandardViolation("City must be shorter than 36 chars")
        return v

    @field_validator("country", mode="before")
    @classmethod
    def validate_country(cls, v):
        v = v.upper()
        if v != "":
            country = pycountry.countries.get(alpha_2=v)
            if country is None:
                raise StandardViolation("Country code unknown")
        return v

    @model_validator(mode="before")
    @classmethod
    def validate_type_based(self, values):
        addrtype = values.get("address_type")
        if addrtype == AddressType.EMPTY:
            checkval = copy(values)
            checkval["address_type"] = addrtype.value
            for k, v in checkval.items():
                if v != "":
                    raise StandardViolation('Payment party of empty type must contain only empty strings')
            return values
        if values.get("name") == "":
            raise StandardViolation('Non-empty payment party must contain a name')
        if values.get("country") == "":
            raise StandardViolation('Non-empty payment party must contain a country')
        if addrtype == AddressType.S:
            if values.get("zipcode") == "":
                raise StandardViolation('Address of type S must contain a zip code')
            if values.get("city") == "":
                raise StandardViolation('Address of type S must contain a city')
        if addrtype == AddressType.K:
            if values.get("addrline2") == "":
                raise StandardViolation('Address of type K must contain addrline2 (containing zip code and city name)')
            if not values.get("zipcode") == "":
                raise StandardViolation('Address of type K must not contain a zip code (belongs into addrline2)')
            if not values.get("city") == "":
                raise StandardViolation('Address of type K must not contain a city name (belongs into addrline2)')

        return values

    def __str__(self):
        if self.address_type == AddressType.K:
            elements = [
                self.address_type.value,
                self.name,
                self.addrline1,
                self.addrline2,
                self.zipcode,
                self.city,
                self.country
            ]
        else:
            elements = [
                self.address_type.value,
                self.name,
                self.street,
                self.street_no,
                self.zipcode,
                self.city,
                self.country
            ]
        return "\r\n".join(elements)

