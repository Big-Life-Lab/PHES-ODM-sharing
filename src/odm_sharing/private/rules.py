import sys

from dataclasses import dataclass
from enum import Enum, EnumMeta
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
    pass


class SchemaCtx:
    filename: str
    row: int  # zero-indexed
    column: str

    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.row = 0
        self.column = ''

    @property
    def line(self) -> int:
        return self.row + 1


@dataclass(init=False)
class Rule:
    # XXX: should be immutable, but then we can't initialize it in a clean and
    # dynamic way
    id: int
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
    col = f',{ctx.column}' if ctx.column else ''
    msg = f'{ctx.filename}({ctx.line}{col}): {desc}'
    print('Error: ' + msg, file=sys.stderr)
    return ParseError(msg)


def fail(ctx: SchemaCtx, desc: str) -> None:
    raise gen_error(ctx, desc)


def prevalidate_row(ctx: SchemaCtx, row: dict) -> None:
    # called before coercing, can't coerce empty values
    # only for non-str columns tho, maybe normalize this into something else

    # ruleID
    col = 'ruleID'
    if row[col] == '':
        ctx.column = col
        fail(ctx, 'missing value')


def quote(x: str) -> str:
    return f"'{x}'"


def fmt_set(values: Iterable) -> str:
    items = ','.join(map(quote, values))
    return f'{{{items}}}'


def coerce_value(  # type: ignore
    ctx: SchemaCtx,
    type_class,
    column: str,
    val: str
) -> Any:
    '''coerce value and validate type'''
    try:
        typed_val = (type_class)(val)
        return typed_val
    except ValueError:

        def get_expected(type_class) -> str:  # type: ignore
            name = type_class.__name__
            if type(type_class) is EnumMeta:
                return fmt_set(list(type_class))
            else:
                return name

        expected = get_expected(type_class)
        fail(ctx, f'got {quote(val)}, expected {expected}')


def init_rule(ctx: SchemaCtx, row: dict) -> Rule:
    '''construct rule and coerce/validate value types'''

    def get_field_name(column: str) -> str:
        return ('id' if column == 'ruleID' else column)

    result = Rule()
    prevalidate_row(ctx, row)
    errors: List[ParseError] = []
    for column, val in row.items():
        if column == 'notes':
            continue
        ctx.column = column
        field = get_field_name(column)
        type_class = RULE_FIELD_TYPES[field]
        try:
            typed_val = coerce_value(ctx, type_class, column, val)
            result.__setattr__(field, typed_val)
        except ParseError as e:
            errors.append(e)
    if errors:
        raise ParseError(errors)
    return result


def validate_headers(ctx: SchemaCtx, schema_headers: List[str]) -> None:
    errors: List[ParseError] = []

    # header count
    expected_len = len(HEADERS)
    actual_len = len(schema_headers)
    if actual_len != expected_len:
        msg = (
            f'got {actual_len} headers, ' +
            f'expected {expected_len} ({HEADER_LIST_STR})')
        errors.append(gen_error(ctx, msg))

    # header names
    for i, header in enumerate(schema_headers):
        expected = HEADERS[i]
        actual = schema_headers[i]
        if actual != expected:
            msg = (
                f'got header name {quote(actual)} ' +
                f'for column #{i+1}, ' +
                f'expected {quote(expected)}')
            errors.append(gen_error(ctx, msg))

    if errors:
        raise ParseError(errors)


def validate_rule(ctx: SchemaCtx, rule: Rule) -> None:
    # called after constructing rule with typed fields

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
    ctx = SchemaCtx(schema_path)
    data = pd.read_csv(schema_path)
    data.fillna('', inplace=True)  # replace NA values with empty string

    # XXX: header errors are not catched, to avoid error propagation
    validate_headers(ctx, data.columns.to_list())

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
