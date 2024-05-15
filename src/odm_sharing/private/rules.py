import sys

from dataclasses import dataclass
from enum import Enum, EnumMeta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Union

import pandas as pd

RuleId = int


class RuleMode(str, Enum):
    SELECT = 'select'
    FILTER = 'filter'
    GROUP = 'group'
    SHARE = 'share'

    def __repr__(self) -> str:
        return self.value


class ParseError(Exception):
    '''schema parsing error'''
    pass


class SchemaCtx:
    '''Keeps track of the current state of the parsing process. This object
    should be created at the beginning of the parsing process and its fields
    updated throughout.'''
    filename: str
    row: int  # current row being parsed
    column: str  # current field being parsed

    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.row = 0
        self.column = ''

    @property
    def line(self) -> int:
        '''line number of current row being parsed'''
        return self.row + 1


@dataclass(init=False)
class Rule:
    '''A rule mapped from a sharing schema row'''
    # XXX: should be immutable, but then we can't initialize it in a clean and
    # dynamic way
    id: int  # aka ruleID
    table: str
    mode: RuleMode
    key: str
    operator: str
    value: str


HEADERS = [
    'ruleID',
    'table',
    'mode',
    'key',
    'operator',
    'value',
    'notes',
]

FILTER_OPERATORS = set([
    '<',
    '<=',
    '=',
    '>',
    '>=',
    'in',
])

ALL_MODES = set(RuleMode)
GROUP_OPERATORS = set(['AND', 'OR'])
RULE_FIELD_TYPES = Rule.__annotations__
HEADER_LIST_STR = ','.join(HEADERS)


def gen_error(ctx: SchemaCtx, desc: str) -> ParseError:
    '''returns a ParseError'''
    col = f',{ctx.column}' if ctx.column else ''
    msg = f'{ctx.filename}({ctx.line}{col}): {desc}'
    print('Error: ' + msg, file=sys.stderr)
    return ParseError(msg)


def fail(ctx: SchemaCtx, desc: str) -> None:
    '''raises a ParseError'''
    raise gen_error(ctx, desc)


def quote(x: str) -> str:
    return f"'{x}'"


def fmt_set(values: Iterable) -> str:
    '''returns a comma-separated string of the items in `values`'''
    items = ','.join(map(quote, values))
    return f'{{{items}}}'


def coerce_value(  # type: ignore
    ctx: SchemaCtx,
    type_class,
    value: str
) -> Any:
    '''converts a value to the specified type, or fails'''
    try:
        typed_val = type_class(value)
        return typed_val
    except ValueError:

        def get_expected(type_class) -> str:  # type: ignore
            if type(type_class) is EnumMeta:
                return fmt_set(list(type_class))
            else:
                return type_class.__name__

        expected = get_expected(type_class)
        fail(ctx, f'got {quote(value)}, expected {expected}')


def init_rule(ctx: SchemaCtx, schema_row: dict) -> Rule:
    '''constructs a rule from a schema row, or fails with list of errors'''

    def get_field_name(column: str) -> str:
        return ('id' if column == 'ruleID' else column)

    result = Rule()
    errors: List[ParseError] = []
    for column, val in schema_row.items():
        if column == 'notes':
            continue
        ctx.column = column
        field = get_field_name(column)
        type_class = RULE_FIELD_TYPES[field]
        try:
            typed_val = coerce_value(ctx, type_class, val)
            result.__setattr__(field, typed_val)
        except ParseError as e:
            errors.append(e)
    if errors:
        raise ParseError(errors)
    return result


def validate_headers(ctx: SchemaCtx, schema_headers: List[str]) -> None:
    '''validates schema headers, or fails'''
    expected = set(HEADERS)
    actual = set(schema_headers)
    missing = expected - actual
    if missing:
        msg = f'missing headers: {", ".join(missing)}'
        fail(ctx, msg)


def validate_rule(ctx: SchemaCtx, rule: Rule) -> None:
    '''checks that the rule's values are valid according to its mode, or fails
    with a list of errors'''
    errors: List[ParseError] = []

    def check_required(ctx: SchemaCtx, val: str, mode: RuleMode,
                       modes: Union[set, list]) -> None:
        if not val and mode in modes:
            msg = f'{ctx.column} required for modes {fmt_set(modes)}'
            errors.append(gen_error(ctx, msg))

    def check_set(ctx: SchemaCtx, actual: str, expected: Union[set, list]
                  ) -> None:
        if actual not in expected:
            msg = f'got {quote(actual)}, expected {fmt_set(expected)}'
            errors.append(gen_error(ctx, msg))

    ctx.column = 'table'
    check_required(ctx, rule.table, rule.mode,
                   [RuleMode.SELECT, RuleMode.FILTER])

    ctx.column = 'key'
    check_required(ctx, rule.key, rule.mode,
                   [RuleMode.FILTER, RuleMode.SHARE])

    ctx.column = 'operator'
    check_required(ctx, rule.operator, rule.mode,
                   [RuleMode.FILTER, RuleMode.GROUP])
    if rule.operator:
        if rule.mode == RuleMode.FILTER:
            check_set(ctx, rule.operator, FILTER_OPERATORS)
        elif rule.mode == RuleMode.GROUP:
            check_set(ctx, rule.operator, GROUP_OPERATORS)

    ctx.column = 'value'
    check_required(ctx, rule.value, rule.mode, ALL_MODES)

    if errors:
        raise ParseError(errors)


def load(schema_path: str) -> Dict[RuleId, Rule]:
    '''loads a sharing schema

    :returns: rules parsed from schema, by rule id
    :raises ParseError:
    '''
    filename = Path(schema_path).name
    ctx = SchemaCtx(filename)
    data = pd.read_csv(schema_path)
    data.fillna('', inplace=True)  # replace NA values with empty string

    # XXX: loading is aborted on header errors since row-parsing depends on it
    validate_headers(ctx, data.columns.to_list())

    # iterate dataset and parse each row into a sharing rule obj
    result: Dict[RuleId, Rule] = {}
    errors: List[ParseError] = []
    for i, row in enumerate(data.itertuples(index=False)):
        ctx.row = i + 1
        try:
            rule = init_rule(ctx, row._asdict())
            validate_rule(ctx, rule)
            result[rule.id] = rule
        except ParseError as e:
            errors.append(e)
    if errors:
        raise ParseError(errors)
    return result
