from pathlib import Path
from typing import List, Set, cast

import pandas as pd
import sqlalchemy as sa


Connection = object  # opaque data-source connection handle


class DataSourceError(Exception):
    pass


def _create_memory_db() -> sa.engine.Engine:
    return sa.create_engine('sqlite://', echo=False)


def _write_table_to_db(db: sa.engine.Engine, table: str, df: pd.DataFrame
                       ) -> None:
    print(f'- table {table}')
    df.to_sql(table, db, index=False, if_exists='replace')


def _connect_csv(path: str) -> Connection:
    '''copies file data to in-memory db

    :raises OSError:'''
    print('importing csv file')
    table = Path(path).stem
    db = _create_memory_db()
    df = pd.read_csv(path)
    _write_table_to_db(db, table, df)
    return cast(Connection, db)


def _connect_excel(path: str, table_whitelist: Set[str]) -> Connection:
    '''copies file data to in-memory db

    :raises OSError:'''
    print('importing excel workbook')
    db = _create_memory_db()
    xl = pd.ExcelFile(path)
    included_tables = set(map(str, xl.sheet_names)) & table_whitelist
    for table in included_tables:
        df = xl.parse(sheet_name=table)
        _write_table_to_db(db, table, df)
    return cast(Connection, db)


def _connect_db(url: str) -> Connection:
    ''':raises sa.exc.OperationalError:'''
    return sa.create_engine(url)


def connect(data_source: str, tables: Set[str] = set()) -> Connection:
    '''
    connects to a data source and returns the connection

    :param tables: when connecting to an excel file, this acts as a sheet
        whitelist

    :raises DataSourceError:
    '''
    try:
        if data_source.endswith('.csv'):
            return _connect_csv(data_source)
        elif data_source.endswith('.xlsx'):
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
