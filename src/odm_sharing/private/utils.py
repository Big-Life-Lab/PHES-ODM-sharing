from io import IOBase
from pathlib import Path
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
    items = ', '.join(values)
    return f'{{{items}}}'


def gen_output_filename(input_name: str, schema_name: str, org: str,
                        table: str, ext: str) -> str:
    parts = (([input_name] if input_name else []) +
             [schema_name, org] +
             ([table] if table else []))
    return '-'.join(parts) + f'.{ext}'


def get_filename(file: Union[str, IOBase]) -> str:
    '''returns the path filename, or a dummy name for file objects'''
    return Path(file).name if isinstance(file, str) else 'file-obj'
