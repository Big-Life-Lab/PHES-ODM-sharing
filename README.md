# Aim/Objective:

The purpose of the ODM is to support wastewater-based surveillance and epidemiology by facilitating the collection, standardization, and transparency of data by providing a more harmonized ODM data format to share data between different data curators and data repositories.

The ODM supports data sharing in two ways:

1.  **Data sharing schema** - The ODM will have a schema that describes what data can be shared with one or more partners or users.
2.  **Data filter based on the data sharing schema** - The ODM will support an open source method for filtering data tables using the data sharing schema.

The data sharing schema will be a csv file (sharing.csv) where each row in the `sharing` file corresponds to a header or table in the PHES-ODM. Attributes in the row describe who the data is shared with and what data is included. See below for an example.

| ruleId | sharedWith | table    | variable   | direction | ruleValue               | notes       |
|--------|------------|----------|------------|-----------|-------------------------|-------------|
| 1      | OPH        | samples  | siteID     | row       | ottawa-1                | link to DSA |
| 2      | PHAC       | samples  | saMaterial | row       | rawWW;sweSwd            | NA          |
| 3      | LPH        | all      | collType   | column    | all.                    |             |
| 4      | OPH;PHAC   | samples  | collDT     | row       | [2021-01-01,2021-12-01] |             |
| 5      | OPH;PHAC   | samples  | collPer    | row       | [Inf,5]                 |             |
| 6      | LPH        | measures | reportable | column    | all                     |             |

The data filter is a Python module (or function) that builds the shareable data based on the inclusion criteria in the data sharing schema. The function accepts ODM-formatted data tables and a sharing schema. The function includes (filters) data variables and rows according to the schema rules. The function then returns a data table with only the data that is to be shared. This new, returned data is ready to be shared and used with a partner.

# Features

High level features include:

-   The data custodian should be able to define all the sharing rules in a CSV file (`sharing.csv`). A standard schema for defining the rules will be developed.
-   The schema should allow a data custodian to define the partner (organization or person - matching to an `organizationID` and/or `contactID` within the model) that each rule pertains to. For example, a certain rule or set of rules may be applicable only to the Public Health Agency of Canada (PHAC) while another rule may be applicable to not only the PHAC but also to Ottawa Public Health.
-   The schema should allow data custodians to define rules that apply to rows or to columns. For example, a rule can be made to exclude all the rows from the `samples` table, and/or to exclude the `collType` column from the `samples` table.
-   Rules can be made within the context of an entire table, to a column that may be present in more than one table or to a column specific to a table. Rules can also be made at the level of all measures or datasets with a ggiven license type.
-   The rules may only be inclusive. For example, rules can be defined to include rows but not to exclude them.
-   Rules can be combined to form more powerful conditions using logical operators. For example, include all rows with `email` equal to "[john.doe\@email.com](mailto:john.doe@email.com){.email}" AND `firstName` equal to "John" AND `lastName` equal to "Doe". Current supported logical operators are `AND` and `OR`.
-   The data custodian will be returned a report at the end which will provide details about how many rows were filtered for inclusion in the shareable data, as well as the tables and headers selected for inclusion.
-   Version 2 of the PHES-ODM allows data generators and custodian to define data licenses. In some jurisdictions, this may be defined in detailed data-sharing agreements (DSA). The DSAs can be short simply referencing a license type, or they can be many pages identifying specifically who can use the data and for what purpose and what will be the data destruction protocols, etc. The notes column in the `sharing.csv` is a free text field, providing an opportunity to reference a longer document or provide more details. Most licenses currently supported by the ODM license field are open.
-   The implementation should take into account the relationship between the different tables as defined in the ODM. For example, removing a row with `siteID = ottawa-1` from the sites table, should also remove all rows in the samples table with `siteID = ottawa-1`. All nested relationships should also be taken care of. The relationships between the tables can be seen [here](https://lucid.app/lucidchart/847978df-d627-4b8a-a379-faca7a517ef4/edit?invitationId=inv_0de7777b-888b-4d8a-827d-2306bdc48cce&page=4OvE58YH3w..#).
-   A python function that implements these rules should be built.

# Sharing CSV

## Introduction

The sharing CSV file provides different data generators or custodians with a standardized and code-agnostic method to define rules for sharing data with different organizations. Each row in the CSV file defines one rule which combined defines all the sharing rules for a given data generator or custodian. The headers of the CSV file define the different parts of the rule. The following sections outline these different parts, and provide a guide to defining a rule.

### 1. Setting the ruleID

Because each sharing schema is a closed system to a given data generator or data custodian, the ruleIDs only need to be unique within a given schema (`sharing.csv`). Using sequential integers for ruleIDs works well, and is the recommended approach.

### 2. Selecting an Organization

Once the ruleID is defined, the next step is deciding to which organization(s) a rule applies. This is done using the `sharedWith` column. A unique identifier for each organization should be used and reused throughout the entire document. This unique identifier should ideally correspond to an organization ID (`organizationID`) in the `organizations` table of the ODM. To apply a single rule across multiple organizations, the different organizations that a rule pertains to can be listed together in the `sharedWith` column. The listed organizations should be separated by a ";". For example, if a rule applies to the **Public Health Agency of Canada** (`organizationID = PHAC`) as well as **Ottawa Public Health** (`organizationID = OPH`) the value of the `sharedWith` cell in the row for that rule would be `PHAC;OPH`. The example assumes that PHAC and OPH are the agreed upon identifiers to represent these organizations.

As with other fields in the sharing schema, the keyword `all` may be used in a cell to mean every organization or all parties.

### 3. Selecting an Entity

The second step involves selecting the parts of the PHES-ODM or entities within the model that the rule applies to. The entities that can be selected are:

-   Data contained in a table
-   Data contained in column(s) of table(s)

This step uses two columns, `tableName` and `variableName`. The `tableName` column can specify the name(s) of the table(s) this rule applies to and the `variableName` column can specify the name(s) of the column(s) this rule applies to.

Some examples are given below:

1.  Selecting the `saMaterial` column in the `samples` table

    | ruleId | ... | tableName | variableName | ... |
    |--------|-----|-----------|--------------|-----|
    | 1      | ... | samples   | saMaterial   | ... |

2.  Selecting the `reportable` and the `pooled` columns in the `measures` table

    | ruleId | ... | tableName | variableName      | ... |
    |--------|-----|-----------|-------------------|-----|
    | 2      | ... | measures  | reportable;pooled | ... |

3.  Selecting all the columns in the `measures` table

    | ruleId.      | ... | tableName | variableName | ... |
    |--------------|-----|-----------|--------------|-----|
    | all_measures | ... | measures  | all          | ... |

4.  Selecting a the `purposeID` column in the `measures` and the `samples` table

    | ruleId | ... | tableName        | variableName | ... |
    |--------|-----|------------------|--------------|-----|
    | 4      | ... | measures;samples | purposeID    | ... |

5.  Selecting the `siteID` column in all tables

    | ruleId | ... | tableName | variableName | ... |
    |--------|-----|-----------|--------------|-----|
    | 5      | ... | all       | siteID       | ... |

Notes:

-   In examples 2 and 4 where multiple columns and tables were selected respectively, a `;` was used to separate the values. The same symbol was used to separate multiple organizations in the previous step. In fact, throughout the entire document when multiple values need to listed in a single cell, the `;` symbol should be used to separate discrete values.

-   In examples 3 and 5 where all the columns in a table and all the tables were selected respectively, the keyword `all` was used. Similar to the `;` symbol, the keyword `all` may be used in a cell to mean everything.

-   The **ruleId** column is mandatory for all rules and each value is unique across the entire sheet (`sharing.csv`). While the recommended value is a number, the `ruleId` column can take either a number or a string as a value. If it is a string, it should not have any spaces in it. The recommended standard is to use [snake_case](https://en.wikipedia.org/wiki/Snake_case) for values in this column. See example 3 for an illustration of this case.

### 4. Selecting the Direction of the Rule

The third step involves selecting the direction in which the rule should be applied. The ODM is a relational database structure, and so it can be conceived of as a set of spreadsheets or tables. Rules can then be understood to be applied in two possible directions:

1.  It can applied by going through each column in the spreadsheet/table and filtering to only include those columns that meets the rule's specification
2.  It can be applied by going through each row in the spreadsheet/table and filtering to only include those rows that meets the rule's specification

This step uses the `direction` column which accepts one of two values, `column` to apply the rule column by column or `row` to apply the rule row by row.

### 5. Selecting the Values to Filter for Sharing

The final step involves inputting the values of the selected entities to filter on. This step uses the `filterValue` column, in combination with the other columns in the `sharing.csv` table. Generally speaking, the `filterValue` column's values depend on the data type (boolean, numeric etc. - defined in the `parts` table column `dataType`) and the statistical type (continuous or categorical - defined in the `parts` table column `aggregationScale`) of the variable. The filtering using the license field is a specific case with the categorical type, explored below.

#### General approach - defined Values

For the statistical type:

-   **Continuous Type**: For continuous entities, the `filterValue` column can either specify an interval with a lower and upper limit, a specific value, or a combination of the two. We use the mathematical notation to define an [interval](https://en.wikipedia.org/wiki/Interval_(mathematics)). Examples are:

    -   1 : All entries where the value is exactly equal to 1 will be selected for sharing

    -   (1, 2] : All values between 1 and 2, only inclusive of 2 will be filtered and selected for sharing

    -   [1, 2) : All values between 1 and 2, only inclusive of 1 will be filtered and selected for sharing

    -   (1, 2) : All values between 1 and 2, excluding 1 and 2 will be filtered and selected for sharing

    -   [1, 2] : All values between 1 and 2, inclusive of 1 and 2 will be filtered and selected for sharing

    Additionally, the **inf** keyword can be used to specify infinity either as the lower or upper bound. Combination of values within this column can be entered in by using the **;** symbol again. For example:

    -   [1, inf) : All values greater than or equal to 1 will be filtered and selected for sharing

    -   [1, 2];(7,8);9 : All values between 1 and 2, inclusive of 1 and 2, all values between 7 and 8, excluding 7 and 8, and all entries where the value is exactly equal to 9 will be filtered and selected for sharing
    
    This same structure applies to date-type data. For example:
    
    -   [2021-03-01,2021-12-01] : Share all values between March 1st 2021 and December 1st 2021, including the endpoints
    
    -   [2021-12-01, 2022-04-01];[2022-06-01,2022-12-01] : Share all values between December 1st, 2021 and April 1st, 2022, and between June 1st, 2022, and December 1st, 2022, including the endpoints

-   **Categorical Type**: For categorical entities, the `filterValue` column should specify the categorical values to filter on for sharing and dissemination. For multiple values, the discrete values can be listed and separated by the **;** symbol, as with the numeric values and sharing organizations. For example:

    -   `rawWW` : All entries with the value of `rawWW` (raw wastewater) will be selected for sharing

    -   `rawWW;swrSed` : All entries with the value of `rawWW` (raw wastewater) or `swrSed` (sewer sediment) will be filtered and selected for sharing

-   Users can also use the **all** keyword to filter our all values in an entity.

For more details on the data type, please refer to the [ODM metadata](https://github.com/Big-Life-Lab/ODM/blob/main/metadata_en.md#entity-relationship-diagram) on the allowable value for each one. For help with ensuring that data is consistent with the ODM structure and is valid, please see the [ODM validation tool](https://validate.phes-odm.org) or the [GitHub page for the vallidation tool](https://github.com/Big-Life-Lab/PHES-ODM-Validation).

#### Filtering on license type

One special case for filtering is using the license type (`license` in the `datasets` table, or `measureLic` in the `measures` table). This is more useful for data generators and custodians who work with a mix of open and private data. By only filtering on open data, or open data with a specific license, all of the data and metadata that are open can be shared, without needing to specify additional sharing filters. For example, to share all data in a given dataset:

| ruleId | sharedWith | table    | variable   | direction | ruleValue               | notes       |
|--------|------------|----------|------------|-----------|-------------------------|-------------|
| 1      | all        | datasets | license    | row       | open                    |             |

For an example pulling just specific open measures:

| ruleId | sharedWith | table    | variable   | direction | ruleValue               | notes       |
|--------|------------|----------|------------|-----------|-------------------------|-------------|
| 1      | all        | measures | measureLic | row       | open                    |             |

## Example Scenarios

In this section we will be working with some data, providing an example scenario for a rule and showing what the rule looks like

The data we will be working with has two tables from the ODM, **samples** and **sites**. It does not include all the columns present in these tables. The rows in the samples and sites table respectively are shown below:

| sampleID  | siteID   | collDT     | saMaterial | reportable | notes  |
|-----------|----------|------------|------------|------------|--------|
| ottWa19-1 | ottawa-1 | 2021-08-19 | rawWW      | TRUE       | Note 1 |
| ottWa18-1 | ottawa-1 | 2021-08-18 | sweSed     | TRUE       | Note 2 |
| ottWa17-1 | laval-1  | 2021-08-17 | pstGrit    | TRUE       | Note 3 |
| ottWa10-1 | laval-1  | 2020-01-10 | water      | FALSE      | Note 4 |


| siteID   | name                 | repOrg1  | sampleshed |
|----------|----------------------|----------|------------|
| ottawa-1 | University of Ottawa | OPH      | school     |
| laval-1  | University of Laval  | LPH      | school     |


1.  Select rows whose site ID in the samples table is "ottawa-1" for Ottawa Public Health (OPH)

    | ruleId | sharedWith | tableName | variableName | direction | filterValue | notes       |
    |--------|------------|-----------|--------------|-----------|-------------|-------------|
    | 1      | OPH        | samples   | siteID       | row       | ottawa-1    |             |

2.  Select rows from the samples table whose sample material (`saMaterial`) is `rawWW` or `sweSed` for the Public Health Agency of Canada (PHAC)

    | ruleId | sharedWith | tableName | variableName | direction | filterValue  | notes       |
    |--------|------------|-----------|--------------|-----------|--------------|-------------|
    | 2      | PHAC       | samples   | saMaterial   | row       | rawWW;sweSed |             |

3.  Select the notes column from all tables for Laval Public Health (LPH)

    | ruleId | sharedWith | tableName | variableName | direction | filterValue | notes       |
    |--------|------------|-----------|--------------|-----------|-------------|-------------|
    | 3      | LPH        | all       | notes        | column    | all         |             |

4.  Select all samples taken in the year 2021 and who have been marked as 'reportable' for Ottawa Public Health (OPH) and the Public Health Agency of Canada (PHAC)

    | ruleId | sharedWith | tableName  | variableName | direction | filterValue             | notes       |
    |--------|------------|------------|--------------|-----------|-------------------------|-------------|
    | 4      | OPH;PHAC   | samples    | dateTime     | row       | [2021-01-01,2021-12-31] |             |
    | 5      | OPH;PHAC   | samples    | reportable   | row       | TRUE                    |             |

5.  Select all columns from the samples table and rows from the sites table that belong to the University of Laval for Laval Public Health (LPH)

    | ruleId | sharedWith | tableName | variableName  | direction | filterValue  | notes       |
    |--------|------------|-----------|---------------|-----------|--------------|-------------|
    | 6      | LPH        | samples   | all           | column    | all          |             |
    | 7      | LPH        | sites     | siteID        | row       | laval-1      |             |

## Sharing CSV Columns

This section summarizes all the columns part of the file

**ruleId**: Mandatory for all rules. Recommended to use sequentil integers for naming, but can be a number or a string. If a string, then its recommended to use [snake_case](https://en.wikipedia.org/wiki/Snake_case) - spaces in names are not supported. Each value should be unique across an entire sharing file.

**sharedWith**: The name(s) of the organizations for this rule. Multiple organizations can be separated by a `;`. Also supports key word `all`. The organizations here reference the organizations table in the ODM data.

**tableName**: The name(s) of the tables for this rule. Allowable values are names (partIDs) of the tables separated by a `;` or `all` to select all tables.

**variableName**: The name(s) of the columns for this rule. Allowable values are names (partIDs) of the columns separated by a `;` or `all` to select all columns.

**direction**: The direction to apply the filtering. Allowable values are **row** or **column**.

**filterValue**: The values of the selected entities to include. These can include an interval, single values or a combination of both. Multiple values can be separated using the `;` symbol. `all` can also be used. For intervals, the mathematical notation is used.

**notes**: Optional description or notes explaining this rule, or other related information deemed worthy of sharing.


# Implementation

## Function Signature

The function which implements the sharing feature takes three arguments:

1.  `data`: A Python dictionary containing the data for each table to filter. The argument does not have to contain all the entities defined in the ODM but can only contain those on which the sharing rules should be applied. An example is shown below,

    ```         
    {
        "measures": [
            {
                "measureRepID": "ottWW100",
                "sampleID": "pgsOttS100",
                "measure": "covN1",
                "value": 0.0023,
                "unit": "gcml",
                "aggregation": "sin",
            },
            {
                "measureRepID": "ottWW101",
                "sampleID": "pgsOttS101",
                "measure": "covN1",
                "value": 0.0023,
                "unit": "gcml",
                "aggregation": "sin",
            },
        ],
        "samples": [
            {
                "sampleID": "pgsOttS100",
                "siteID": "ottawa-1",
                "collDT": "2021-02-01  9:00:00 PM",
                "saMaterial": "RawWW",
            },
            {
                "sampleID": "pgsOttS101",
                "siteID": "ottawa-1",
                "collDT": "2021-02-01  9:00:00 PM",
                "saMaterial": "RawWW",
            },
            {
                "sampleID": "pgsOttS102",
                "siteID": "ottawa-1",
                "collDT": "2021-02-01  9:00:00 PM",
                "saMaterial": "RawWW",
            },
        ],
        "organizations": [
            {
                "organizationID": "labL100",
                "name": "University L100 Lab",
                "orgType": "academ",
            },
            {
                "organizationID": "labL101",
                "name": "University L101 Lab",
                "orgType": "academ",
            },
        ],
    }
    ```

    The above `data` argument example has three tables, **measures**, **samples**, and **organizations**, with each table containing two or three rows. The dictionary keys are the table names (partIDs) as specified in the ODM and the values contain a list of dictionaries for each row in that table. Once again, the names of the columns and their value types should match up with their specification (including the named partID) in the ODM.

2.  `sharing_rules`: A list containing the sharing rules to be applied to the data argument. Each item in the list is a dictionary containing all the fields as defined in the schema section above. An example is shown below,

    ```         
    [
        {
            "ruleID": "1",
            "sharedWith": "Public;PHAC;Local;Provincial;Quebec;OntarioWSI;CanadianWasteWaterDatabase",
            "table": "ALL",
            "variable": "sampleID",
            "direction": "row",
            "ruleValue": "pgsOttS101;pgsOttS102",
        },
        {
            "ruleID": "2",
            "sharedWith": "Public",
            "table": "samples",
            "variable": "collDT",
            "direction": "row",
            "ruleValue": "[2021-01-25, 2021-02-26); (2021-02-26,2021-02-31]",
        },
    ]
    ```

    The above `sharing_rules` example contains two rules to apply to the data.

3.  `organization`: A string containing the name of the organization for whom the filtered data will be shared with. The value of this argument should match up with an organization provided in the `sharing_rules` argument and the `organizationID` in the `organizations` table.

The function will return a dictionary whose keys and values are given below:

-   **filtered_data**: The data to share with an organization. This is a copy of the `data` parameter with the columns and rows that meet the inclusion rules defined in the sharing rules for the passed organization filtered out. It has the same structure as the `data` argument described above.

-   **sharing_summary**: A list of dictionaries containing the columns/rows included, the name(s) of the table(s) they were included from and the ID of the rule that included them. An example is shown below,

    ```         
    [
        {
            "rule_id": "1",
            "entities_filtered": [
                {
                    "table": "measures",
                    "columns_included": {
                        "type": [
                            {
                                "measureRepID": "ottWW101",
                                "sampleID": "pgsOttS101",
                                "measure": "covN1",
                                "value": 0.0023,
                                "unit": "gcml",
                                "aggregation": "sin",
                            }
                        ]
                  },
                    "table": "samples",
                    "columns_included": {
                            {
                                "sampleID": "pgsOttS101",
                                "siteID": "ottawa-1",
                                "collDT": "2021-02-01  9:00:00 PM",
                                "saMaterial": "RawWW",
                            },
                            {
                                "sampleID": "pgsOttS102",
                                "siteID": "ottawa-1",
                                "collDT": "2021-02-01  9:00:00 PM",
                                "saMaterial": "RawWW",
                            }
                }
            ]
        },
        {
            "rule_id: "2",
            "entities_filtered": [
                {
                    "table": "samples",
                    "rows_included": [
                            {
                               "sampleID": "pgsOttS100",
                               "siteID": "ottawa-1",
                               "collDT": "2021-02-01  9:00:00 PM",
                               "saMaterial": "RawWW",
                            },
                            {
                               "sampleID": "pgsOttS101",
                               "siteID": "ottawa-1",
                               "collDT": "2021-02-01  9:00:00 PM",
                               "saMaterial": "RawWW",
                            },
                            {
                               "sampleID": "pgsOttS102",
                               "siteID": "ottawa-1",
                               "collDT": "2021-02-01  9:00:00 PM",
                               "saMaterial": "RawWW",
                            }
                    ]
                }
            ]
        }
    ]
    ```

    The above example contains two dictionaries which describes the entities filtered for due to the rule with ID 1 and 2.

    The `rule_id` field in each dictionary gives the ID of the rule due to which the entities in the `entities_filtered` field were filtered.

    The `entities_filtered` field is a list of dictionaries where each dictionary gives the name of the table and the rows/columns that were included. The keys in each dictionary are described below:

    -   `table`: The name of table from where the rows/columns were filtered.
    -   `rows_included`: A list of dictionaries, where each dictionary is the row that was included from the table
    -   `columns_included`: A list of dictionaries where the key in each dictionary is the name of the column that was included from the table and the value is a list of dictionaries containing the value of each cell in the included column along with the value of the primary key of the row.

    Describing the example above,

    1.  For the rule with ID 1, the rows with the **sampleID** of "pgsOttS101" or "pgsOttS102" were included across all tables. In thi case, this meant both the `measures` table and the `samples` table. This meant that only one row that ment this criteria in the **measures** table was included, and the two rows from the **samples** table that met that criteria were included. The primary keys of the included rows were also reported, with the `measureRepID1 of **ottWW101**, and the filtered sample IDs.
    2.  The For the rule with ID 2, all rows were selected from the **samples** as all data matched the inclusion criteria. The **organizations** table was not included as no rules mentioned it's inclusion and it does not have sample ID (`sampleID`) or collection date and time (`collDT`) headers that would correspond to these rules.
