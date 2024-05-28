'''see docs/trees-algo.md'''

import sys
# from pprint import pprint

from collections import defaultdict
from dataclasses import dataclass, field
from functools import partial
from typing import Dict, List, Optional, Set, Union, cast

from functional import seq

from odm_sharing.private.common import TableName
from odm_sharing.private.stdext import StrEnum
from odm_sharing.private.utils import not_empty, qt
from odm_sharing.private.rules import (
    ParseError,
    Rule,
    RuleId,
    RuleMode,
    TABLE_MODES,
)


# {{{1 types


class Op(StrEnum):
    AND = 'and'
    EQ = '='
    GT = '>'
    GTE = '>='
    LT = '<'
    LTE = '<='
    OR = 'or'
    IN = 'in'


class NodeKind(StrEnum):
    ROOT = 'root'
    SHARE = 'share'
    TABLE = 'table'
    SELECT = 'select'
    GROUP = 'group'
    FILTER = 'filter'
    FIELD = 'field'
    LITERAL = 'literal'


@dataclass(frozen=True)
class Node:
    rule_id: RuleId
    kind: NodeKind
    str_val: str = field(default_factory=str)
    sons: list = field(default_factory=list)

    @staticmethod
    def _get_repr(node, depth: int = 0) -> str:  # type: ignore
        result = ('    ' * depth) + str(node) + '\n'
        for child in node.sons:
            result += Node._get_repr(child, depth+1)
        return result

    def __repr__(self) -> str:
        return Node._get_repr(self)

    def __str__(self) -> str:
        return f'({self.rule_id}, {self.kind}, {qt(self.str_val)})'


RuleTree = Node  # alias for a complete node tree


class Ctx:
    '''Keeps track of the current parsing process. This object should be
    created at the beginning of the parsing process and its fields updated
    throughout'''
    filename: str  # filename reference for error messages
    rule_tables: Dict[RuleId, List[str]]  # rule-table mapping
    nodes: Dict[RuleId, Node]  # collection of nodes
    root: Optional[Node]  # current tree root
    rule_id: RuleId  # current node's rule-id

    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.rule_tables = defaultdict(list)
        self.nodes = {}
        self.root = None
        self.rule_id = 0


# {{{1 constants


ALL_LIT = "all"
VAL_SEP = ";"


# {{{1 error gen


def gen_error(ctx: Ctx, desc: str) -> ParseError:
    msg = f'{ctx.filename}(rule {ctx.rule_id}): {desc}'
    print('Error: ' + msg, file=sys.stderr)
    return ParseError(msg)


def fail(ctx: Ctx, desc: str) -> None:
    raise gen_error(ctx, desc)


# {{{1 input text parsing


def parse_list(
    ctx: Ctx,
    val_str: str,
    min: int = 0,
    max: int = 0,
    sep: str = VAL_SEP,
) -> List[str]:
    '''splits a multiple-value string into a list, and validates the number of
    elements

    :param val_str: the string to parse values from
    :param min: min required number of elements, or zero
    :param max: max required number of elements, or zero
    :param sep: the value separator

    :raises ParseError
    '''
    result = seq(val_str.split(sep))\
        .map(str.strip)\
        .filter(not_empty)\
        .list()
    n = len(result)

    has_constraint = min > 0 or max > 0
    absolute = min == max
    no_max = max == 0
    in_range = min <= n <= max

    if has_constraint:
        if absolute:
            if n != min:
                fail(ctx, f'expected {min} values, got {n}')
        elif no_max:
            if n < min:
                fail(ctx, f'expected at least {min} values, got {n}')
        elif not in_range:
            fail(ctx, f'expected {min}-{max} values, got {n}')

    return result


def parse_int_list(ctx: Ctx, val_str: str,
                   min: int = 0, max: int = 0) -> List[int]:
    '''splits a multiple-value string into a list of ints, or raises
    ParseError. See `parse_list`.'''
    int_strings = parse_list(ctx, val_str, min, max)
    result = [0] * len(int_strings)
    for i, int_str in enumerate(int_strings):
        try:
            result[i] = int(int_str)
        except ValueError:
            fail(ctx, 'invalid integer {qt(int_str)} (#{i}) in value list')
    return result


def parse_mode(ctx: Ctx, mode_str: str) -> RuleMode:
    '''converts str to mode enum, or raises ParseError'''
    try:
        return RuleMode(mode_str.upper())
    except ValueError:
        raise gen_error(ctx, f'invalid mode {qt(mode_str)}')


def parse_op(op_str: str) -> Op:
    '''converts str to operator enum'''
    return Op(op_str.lower())


def parse_ctx_op(ctx: Ctx, op_str: str) -> Op:
    '''converts str to operator enum, or raises ParseError'''
    try:
        return parse_op(op_str)
    except ValueError:
        raise gen_error(ctx, f'invalid operator {qt(op_str)}')


