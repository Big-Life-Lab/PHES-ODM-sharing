'''python standard library extensions'''

from enum import Enum


class StrEnum(str, Enum):
    '''shim for python < 3.11

    Provides a ``__str__()`` function that returns the enum string-value, which
    is useful for printing the value or comparing it with another string.

    See https://docs.python.org/3.11/library/enum.html#enum.StrEnum
    '''
    pass


class StrValueEnum(StrEnum):
    '''extension of `StrEnum` that makes it look cleaner with pprint'''
    def __repr__(self) -> str:
        return self.value


def sorted_dict(d: dict) -> dict:
    '''sorts a dict so that the keys are in sorted order'''
    return {k: d[k] for k in sorted(d.keys())}
