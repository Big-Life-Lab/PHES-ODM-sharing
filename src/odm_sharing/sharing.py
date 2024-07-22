from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
from functional import seq

import odm_sharing.private.cons as cons
import odm_sharing.private.queries as queries
import odm_sharing.private.rules as rules
import odm_sharing.private.trees as trees
from odm_sharing.private.common import OrgName, TableName
from odm_sharing.private.cons import Connection
from odm_sharing.private.queries import OrgTableQueries, Query, TableQuery
from odm_sharing.private.rules import RuleId


ColumnName = str


def parse(schema_path: str, orgs: List[str] = []) -> OrgTableQueries:
    '''returns queries for each org and table, generated from the rules
    specified in `schema_file`

    :raises OSError, ParseError:
    '''
    ruleset = rules.load(schema_path)
    filename = Path(schema_path).name
    tree = trees.parse(ruleset, orgs, filename)
    return queries.generate(tree)


def connect(data_source: str, tables: List[str] = []) -> Connection:
    '''returns a connection object that can be used together with a query
    object to retrieve data from `data_source`

    :raises DataSourceError:'''
    return cons.connect(data_source, set(tables))


def get_data(c: Connection, tq: TableQuery) -> pd.DataFrame:
    '''returns the data extracted from running query `q` on data-source
    connection `c`, as a pandas DataFrame

    :raises DataSourceError:'''
    dq = tq.data_query
    return cons.exec(c, dq.sql, dq.args)


def get_counts(c: Connection, tq: TableQuery) -> Dict[RuleId, int]:
    '''returns the row counts for each rule

    :raises DataSourceError:'''

    def get_rule_count(rule_id: RuleId, q: Query) -> Tuple[RuleId, int]:
        count = int(cons.exec(c, q.sql, q.args).iat[0, 0])
        return (rule_id, count)

    return seq(tq.rule_count_queries.items()).smap(get_rule_count).dict()


def get_columns(c: Connection, tq: TableQuery
                ) -> Tuple[RuleId, List[ColumnName]]:
    '''returns the select-rule id together with the column names that would be
    extracted when calling `get_data`

    :raises DataSourceError:'''
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
) -> Dict[OrgName, Dict[TableName, pd.DataFrame]]:
    '''returns a Pandas DataFrame per table per org

    :param data_source: a file path or database url (in SQLAlchemy format)
    :param schema_path: rule schema file path
    :param orgs: orgs to share with, or all if empty

    :raises DataSourceError:
    '''
    con = connect(data_source)
    queries = parse(schema_path, orgs)
    result: Dict[OrgName, Dict[TableName, pd.DataFrame]] = {}
    for org, tablequeries in queries.items():
        result[org] = {}
        for table, query in tablequeries.items():
            result[org][table] = get_data(con, query)
    return result
