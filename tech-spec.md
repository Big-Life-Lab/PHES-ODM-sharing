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

## CLI

**Usage**

```
./share.py [OPTION]... SCHEMA INPUT
```

Arguments:

- SCHEMA

  sharing schema file path

- INPUT

  spreadsheet file path or [SQLAlchemy database url](https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls)

Options:

- `--orgs=NAME[,...]`

    comma separated list of organizations to output data for, defaults to all

- `--outfmt=FORMAT`

    output format (excel or csv), defaults to excel

- `--outdir=PATH`

    output file directory, defaults to the current directory

- `-d`, `--dry-run`, `--debug`:

    only output the intermediary debug information describing what would
    happen, and don't create any output files.

One or multiple sharable output files will be created in the chosen output
directory according to the chosen output format and organization(s). Each
output file will have the input filename followed by a postfix with the org
name (and table name if CSV).

(Debug) information about the operation will be printed to STDOUT, as well as
written to a `debug.txt` file in the same directory.

**Examples**

Create a sharable excel file in the "~/ohri" directory, for the "OHRI"
organization, applying the rules from schema.csv on the input from data.xlsx:

```bash
./share.py --orgs=OHRI --outdir=~/ohri/ schema.csv data.xlsx
```

Output to the default (current) directory, for all organizations specified in
the schema, using a MySQL database (with the pymysql package) as input:

```bash
./share.py schema.csv mysql+pymysql://scott:tiger@localhost/foo
```

Same as above, using a MS SQL Server database through ODBC (with the pyodbc
package):

```bash
./share.py schema.csv mssql+pyodbc://user:pass@mydsn
```

## API

### Public modules

#### sharing

- high level:
    - `extract(data_source: str, schema_file: str, orgs: List[str]=[]) -> ...`
        - returns a Pandas Dataframe per table per org
        - data_source: a file path or database url (in SQLAlchemy format)
        - schema_file: rule schema file path
        - orgs: orgs to share with, or all if empty
- low level:
    - `connect(data_source: str) -> Connection`

        returns a connection object that can be used together with a query
        object to retrieve data from `data_source`

    - `parse(schema_file: str) -> Dict[OrgName, Dict[TableName, Query]]`

        returns queries for each org and table, generated from the rules
        specified in `schema_file`

    - `extract(c: Connection, q: Query) -> Dataframe`

        returns the data extracted from running query `q` on data-source
        connection `c`, as a pandas dataframe

    - `get_counts(c: Connection, q: Query) -> Dict[RuleId, int]`

        returns the row counts for each rule, corresponding to how each part of
        query `q` would filter the data extracted from connection `c`

    - `get_columns(c: Connection, q: Query) -> Tuple[RuleId, List[ColumnName]]`

        returns the select-rule id together with the column names that would be
        extracted from using query `q` on connection `c`

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

- parse(rules: Dict[RuleId, Rule] | List[Rule]) -> RuleTree

#### queries

(SQL) query generation from ASTs.

- generate(rt: RuleTree) -> Dict[OrgName, Query]

### Examples

common definitions:
```python
import pandas as pd

import sharing as s

data_file = 'data.xlsx'
rule_file = 'rules.csv'
org = 'OHRI'
```

high-level one-shot function:

```python
results = s.extract(data_file, rules, orgs=[org])
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
    data: pd.Dataframe = s.extract(con, query)
    data.to_csv(f'{org}-{table}.csv')

con = s.connect(data_file)
rules = s.load(rule_file)
rule_tree = s.parse(rules)
table_queries = s.generate(rule_tree)[org]
for table, query in table_queries.items():
    describe_table_query(con, rules, table, query)
    extract_filtered_data(con, table, query)
```

## Rule schema parsing

1. open schema file
2. parse each line into a rule obj:
    - validate and throw exception on error
3. add each rule obj to a dictionary with rule id as key

Error messages should contain all the necessary info to find and fix the issue,
including the line number, row number, rule id and column name (if applicable).
Parsing can be wrapped in a try-block to accumulate errors instead of aborting
on the first error. This is a viable option since each line is parsed
individually, and their relationships aren't taken into account before the next
(AST generation) step.

## AST generation

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

Node structure:

- (ruleId: int)
- kind: NodeKind
- str_val: str
- children: List[Node]

Tree structure:

For each rule, a node is added based on its mode. The node order is fixed as
specified, so the filter.field node comes before any filter.literal nodes, etc.

- select:
    - (**select**, ("" or "all")):
        - (**literal**, column) for column in rule.key
- filter:
    - (**filter**, rule.operator):
        - (**field**, rule.key)
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

## SQL query generation

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
    result = recurse(first-child) + operator + recurse(second-child)
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
