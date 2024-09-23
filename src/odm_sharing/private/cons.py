import logging
import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Generator, List, Set

import openpyxl as xl
import pandas as pd
import sqlalchemy as sa
from functional import seq
from openpyxl.workbook import Workbook

from odm_sharing.private.common import ColumnName, TableName, F, T
from odm_sharing.private.utils import qt


Sheet = xl.worksheet._read_only.ReadOnlyWorksheet


@dataclass(frozen=True)
class Connection:
    handle: sa.engine.Engine
    bool_cols: Dict[TableName, Set[ColumnName]]


@dataclass
class DataSource:
    table: str
    path: str


class DataSourceError(Exception):
    pass


F_FORMULA = '=FALSE()'
T_FORMULA = '=TRUE()'

BOOL_FORMULAS = [F_FORMULA, T_FORMULA]
BOOL_VALS = [F, T]
NA_VALS = ['', 'NA']


def _create_temp_db() -> sa.engine.Engine:
    path = ''  # in-memory by default
    custom_path = os.environ.get('ODM_TEMP_DB', '')
    if custom_path:
        # XXX: extra initial slash required for both rel and abs paths
        path = '/' + custom_path
        logging.info(f'using temp db {custom_path}')
    return sa.create_engine(f'sqlite://{path}', echo=False)


def _write_table_to_db(db: sa.engine.Engine, table: str, df: pd.DataFrame
                       ) -> None:
    logging.info(f'- table {table}')
    df.to_sql(table, db, index=False, if_exists='replace')


def _datasets_to_db(datasets: Dict[TableName, pd.DataFrame]
                    ) -> sa.engine.Engine:
    '''creates a temp db and writes the datasets as tables'''
    db = _create_temp_db()
    for table, df in datasets.items():
        _write_table_to_db(db, table, df)
    return db


def _find_bool_cols(df: pd.DataFrame, bool_vals: List[str],
                    exclude_cols: Set[str] = set()) -> Set[str]:
    '''Finds boolean columns in a dataframe.

    :returns: a set of column names
    '''

    # The following columns are included:
    # - col-type=bool
    # - col-type=object and val-type=bool
    # - col-type=object and val-type=str and upper(val) in ['FALSE', 'TRUE']
    #
    # NA-values are ignored and won't interfere with the result.
    #
    # The search is non-exhaustive, and will assume a valid bool column after
    # the first match even if there are invalid values further down the column.

    result: Set[str] = set()

    for col in df:
        col_name = str(col)
        if col_name in exclude_cols:
            continue

        def add_bool_col() -> None:
            result.add(col_name)

        # check column type
        # XXX: columns with mixed types have dtype=object
        if df[col].dtype == bool:
            add_bool_col()
            continue
        if df[col].dtype != object:
            continue

        # check cell value type
        for val in df[col]:
            if val is None:  # empty cell -> NA
                continue
            if isinstance(val, bool):
                add_bool_col()
            elif isinstance(val, str):
                norm_val = val.strip().upper()
                if norm_val in NA_VALS:
                    continue
                if norm_val in bool_vals:
                    add_bool_col()
            break

    return result


def _sheet_to_df(sheet: Sheet) -> pd.DataFrame:
    '''converts an excel sheet to a pandas dataframe'''
    row_iter = sheet.values
    columns = list(next(row_iter))  # consumes first row
    return pd.DataFrame(row_iter, columns=columns)


def _normalize_bool_values(df: pd.DataFrame, bool_cols: Set[ColumnName]
                           ) -> None:
    '''normalize bool (string) values to 0/1'''
    # XXX: this is needed to be able to run the same query filter on booleans
    # coming from different data types (like string)
    for col in bool_cols:
        if df[col].dtype == object:  # potentially str
            df[col] = df[col].replace({F: '0', T: '1'})


def _connect_csv(data_sources: List[DataSource]) -> Connection:
    '''copies file data to in-memory db

    :raises OSError:'''

    # XXX: NA-values are not normalized to avoid mutating user data (#31)
    dfs = {}
    bool_cols = {}
    for ds in data_sources:
        table = ds.table if ds.table else Path(ds.path).stem
        path = ds.path
        logging.info(f'importing {qt(table)} from {path}')
        df = pd.read_csv(path, na_filter=False)
        bool_cols[table] = _find_bool_cols(df, BOOL_VALS)
        _normalize_bool_values(df, bool_cols[table])
        dfs[table] = df
    db = _datasets_to_db(dfs)
    return Connection(db, bool_cols)


def _iter_sheets(wb: Workbook, included_tables: Set[str]) -> Generator:
    for sheet in wb:
        table_name = sheet.title
        if table_name in included_tables:
            yield (sheet, table_name)


