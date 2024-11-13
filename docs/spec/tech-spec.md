# Tech spec

The ODM sharing library aims to be able to read the most used file formats and
databases, provide useful feedback to help build correct filters, and output
easy-to-share result data.

## Overview

A sharing schema (in CSV format) is used to define individual rules (as rows),
which come together to form a data query.

The query rules are parsed into an abstract syntax tree (AST), which represents
the structure of the query. It effectively separates rule-parsing from
query-generation, making it more modular. The AST can then be used to generate
concrete queries in SQL or other query languages, or it can be used directly to
call functions on data while iterating over it.

The library will focus on using SQL as the query language, since it has wide
support and is easy to generate. Using SQL will also provide a free performance
boost when running queries on big indexed databases, as well as enable us to
output the intermediate SQL to the user in case they want to inspect or execute
the queries themselves.

## API

### Public modules

#### sharing

- types:
    - `ColumnName = str`
    - `Connection = object # opaque data-source connection handle`
    - `DataFrame = pandas.DataFrame`
    - `OrgName = str`
    - `Query = object # opaque for now`
    - `RuleId = int`
    - `TableName = str`

- high level functions:
    - `extract(schema_file: str, data_source: str, orgs: List[str]=[]) -> ...`

        returns a Pandas DataFrame per table per org

        Parameters:

        - schema_file: rule schema file path
        - data_source: a file path or database url (in SQLAlchemy format)
        - orgs: orgs to share with, or all if empty

        Exceptions: ConnectionError, OSError, ParseError

- low level functions:
    - `connect(data_source: str) -> Connection`

        returns a connection object that can be used together with a query
        object to retrieve data from `data_source`

        Exceptions: ConnectionError

    - `parse(schema_path: str, orgs=[]) -> Dict[OrgName, Dict[TableName, Query]]`

        returns queries for each org and table, generated from the rules
        specified in `schema_path`

        Exceptions: OSError, ParseError

    - `get_data(c: Connection, q: Query) -> DataFrame`

        returns the data extracted from running query `q` on data-source
        connection `c`, as a pandas dataframe

        Exceptions: ConnectionError

    - `get_counts(c: Connection, q: Query) -> Dict[RuleId, int]`

        returns the row counts for each rule, corresponding to how each part of
        query `q` would filter the data extracted from connection `c`

        Exceptions: ConnectionError

    - `get_columns(c: Connection, q: Query) -> Tuple[RuleId, List[ColumnName]]`

        returns the select-rule id together with the column names that would be
        extracted from using query `q` on connection `c`

        Exceptions: ConnectionError

### Private modules

#### cons

Data source connection abstraction, including intermediate copy of spreadsheet
files to in-memory DBs.

- connect(data_source: str) -> Connection

#### rules

Loading of rule files.

- load(schema_file: str) -> Dict[RuleId, Rule]

#### trees

Parsing of rules into abstract syntax trees.

- parse(rules: Dict[RuleId, Rule] | List[Rule], orgs=[]) -> RuleTree

#### queries

(SQL) query generation from ASTs.

- generate(rt: RuleTree) -> Dict[OrgName, Dict[TableName, TableQuery]]

### Errors

The exception types that may be thrown, as well as examples of what they cover:

- DataSourceError:
    - table not found in data source
    - unable to open/read data source
- OSError:
    - failed to read schema file
    - failed to write output file
- ParseError:
    - headers are missing
    - value can't be coerced to the correct type
    - required table/key/operator/mode is missing
    - invalid filter/group operator

### Examples

common definitions:
```python
import pandas as pd

import sharing as s

data_file = 'data.xlsx'
rule_file = 'rules.csv'
org = 'OHRI'
orgs = [org]
```

high-level one-shot function:

```python
results = s.extract(rules, data_file, orgs)
for org, tabledata in results.items():
    for table, data in tabledata.items():
        data.to_csv(f'{org}-{table}.csv')
```

low-level sample code:

```python
def describe_table_query(con, rules, table, query):
    print(f'query table: {table}')

    (select_rule_id, columns) = s.get_columns(con, query)
    print(f'query columns (from rule {select_rule_id}):')
    print(','.join(columns))

    print('query counts per rule:')
    rule_counts = s.get_counts(con, query)
    for ruleId, count in rule_counts.items():
        r = rules[ruleId]
        rule_filter = f'{r.key} {r.operator} {r.value}'
        print(f'{ruleId} | {count} | {rule_filter}')

def extract_filtered_data(con, table, query):
    data: pd.DataFrame = s.get_data(con, query)
    data.to_csv(f'{org}-{table}.csv')

con = s.connect(data_file)
rules = s.load(rule_file)
rule_tree = s.parse(rules, orgs)
table_queries = s.generate(rule_tree)[org]
for table, query in table_queries.items():
    describe_table_query(con, rules, table, query)
    extract_filtered_data(con, table, query)
```

## Schema parsing and query generation

### CSV rule parsing

1. read csv, or fail with OSError
2. normalize NA values
3. validate headers, or fail with ParseError(s)
4. parse each row into a rule obj:
    - validate rule, or accumulate ParseError(s):
        - coerce values into the right types
        - check existence of required values
        - check operator values
5. return a dict with rule-ids and rules, or raise accumulated errors

Error messages should contain all the necessary info to find and fix the issue,
including the line number and column name (if applicable). Errors can be
accumulated, but the result is only valid if no errors occured.

### AST generation

An abstract syntax tree is incrementally generated from the list of rules.

When an error is encountered an exception will be thrown with a message
describing what's wrong and which rule is responsible. Errors can't be
accumulated at this point since it would cause error propagation.

Node kinds:

- **root**: AST root
- **share**: what to share with each org
- **table**: table name
- **select**: lists column name values
- **group**: groups filters together
- **filter**: defines a filter with operator, key and value
- **field**: a field name
- **literal**: a string literal
- **range-kind**: specifies if a range is an interval or a set

Node structure:

- rule_id: int
- kind: NodeKind
- str_val: str
- sons: List[Node]

Tree structure:

For each rule, a node is added based on its mode. The node order is fixed as
specified, so the filter.field node comes before any filter.literal nodes, etc.

- select:
    - (**select**, ("" or "all")):
        - (**literal**, column) for column in rule.key
- filter:
    - (**filter**, rule.operator):
        - (**field**, rule.key)
        - (**range-kind**, 'interval'/'set') # only present for 'in' operator
        - (**literal**, x) for x in rule.value
- group:
    - (**group**, rule.operator):
        - nodes where node.ruleId in rule.value
- share:
    - (**root**, ""):
        - (**share**, org) for org in rule.key
            - (**table**, x) for x in select-rule-tables
                - filter-root node

Example rules with its generated tree:

|ruleId|table   |mode  |key       |operator|value                         |notes|
|------|--------|------|----------|--------|------------------------------|-----|
|10    |measures|select|NA        |NA      |all                           |     |
|11    |measures|select|NA        |NA      |measure;value;unit;aggregation|     |
|12    |measures|filter|measure   |=       |mPox                          |     |
|13    |measures|filter|reportDate|in      |2021-01-01;2021-12-31         |     |
|14    |NA      |group |NA        |AND     |12;13                         |     |
|15    |measures|filter|measure   |=       |cov                           |     |
|16    |measures|filter|reportDate|>=      |2020-01-01                    |     |
|17    |NA      |group |NA        |AND     |15;16                         |     |
|18    |NA      |group |NA        |OR      |14;17                         |     |
|19    |NA      |share |ohri      |NA      |11;18                         |     |
|20    |NA      |share |other     |NA      |10                            |     |

```
(root, "")
    (share, "OHRI")
        (table, "measures")
            (select, "")
                (literal, "measure")
                (literal, "value")
                (literal, "unit")
                (literal, "aggregation")
            (group, "OR")
                (group, "AND")
                    (filter, "=")
                        (field, "measure")
                        (literal, "mPox")
                    (filter, "in")
                        (field, "reportDate")
                        (range-kind, "interval")
                        (literal, "2021-01-01")
                        (literal, "2021-12-31")
                (group, "AND")
                    (filter, "=")
                        (field, "measure")
                        (literal, "cov")
                    (filter, ">=")
                        (field, "reportDate")
                        (literal, "2020-01-01")
    (share, "other")
        (table, "measures")
            (select, "all")
```

#### Algorithm

