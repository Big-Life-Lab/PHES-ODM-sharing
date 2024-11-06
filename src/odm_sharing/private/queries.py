from collections import defaultdict
from dataclasses import dataclass, field
from functools import partial
from typing import Dict, List, Tuple
# from pprint import pprint

from functional import seq

from odm_sharing.private.common import OrgName, TableName
from odm_sharing.private.rules import RuleId
from odm_sharing.private.stdext import StrEnum, sorted_dict
from odm_sharing.private.utils import dqt

from odm_sharing.private.trees import (
    ALL_LIT,
    Node,
    NodeKind,
    Op,
    ParseError,
    RangeKind,
    RuleTree,
    parse_op,
)


Sql = str
SqlArgs = List[str]


class SqlDialect(StrEnum):
    OTHER = ''
    MSSQL = 'mssql'
    SYBASE = 'sybase'


@dataclass(frozen=True)
class Query:
    sql: Sql
    args: SqlArgs = field(default_factory=list)


PartialQuery = Query  # incomplete query


@dataclass(frozen=True)
class TableQuery:
    '''collection of queries for a single table'''
    table_name: str

    columns: List[str]
    '''columns specified in the select-rule (unless "all" is used), which can
    be used instead of querying the columns using `get_column_sql`'''

    data_query: Query
    rule_count_queries: Dict[RuleId, Query]
    select_rule_id: RuleId
    _select_query: Query


OrgTableQueries = Dict[OrgName, Dict[TableName, TableQuery]]


def ident(x: str) -> str:
    '''make a sanitized/quoted sql identifier

    :raises ParseError:
    '''
    # Double-quotes should be used as the delimiter for column-name
    # identifiers. (https://stackoverflow.com/a/2901499)
    #
    # It should be enough to simply disallow double-quotes in the name.
    if '"' in x:
        raise ParseError('the following column-name contains double-quotes, ' +
                         f'which is not allowed: \'{x}\'')
    return dqt(x)


def convert(val: str) -> str:
    '''convert to sql equivalent value'''
    norm_val = val.lower()
    if norm_val == 'true':
        return '1'
    elif norm_val == 'false':
        return '0'
    else:
        return val


def gen_data_sql(
    node: Node,
    args: SqlArgs,
    rule_queries: Dict[RuleId, PartialQuery],
) -> Sql:
    '''recursive helper function of ``gen_data_query``

    :param node: should be a table-node in the outer call for a complete query
    to be generated, but it'll also work on any node in the table-subtree.
    :param args: (output) sql arguments
    :param rule_queries: (output) see ``gen_data_query``

    :raises ParseError:
    '''

    def recurse(node: Node) -> str:
        return gen_data_sql(node, args, rule_queries)

    def record(node: Node, sql: str, args: SqlArgs) -> None:
        '''associate (partial) sql query with node's rule'''
        assert node.kind in [NodeKind.TABLE, NodeKind.FILTER, NodeKind.GROUP]
        rule_queries[node.rule_id] = PartialQuery(sql=sql, args=args)

    n = node
    if n.kind == NodeKind.TABLE:
        # table has a select followed by an optional filter/group
        table = n.str_val
        select = n.sons[0]
        filter_root = n.sons[1] if len(n.sons) > 1 else None
        select_sql = f'SELECT {recurse(select)} FROM {ident(table)}'
        filter_sql = f'WHERE {recurse(filter_root)}' if filter_root else ''
        record(n, select_sql, [])
        return (select_sql + ' ' + filter_sql)
    elif n.kind == NodeKind.SELECT:
        # select has an all-value or fields as children
        if n.str_val == ALL_LIT:
            return '*'
        else:
            columns = seq(n.sons).map(lambda x: ident(x.str_val))
            return ','.join(columns)
    elif n.kind == NodeKind.GROUP:
        # group combines any number of children with its operator
        op_str = n.str_val.upper()
        assert op_str in ['AND', 'OR']
        arg_start = len(args)
        sql = seq(n.sons)\
            .map(recurse)\
            .reduce(lambda x, y: f'({x} {op_str} {y})')
        record(n, sql, args[arg_start:])
        return sql
    elif n.kind == NodeKind.FILTER:
        # filter has op as value, children define field, kind and literals
        op = parse_op(n.str_val)
        key_ident = recurse(n.sons[0])

        def gen_range_sql(range_kind: RangeKind, values: List[str]) -> str:
            '''generates sql for a range of values'''
            if range_kind == RangeKind.INTERVAL:
                a = values[0]
                b = values[1]
                return f'({key_ident} BETWEEN {a} AND {b})'
            elif range_kind == RangeKind.SET:
                return f"({key_ident} IN ({','.join(values)}))"
            else:
                assert False, 'unreachable'

        if op == Op.RANGE:
            range_kind = RangeKind(n.sons[1].str_val)
            literals: List[str] = seq(n.sons[2:]).map(recurse).list()
            sql = gen_range_sql(range_kind, literals)
            record(n, sql, args[-len(literals):])
            return sql
        else:
            val = recurse(n.sons[1])
            sql = f'({key_ident} {op} {val})'
            record(n, sql, args[-1:])
            return sql
    elif n.kind == NodeKind.FIELD:
        return ident(n.str_val)
    elif n.kind == NodeKind.LITERAL:
        # literal value is converted and added to list of args, while only a
        # parameter placeholder is added to the sql
        val = convert(n.str_val)
        args.append(val)
        return '?'
    else:
        assert False, 'unreachable'
        return ''


