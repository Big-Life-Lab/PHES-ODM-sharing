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
    '''The error when parsing a sharing schema file'''
    pass


class SchemaCtx:
    '''Keeps track of the current state of the parsing process. This object 
    should be created at the beginning of the parsing process and its fields 
    updated throughout.'''

    filename: str
    '''The path of the schema file being parsed. This is the path as passed in 
    by the user.'''

    row: int  # zero-indexed
    '''The current row being parsed'''

    column: str
    '''The current column being parsed within the current row'''

    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.row = 0
        self.column = ''

    @property
    def line(self) -> int:
        '''Increments the current row being parsed'''
        return self.row + 1


@dataclass(init=False)
class Rule:
    '''A sharing rule'''
    # XXX: should be immutable, but then we can't initialize it in a clean and
    # dynamic way
    id: int
    '''The unique ID of the rule. This is mapped to the ruleId column in the 
    sharing schema file'''
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
    '''Creates a ParseError
    
    Parameters:
        ctx (SchemaCtx): The context object for the current parsing process
        desc (str): A human readable description for the error

    Returns:
        ParseError
    '''

    col = f',{ctx.column}' if ctx.column else ''
    msg = f'{ctx.filename}({ctx.line}{col}): {desc}'
    print('Error: ' + msg, file=sys.stderr)
    return ParseError(msg)


def fail(ctx: SchemaCtx, desc: str) -> None:
    '''Create and throw an error encountered during the parsing process 
    Parameters:
        ctx (SchemaCtx): The context object for the current parsing process 
        desc (str): A human readable description of the error


    Returns:
        None

    Raises:
        ParseError: The error that is created
    '''
    raise gen_error(ctx, desc)


def quote(x: str) -> str:
    return f"'{x}'"


def fmt_set(values: Iterable) -> str:
    '''Formats the values in an iterable as a single string separated by commas
    
    Parameters:
        values (Iterable): The iterable to format

    Returns:
        str: The formatted string
    '''
    items = ','.join(map(quote, values))
    return f'{{{items}}}'


def coerce_value(  # type: ignore
    ctx: SchemaCtx,
    type_class,
    column: str,
    val: str
) -> Any:
    '''coerce value and validate type of a column

    Parameters:
        ctx (SchemaCtx): The context object for the current parsing process
        type_class: The expected type of the column. This should be a value 
                    from the dictionary returned by the `get_annotations`
                    function.
        column (str): The name of the column
        val (str): The column value

    Returns: 
        The coerced value 

    Raises:
        ParseError: When the column value cannot be coerced
    '''
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
    '''construct rule and coerce/validate value types.
    
    Parameters:
        ctx (SchemaCtx): The context object for the current parsing process
        row (dict): The row of the sharing schema file to parse

    Returns:
        Rule: The created rule

    Raises:
        ParseError: When a column(s) cannot be coerced into its type
    '''

    def get_field_name(column: str) -> str:
        return ('id' if column == 'ruleID' else column)

    result = Rule()
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
    '''Checks the columns in a sharing schema file. The only check done is 
    whether the expected columns have been found in the file. 

    Parameters:
        ctx (SchemaCtx): The context object for the current parsing process
        schema_headers (List[str]): The list of columns in the schema file

    Returns:
        None

    Raises:
        ParseError: If the check fails
    '''

    expected = set(HEADERS)
    actual = set(schema_headers)
    missing = expected - actual
    if missing:
        msg = f'missing headers: {", ".join(missing)}'
        fail(ctx, msg)


def validate_rule(ctx: SchemaCtx, rule: Rule) -> None:
    '''Validates a rule object throwing a ParseError if validation fails. 

    Validates the following:

    1. The table column is not missing for a FILTER and SELECT rule
    2. The key column is not missing for a FILTER and SHARE rule
    3. The operator column is not missing for a FILTER and GROUP rule 
    4. The operator column has the right values depending on the rule mode
    5. The value column is not missing

    Parameters:
        ctx (SchemaCtx): The context object for the current parsing process
        rule (Rule): The rule object to validate

    Returns:
        None

    Raises:
        ParseError: When the validation fails
    '''
    # called after constructing rule with typed fields

    errors: List[ParseError] = []

    def check_required(ctx: SchemaCtx, val: str, mode: RuleMode,
                       modes: Union[set, list]) -> None:
    '''Validates that a column value in a row is not missing based on the mode 
    for that row. For example, the table column is mandatory when the mode is 
    SELECT or FILTER. If validation is found then a ParseError is added to the 
    list of errors.

    Parameters:
        ctx (SchemaCtx): The context object for the current parsing process
        val (str): The column value to validate
        mode (RuleMode): The mode for the column value
        modes (Union[set, list]): The list of modes for which the column should 
                                  not have a missing value

    Returns: 
        None
    '''
        if not val and mode in modes:
            msg = f'{ctx.column} required for modes {fmt_set(modes)}'
            errors.append(gen_error(ctx, msg))

    def check_set(ctx: SchemaCtx, actual: str, expected: Union[set, list]
                  ) -> None:
    '''Checks if a column value is one of the expected values. If the check 
    fails then a ParseError is added to the list of errors.

    Parameters:
        ctx (SchemaCtx): The context object for the current parsing process
        actual (str): The column value to check
        expected (Union[set, list]): The list of values the column value can 
                                     take
    
    Returns:
        None
    '''
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
    '''Converts a sharing schema CSV file into a format used by other functions 
    in the library

    Parameters:
        schema_path (str): The file path of the sharing schema file to convert

    Returns:
        Dict[RuleId, Rule]: A dictionary where each field is ID of the rule and 
                            the value is the corresponding rule

    Raises:
        ParseError: If the file parsing failed
    '''
    ctx = SchemaCtx(schema_path)
    data = pd.read_csv(schema_path)
    data.fillna('', inplace=True)  # replace NA values with empty string

    # XXX: header errors are not catched, to avoid error propagation
    validate_headers(ctx, data.columns.to_list())

    # Iterate through each row in the schema file creating the dictonary of rule 
    # objects and list of errors encountered during the creation
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