# {{{1 ast gen


def is_filter_for_table(ctx: Ctx, table: str, node: Node) -> bool:
    '''checks if the node is of kind filter/group and if its children
    references the table'''
    assert table != ALL_LIT
    if node.kind == NodeKind.FILTER:
        return (table in ctx.rule_tables[node.rule_id])
    elif node.kind == NodeKind.GROUP:
        if node.sons:
            return is_filter_for_table(ctx, table, node.sons[0])
    return False


def get_table_select_ids(ctx: Ctx, select_nodes: List[Node]
                         ) -> Dict[TableName, RuleId]:
    '''returns mapping between tables and their select-rule ids, or raises
    ParseError'''
    # enforces only one select per table
    result: Dict[TableName, RuleId] = {}
    for node in select_nodes:
        assert node.kind == NodeKind.SELECT
        id = node.rule_id
        select_tables = ctx.rule_tables[id]
        for table in select_tables:
            if table in result:
                orig_id = result[table]
                fail(ctx, f'select-rule {id}\'s table {qt(table)} ' +
                          f'is already used by select-rule {orig_id}')
            result[table] = id
    return result


def to_literal_node(rule_id: int, val: str) -> Node:
    '''init literal-node with value'''
    return Node(rule_id=rule_id, kind=NodeKind.LITERAL, str_val=val.strip())


def to_literal_nodes(rule_id: RuleId, values: List[str]) -> List[Node]:
    '''init literal-nodes from list of values'''
    to_literal_node2 = partial(to_literal_node, rule_id)
    return seq(values).map(to_literal_node2).list()


def get_filter_root(ctx: Ctx, table: str, nodes: List[Node]) -> Optional[Node]:
    '''returns the root of the filter node tree for the table'''
    is_filter_for_table2 = partial(is_filter_for_table, ctx, table)
    filter_nodes = seq(nodes).filter(is_filter_for_table2).list()
    n = len(filter_nodes)
    if n == 0:
        return None
    elif n == 1:
        return filter_nodes[0]
    else:
        return Node(
            rule_id=0,
            kind=NodeKind.GROUP,
            str_val=Op.AND.value,
            sons=filter_nodes,
        )


def get_node(ctx: Ctx, rule_id: RuleId) -> Node:
    '''returns node generated from the rule id, or raises ParseError'''
    assert rule_id
    try:
        return ctx.nodes[rule_id]
    except KeyError:
        msg = (f'missing rule {rule_id}. ' +
               'Hint: Rules must be declared before they are referenced.')
        raise gen_error(ctx, msg)


def parse_filter_values(ctx: Ctx, op: Op, val_str: str) -> List[str]:
    if op == Op.IN:
        return parse_list(ctx, val_str, min=2, max=2)
    else:
        return [val_str]


def init_node(ctx: Ctx, rule_id: RuleId, mode: RuleMode, key: str, op_str: str,
              val_str: str) -> Node:
    '''initializes and returns a new node from rule attributes, or raises
    ParseError'''
    get_ctx_node = partial(get_node, ctx)

    if mode == RuleMode.SELECT:
        values = parse_list(ctx, val_str, 1)
        use_all = ALL_LIT in values
        to_literal_node2 = partial(to_literal_node, rule_id)
        return Node(
            rule_id=rule_id,
            kind=NodeKind.SELECT,
            str_val=(ALL_LIT if use_all else ''),
            sons=([] if use_all else seq(values).map(to_literal_node2).list()),
        )
    elif mode == RuleMode.FILTER:
        op = parse_ctx_op(ctx, op_str)
        values = parse_filter_values(ctx, op, val_str)
        field_node = Node(rule_id=rule_id, kind=NodeKind.FIELD, str_val=key)
        literal_nodes = to_literal_nodes(rule_id, values)
        return Node(
            rule_id=rule_id,
            kind=NodeKind.FILTER,
            str_val=op_str,
            sons=([field_node] + literal_nodes),
        )
    elif mode == RuleMode.GROUP:

        def not_filter_group(node: Node) -> bool:
            return node.kind not in [NodeKind.FILTER, NodeKind.GROUP]

        op = parse_ctx_op(ctx, op_str)
        if op not in [Op.AND, Op.OR]:
            fail(ctx, 'incompatible group operator')
        ids = parse_int_list(ctx, val_str, min=2)
        sons = seq(ids).map(get_ctx_node).list()
        if seq(sons).map(not_filter_group).any():
            fail(ctx, 'group-rules can only refer to other filter/group-rules')
        return Node(
            rule_id=rule_id,
            kind=NodeKind.GROUP,
            str_val=op.value,
            sons=sons,
        )
    elif mode == RuleMode.SHARE:

        def is_select(node: Node) -> bool:
            return node.kind == NodeKind.SELECT

        def init_table_node(share_value_nodes: List[Node],
                            table: str, select_id: int) -> Node:
            assert select_id
            select_node = get_ctx_node(select_id)
            filter_root = get_filter_root(ctx, table, share_value_nodes)
            return Node(
                rule_id=select_id,
                kind=NodeKind.TABLE,
                str_val=table,
                sons=([select_node] + ([filter_root] if filter_root else [])),
            )

        def init_share_node(rule_id: int, table_nodes: List[Node], org: str
                            ) -> Node:
            return Node(
                rule_id=rule_id,
                kind=NodeKind.SHARE,
                str_val=org,
                sons=table_nodes,
            )

        orgs = parse_list(ctx, key, min=1)
        ids = parse_int_list(ctx, val_str, min=1)

        # the nodes the user wants to share with the specified orgs
        share_value_nodes = seq(ids).map(get_ctx_node).list()

        select_nodes = seq(share_value_nodes).filter(is_select).list()
        table_select_ids = get_table_select_ids(ctx, select_nodes)

        init_table_node2 = partial(init_table_node, share_value_nodes)
        table_nodes = seq(table_select_ids.items())\
            .smap(init_table_node2)\
            .list()

        init_share_node2 = partial(init_share_node, rule_id, table_nodes)
        share_nodes = seq(orgs).map(init_share_node2).list()

        root_node_candidate = Node(
            rule_id=0,
            kind=NodeKind.ROOT,
            sons=share_nodes
        )
        return root_node_candidate
    else:
        assert False, 'not all cases covered'


