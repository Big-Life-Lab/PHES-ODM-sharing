from pathlib import Path
from typing import Dict, List, Tuple

import pandas
from functional import seq

import odm_sharing.private.cons as cons
import odm_sharing.private.queries as queries
import odm_sharing.private.rules as rules
import odm_sharing.private.trees as trees
from odm_sharing.private.common import ColumnName, OrgName, TableName
from odm_sharing.private.cons import Connection
from odm_sharing.private.queries import OrgTableQueries, Query, TableQuery
from odm_sharing.private.rules import RuleId


def parse(schema_path: str, orgs: List[str] = []) -> OrgTableQueries:
    '''loads and parses a schema file into query objects

    :param schema_path: schema filepath
    :param orgs: organization whitelist, disabled if empty

    :return: a query per table per org. `OrgName` and `TableName` are
        strings.
    :rtype: Dict[OrgName, Dict[TableName, TableQuery]]

    :raises OSError: if the schema file can't be loaded
    :raises ParseError: if the schema parsing fails
    '''
    ruleset = rules.load(schema_path)
    filename = Path(schema_path).name
    tree = trees.parse(ruleset, orgs, filename)
    return queries.generate(tree)


def connect(data_source: str, tables: List[str] = []) -> Connection:
    '''
    creates a connection to a data source that later can be used with a query
    to retrieve data

    :param data_source: filepath or database URL
    :param tables: table name whitelist, disabled if empty

    :return: the data source connection object

    :raises DataSourceError: if the connection couldn't be established
    '''
    return cons.connect(data_source, set(tables))


def get_data(c: Connection, tq: TableQuery) -> pandas.DataFrame:
    '''retrieves filtered data from a specific table of a data source

    :param c: the data source connection
    :param tq: the table query

    :return: the resulting (filtered) dataset

    :raises DataSourceError: if an error occured while retrieving data
    '''
    dq = tq.data_query
    return cons.exec(c, dq.sql, dq.args)


def get_counts(c: Connection, tq: TableQuery) -> Dict[RuleId, int]:
    '''gives the row count of the query for each rule

    :param c: connection
    :param tq: table query

    :return: the row count for each rule. `RuleId` is an integer.

    :raises DataSourceError: if an error occured while counting rows
    '''
    def get_rule_count(rule_id: RuleId, q: Query) -> Tuple[RuleId, int]:
        count = int(cons.exec(c, q.sql, q.args).iat[0, 0])
        return (rule_id, count)

    return seq(tq.rule_count_queries.items()).smap(get_rule_count).dict()


def get_columns(c: Connection, tq: TableQuery
                ) -> Tuple[RuleId, List[ColumnName]]:
    '''gives the column names of a query

    :param c: connection
    :param tq: table query

    :return: the select-rule's ID, and the list of column names
    associated with it. `RuleId` is an integer, and `ColumnName` is a string.

    :raises DataSourceError: if an error occured while retrieving the column
    names
    '''
    if tq.columns:
        return (tq.select_rule_id, tq.columns)
    else:
        dialect = queries.parse_sql_dialect(cons.get_dialect_name(c))
        sql = queries.get_column_sql(tq, dialect)
        columns = cons.exec(c, sql).columns.array.tolist()
        return (tq.select_rule_id, columns)


def extract(
    schema_path: str,
    data_source: str,
    orgs: List[str] = [],
) -> Dict[OrgName, Dict[TableName, pandas.DataFrame]]:
    '''high-level function for retrieving filtered data

    :param schema_path: rule schema filepath
    :param data_source: filepath or database URL
    :param orgs: organization whitelist, disabled if empty

    :return: a dataset per table per org. `OrgName` and `TableName` are
    strings.

    :raises DataSourceError: if an error occured while extracting data from the
    data source
    '''
    con = connect(data_source)
    queries = parse(schema_path, orgs)
    result: Dict[OrgName, Dict[TableName, pandas.DataFrame]] = {}
    for org, tablequeries in queries.items():
        result[org] = {}
        for table, query in tablequeries.items():
            result[org][table] = get_data(con, query)
    return result
