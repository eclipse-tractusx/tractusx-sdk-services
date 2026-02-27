from enum import Enum, auto

class UnsupportedRevision(Exception):
    """Raise for an invalid standard revision"""

class StandardRevision(Enum):
    """This serves as an indicator for the current standard revision used"""
    JUPITER = auto()
    SATURN  = auto()
