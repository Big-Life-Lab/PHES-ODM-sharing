from typing import Dict, List, Tuple
from pathlib import Path
from pprint import pprint

import pandas as pd

import odm_sharing.private as private
import odm_sharing.private.trees
from odm_sharing.private.cons import Connection
from odm_sharing.private.queries import Query
from odm_sharing.private.rules import ParseError, RuleId
from odm_sharing.private.common import TableName

# type aliases
ColumnName = str
OrgName = str


def connect(data_source: str) -> Connection:
    '''returns a connection object that can be used together with a query
    object to retrieve data from `data_source`'''
    return private.cons.connect(data_source)


def parse(schema_path: str, orgs: List[str] = []
          ) -> Dict[OrgName, Dict[TableName, Query]]:
    '''returns queries for each org and table, generated from the rules
    specified in `schema_file`'''
    try:
        rules = private.rules.load(schema_path)
        print('\nrules:')
        pprint(rules)

        filename = Path(schema_path).name
        tree = private.trees.parse(rules, orgs, filename)
        print('\nabstract syntax tree:')
        pprint(tree)
    except ParseError:
        pass

    # TODO: implement the rest
    return None  # type: ignore


def get_data(c: Connection, q: Query) -> pd.DataFrame:
    '''returns the data extracted from running query `q` on data-source
    connection `c`, as a pandas dataframe'''
    return private.cons.exec(c, q.data_sql)


def get_counts(c: Connection, q: Query) -> Dict[RuleId, int]:
    '''returns the row counts for each rule, corresponding to how each part of
    query `q` would filter the data extracted from connection `c`'''
    pass


def get_columns(c: Connection, q: Query) -> Tuple[RuleId, List[ColumnName]]:
    '''returns the select-rule id together with the column names that would be
    extracted from using query `q` on connection `c`'''
    pass


def extract(
    data_source: str,
    schema_file: str,
    orgs: List[str] = [],
) -> Dict[OrgName, Dict[TableName, pd.DataFrame]]:
    '''returns a Pandas DataFrame per table per org

    :param data_source: a file path or database url (in SQLAlchemy format)
    :param schema_file: rule schema file path
    :param orgs: orgs to share with, or all if empty
    '''
    con = connect(data_source)
    queries = parse(schema_file, orgs)
    result: Dict[OrgName, Dict[TableName, pd.DataFrame]] = {}
    for org, tablequeries in queries.items():
        result[org] = {}
        for table, query in tablequeries.items():
            result[org][table] = get_data(con, query)
    return result