def _connect_excel(path: str, table_whitelist: Set[str]) -> Connection:
    '''copies excel file data to in-memory db

    :returns: a connection to the db

    :raises OSError:
    '''
    # XXX: we must NOT change the data (#31).

    # XXX: We can NOT use Pandas to import Excel files, since it may convert
    # booleans to float when the first column cell value isn't a valid boolean.
    # This happens even with `dtype=str`. Invalid booleans happen because
    # we must allow empty cells and NA values, and we can't normalize the data
    # (#31). Pandas uses openpyxl under the hood as its Excel backend, and we
    # can use it directly to avoid this issue.

    # XXX: We will NOT use `dtype=str` when converting the imported data to
    # Pandas-dataframes, since there's no need at this point.

    logging.info('importing excel workbook')

    # load excel file
    wb = xl.load_workbook(path, read_only=True, data_only=True)
    sheet_names = seq(wb).map(lambda sheet: sheet.title).list()
    included_tables = set(sheet_names)
    if table_whitelist:
        included_tables &= table_whitelist

    # convert to dataframes
    dfs = {}
    bool_cols = {}
    for sheet, table in _iter_sheets(wb, included_tables):
        df = _sheet_to_df(sheet)
        bool_cols[table] = _find_bool_cols(df, BOOL_VALS)
        _normalize_bool_values(df, bool_cols[table])
        dfs[table] = df

    # include bool formulas when looking for bool columns
    formula_wb = xl.load_workbook(path, read_only=True, data_only=False)
    for sheet, table in _iter_sheets(formula_wb, included_tables):
        df = _sheet_to_df(sheet)
        bc = bool_cols[table]
        bc |= _find_bool_cols(df, BOOL_FORMULAS, bc)

    # write to db
    db = _datasets_to_db(dfs)
    return Connection(db, bool_cols)


def _connect_db(url: str) -> Connection:
    ''':raises sa.exc.OperationalError:'''
    handle = sa.create_engine(url)

    # find bool cols
    bool_cols = defaultdict(set)
    db_info = sa.inspect(handle)
    for table in db_info.get_table_names():
        for col_info in db_info.get_columns(table):
            if isinstance(col_info['type'], sa.sql.sqltypes.BOOLEAN):
                bool_cols[table].add(col_info['name'])

    return Connection(handle, bool_cols)


def _detect_sqlite(path: str) -> bool:
    # https://www.sqlite.org/fileformat.html
    MAGIC = b'SQLite format 3'
    try:
        with open(path, 'rb') as f:
            return f.read(len(MAGIC)) == MAGIC
    except Exception:
        return False


def _detect_sqlalchemy(path: str) -> bool:
    if not path:
        return False
    try:
        sa.engine.url.make_url(path)
        return True
    except sa.exc.ArgumentError:
        return False


def connect(data_sources: List[DataSource], tables: Set[str] = set()
            ) -> Connection:
    '''
    connects to one or more data sources and returns the connection

    :param tables: when connecting to an excel file, this acts as a sheet
        whitelist

    :raises DataSourceError:
    '''

    # XXX: After import of CSV/Excel files, boolean values will be normalized
    # as 0/1, which we'll have to convert back (using previously detected bool
    # columns) to 'FALSE'/'TRUE' before returning the data to the user. This
    # happens in `odm_sharing.sharing.get_data`.
    if not data_sources:
        raise DataSourceError('no data source')
    try:
        first = data_sources[0]
        path = first.path
        is_csv = path.endswith('.csv')
        if not is_csv and len(data_sources) > 1:
            logging.warning('ignoring additional inputs (for CSV only)')

        if is_csv:
            return _connect_csv(data_sources)
        elif path.endswith('.xlsx'):
            return _connect_excel(path, tables)
        elif _detect_sqlite(path):
            return _connect_db(f'sqlite:///{path}')
        elif _detect_sqlalchemy(path):
            return _connect_db(path)
        else:
            raise DataSourceError('unrecognized data source format')
    except (OSError, sa.exc.OperationalError) as e:
        raise DataSourceError(str(e))


def get_dialect_name(c: Connection) -> str:
    '''returns the name of the dialect used for the connection'''
    return c.handle.dialect.name


def exec(c: Connection, sql: str, sql_args: List[str] = []) -> pd.DataFrame:
    '''executes sql with args on connection

    :raises DataSourceError:
    '''
    try:
        return pd.read_sql_query(sql, c.handle, params=tuple(sql_args))
    except sa.exc.OperationalError as e:
        raise DataSourceError(str(e))
