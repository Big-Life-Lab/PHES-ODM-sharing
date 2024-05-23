import sys

from dataclasses import dataclass, field
from enum import EnumMeta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Union

import pandas as pd

from odm_sharing.private.stdext import StrValueEnum
from odm_sharing.private.utils import qt

RuleId = int


class RuleMode(StrValueEnum):
    SELECT = 'select'
    FILTER = 'filter'
    GROUP = 'group'
    SHARE = 'share'


class SchemaCtx:
    '''Keeps track of the current state of the parsing process. This object
    should be created at the beginning of the parsing process and its fields
    updated throughout.'''
    filename: str
    row_ix: int  # current row being parsed
    column: str  # current field being parsed

    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.row_ix = 0
        self.column = ''

    @property
    def line_num(self) -> int:
        '''line number of current row being parsed'''
        return self.row_ix + 1


@dataclass(frozen=True)
class Rule:
    '''A rule mapped from a sharing schema row'''
    id: int  # aka ruleID
    table: str
    mode: RuleMode
    key: str = field(default='')
    operator: str = field(default='')
    value: str = field(default='')


class ParseError(Exception):
    pass


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
RULE_FIELDS = set(RULE_FIELD_TYPES.keys())
HEADER_LIST_STR = ','.join(HEADERS)


def gen_error(ctx: SchemaCtx, desc: str) -> ParseError:
    '''returns a ParseError'''
    col = f',{ctx.column}' if ctx.column else ''
    msg = f'{ctx.filename}({ctx.line_num}{col}): {desc}'
    print('Error: ' + msg, file=sys.stderr)
    return ParseError(msg)


def fail(ctx: SchemaCtx, desc: str) -> None:
    '''raises a ParseError'''
    raise gen_error(ctx, desc)


def fmt_set(values: Iterable) -> str:
    '''returns a comma-separated string of the items in `values`'''
    items = ','.join(map(qt, values))
    return f'{{{items}}}'


def coerce_value(  # type: ignore
    ctx: SchemaCtx,
    type_class,
    value: str
) -> Any:
    '''converts a value from string to the specified type, using the type class
    (aka. class-constructor) for that type.

    :param type_class: str, int, MyEnum, etc.
    :raises ParseError:
    '''
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
        fail(ctx, f'got {qt(value)}, expected {expected}')


def init_rule(ctx: SchemaCtx, schema_row: dict) -> Rule:
    '''constructs a rule from a schema row, or raises list of ParseError(s)'''

    def get_field_name(column: str) -> str:
        return ('id' if column == 'ruleID' else column)

    def init_default_rule() -> Rule:
        # XXX: `mode` doesn't have a default value, but it'll be overwritten
        return Rule(id=0, table='', mode=RuleMode.SELECT)

    rule = init_default_rule()
    errors: List[ParseError] = []
    assigned_fields: Set[str] = set()
    for column, val in schema_row.items():
        if column == 'notes':
            continue
        ctx.column = column
        field = get_field_name(column)
        type_class = RULE_FIELD_TYPES[field]
        try:
            typed_val = coerce_value(ctx, type_class, val)
            object.__setattr__(rule, field, typed_val)
            assigned_fields.add(field)
        except ParseError as e:
            errors.append(e)
    assert assigned_fields == RULE_FIELDS, 'some rule fields were not set'
    if errors:
        raise ParseError(errors)
    return rule


def validate_headers(ctx: SchemaCtx, schema_headers: List[str]) -> None:
    '''validates schema headers, or raises ParseError'''
    expected = set(HEADERS)
    actual = set(schema_headers)
    missing = expected - actual
    if missing:
        msg = f'missing headers: {", ".join(missing)}'
        fail(ctx, msg)


def validate_rule(ctx: SchemaCtx, rule: Rule) -> None:
    '''checks that the rule's values are valid according to its mode, or raises
    list of ParseError(s)'''
    errors: List[ParseError] = []

    def err(msg: str) -> None:
        errors.append(gen_error(ctx, msg))

    def check_required(ctx: SchemaCtx, val: str, mode: RuleMode,
                       modes: Union[set, list]) -> None:
        if not val and mode in modes:
            err(f'{ctx.column} required for modes {fmt_set(modes)}')

    def check_set(ctx: SchemaCtx, actual: str, expected: Union[set, list]
                  ) -> None:
        if actual not in expected:
            err(f'got {qt(actual)}, expected {fmt_set(expected)}')

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
    :raises OSError, ParseError:
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
        ctx.row_ix = i + 1
        try:
            rule = init_rule(ctx, row._asdict())
            validate_rule(ctx, rule)
            result[rule.id] = rule
        except ParseError as e:
            errors.append(e)
    if errors:
        raise ParseError(errors)
    return result
