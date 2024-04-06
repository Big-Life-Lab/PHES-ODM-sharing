# Aim/Objective:

The purpose of the ODM is to support wastewater-based surveillance and
epidemiology by facilitating the collection, standardization, and transparency
of data by providing a more harmonized ODM data format to share data between
different data curators and data repositories.

The ODM supports data sharing in two ways:

1.  **Data sharing schema** - The ODM will have a schema that describes what data can be shared with one or more partners or users.
2.  **Data filter based on the data sharing schema** - The ODM will support an open source method for filtering data tables using the data sharing schema. This will be accomplished in large part by generating one, or a series of, SQL querries that can be used to pull selected data from a variety of different database structures.

The data sharing schema will be a csv file (sharing.csv) where each row in the `sharing` file corresponds to one or more headers and/or tables in the PHES-ODM, or one or more organizations with whom to share the output data. See below for an example.

| ruleId | table    | mode   | key        | operator | value                                       | notes                  |
|--------|----------|--------|------------|----------|---------------------------------------------|------------------------|
| 1      | measures | select | NA         | NA       | measureRepID,measure,value,unit,aggregation | basic measures details |
| 2      | measures | filter | measure    | =        | mPox                                        |                        |
| 3      | measures | filter | reportable | =        | TRUE                                        | NA                     |
| 4      | NA       | share  | OPH        | NA       | 1; 2                                        | link to DSA            |
| 5      | NA       | share  | PHAC       | NA       | 1; 2; 3                                     | changed for new DSA    |

The `sharing` file should be accompanied by a metadata file, `sharing_metadata.csv`. This csv file provides additional information about the sharing schema, as shown in the example below:

| name          | datasetID     | organizationID | numberRules | orgsServed | contactID   | version | firstReleased | lastUpdated | changes                                | notes                                      |
|---------------|---------------|----------------|-------------|------------|-------------|---------|---------------|-------------|----------------------------------------|--------------------------------------------|
| quebecSharing | universityLab | university-1   | 5           | PHAC;OPH   | lastnamePer | 1.0.0   | 2024-03-26    | 2024-03-26  | Deprecated outdated rules for LPH, OPH | in line with DSA number 234, 565, and 901. |

The data filter is a Python module (or function) that generates a SQL query to
pull the shareable data based on the inclusion criteria in the data sharing
schema. The function queries ODM-formatted data tables and takes a sharing
schema as an input. The function includes (filters) data according to the
schema rules. The function then returns a data table with only the data that is
to be shared. This new, returned data is ready to be shared and used with a
partner.

# Features

High level features include:

-   The data custodian should be able to define all the sharing rules in a CSV
    file (`sharing.csv`). A standard schema for defining the rules will be
    developed.
-   The schema should allow a data custodian to define the partner
    (organization or person - matching to an `organizationID` and/or
    `contactID` within the model) that each rule pertains to. For example, a
    certain rule or set of rules may be applicable only to the Public Health
    Agency of Canada (PHAC) while another rule may be applicable to not only
    the PHAC but also to Ottawa Public Health.
-   The schema should allow data custodians to define rules that apply to rows
    or to columns. For example, a rule can be made to share all the rows from
    the `samples` table, and/or to only include the `collType` column from the
    `samples` table.
-   The schema is built using the logic and arguments of the `filter()` and
    `select()` functions of the Dplyr package in R. When specifying details of
    the filter function (mode), use of the `=`, `>`, `<`, `>=`, and `<=`
    operators are supported, along with `in` for ranges of continuous data and
    `NA` where the operator is not relevant, like for the select function
    (mode).
-   Rules can be combined to form more powerful conditions by building across
    rows of the `sharing` csv. For example, include all rows with `email` equal
    to "[john.doe\@email.com](mailto:john.doe@email.com){.email}", `firstName`
    equal to "John", and `lastName` equal to "Doe". This is accomplished by
    grouping rules together using the mode `group` with the operators `AND` or
    `OR`, creating customized combinations of conditions.
-   Rules can be made within the context of an entire table, to a column that
    may be present in more than one table, or to a column specific to a table.
    Rules can also be made at the level of all measures or datasets with a
    given license type.
-   The rules may only be inclusive. For example, rules can be defined to
    include rows but not to exclude them.
-   The data custodian will be returned a report at the end which will provide
    details about how many rows were filtered for inclusion in the shareable
    data, as well as the tables and headers selected for inclusion.
-   Version 2 of the PHES-ODM allows data generators and custodian to define
    data licenses. In some jurisdictions, this may be defined in detailed
    data-sharing agreements (DSA). The DSAs can be short simply referencing a
    license type, or they can be many pages identifying specifically who can
    use the data and for what purpose and what will be the data destruction
    protocols, etc. The notes column in the `sharing.csv` is a free text field,
    providing an opportunity to reference a longer document or provide more
    details. Most licenses currently supported by the ODM license field are
    open.