def add_node(ctx: Ctx, rule_id: RuleId, table: str, mode: RuleMode,
             key: str, op_str: str, val_str: str) -> None:
    '''parses a rule into a tree node, and adds it to the context object

    :param ctx: the context object to update
    :param rule_id: rule id
    :param table: rule table, required for select/filter rules, otherwise empty
    :param mode: rule mode
    :param key: rule key
    :param op_str: rule operator
    :param val_str: rule value

    :raises ParseError:
    '''
    # - rule tables are recorded for later lookup
    # - new nodes are added to ctx
    # - new root nodes are also merged with ctx.root
    if table:
        ctx.rule_tables[rule_id].append(table)
    node = init_node(ctx, rule_id, table, mode, key, op_str, val_str)
    ctx.nodes[rule_id] = node
    if node.kind == NodeKind.ROOT:
        if not ctx.root:
            ctx.root = node
        else:
            ctx.root = Node(
                rule_id=0,
                kind=NodeKind.ROOT,
                sons=(ctx.root.sons+node.sons)
            )


def validate_schema(ctx: Ctx, rules: List[Rule]) -> None:
    '''checks that the required rules are present in the schema

    :raises ParseError'''
    if not seq(rules).filter(lambda x: x.mode == RuleMode.SHARE).any():
        fail(ctx, 'no share-rules in schema')
    if not seq(rules).filter(lambda x: x.mode == RuleMode.SELECT).any():
        fail(ctx, 'no select-rules in schema')


def filter_rule_orgs(ctx: Ctx, rule: Rule, org_whitelist: Set[str]) -> Rule:
    '''return a new rule with orgs filtered using whitelist'''
    assert rule.mode == RuleMode.SHARE
    rule_orgs = set(parse_list(ctx, rule.key, 1))
    new_orgs = rule_orgs & org_whitelist
    orgs_str = VAL_SEP.join(new_orgs)
    return Rule(id=rule.id, table='', mode=RuleMode.SHARE, key=orgs_str,
                value=rule.value)


def parse(rules: Union[Dict[RuleId, Rule], List[Rule]],
          orgs: List[str] = [], filename: str = '') -> RuleTree:
    '''parses rules into an abstract syntax tree

    :param rules: collection of rules to be parsed
    :param orgs: list of organization names to include, or an empty list for
        all orgs
    :param filename: the filename of the schema the rules were loaded from.
        Only used as context in error messages

    :raises ParseError:

    :return: an opaque rule-tree object for query generation
    '''
    if isinstance(rules, dict):
        rules = list(rules.values())
    org_whitelist = set(orgs)

    ctx = Ctx(filename)

    # make sure schema has the required (share and select) rules
    validate_schema(ctx, rules)

    for rule in rules:
        ctx.rule_id = rule.id

        # remove non-whitelisted orgs, skip if no orgs left
        if orgs and rule.mode == RuleMode.SHARE:
            rule = filter_rule_orgs(ctx, rule, org_whitelist)
            if not rule.key:
                continue

        min_tables = 1 if rule.mode in TABLE_MODES else 0
        tables = parse_list(ctx, rule.table, min_tables) or ['']
        for table in tables:
            add_node(ctx, rule.id, table, rule.mode, rule.key, rule.operator,
                     rule.value)
    assert ctx.root
    return cast(RuleTree, ctx.root)
