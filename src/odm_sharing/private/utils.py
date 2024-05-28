from typing import Iterable, Union


def qt(x: str) -> str:
    '''quote `x`'''
    return f"'{x}'"


def dqt(x: str) -> str:
    '''double-quote `x`'''
    return f"\"{x}\""


def not_empty(x: Union[list, set, str]) -> bool:
    return len(x) > 0


def fmt_set(values: Iterable) -> str:
    '''returns a comma-separated string of the items in `values`, surrounded by
    curly-brackets'''
    items = ','.join(map(qt, values))
    return f'{{{items}}}'
