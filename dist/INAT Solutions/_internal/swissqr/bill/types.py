from enum import Enum


class AddressType(str, Enum):
    STRUCTURED = "STRUCTURED"
    COMBINED = "COMBINED"