- Each rule in a sharing CSV sheet can only reference rules defined in a
  previous row.
- a node has a type/kind, a value, and a list of children
- the children of a node is called 'sons' since it's shorter
- nodes are first added to ctx and then later added to parent nodes with O(1)
  lookup, this way the tree is constructed incrementally while parsing each
  rule
- share nodes are made to be children of a single root-node, since each org
  gets its own node, there may be multiple share-rules, and the tree
  can only have a single root node
- the root-node is updated every time a new share-node is added
- tables of each rule are cached for O(1) lookup

```
for each rule:
    for each table in rule, or just once if no table:
        init node, depending on rule mode:
            select:
                kind = select
                value = empty if sons are specified, otherwise 'all'
                sons = a value node for each column name
            filter:
                kind = filter
                value = operator
                sons =
                    1. a key node for the field name
                    2. a value node for each filter value
            group:
                kind = group
                value = operator
                sons = nodes matching the rule's list of ids
            share:
                kind = root
                sons =
                    for each organization:
                        kind = share
                        value = org
                        sons =
                            for each select-node referenced in share-rule:
                                for each table in select-node's rule:
                                    kind = "table"
                                    value = table
                                    sons =
                                        1. select node
                                        2. filter/group node referenced in
                                           share-node. Multiple nodes are
                                           implicitly grouped with an AND-node.
```

### SQL query generation

SQL queries are (recursively) generated from each table-node of the AST. Values
are separated to take advantage of [parameterized queries](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
to prevent SQL injections. Multiple kinds of queries can be generated for
different purposes, including retrieving only the row-counts or column names.

Starting at the table node, the recursive function will generate an SQL query
by first recursing down to the leaf nodes, then making it all come together in
the table node:

- **table**:

    ```
    table_name = str_val
    result =
        "select " + recurse(select-child)
        "from " + table_name
        "where " + recurse(filter-child)
    ```

- **select**:

    ```
    result =
        if "all" in values: " * "
        else: join quoted child values with commas
    ```

- **group**:

    ```
    operator = str_val
    result = fold children with operator
    ```

- **filter**:

    ```
    operator = str_val
    result = recurse(first-child) + (logic depending on range-kind)
    ```

- **field**:

    ```
    result = quote str_val
    ```

- **literal**:

    ```
    append to separate parameter value list
    ```

Example implementation of SQL-generation for a filter node:

```python
field = Node(kind: field, str_val: 'siteID')
value = Node(kind: literal, str_val: 'ottawa-1')

param_values = []
sql = gen_sql(field, param_values) + ' = ' + gen_sql(value, param_values)
assert sql == 'siteID = ?'
assert param_values == ['ottawa-1']
```

## Data source connections

A connection can be established to multiple data sources, including databases
and spreadsheet files.

### Excel

Excel seems to be the main data source used by the ODM community.

Unofficial Excel plugins are available for SQLAlchemy, but users may not want
to install them. The pyodbc library can also be used directly (instead of SQLAlchemy) together with the ODBC driver for Excel, but only on Windows.

SQLAlchemy Excel dialect plugin:

https://github.com/mclovinxie/dialect-pyexcel

Using the ODBC Excel driver on Windows:

https://github.com/mkleehammer/pyodbc/wiki/Connecting-to-Microsoft-Excel

As an alternative to the above, we will load the spreadsheet file into a
temporary in-memory SQLite database and perform queries on that instead. It
will work like the following:

1. read into memory (using pandas)
2. create in-memory sqlite db (using sqlalchemy)
3. copy data to db (using pandas)

Pandas and SQLAlchemy are both widely used and work well together.

### Databases

The SQLAlchemy library is used for database-abstraction. (ODBC was initially
considered as the database-connectivity library of choice, but seeing that most
people want to use Excel documents as input files (which would only work on
Windows or with unofficial plugins), it became clear that we needed an
alternative.)

In this first version, we'll only accept [sqlalchemy database urls](https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls).
In future versions we may want to provide a more abstract and user friendly
way.

Users will need to install the python package for their database, in addition
to installing this library. There may be multiple options for each
vendor/dialect. Please see the [list of SQLAlchemy dialects](https://docs.sqlalchemy.org/en/20/dialects/index.html#dialects)
for more information.
