# Aim/Objective:

The purpose of the ODM is to support wastewater-based surveillance and epidemiology by facilitating the collection, standardization, and transparency of data by providing a more harmonized ODM data format to share data between different data curators and data repositories.

The ODM supports data sharing in two ways:

1.  **Data sharing schema** - The ODM will have a schema that describes what data can be shared with one or more partners or users.
2.  **Data filter based on the data sharing schema** - The ODM will support an open source method for filtering data tables using the data sharing schema.

The data sharing schema will be a csv file (sharing.csv) where each row in the `sharing` file corresponds to a header or table in the PHES-ODM. Attributes in the row describe who the data is shared with and what data is included. See below for an example.

| ruleId | sharedWith | table   | select   | filter               | valid_period           | status|firstReleased|lastUpdated|changes | notes      |
|--------|------------|---------|----------|----------------------|------------------------|-------|-------------|-----------|--------|------------|
| 1      | OPH        | samples | NA       | siteID == "ottawa-1" | [2022-02-01,2023-01-31]|active | 2022-02-01  |2022-02-01 | added  |link to DSA |
| 2      | PHAC       | samples | NA       | saMaterial == "rawWW"\|\"sweSwd"| NA          |active | 2022-02-01  |2022-02-01 | added  | NA         |
| 3      | LPH        | all     | collType | NA                   | NA                     |active | 2022-02-01  |2022-02-01 | added  | NA         |
| 4 | OPH,PHAC |samples|NA|collDT >= 2021-01-01 & collDT <= 2021-12-01|[2021-02-01,2022-01-31]|deprecated|2021-02-01|2022-02-01|changed for new DSA|NA|
| 5      | OPH,PHAC   | samples | NA       | collPer >= 5         |[2023-12-01,2024-01-31] |active | 2022-02-01  | 2022-02-01| NA     |            |
| 6      | LPH        | measures| all      | NA                   | NA                     |active | 2022-02-01  | 2022-02-01| NA     |            |
| 7      | OPH        | measures| measureRepID:aggregation | NA   | NA                     |active | 2022-02-01  | 2022-02-01| NA     |            |
| 8      | PHAC       | measures| measureRepID,measure,value,unit,aggregation,measureLic| NA| NA|active |2022-02-01|2022-02-01|NA     |            |
| 9      | LPH,OPH    | polygons| polygonID,name,polyPop,geoType,geoWKT| organizationID == "LPH"\|\"OPH"|NA|active|2022-02-01|2022-02-01|added|NA  |

The `sharing` file should be accompanied by a metadata file, `sharing_metadata.csv`. This csv file provides additional information about the sharing schema, as shown in the example below:

| name          | datasetID     | version | organizationID  | contactID    |firstReleased|lastUpdated|changes                              | notes |
|---------------|---------------|---------|-----------------|--------------|-------------|-----------|-------------------------------------|-------|
| ottawaSharing | universityLab | 1.0.0   | university-1    | lastnamePer  |2022-02-01   |2023-03-01 | Deprecated outdated rules for LPH, OPH | NA | 

The data filter is a Python module (or function) that builds the shareable data based on the inclusion criteria in the data sharing schema. The function accepts ODM-formatted data tables and a sharing schema. The function includes (filters) data according to the schema rules. The function then returns a data table with only the data that is to be shared. This new, returned data is ready to be shared and used with a partner.

# Features

High level features include:

-   The data custodian should be able to define all the sharing rules in a CSV file (`sharing.csv`). A standard schema for defining the rules will be developed.
-   The schema should allow a data custodian to define the partner (organization or person - matching to an `organizationID` and/or `contactID` within the model) that each rule pertains to. For example, a certain rule or set of rules may be applicable only to the Public Health Agency of Canada (PHAC) while another rule may be applicable to not only the PHAC but also to Ottawa Public Health.
-   The schema should allow data custodians to define rules that apply to rows or to columns. For example, a rule can be made to share all the rows from the `samples` table, and/or to only include the `collType` column from the `samples` table.
-   The schema is built using the logic and arguments of the `filter()` and `select()` functions of the Dplyr package in R. When specifying details of the filter function, use ofthe `==`, `>=`, and `<=` operators are supported, along with `&` and `|` as "AND" and "OR" operators for the combination of conditions.
-   Rules can be combined to form more powerful conditions by building across rows of the `sharing` csv. For example, include all rows with `email` equal to "[john.doe\@email.com](mailto:john.doe@email.com){.email}", `firstName` equal to "John", and `lastName` equal to "Doe".
-   Rules can be made within the context of an entire table, to a column that may be present in more than one table, or to a column specific to a table. Rules can also be made at the level of all measures or datasets with a given license type.
-   The rules may only be inclusive. For example, rules can be defined to include rows but not to exclude them.
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

