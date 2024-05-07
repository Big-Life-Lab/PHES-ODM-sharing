from typing import cast

import pandas as pd
import sqlalchemy as sa

Connection = object  # opaque data-source connection handle


def connect_excel(path: str) -> Connection:
    # copies excel data to in-memory db, to abstract everything as a db
    data = pd.read_excel(path)
    db = sa.create_engine('sqlite://', echo=False)
    for table in data.keys():
        data.to_sql(table, db, index=False)
    return cast(Connection, db)


def connect_db(url: str) -> Connection:
    return sa.create_engine(url)


def connect(data_source: str) -> Connection:
    if data_source.endswith('.xlsx'):
        return connect_excel(data_source)
    else:
        return connect_db(data_source)


def exec(c: Connection, sql: str) -> pd.DataFrame:
    '''executes `sql` on connection `c`'''
    db = cast(sa.engine.Engine, c)
    return pd.read_sql_query(sql, db)