def gen_data_query(
    table_node: Node,
    rule_queries: Dict[RuleId, PartialQuery],
) -> Query:
    '''generates sql from a node-tree

    :param root_node: the root-node of the tree to generate sql from
    :param rule_queries: (output) partial filter and select queries

    :return: complete query

    :raises ParseError:
    '''
    args: List[str] = []
    sql = gen_data_sql(table_node, args, rule_queries)
    return Query(sql=sql, args=args)


def get_table_node_columns(table_node: Node) -> List[str]:
    '''returns the column-values of a select-node of a table-node'''
    assert table_node.kind == NodeKind.TABLE
    select_node = table_node.sons[0]
    assert select_node.kind == NodeKind.SELECT
    return seq(select_node.sons).map(lambda x: x.str_val).list()


def parse_sql_dialect(dialect_str: str) -> SqlDialect:
    '''parse dialect str to enum value, or fall back to default'''
    try:
        return SqlDialect(dialect_str.lower())
    except ValueError:
        return SqlDialect.OTHER


def get_share_query(
    table_node: Node,
    rule_queries: Dict[RuleId, PartialQuery]
) -> Query:
    '''returns the complete query associated with a table-node (belonging to a
    share-node)'''
    # if a zero-rule exist (which is an implicit top-level AND-group) then use
    # it, otherwise, if the table-node has a filter/group-node then use it,
    # otherwise, use the table-node's select-node
    if 0 in rule_queries:
        return rule_queries[0]
    else:
        if len(table_node.sons) == 1:
            select_node = table_node.sons[0]
            assert select_node.kind == NodeKind.SELECT
            return rule_queries[select_node.rule_id]
        else:
            filter_root = table_node.sons[1]
            assert filter_root.kind in [NodeKind.FILTER, NodeKind.GROUP]
            return rule_queries[filter_root.rule_id]


def gen_count_query_sql(
    table: str,
    rule_id: int,
    filter_query: PartialQuery,
) -> Tuple[RuleId, Query]:
    '''generate count query for table from partial filter query

    :raises ParseError:
    '''
    sql = (
        f'SELECT COUNT(*) FROM {ident(table)}' +
        (f' WHERE {filter_query.sql}' if filter_query.sql else '')
    )
    return (rule_id, Query(sql=sql, args=filter_query.args))


def gen_table_query(share_node: Node, table_node: Node) -> TableQuery:
    '''generates a table-query for a specific table node of a share node

    :raises ParseError:
    '''
    assert share_node.kind == NodeKind.SHARE
    assert table_node.kind == NodeKind.TABLE
    assert table_node in share_node.sons

    # generate complete sql and partial rule queries
    rule_queries: Dict[RuleId, PartialQuery] = {}
    data_query = gen_data_query(table_node, rule_queries)

    select_node = table_node.sons[0]
    assert select_node.kind == NodeKind.SELECT
    select_id = select_node.rule_id

    # save select query and replace with an empty partial query so that we'll
    # get a count-query without a filter for the select rule
    select_query = rule_queries[select_id]
    no_filter_query = PartialQuery(sql='')
    rule_queries[select_id] = no_filter_query

    # add share-rule to partial queries so that it'll be included in the count
    share_id = share_node.rule_id
    assert share_id not in rule_queries
    rule_queries[share_id] = get_share_query(table_node, rule_queries)

    # generate count queries, making sure sure they're sorted to retain rule
    # order for the user
    gen_count_query_sql2 = partial(gen_count_query_sql, table_node.str_val)
    count_queries = sorted_dict(
        seq(rule_queries.items()).smap(gen_count_query_sql2).dict())

    return TableQuery(
        table_name=table_node.str_val,
        data_query=data_query,
        rule_count_queries=count_queries,
        select_rule_id=select_id,
        columns=get_table_node_columns(table_node),
        _select_query=select_query,
    )


def generate(rule_tree: RuleTree) -> OrgTableQueries:
    '''generate queries from a rule tree

    :param rule_tree: the tree to generate queries from

    :return: query-objects for each org and table

    :raises ParseError:
    '''

    def gen_table_query_entry(share_node: Node, table_node: Node
                              ) -> Tuple[TableName, TableQuery]:
        table_name = table_node.str_val
        table_query = gen_table_query(share_node, table_node)
        return (table_name, table_query)

    result: OrgTableQueries = defaultdict(dict)
    root: Node = rule_tree
    assert root.kind == NodeKind.ROOT
    for share in root.sons:
        assert share.kind == NodeKind.SHARE
        org = share.str_val
        table_nodes = seq(share.sons)
        gen_table_query_entry2 = partial(gen_table_query_entry, share)
        result[org] = table_nodes.map(gen_table_query_entry2).dict()
    return result


def gen_column_sql(select_sql: Sql, dialect: SqlDialect) -> Sql:
    '''returns an sql statement that selects zero rows of data, but gives the
    column names'''
    if dialect in [SqlDialect.MSSQL, SqlDialect.SYBASE]:
        return 'SELECT TOP 0 ' + select_sql[len('SELECT '):]
    else:
        return select_sql + ' LIMIT 0'


def get_column_sql(q: TableQuery, dialect: SqlDialect) -> Sql:
    '''returns sql for querying actual colums, for when columns are not
    pre-specified'''
    # XXX: this query is generated on demand due to dependency on sql dialect,
    # which we want to keep separate from query generation to keep modularity
    return gen_column_sql(q._select_query.sql, dialect)