Once the ruleID is defined, the next step is deciding to which organization(s) or person/people a rule applies. This is done using the `sharedWith` column. A unique identifier for each organization or person should be used and reused throughout the entire document. This unique identifier should ideally correspond to an organization ID (`organizationID`) in the `organizations` table, or a contact ID (`contactID`) in the `contacts` table of the ODM. To apply a single rule across multiple organizations, the different organizations that a rule pertains to can be listed together in the `sharedWith` column. The listed organizations should be separated by a ",". For example, if a rule applies to the **Public Health Agency of Canada** (`organizationID = PHAC`) as well as **Ottawa Public Health** (`organizationID = OPH`) the value of the `sharedWith` cell in the row for that rule would be `PHAC,OPH`. The example assumes that PHAC and OPH are the agreed upon identifiers to represent these organizations.

As with other fields in the sharing schema, the keyword `all` may be used in a cell to mean every organization or all parties.

### 3. Selecting an Entity

The second step involves selecting the parts of the PHES-ODM or entities within the model that the rule applies to. The entities that can be selected are:

-   Data contained in a table
-   Data contained in column(s) of table(s)
-   Data contained in row(s) of table(s)

This step uses three columns, `table`, `select`, and/or `filter`. The `table` column specifies the name(s) of the table(s) to which this rule applies. The `select` column can specify the name(s) of the column(s) to be included in the shared data output as specified by this rule. The `filter` column takes an argument to specify the condition(s) for inclusion of certain rows.

#### 3.1. Selecting Columns

To specify which columns should be shared, specify the table or tables in the `table` column, and then list the column or columns to be shared in the `select` column. When specifying the columns, you can separate distinct column names with a ",", or if choosing several sequential columns you can list the first and last of the sequential series separated by a ":" (ex: column2:column5). If the rule is only for selecting columns, leave the `filter` column blank (or `NA`).

Some examples are given below:

1.  Selecting the `saMaterial` column in the `samples` table

    | ruleId | ... | table   | select     | filter     | ... |
    |--------|-----|---------|------------|------------|-----|
    | 1      | ... | samples | saMaterial | NA         | ... |

2.  Selecting the `reportable` and the `pooled` columns in the
    `measures` table

    | ruleId | ... | table    | select            | filter     | ... |
    |--------|-----|----------|-------------------|------------|-----|
    | 2      | ... | measures | reportable,pooled | NA         | ... |

3.  Selecting all the columns in the `measures` table

    | ruleId       | ... | table    | select            | filter     | ... |
    |--------------|-----|----------|-------------------|------------|-----|
    | all_measures | ... | measures | all               | NA         | ... |

4.  Selecting a the `purposeID` column in the `measures` and the
    `samples` table

    | ruleId | ... | table            | select            | filter     | ... |
    |--------|-----|------------------|-------------------|------------|-----|
    | 3      | ... | measures,samples | purposeID         | NA         | ... |

5.  Selecting the `siteID` column in all tables

    | ruleId | ... | table | select | filter     | ... |
    |--------|-----|-------|--------|------------|-----|
    | 4      | ... | all   | siteID | NA         | ... |

6.  Selecting all of the columns in the `polygons` table except for `reflink`, `lastEditted`, and `notes`.

    | ruleId | ... | table    | select                                          | filter     | ... |
    |--------|-----|----------|-------------------------------------------------|------------|-----|
    | 5      | ... | polygons | polygonID:fileLocation,organizationID,conatctID | NA         | ... |
    
Notes:

-   In examples 2 and 4 where multiple columns and tables were selected respectively, a `,` was used to separate the values. The same symbol was used to separate multiple organizations in the previous step. In fact, throughout the entire document when multiple values need to listed in a single cell, the `,` symbol should be used to separate discrete values.