-   The implementation should take into account the relationship between the
    different tables as defined in the ODM. For example, removing a row with
    `siteID = ottawa-1` from the sites table, should also remove all rows in
    the samples table with `siteID = ottawa-1`. All nested relationships should
    also be taken care of. The relationships between the tables can be seen
    [here](https://lucid.app/lucidchart/847978df-d627-4b8a-a379-faca7a517ef4/edit?invitationId=inv_0de7777b-888b-4d8a-827d-2306bdc48cce&page=4OvE58YH3w..#).
-   A python function that implements these rules should be built.

# Sharing CSV

## Introduction

The sharing CSV file provides different data generators or custodians with a
standardized and code-agnostic method to define rules for sharing data with
different organizations. Each row in the CSV file defines one rule which
combined defines all the sharing rules for a given data generator or custodian.
The headers of the CSV file define the different parts of the rule. The
following sections outline these different parts, and provide a guide to
defining a rule.

### 1. Setting the ruleID

Because each sharing schema is a closed system to a given data generator or
data custodian, the ruleIDs only need to be unique within a given schema
(`sharing.csv`). Using sequential integers for ruleIDs works well, and is the
recommended approach.

### 2. Rules and Modes

After defining the unique ID for a rule, the next step is to determine the
`mode` of a rule. There are four possible values for the `mode` column:

1. `select`: This indicates that the effect of this rule will be to select the
   tables and columns for inclusion in the output shareable data. It also means
   that the `key` and `operator` columns do not need to be defined for this
   rule.
2. `filter`: This is used for rules that will filter the shareble data output
   rows based on row values. The full rule will require the `key` and
   `operator` columns to be fully specified.
3. `group`: This defines activities for a rule that groups or combines rules
   together for execution. The full rule will require the `operator` column to
   be fully specified.
4. `share`: This defines a rule that specifies the `organizationID` or
   `contactID` with which an output will be shared, as well as the rules to
   apply to generate the specific output data. The full rule will require the
   `key` column, but not the `operator` column, to be fully specified.

Generally, the bulk of a sharing csv will be composed of `filter` and `select`
rules, with a few `group` rules, and the final `share` rules at the very end.
Rules should also be written and specified in this same order.

### 3. Selecting an Entity

In order to generate an intelligible output dataset, several `select` and
`filter` rules will need to first be stacked and applied. This step involves
selecting the parts of the PHES-ODM or entities within the model. The entities
that can be selected are:

-   Data contained in a table
-   Data contained in column(s) of table(s)
-   Data contained in row(s) of table(s)

This step uses four columns, `table`, `mode`, `key`, and/or `value`. The
`table` column specifies the name(s) of the table(s) to which this rule
applies. The `mode` column specifies the action of a rule the name(s) of the
column(s) to be included in the shared data output as specified by this rule.
For rules that select entities, the `filter` and `select` modes will be used.

#### 3.1. Selecting Columns

In order to have any data to share, tables and columns need to be specified for
inclusion. These are the first rules to define in your schema. To specify which
columns should be shared, specify the table or tables in the `table` column,
list `select` in the `mode` column, and then list the column or columns to be
shared in the `value` column. When specifying the columns, you can separate
distinct column names with a ";", or if choosing several sequential columns you
can list the first and last of the sequential series separated by a ":" (ex:
column2:column5). The `key` and `operator` columns should be left blank (or
`NA`) as they are not used in these rules, and any values in these columns for
`select`-mode rows will be ignored.

To select all tables or all columns, an `all` value can be used in the `table`
and/or `value` columns of the sharing csv.

Some examples are given below:

1.  Selecting only the `saMaterial` column in the `samples` table

    | ruleId | table   | mode   | key | operator | value      | notes     |
    |--------|---------|--------|-----|----------|------------|-----------|
    | 1      | samples | select | NA  | NA       | saMaterial | NA        |

2.  Selecting only the `reportable` and the `pooled` columns in the `measures`
table

    | ruleId | table    | mode   | key | operator | value      | notes     |
    |--------|----------|--------|-----|----------|------------|-----------|
    | 2      | measures | select | NA  | NA       | reportable;pooled | NA |

3.  Selecting all the columns in the `measures` table

    | ruleId       | table    | mode   | key | operator | value      | notes     |
    |--------------|----------|--------|-----|----------|------------|-----------|
    | 3            | measures | select | NA  | NA       | all        | NA        |

4.  Selecting only the `purposeID` column in the `measures` and the `samples` table

    | ruleId       | table    | mode   | key | operator | value      | notes     |
    |--------------|----------|--------|-----|----------|------------|-----------|
    | 4            | measures;samples | select | NA  | NA | purposeID | NA       |

5.  Selecting the `siteID` column in all tables

    | ruleId       | table    | mode   | key | operator | value      | notes     |
    |--------------|----------|--------|-----|----------|------------|-----------|
    | 5            | all      | select | NA  | NA       | siteID     | NA        |

6.  Selecting all of the columns in the `polygons` table except for `reflink`, `lastEditted`, and `notes`.

    | ruleId | table    | mode   | key | operator | value                                           | notes |
    |--------|----------|--------|-----|----------|-------------------------------------------------|-------|
    | 6      | polygons | select | NA  | NA       | polygonID:fileLocation;organizationID;conatctID | NA    |

Notes:

-   In examples 2 and 4 where multiple columns and tables were selected
    respectively, a `;` was used to separate the values. Throughout this entire
    document when multiple values need to listed in a single cell, the `;`
    symbol should be used to separate discrete values.

-   In examples 3 and 5 where all the columns in a table and all the tables
    were selected respectively, the keyword `all` was used. Similar to the `;`
    symbol, the keyword `all` may be used in a cell to mean everything.

-   In example 6, all columns between 'polygonID' and 'fileLocation' were
    selected (inclusively), by separating them with a ":". The ";" symbol was
    also used to specify two more additional columns for inclusion.

-   The **ruleId** column is mandatory for all rules and each value is unique
    across the entire sheet (`sharing.csv`). It must be a number.

#### 3.2. Filtering Rows

Once the columns and tables for inclusion have been specified, users can
specify which rows should be shared using rules with the `filter` mode. Note
that rules that filter can use values in any columns, including columns that
are not being shared in the final output. To specify a `filter` rule, users
need to specify the table or tables in the `table` column, and define the
`mode` as filter. Then users can specify the columns which the filter will act
on in the `key` column, specify the nature of the filter using the `operator`
column, and the filter values in the `value` column. The general structure for
the filter argument is:

``` **column name** **operator** **value**

```

Where the "column name" the name of a column (specified in the `key` column)
from the table(s) specified in the `table` column, and the "value" is the value
or range of values that determine whether a row is selected for sharing, stored
in the `value` column. The "operator" is a placeholder for the symbol indicates
that the nature of the filter to be applied, and the desired relationship
between the `key` and the `value`. The currently accepted values for the
`operator` column are:

-   **=**: Denotes exact equivalence. This should be used for categorical or
    character variables.
-   **\>**: Denotes "greater-than". This can be used for numeric, integer, or
    date-type variables. Note that it is exclusive of the value used in the
    expression.
-   **\<**: Denotes "lesser-than". This can be used for numeric, integer, or
    date-type variables. Note that it is exclusive of the value used in the
    expression.
-   **\>=**: Denotes "greater-than-or-equal-to". This can be used for numeric,
    integer, or date-type variables. Note that it is inclusive of the value
    used in the expression.
-   **\<=**: Denotes "lesser-than". This can be used for numeric, integer, or
    date-type variables. Note that it is inclusive of the value used in the
    expression.
-   **in**: Denotes that a value is contained in a range of continuous data.
    This can be used for numeric, integer, or date-type variables. Note that it
    is inclusive of the values used in the expression.

Technically the `operator` column also accepts `AND` and `OR` as values, but
only for rules of the `group` mode.

Some examples of how these rules can be constructed and applied in practice are
given below:

1.  Selecting only the rows where the value of `siteID` is exactly equal to
"ottawa-1" in the `samples` table.

    | ruleId | table    | mode   | key     | operator | value     | notes     |
    |--------|----------|--------|---------|----------|-----------|-----------|
    | 6      | samples  | filter | siteID  | =        | ottawa-1  |           |

2.  Selecting only the rows where the value of "Collection period" (`collPer`)
is greater than or equal to 5 in the `samples` table.

    | ruleId | table    | mode   | key     | operator | value     | notes     |
    |--------|----------|--------|---------|----------|-----------|-----------|
    | 7      | samples  | filter | >=      | collPer  | 5         |           |

3.  Selecting only the rows where the value of "Collection period" (`collPer`)
is less than 5 in the `samples` table.

    | ruleId | table    | mode   | key     | operator | value     | notes     |
    |--------|----------|--------|---------|----------|-----------|-----------|
    | 8      | samples  | filter | <=      | collPer  | 5         |           |

4.  Selecting only the rows where the value of "Analysis date end" (`aDateEnd`)
is exactly equal to February 1st, 2022 (2022-02-01) from the `measures` table.

    | ruleId | table    | mode   | key      | operator | value      | notes     |
    |--------|----------|--------|----------|----------|------------|-----------|
    | 9      | measures | filter | aDateEnd | =        | 2022-02-01 |           |

5.  Selecting only the rows where the value of "Analysis date end" (`aDateEnd`)
is a date in February from the `measures` table.

    | ruleId | table    | mode   | key      | operator | value                 | notes |
    | ------ | -------- | ------ | -------- | -------- | --------------------- | ----- |
    | 10     | measures | filter | aDateEnd | in       | 2022-02-01:2022-02-28 |       |


### 4. Grouping Rules

To stack particular rules to be applied together, users can rely on the `group`
mode. To create a `group` rule, the mode column needs to be specified to
`group`, and the rule IDs of the rules to be groups should be listed in the
`value` column, separated by a ";". To specify how the rules are being grouped,
the operator needs to be specified as `AND` or `OR`. Group-type rules can also
be grouped together, creating nested group rules.

Some examples are given below:

1.  Selecting only the rows where the value of "Analysis date end" (`aDateEnd`)
is exactly equal to February 1st, 2022 (2022-02-01) or February 1st, 2023
(2023-02-01) from the `measures` table.

    | ruleId | table    | mode   | key      | operator | value      | notes     |
    |--------|----------|--------|----------|----------|------------|-----------|
    | 11     | measures | select | NA       | NA       | all        | This rule selects all the columns from the measures table for inclusion |
    | 12     | measures | filter | aDateEnd | =        | 2022-02-01 | This rules takes all rows where analysis date end is February 1st, 2022 |
    | 13     | measures | filter | aDateEnd | =        | 2023-02-01 | This rules takes all rows where analysis date end is February 1st, 2023 |
    | 14     | NA       | group  | NA       | OR       | 12;13      | This rule groups rules 12 and 13 together with "OR", such that if either rule is true, the data is selected |

2.  Selecting only the rows where the value of `siteID` is exactly equal to "ottawa-1" or "laval-1" in the `samples` table.

    | ruleId | table    | mode   | key      | operator | value      | notes     |
    |--------|----------|--------|----------|----------|------------|-----------|
    | 15     | samples  | select | NA       | NA       | all        | This rule selects all the columns from the samples table for inclusion |
    | 16     | samples  | filter | siteID   | =        | ottawa-1   | This rules takes all rows with a siteID of ottawa-1 |
    | 17     | samples  | filter | siteID   | =        | laval-1    | This rules takes all rows with a siteID of laval-1 |
    | 18     | NA       | group  | NA       | OR       | 16;17      | This rule groups rules 16 and 17 together with "OR", such that if either rule is true, the data is selected |

3.  Selecting only the rows where the value of `siteID` is "ottawa-1" and the collection datetime (`collDT`) was February 1st, 2023 (2023-02-01) from the `samples` table.

    | ruleId | table    | mode   | key      | operator | value      | notes     |
    |--------|----------|--------|----------|----------|------------|-----------|
    | 19     | samples  | select | NA       | NA       | all        | This rule selects all the columns from the samples table for inclusion |
    | 20     | samples  | filter | siteID   | =        | ottawa-1   | This rules takes all rows with a siteID of ottawa-1 |
    | 21     | samples  | filter | collDT   | =        | 2023-02-01 | This rules takes all rows with a collection date of February 1st, 2023 |
    | 22     | NA       | group  | NA       | AND      | 20;21      | This rule groups rules 20 and 21 together with "AND", such that only rows that met both conditions are selected |

4. Selecting only the rows from the `measures` table that correspond to MPox measures between January 1st, 2021 and December 31st, 2021, or SARS-CoV-2 measures after January 1st, 2020.

    | ruleId | table    | mode   | key        | operator | value      | notes     |
    |--------|----------|--------|------------|----------|------------|-----------|
    | 23     | measures | select | NA         | NA       | measure; value; unit; aggregation | This rule selects the measure, value, unit, and aggregation columns from the measures table for inclusion |
    | 24     | measures | filter | measure    | =        | mPox       | This rules takes all rows with an MPox measure in the measures table |
    | 25     | measures | filter | reportDate | in       | 2021-01-01:2021-12-31 | This rules takes all rows with a report date between jan.1 and dec. 31, 2021 in the measures table |
    | 26     | NA       | group  | NA         | AND      | 24;25      | This rule groups rules 24 and 25 together with "AND", such that only rows that met both conditions are selected |
    | 27     | measures | filter | measure    | =        | cov        | This rules takes all rows with a SARS-CoV-2 measure in the measures table |
    | 28     | measures | filter | reportDate | >=       | 2020-01-01 | This rules takes all rows with a report date after jan.1, 2020 in the measures table |
    | 29     | NA       | group  | NA         | AND      | 27;28      | This rule groups rules 27 and 28 together with "AND", such that only rows that met both conditions are selected |
    | 30     | NA       | group  | NA         | OR       | 26;29      | This rule groups rules 26 and 29 together with "OR", such that if either grouping of rules is true, the data is selected |

### 5. Selecting an Organization for Sharing

Once the rules in the sharing csv are defined, the next step is deciding to
which organization(s) or person/people a rule applies. This is done using the
an additional rule row with the `mode` columns value specified as `share`. A
unique identifier for each organization or person should be used and reused
throughout the entire document, and is used in the `key` column for sharing
rules. This unique identifier should ideally correspond to an organization ID
(`organizationID`) in the `organizations` table, or a contact ID (`contactID`)
in the `contacts` table of the ODM. To apply a single rule across multiple
organizations, the different organizations that a rule pertains to can be
listed together in the `key` column. The listed organizations should be
separated by a ";". For example, if a rule applies to the **Public Health
Agency of Canada** (`organizationID = PHAC`) as well as **Ottawa Public
Health** (`organizationID = OPH`) the value of the `key` cell in the row for
that rule would be `PHAC;OPH`. The example assumes that PHAC and OPH are the
agreed upon identifiers to represent these organizations. The rules to apply
for the shared data output should be listed in the `value` column, with that
various rule IDs separated by a ";". To specify different rules for different
organizations/people, users will need to generate addition `share`-mode rules.

Some examples of how these rules can be constructed and applied in practice are
given below:

1. Selecting only all columns of the `measures` table, but only the rows where
the value of "Analysis date end" (`aDateEnd`) is exactly equal to February 1st,
2022 (2022-02-01) or February 1st, 2023 (2023-02-01), and everything from the
`samples` table with the Public Health Agency of Canada (`organizationID =
PHAC`) and Ottawa Public Health (`organizationID = OPH`). Using those same
rules for Laval Public Health (`organizationID = LPH`), except only including
the rows of the `samples` table where the value of `siteID` is exactly equal to
"ottawa-1" or "laval-1".

    | ruleId | table    | mode   | key      | operator | value      | notes
    |--------|----------|--------|----------|----------|------------|-----------|
    | 11     | measures | select | NA       | NA       | all        | This rule selects all the columns from the measures table for inclusion |
    | 12     | measures | filter | aDateEnd | =        | 2022-02-01 | This rules takes all rows where analysis date end is February 1st, 2022 |
    | 13     | measures | filter | aDateEnd | =        | 2023-02-01 | This rules takes all rows where analysis date end is February 1st, 2023 |
    | 14     | NA       | group  | NA       | OR       | 12;13      | This rule groups rules 12 and 13 together with "OR", such that if either rule is true, the data is selected |
    | 15     | samples  | select | NA       | NA       | all        | This rule selects all the columns from the samples table for inclusion |
    | 16     | samples  | filter | siteID   | =        | ottawa-1   | This rules takes all rows with a siteID of ottawa-1 |
    | 17     | samples  | filter | siteID   | =        | laval-1    | This rules takes all rows with a siteID of laval-1 |
    | 18     | NA       | group  | NA       | OR       | 16;17      | This rule groups rules 16 and 17 together with "OR", such that if either rule is true, the data is selected |
    | 31     | NA       | share  | OPH;PHAC | NA       | 11;14;15   | Share all measures from feb. 1 2022 and 2023, and all samples information |
    | 32     | NA       | share  | LPH      | NA       | 11;14;15;18| Share all measures from feb. 1 2022 and 2023, and all samples from ottawa and laval |

2. Share MPox data from 2021 with Ottawa Public Health (`organizationID =
   OPH`), share all SARS-CoV-2 data since 2020 with Laval Public Health
   (`organizationID = LPH`), and share MPox data from 2021 and all SARS-CoV-2
   data since 2020 with the Public Health Agency of Canada (`organizationID =
   PHAC`).

    | ruleId | table    | mode   | key        | operator | value      | notes     |
    |--------|----------|--------|------------|----------|------------|-----------|
    | 23     | measures | select | NA         | NA       | measure; value; unit; aggregation | This rule selects the measure, value, unit, and aggregation columns from the measures table for inclusion |
    | 24     | measures | filter | measure    | =        | mPox       | This rules takes all rows with an MPox measure in the measures table |
    | 25     | measures | filter | reportDate | in       | 2021-01-01:2021-12-31 | This rules takes all rows with a report date between jan.1 and dec. 31, 2021 in the measures table |
    | 26     | NA       | group  | NA         | AND      | 24;25      | This rule groups rules 24 and 25 together with "AND", such that only rows that met both conditions are selected |
    | 27     | measures | filter | measure    | =        | cov        | This rules takes all rows with a SARS-CoV-2 measure in the measures table |
    | 28     | measures | filter | reportDate | >=       | 2020-01-01 | This rules takes all rows with a report date after jan.1, 2020 in the measures table |
    | 29     | NA       | group  | NA         | AND      | 27;28      | This rule groups rules 27 and 28 together with "AND", such that only rows that met both conditions are selected |
    | 30     | NA       | group  | NA         | OR       | 26;29      | This rule groups rules 26 and 29 together with "OR", such that if either grouping of rules is true, the data is selected |
    | 33     | NA       | share  | OPH        | NA       | 23;26   | Share MPox data from 2021 with Ottawa Public Health |
    | 34     | NA       | share  | LPH        | NA       | 23;29   | Share all SARS-CoV-2 data since 2020 with Laval Public Health |
    | 35     | NA       | share  | PHAC       | NA       | 23;30   | Share MPox data from 2021 and all SARS-CoV-2 data since 2020 with PHAC |

## Example Scenarios

In this section we will be working with some data, providing an example
scenario for a rule and showing what the rule looks like in practice.

### Filtering on license type

One special case for filtering is using the license type (`license` in the
`datasets` table, or `measureLic` in the `measures` table). This is more useful
for data generators and custodians who work with a mix of open and private
data. By only filtering on open data, or open data with a specific license, all
of the data and metadata that are open can be shared, without needing to
specify additional sharing filters. For example, to share all data in a given
dataset:

| ruleId | table | mode   | key        | operator | value | notes                                                                                                     |
|--------|-------|--------|------------|----------|-------|-----------------------------------------------------------------------------------------------------------|
| 1      | all   | select | NA         | NA       | all   | This rule selects all the columns and tables for inclusion                                                |
| 2      | all   | filter | license    | =        | open  | This rules takes all rows where the license is open                                                       |
| 3      | all   | filter | measureLic | =        | open  | This rules takes all rows where the measure license is open                                               |
| 4      | NA    | group  | NA         | OR       | 2; 3  | This rule groups rules 2 and 3 together with "OR", such that if either rule is true, the data is selected |
| 5      | NA    | share  | PHAC       | NA       | 1; 4  | This rule specifies that the data should be filtered using rules 1 and 4, and shared with PHAC            |

For an example pulling specifically open measures:

| ruleId | table    | mode   | key        | operator | value | notes                                                                                          |
|--------|----------|--------|------------|----------|-------|------------------------------------------------------------------------------------------------|
| 1      | measures | select | NA         | NA       | all   | This rule selects all the columns from the measures tables for inclusion                       |
| 2      | measures | filter | measureLic | =        | open  | This rules takes all rows in the measures table where the measure license is open              |
| 3      | NA       | share  | PHAC       | NA       | 1; 2  | This rule specifies that the data should be filtered using rules 1 and 2, and shared with PHAC |

### General Example

The data we will be working with has two tables from the ODM, **samples** and
**sites**. It does not include all the columns present in these tables. The
rows in the samples and sites table respectively are shown below:

**samples**:
| sampleID  | siteID   | collDT     | saMaterial | reportable | notes  |
|-----------|----------|------------|------------|------------|--------|
| ottWa19-1 | ottawa-1 | 2021-08-19 | rawWW      | TRUE       | Note 1 |
| ottWa18-1 | ottawa-1 | 2021-08-18 | sweSed     | TRUE       | Note 2 |
| ottWa17-1 | laval-1  | 2021-08-17 | pstGrit    | TRUE       | Note 3 |
| ottWa10-1 | laval-1  | 2020-01-10 | water      | FALSE      | Note 4 |

**sites**:
| siteID   | name                 | repOrg1 | sampleshed |
|----------|----------------------|---------|------------|
| ottawa-1 | University of Ottawa | OPH     | school     |
| laval-1  | University of Laval  | LPH     | school     |

#### Basic Example

1.  Share all columns in the `samples` table, but select only rows whose site
ID is "ottawa-1" for Ottawa Public Health (OPH)

    | ruleId | table    | mode   | key        | operator | value      | notes     |
    |--------|----------|--------|------------|----------|------------|-----------|
    | 1      | samples  | select |            |          | all        |           |
    | 2      | samples  | filter | siteID     | =        | ottawa-1   |           |
    | 3      | NA       | share  | OPH        |          | 1;2        |           |

2.  Share all columns in the `samples` table, but select rows whose sample
material (`saMaterial`) is `rawWW` or `sweSed` for the Public Health Agency of
Canada (PHAC)

    | ruleId | table    | mode   | key        | operator | value        | notes     |
    |--------|----------|--------|------------|----------|--------------|-----------|
    | 4      | samples  | select |            |          | all          |           |
    | 5      | samples  | filter | saMaterial | =        | rawWW;sweSed |           |
    | 6      | NA       | share  | PHAC       |          | 4;5          |           |

3.  Share all rows, but select the `notes` column from all tables for Laval
Public Health (LPH)

    | ruleId | table    | mode   | key        | operator | value        | notes     |
    |--------|----------|--------|------------|----------|--------------|-----------|
    | 7      | all      | select |            |          | notes        |           |
    | 8      | NA       | share  | LPH        |          | 4;5          |           |

4.  Share all columns, but select only the rows for samples taken in the year
2021 and who have been marked as 'reportable' for Ottawa Public Health (OPH)
and the Public Health Agency of Canada (PHAC)

    | ruleId | table   | mode   | key        | operator | value                 | notes |
    |--------|---------|--------|------------|----------|-----------------------|-------|
    | 9      | all     | select |            |          | all                   |       |
    | 10     | samples | filter | reportable | =        | TRUE                  |       |
    | 11     | samples | filtr  | collDT     | in       | 2021-01-01:2021-12-31 |       |
    | 12     | NA      | group  |            | AND      | 10;11                 |       |
    | 13     | NA      | share  | PHAC       |          | 9;12                  |       |

5.  Select all columns from the samples and sites tables, but only rows that
    belong to the University of Laval for Laval Public Health (LPH)

    | ruleId | table    | mode   | key        | operator | value        | notes     |
    |--------|----------|--------|------------|----------|--------------|-----------|
    | 14     | all      | select |            |          | all          |           |
    | 15     | all      | filter | siteID     | =        | laval-1      |           |
    | 16     | NA       | share  | LPH        |          | 14;15        |           |

### A Note on Filter and Select, Groups

When specifying the columns to include in the shared data with the `select`
column, it is implied that all rows will be included **unless** a filter has
also been specified separately. Conversely, specifying the rows you want to
include in the `filter` column **does not** specifies that the column used for
filtering should be included in the `filtered_data` output. `select` is the
only way to specify columns for inclusion.

As such, if you wanted to share all of the `samples` table data with Laval
Public Health (LPH), it would suffice to define the rules as:

    | ruleId | table    | mode   | key        | operator | value        | notes     |
    |--------|----------|--------|------------|----------|--------------|-----------|
    | 1      | samples  | select |            |          | all          |           |
    | 2      | NA       | share  | LPH        |          | 1            |           |

Similarly, if you only wanted to share the measure, value, and unit columns for
the siteID that belong to the University of Laval, but did not want to share
the siteID column, the rules would be:

    | ruleId | table    | mode   | key    | operator | value              | notes |
    |--------|----------|--------|--------|----------|--------------------|-------|
    | 1      | measures | select |        |          | measure;value;unit |       |
    | 2      | measures | filter | siteID | =        | laval-1            |       |
    | 3      | NA       | share  | LPH    |          | 1;2                |       |

With group-type rules, the rules are combined with an `AND` or `OR` operator,
and the rules to be combined are listed in the value field. Similarly, when
specifying the sharing target, users also list the rules to apply for the
output. The result is that with the sharing, there is an implicit grouping
action run by the library as part of this activity as well.


| ruleId | table    | mode   | key        | operator | value                 | notes     |
| ---    | ---      | ---    | ---        | ---      | ---                   |-----------|
| 1      | measures | select | NA         | NA       | measure;value;unit    |           |
| 4      | measures | filter | measure    | =        | mPox                  |           |
| 5      | measures | filter | reportDate | in       | 2021-01-01;2021-12-31 |           |
| 6      | measures | filter | measure    | =        | cov                   |           |
| 7      | measures | filter | reportDate | >=       | 2020-01-01            |           |
| 8      | NA       | group  | NA         | AND      | 4; 5                  |           |
| 9      | NA       | group  | NA         | AND      | 6; 7                  |           |
| 10     | NA       | group  | NA         | OR       | 8; 9                  |           |
| 11     | measures | filter | reportable | =        | TRUE                  |           |
| 12     | NA       | share  | PHAC       | NA       | 10;11                 |           |

Which implicitly generates -->

| ruleId | table    | mode  | key | operator | value | notes       |
| ---    | ---      | ---   | --- | ---      | ---   | ----------- |
| 13     | measures | group | NA  | AND      | 10;11 |             |

Which then generates the SQL query for sharing with PHAC for this example -->

```
select measure, value, unit from measures where ((4 and 5) or (6 and 7)) and 11
```

## Sharing CSV Columns

This section summarizes all the columns that are a part of the file

**ruleId**: Mandatory for all rules. Recommended to use sequential integers for
naming, but can be a number or a string. If a string, then its recommended to
use [snake_case](https://en.wikipedia.org/wiki/Snake_case) - spaces in names
are not supported. Each value should be unique across an entire sharing file
(`sharing.csv`).

**table**: The name(s) of the tables for this rule. Allowable values are names
(partIDs) of the tables separated by a `;`, or `all` to select all tables.

**mode**: The activity and modality of a rule. Allowable values are:
  - `select`: used for rules that define which tables and columns are to be
    shared. Requires values in the `ruleID`, `table`, `mode`, and `value`
    columns of the sharing csv.
  - `filter`: used for rules that define which rows of data are appropriate for
    sharing. Requires values in the `ruleID`, `table`, `mode`, `key`,
    `operator` and `value` columns of the sharing csv.
  - `group`: used for grouping together rules that should be applied as
    combined conditions, using either `AND` or `OR` as the operator. Requires
    values in the `ruleID`, `mode`, `operator` and `value` columns of the
    sharing csv.
  - `share`: used for rules defining the target for the sharing data output.
    Requires values in the `ruleID`, `mode`, `key` (to specify the
    organizationID(s) or contactID(s)) and `value` (to specify the rules to
    apply for the output) columns of the sharing csv.

**key**: The argument used to specify the header or headers used for a
filtering rule, or the destination organization or person for a sharing rule.
Multiple headers can be listed, and likewise multiple organizations/individuals
can be separated by a `;`. Also supports key word `all`. The organizations here
reference the organizations table (`organizationID`), or the contacts table
(`contactID`) in the ODM data.

**operator**: The operator used to define the logic of filtering and grouping
rules. For `filter`-mode rules, use of the `=`, `>`, `<`, `>=`, and `<=`
operators are supported, along with `in` for ranges of continuous data. For
`group`-mode rules, the acceptable values for this field are `AND` or `OR`.

**value**: Specifies the values for filtering rules, and the rules to be
grouped for grouping rules. Discrete, listed values in this field should be
separated by a ";".

**notes**: An optional, free-text description or notes explaining this rule, or
other related information deemed worthy of sharing.

## Sharing Metadata CSV Columns

Metadata for the sharing csv is stored in a separate file, the
`sharingMetadata.csv`. This section summarizes all the columns that are a part
of the file:

**name**: the name given to a sharing schema. This is less important for data
custodians/generators who only use a single schema, but these are unique names
for each `sharing.csv` for each group or dataset. For naming, it is recommended
to use [snake_case](https://en.wikipedia.org/wiki/Snake_case) - spaces in names
are not supported. Each value should be unique across an entire sharing
metadata file (`sharing_metadata.csv`).

**datasetID**: The dataset(s) for which a given sharing schema applies.
Multiple datasets can be separated by a `;`. The dataset(s) here reference the
datasets table (`datasetID`) in the ODM data.

**version**: The version number of a given sharing schema. Version numbering
should be updated with each change, ideally following [semantic
versioning](https://semver.org) structure. Given a version number "x.y.z", or
"1.0.0", for example. The meaning of a change to each of these numbers based on
position is: MAJOR.MINOR.PATCH. MAJOR version updates are when rules are added
or removed, MINOR version updates are when when you are editing rules, and
PATCH version updates are when you tweak the `status` or `valid_period`
columns.

**organizationID**: The organization who created a given sharing schema. The
organization here should reference the organizations table (`organizationID`)
in the ODM data.

**contactID**: The contact information for the person who created a given
sharing schema. The contact here references the contacts table (`contactID`) in
the ODM data.

**numberRules**: The number of rules defined in the sharing csv schema.

**orgsServed**: A list of the organizations/people served by a sharing csv.
This is a list of `organizationID` and/or `contactID` entries in the `key`
field for sharing-type rules. The values should be separated with a ";".

**firstReleased**: A date to specify when the sharing schema was made.

**lastUpdated**: A date to specify when the sharing schema was last edited or
updated.

**changes**: A free-text field to record changes made at the last update to the
sharing schema.

**notes**: An optional, free-text description or notes explaining details about
the sharing schema, or other related information deemed worthy of sharing.

An example of this table is found below. For this example, the university lab
records data for two different municipalities, and has separate datasetIDs for
data from the different municipalities. To make their workflow clearer, they've
also opted to created separate sharing schemas for the separate datsets.

| name           | datasetID       | version | organizationID | contactID   | firstReleased | lastUpdated | changes                              | notes |
|----------------|-----------------|---------|----------------|-------------|---------------|-------------|--------------------------------------|-------|
| ottawaSharingA | cityAReportData | 1.1.0   | university-1   | lastnamePer | 2022-02-01    | 2023-03-01  | Deprecated outdated rules for city A | NA    |
| ottawaSharingB | cityBReportData | 1.2.0   | university-1   | lastnamePer | 2022-03-15    | 2023-03-01  | Changed outdated rules for city B    | NA    |

Many of these values can be generated automatically: `name` can be extracted
from the filename of the schema. `lastEdited` can be inferred by reading in the
modified date from the filesystem. `organizationID`, `status`, `version`, and
`notes` are not able to be automatically inferred ar this point, but we hope to
be able to infer them automatically in a later version of the sharing system.

# Implementation

## Function Signature

The function which implements the sharing feature takes two arguments:

1.  `data`: A series of tables from PHES-ODM formatted data. The data input
does not have to contain all the entities defined in the ODM, but can only
contain those on which the sharing rules should be applied. An example is shown
below,

**measures**

| measureRepID   | sampleID     | measure   | value    | unit   | aggregation   |
| -------------- | ------------ | --------- | -------- | ------ | ------------- |
| ottWW100       | pgsOttS100   | covN1     | 0.0023   | gcml   | sin           |
| ottWW101       | pgsOttS101   | covN1     | 0.0402   | gcml   | sin           |

**samples**

| sampleID     | siteID     | collDT                  | saMaterial    |
| ------------ | ---------- | ----------------------- | ------------- |
| pgsOttS100   | ottawa-1   | 2021-02-01 9:00:00 PM   | rawWW         |
| pgsOttS101   | ottawa-1   | 2021-02-01 9:00:00 PM   | rawWW         |
| pgsOttS102   | ottawa-1   | 2021-02-26 9:00:00 PM   | rawWW         |

**organizations**

| organizationID   | name                  | orgType   |
| ---------------- | --------------------- | --------- |
| lab100           | University L100 Lab   | academ    |
| lab101           | University L101 Lab   | academ    |

The above `data` example has three tables, **measures**, **samples**, and
**organizations**, with each table containing two or three rows. The table
names (`partID`s) as specified in the ODM should match the input file names.
The names of the columns and their value types should match up with their
specification (including the named `partID`) in the ODM.

2.  `sharing_rules`: The tabular `sharing.csv` containing the sharing rules to
be applied to the data. Each item must reference a table (or multiple tables),
and reference some or all of the fields as defined in the data above. An
example is shown below,

| ruleId | table            | mode   | key      | operator | value                 | notes |
|--------|------------------|--------|----------|----------|-----------------------|-------|
| 1      | all              | select | NA       | NA       | all                   |       |
| 2      | samples          | filter | collDT   | in       | 2021-01-25:2021-02-25 |       |
| 3      | samples;measures | filter | sampleID | =        | pgsOttS101;pgsOttS102 |       |
| 4      | NA               | share  | PHAC     | NA       | 1;3                   |       |
| 5      | NA               | share  | public   | NA       | 1;2;3                 |       |

The above `sharing_rules` example contains three rules to apply to the data,
and 2 rules for targetting the sharing of data.

The function will then return one dataset output (either xlsx file or series of
csv files) per organization/individual named in the rules with a `share` value
in the `mode` column. This will be the `filtered_data`, with the example shown
below:

-   **filtered_data**: The data to share with an organization. This is a copy
    of the `data` parameter with the columns and rows that meet the inclusion
    rules defined in the sharing rules for the passed organization. It has the
    same structure as the `data` argument described above. To continue our
    example:

**FOR: PUBLIC**

**measures**

| measureRepID   | sampleID     | measure   | value    | unit   | aggregation   |
| -------------- | ------------ | --------- | -------- | ------ | ------------- |
| ottWW101       | pgsOttS101   | covN1     | 0.0402   | gcml   | sin           |

**samples**

| sampleID     | siteID     | collDT                  | saMaterial   |
| ------------ | ---------- | ----------------------- | ------------ |
| pgsOttS101   | ottawa-1   | 2021-02-01 9:00:00 PM   | rawWW        |

**organizations**

| organizationID   | name                  | orgType   |
| ---------------- | --------------------- | --------- |
| lab100           | University L100 Lab   | academ    |
| lab101           | University L101 Lab   | academ    |

**FOR: PHAC**

**measures**

| measureRepID | sampleID   | measure | value  | unit | aggregation |
|--------------|------------|---------|--------|------|-------------|
| ottWW101     | pgsOttS101 | covN1   | 0.0402 | gcml | sin         |

**samples**

| sampleID   | siteID   | collDT                | saMaterial |
|------------|----------|-----------------------|------------|
| pgsOttS101 | ottawa-1 | 2021-02-01 9:00:00 PM | rawWW      |
| pgsOttS102 | ottawa-1 | 2021-02-26 9:00:00 PM | rawWW      |

**organizations**

| organizationID   | name                  | orgType   |
| ---------------- | --------------------- | --------- |
| lab100           | University L100 Lab   | academ    |
| lab101           | University L101 Lab   | academ    |

The above data can then be exported as two separate excel files (or sets of csv
files), with one for the public and one for PHAC.

-   **sharing_summary**: A tabular breakdown of entities for whom sharing data
    was generated, and for each organization it lists the ruleIDs of the
    applied rules, the tables included in the shared data, and the number of
    rows for each shared table. An example is shown below:

**summary_table:**

| destination_org | rule_ids_used | tables_shared | number_rows_output |
|-----------------|---------------|---------------|--------------------|
| public          | 1,2,3         | measures      | 1                  |
| public          | 1,2,3         | samples       | 1                  |
| public          | 1,2,3         | organizations | 2                  |
| PHAC            | 1,3           | measures      | 1                  |
| PHAC            | 1,3           | samples       | 2                  |
| PHAC            | 1,3           | organizations | 2                  |

-   **sharing_rules_summary**: A copy of the sharing rules csv, but with an
    additional column for recording the number of cells selected by each rule.
    Allows for users to check the fineness of their data filtration, and detect
    potential errors. As an example:

| ruleId | table            | mode   | key      | operator | value                 | notes | selectedCells |
|--------|------------------|--------|----------|----------|-----------------------|-------|---------------|
| 1      | all              | select | NA       | NA       | all                   |       | 30            |
| 2      | samples          | filter | collDT   | in       | 2021-01-25:2021-02-25 |       | 8             |
| 3      | samples;measures | filter | sampleID | =        | pgsOttS101;pgsOttS102 |       | 14            |
| 4      | NA               | share  | PHAC     | NA       | 1;3                   |       | 20            |
| 5      | NA               | share  | public   | NA       | 1;2;3                 |       | 16            |

The `sharing_summary` and `sharing_rules_summary` tables should be shared with
the `filtered_data` output, along with the `sharing_metadata` file.

Describing the example above,

1.  For the rule with ID 1, it says to include all tables and columns. So all
tables and columns were included in the output `filtered_data`, with only the
rows that matched inclusion criteria. If no filtration on rows was provided,
the column-based rules set the definition to include all rows in the included
columns.
2.  For the rule with ID 2, an additional row was filtered out of **samples**
as one the of entries did not match the inclusion criteria for the collection
date.
3.  The rule with ID 3 says that rows with the **sampleID** of "pgsOttS101" or
"pgsOttS102" were included across the `measures` and `samples` tables. This
meant that only one row that met this criteria in the **measures** table was
included, and the two rows from the **samples** table that met that criteria
were included.
4. RuleID 4 says to share with PHAC the data that meets the criteria of both 1
and 3, and RuleID 5 says to share with the public the data that meets the
criteria of both 1, 2, and 3. So those rules are applied together to generate
the two outputs, one for each sharing partner.
