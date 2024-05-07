from typing import Union


def qt(x: str) -> str:
    '''quote `x`'''
    return f"'{x}'"


def not_empty(x: Union[list, set, str]) -> bool:
    return len(x) > 0