-   In examples 3 and 5 where all the columns in a table and all the tables were selected respectively, the keyword `all` was used. Similar to the `,` symbol, the keyword `all` may be used in a cell to mean everything.

-   In example 6, all columns between 'polygonID' and 'fileLocation' were selected (inclusively), by separating them with a ":". The "," symbol was also used to specify two more additional columns for inclusion.

-   The **ruleId** column is mandatory for all rules and each value is unique across the entire sheet (`sharing.csv`). While the recommended value is a number, the `ruleId` column can take either a number or a string as a value. If it is a string, it should not have any spaces in it. The recommended standard is to use [snake_case](https://en.wikipedia.org/wiki/Snake_case) for values in this column. See example 3 for an illustration of this case.

#### 3.2. Filtering Rows

To specify which rows should be shared, specify the table or tables in the `table` column, and then create the row filter in the `filter` column. The general structure for the filter argument is:

      **column name** == **value**
      
Where the "column name" the name of a column from the table(s) specified in the `table` column, and the "value" is the value or range of values that determine whether a row is selected for sharing. The "==" symbol indicates that the column needs to have that exact value, but "greater-than", "lesser-than", and other symbols are acceptable too. The currently accepted operators are:

-   **==**: Denotes exact equivalence. This should be used for categorical or character variables.
-   **>**: Denotes "greater-than". This can be used for numeric, integer, or date-type variables. Note that it is exclusive of the value used in the expression.
-   **<**: Denotes "lesser-than". This can be used for numeric, integer, or date-type variables. Note that it is exclusive of the value used in the expression.
-   **>=**:Denotes "greater-than-or-equal-to". This can be used for numeric, integer, or date-type variables. Note that it is inclusive of the value used in the expression.
-   **<=**:Denotes "lesser-than". This can be used for numeric, integer, or date-type variables. Note that it is inclusive of the value used in the expression.

If the rule is only for selecting rows, leave the `select` column blank (or `NA`).

Some examples are given below:

1.  Selecting only the rows where the value of `siteID` is exactly equal to "ottawa-1" in the `samples` table.

    | ruleId | ... | table   | select   | filter               | ... |
    |--------|-----|---------|----------|----------------------|-----|
    | 1      | ... | samples | NA       | siteID == "ottawa-1" | ... |
    
2.  Selecting only the rows where the value of "Collection period" (`collPer`) is greater than or equal to 5 in the `samples` table.

    | ruleId | ... | table   | select   | filter               | ... |
    |--------|-----|---------|----------|----------------------|-----|
    | 2      | ... | samples | NA       | collPer >= 5         | ... |

3.  Selecting only the rows where the value of "Collection period" (`collPer`) is less than 5 in the `samples` table.    

    | ruleId | ... | table   | select   | filter               | ... |
    |--------|-----|---------|----------|----------------------|-----|
    | 3      | ... | samples | NA       | collPer < 5          | ... |

4.  Selecting only the rows where the value of "Analysis date end" (`aDateEnd`) is exactly equal to February 1st, 2022 (2022-02-01) from the `measures` table.    

    | ruleId | ... | table    | select   | filter                 | ... |
    |--------|-----|----------|----------|------------------------|-----|
    | 4      | ... | measures | NA       | aDateEnd == 2022-02-01 | ... |

Logical operators can be used to to specify a series or range of values for filtering. Currently supported is the "&" symbol and the "|" symbol that represent the "AND" and "OR" operators respectively. For example:

5.  Selecting only the rows where the value of "Analysis date end" (`aDateEnd`) is a date in February from the `measures` table.    

    | ruleId | ... | table    | select   | filter                                          | ... |
    |--------|-----|----------|----------|-------------------------------------------------|-----|
    | 5      | ... | measures | NA       | aDateEnd >= 2022-02-01 & aDateEnd <= 2022-02-28 | ... |

6.  Selecting only the rows where the value of "Analysis date end" (`aDateEnd`) is exactly equal to February 1st, 2022 (2022-02-01) or February 1st, 2023 (2023-02-01) from the `measures` table.    

    | ruleId | ... | table    | select   | filter                                            | ... |
    |--------|-----|----------|----------|---------------------------------------------------|-----|
    | 6      | ... | measures | NA       | aDateEnd == 2022-02-01 | aDateEnd == 2023-02-01 | ... |
    
7.  Selecting only the rows where the value of `siteID` is exactly equal to "ottawa-1" or "laval-1" in the `samples` table.

    | ruleId | ... | table   | select   | filter                                       | ... |
    |--------|-----|---------|----------|----------------------------------------------|-----|
    | 7      | ... | samples | NA       | siteID == "ottawa-1" | siteID == "laval-1" | ... |
    
8.  Selecting only the rows where the value of `siteID` is "ottawa-1" and the collection datetime (`collDT`) was February 1st, 2023 (2023-02-01) from the `samples` table.

    | ruleId | ... | table   | select   | filter                                      | ... |
    |--------|-----|---------|----------|---------------------------------------------|-----|
    | 8      | ... | samples | NA       | siteID == "ottawa-1" & collDT == 2023-02-01 | ... |
    
#### 3.3 Filtering on license type

One special case for filtering is using the license type (`license` in the `datasets` table, or `measureLic` in the `measures` table). This is more useful for data generators and custodians who work with a mix of open and private data. By only filtering on open data, or open data with a specific license, all of the data and metadata that are open can be shared, without needing to specify additional sharing filters. For example, to share all data in a given dataset:

| ruleId | sharedWith | table   | select   | filter                                      | ... |
|--------|------------|---------|----------|---------------------------------------------|-----|
| 1      | all        | all     | all      | license == "open" \|\ measureLic == "open"  | ... |

For an example pulling specificly open measures:

| ruleId | sharedWith | table    | select   | filter                | ... |
|--------|------------|----------|----------|-----------------------|-----|
| 1      | all        | measures | all      | measureLic == "open"  | ... |

## Example Scenarios

In this section we will be working with some data, providing an example scenario for a rule and showing what the rule looks like in practice.

The data we will be working with has two tables from the ODM, **samples** and **sites**. It does not include all the columns present in these tables. The rows in the samples and sites table respectively are shown below:

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

### Basic Example

1.  Share all columns, but select only rows whose site ID in the samples table is "ottawa-1" for Ottawa Public Health (OPH)

    | ruleId | sharedWith | table   | select   | filter                | ... |
    |--------|------------|---------|----------|-----------------------|-----|
    | 1      | OPH        | samples | all      | siteID == "ottawa-1"  | ... |

2.  Share all columns, but select rows from the samples table whose sample material (`saMaterial`) is `rawWW` or `sweSed` for the Public Health Agency of Canada (PHAC)

    | ruleId | sharedWith | table   | select  | filter                                         | ... |
    |--------|------------|---------|---------|------------------------------------------------|-----|
    | 2      | PHAC       | samples | all     | saMaterial == "rawWW" | saMaterial == "sweSed" | ... |

3.  Share all rows, but select the `notes` column from all tables for Laval Public Health (LPH)

    | ruleId | sharedWith | table   | select  | filter   | ... |
    |--------|------------|---------|---------|----------|-----|
    | 3      | LPH        | all     | notes   | NA       | ... |

4.  Share all columns, but select only the rows for samples taken in the year 2021 and who have been marked as 'reportable' for Ottawa Public Health (OPH) and the Public Health Agency of Canada (PHAC)

    | ruleId | sharedWith | table   | select  | filter                                                                 | ... |
    |--------|------------|---------|---------|------------------------------------------------------------------------|-----|
    | 4      | OPH,PHAC   | samples | all     | dateTime >= 2021-01-01 | dateTime <= 2021-12-31 & reportable == "TRUE" | ... |

5.  Select all columns from the samples and sites tables, but only rows from the sites table that belong to the University of Laval for Laval Public Health (LPH)

    | ruleId | sharedWith | table   | select  | filter              | ... |
    |--------|------------|---------|---------|---------------------|-----|
    | 5      | LPH        | samples | all     | NA                  | ... |
    | 6      | LPH        | sites   | all     | siteID == "laval-1" | ... |

### Combining Filter and Select

When specifying the columns to include in the shared data with the `select` column, it is implied that all rows will be included **unless** a filter has also been specified separately. Conversely, specifying the rows you want to include in the `filter` column **does not** specifies that the column used for filtering should be included in the `filtered_data` output. `select` is the only way to specify columns for inclusion. 

As such, if you wanted to share data with Laval Public Health (LPH) with all the columns of the `samples` table, but only for rows for the siteID that belong to the University of Laval, the rules would be:

```         
    | ruleId | sharedWith | table   | select  | filter              | ... |
    |--------|------------|---------|---------|---------------------|-----|
    | 8      | LPH        | samples | all     | siteID == "laval-1" | ... |

```

Similarly, if you only wanted to share the siteID, measure, value, and unit columns for the siteID that belong to the University of Laval, the rules would be:

```         
    | ruleId | sharedWith | table   | select                     | filter              | ... |
    |--------|------------|---------|----------------------------|---------------------|-----|
    | 9      | LPH        | samples | siteID,measure,value, unit | siteID == "laval-1" | ... |
```

If you were to specify the same rule, but not mention `siteID` in the `select` column, as below:

```         
    | ruleId | sharedWith | table   | select              | filter              | ... |
    |--------|------------|---------|---------------------|---------------------|-----|
    | 10     | LPH        | samples | measure,value, unit | siteID == "laval-1" | ... |
```

You would generate a `filtered_data` output with the measure, value, and unit headers for which the siteID in the original data was equal to `laval-1`. The siteID column would not be included in the output, however.

## Sharing CSV Columns

This section summarizes all the columns that are a part of the file

**ruleId**: Mandatory for all rules. Recommended to use sequential integers for naming, but can be a number or a string. If a string, then its recommended to use [snake_case](https://en.wikipedia.org/wiki/Snake_case) - spaces in names are not supported. Each value should be unique across an entire sharing file (`sharing.csv`).

**sharedWith**: The name(s) of the organizations or individuals for this rule. Multiple organizations/individuals can be separated by a `,`. Also supports key word `all`. The organizations here reference the organizations table (`organizationID`), or the contacts table (`contactID`) in the ODM data.

**table**: The name(s) of the tables for this rule. Allowable values are names (partIDs) of the tables separated by a `,` or `all` to select all tables.

**select**: The name(s) of the columns to include in the `filtered_data` output for this rule. Allowable values are names (partIDs) of the columns separated by a `,` or `all` to select all columns.

**filter**: The argument used to filter rows for the `filtered_data` output for this rule. Allowable values are arguments of the stucture "**column name** == **value**", where "column name" is the partID of the column, "value" is a specified value, and the "==" is a symbol to specify the acceptable relationship between "column name" and "value". Logical operators "&" and "|" are also allowed to combine multiple arguments. 

**valid_period**: A date period that specifies the period for which a rule is valid. If the schema is being used outside of the period, this rule will be ignored. Notation for this field can either specify an interval with a lower and upper limit, a specific value, or a combination of the two. We use the mathematical notation to define an [interval](https://en.wikipedia.org/wiki/Interval_(mathematics)).

Examples are:

    -   2021-03-01 : this rule is valid exclusively for one day, March 1st, 2021.

    -   (2021-03-01,2021-12-01] :  this rule is valid between March 1st 2021 and December 1st 2021, excluding March 1st 2021 but inclusive of December 1st.

    -   [2021-03-01,2021-12-01) : this rule is valid between March 1st 2021 and December 1st 2021, including March 1st 2021 but exclusive of December 1st.

    -   (2021-03-01,2021-12-01) : this rule is valid between March 1st 2021 and December 1st 2021, excluding both March 1st 2021 and December 1st.

    -   [2021-03-01,2021-12-01] : this rule is valid between March 1st 2021 and December 1st 2021, including both March 1st 2021 and December 1st.

    Additionally, the **inf** keyword can be used to specify infinity either as the lower or upper bound. Combination of values within this column can be entered in by using the **,** symbol again. For example:

    -   [2021-12-01, inf) : this rule is valid from December 1st 2021 to infinity, including December 1st 2021.

**status**: Reflects whether a rule is currently in use. Possible values are either `active` or `deprecated`. If the schema being used has a rule where status is marked as `deprecated`, this rule will be ignored.

**firstReleased**: A date to specify when a rule was made.

**lastUpdated**: A date to specify when a rule was last edited or updated.

**changes**: A free-text field to record changes made at the last update to the rule.

**notes**: An optional, free-text description or notes explaining this rule, or other related information deemed worthy of sharing.

## Sharing Metadata CSV Columns

This section summarizes all the columns that are a part of the file

**name**: the name given to a sharing schema. This is less important for data custodians/generators who only use a single schema, but these are unique names for each `sharing.csv` for each group or dataset. For naming, it is recommended to use [snake_case](https://en.wikipedia.org/wiki/Snake_case) - spaces in names are not supported. Each value should be unique across an entire sharing metadata file (`sharing_metadata.csv`).

**datasetID**: The dataset(s) for which a given sharing schema applies. Multiple datasets can be separated by a `,`. The dataset(s) here reference the datasets table (`datasetID`) in the ODM data.

**version**: The version number of a given sharing schema. Version numbering should be updated with each change, ideally following [semantic versioning](https://semver.org) structure. Given a version number "x.y.z", or "1.0.0", for example. The meaning of a change to each of these numbers based on position is: MAJOR.MINOR.PATCH. MAJOR version updates are when rules are added or removed, MINOR version updates are when when you are editing rules, and PATCH version updates are when you tweak the `status` or `valid_period` columns.

**organizationID**: The organization who created a given sharing schema. The organization here should reference the organizations table (`organizationID`) in the ODM data.

**contactID**: The contact information for the person who created a given sharing schema. The contact here references the contacts table (`contactID`) in the ODM data.

**firstReleased**: A date to specify when the sharing schema was made.

**lastUpdated**: A date to specify when the sharing schema was last edited or updated.

**changes**: A free-text field to record changes made at the last update to the sharing schema.

**notes**: An optional, free-text description or notes explaining details about the sharing schema, or other related information deemed worthy of sharing.

An example of this table is found below. For this example, the university lab records data for two different municipalities, and has separate datasetIDs for data from the different municipalities. To make their workflow clearer, they've also opted to created separate sharing schemas for the separate datsets.

| name           | datasetID     | version | organizationID  | contactID    |firstReleased|lastUpdated|changes                              | notes |
|----------------|---------------|---------|-----------------|--------------|-------------|-----------|-------------------------------------|-------|
| ottawaSharingA |cityAReportData| 1.1.0   | university-1    | lastnamePer  |2022-02-01   |2023-03-01 | Deprecated outdated rules for city A| NA    | 
| ottawaSharingB |cityBReportData| 1.2.0   | university-1    | lastnamePer  |2022-03-15   |2023-03-01 | Changed outdated rules for city B   | NA    |

# Implementation

## Function Signature

The function which implements the sharing feature takes three arguments:

1.  `data`: A series of tables from PHES-ODM formatted data. The data input does not have to contain all the entities defined in the ODM, but can only contain those on which the sharing rules should be applied. An example is shown below,

**measures** 
| measureRepID | sampleID | measure | value  | unit | aggregation |
|--------------|------------|-------|--------|------|-------------|
| ottWW100     | pgsOttS100 | covN1 | 0.0023 | gcml | sin         |
| ottWW101     | pgsOttS101 | covN1 | 0.0402 | gcml | sin         |

**samples** 
| sampleID   | siteID   | collDT                | saMaterial  |
|------------|----------|-----------------------|-------------|
| pgsOttS100 | ottawa-1 | 2021-02-01 9:00:00 PM | rawWW       |
| pgsOttS101 | ottawa-1 | 2021-02-01 9:00:00 PM | rawWW       |
| pgsOttS102 | ottawa-1 | 2021-02-26 9:00:00 PM | rawWW       |

**organizations**
| organizationID | name                 | orgType |
|----------------|----------------------|---------| 
| lab100         | University L100 Lab  | academ  | 
| lab101         | University L101 Lab  | academ  |

The above `data` example has three tables, **measures**, **samples**, and **organizations**, with each table containing two or three rows. The table names (partIDs) as specified in the ODM should match the input file names. The names of the columns and their value types should match up with their specification (including the named partID) in the ODM.

2.  `sharing_rules`: The tabular `sharing.csv` containing the sharing rules to be applied to the data. Each item must reference a table (or multiple tables), and reference some or all of the fields as defined in the data above. An example is shown below,


| ruleId | sharedWith | table   | select   | filter               | valid_period           | status|firstReleased|lastUpdated|changes | notes      |
|--------|------------|---------|----------|----------------------|------------------------|-------|-------------|-----------|--------|------------|
| 1      | public,PHAC| all     | all      | NA                   | [2022-02-01,2025-01-31]|active | 2022-02-01  |2022-02-01 | added  |link to DSA |
| 2      | public     | samples | NA       | collDT >= 2021-01-25 & collDT > 2021-02-26| NA|active | 2021-02-01  |2022-02-01 | added  | NA         |
| 3      | public,PHAC| samples | NA       | sampleID == "pgsOttS101"\|\ sampleID == "pgsOttS102"|NA|active | 2022-02-01|2022-02-01|added|NA       |


The above `sharing_rules` example contains three rules to apply to the data.


3.  `organization`: A string containing the name of the organization or individual for whom the filtered data will be shared with. The value of this argument should match up with an organization provided in the `sharing_rules` column, `sharedWith` and the `organizationID` in the `organizations` table or `contactID` in the `contacts` table.

The function will return one dataset output (either xlsx file or series of csv files) per organization/individual named in `organization`. This will be the `filtered_data`, with the example shown below:

-   **filtered_data**: The data to share with an organization. This is a copy of the `data` parameter with the columns and rows that meet the inclusion rules defined in the sharing rules for the passed organization. It has the same structure as the `data` argument described above. To continue our example:

**FOR: PUBLIC** 

**measures** 
| measureRepID | sampleID.  | measure | value  | unit | aggregation |
|--------------|------------|---------|--------|------|-------------|
| ottWW101     | pgsOttS101 | covN1   | 0.0402 | gcml | sin         |

**samples** 
| sampleID   | siteID   | collDT                 | saMaterial |
|------------|----------|------------------------|------------|
| pgsOttS101 | ottawa-1 | 2021-02-01 9:00:00 PM  | rawWW      |

**organizations** 
| organizationID | name                 | orgType |
|----------------|----------------------|---------| 
| lab100         | University L100 Lab  | academ  | 
| lab101         | University L101 Lab  | academ  |

**FOR: PHAC** 

**measures** 
| measureRepID | sampleID | measure | value | unit | aggregation |
|--------------|------------|---------|---------|------|-------------|
| ottWW101 | pgsOttS101 | covN1 | 0.0402 | gcml | sin |

**samples** 
| sampleID | siteID | collDT | saMaterial |
|------------|----------|------------------------|------------| 
| pgsOttS101 | ottawa-1 | 2021-02-01 9:00:00 PM | rawWW | 
| pgsOttS102 | ottawa-1 | 2021-02-26 9:00:00 PM | rawWW |

**organizations** 
| organizationID | name | orgType |
|------------------|----------------------|---------| 
| lab100 | University L100 Lab | academ | 
| lab101 | University L101 Lab | academ |

The above data can then be exported as two separate excel files (or sets of csv files), with one for the public and one for PHAC.

-   **sharing_summary**: A tabular breakdown of entities for whom sharing data was generated, and for each organization it lists the ruleIDs of the applied rules, the tables included in the shared data, and the number of rows for each shared table. An example is shown below:

**summary_table:** 
| destination_org | rule_ids_used | tables_shared | number_rows_output |
|-----------------|---------------|---------------|--------------------|
| public          | 1,2,3         | measures      | 1                  | 
| public          | 1,2,3         | samples       | 1                  | 
| public          | 1,2,3         | organizations | 2                  | 
| PHAC            | 1,3           | measures      | 1                  | 
| PHAC            | 1,3           | samples       | 2                  | 
| PHAC            | 1,3           | organizations | 2                  |

The `sharing_summary` table should be shared with the `filtered_data` output, along with the `sharing.csv` file and the `sharing_metadata` file.
        
Describing the example above,

1.  For the rule with ID 1, it says for the Public and for PHAC to include all tables and columns. So all tables and columns were included in the output `filtered_data`, with only the rows that matched inclusion criteria. If no filtration on rows was provided, the column-based rules set the definition to include all rows in the included columns.
2.  The For the rule with ID 2, only for the public, an additional row was filtered out of **samples** as one the of entries did not match the inclusion criteria for the collection date.
3.  The final rule said that for the Public and for PHAC the rows with the **sampleID** of "pgsOttS101" or "pgsOttS102" were included across all tables. In this case, this meant both the `measures` table and the `samples` table. This meant that only one row that met this criteria in the **measures** table was included, and the two rows from the **samples** table that met that criteria were included.

