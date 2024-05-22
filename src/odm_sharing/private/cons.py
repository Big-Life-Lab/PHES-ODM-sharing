from typing import List, cast

import pandas as pd
import sqlalchemy as sa


Connection = object  # opaque data-source connection handle


class DataSourceError(Exception):
    pass


def _connect_excel(path: str, tables: List[str]) -> Connection:
    ''':raises OSError:'''
    # copies excel data to in-memory db, to abstract everything as a db
    print('importing excel workbook')
    table_whitelist = set(tables)
    db = sa.create_engine('sqlite://', echo=False)
    xl = pd.ExcelFile(path)
    included_tables = set(map(str, xl.sheet_names)) & table_whitelist
    for table in included_tables:
        print(f'- table {table}')
        df = xl.parse(sheet_name=table)
        df.to_sql(table, db, index=False, if_exists='replace')
    return cast(Connection, db)


def _connect_db(url: str) -> Connection:
    ''':raises sa.exc.OperationalError:'''
    return sa.create_engine(url)


def connect(data_source: str, tables: List[str] = []) -> Connection:
    '''
    connects to a data source and returns the connection

    :param tables: when connecting to an excel file, this acts as a sheet
        whitelist

    :raises DataSourceError:
    '''
    try:
        if data_source.endswith('.xlsx'):
            return _connect_excel(data_source, tables)
        else:
            return _connect_db(data_source)
    except (OSError, sa.exc.OperationalError) as e:
        raise DataSourceError(str(e))


def get_dialect_name(c: Connection) -> str:
    '''returns the name of the dialect used for the connection'''
    return cast(sa.engine.Engine, c).dialect.name


def exec(c: Connection, sql: str, sql_args: List[str] = []) -> pd.DataFrame:
    '''executes sql with args on connection

    :raises DataSourceError:
    '''
    db = cast(sa.engine.Engine, c)
    try:
        return pd.read_sql_query(sql, db, params=tuple(sql_args))
    except sa.exc.OperationalError as e:
        raise DataSourceError(str(e))
