import contextlib
import os
import sys
from enum import Enum
from os import linesep
from pathlib import Path
from typing import Dict, List, Optional, Set, TextIO, Union
from typing_extensions import Annotated

import pandas as pd
import typer
from tabulate import tabulate
from functional import seq

import odm_sharing.sharing as sh

import odm_sharing.private.cons as cons
import odm_sharing.private.queries as queries
import odm_sharing.private.rules as rules
import odm_sharing.private.trees as trees
from odm_sharing.private.rules import Rule, RuleId, RuleMode
from odm_sharing.private.utils import qt


class OutFmt(str, Enum):
    '''output format'''
    AUTO = 'auto'
    CSV = 'csv'
    EXCEL = 'excel'


SCHEMA_DESC = 'Sharing schema file path.'
INPUT_DESC = 'Input spreadsheet file-path or SQLAlchemy database-url.'

ORGS_DESC = '''Comma separated list of organizations to share with, defaults to
all.'''

OUTFMT_DESC = 'Output format.'
OUTDIR_DESC = 'Output directory.'

DEBUG_DESC = '''Output debug info to STDOUT (and ./debug.txt) instead of
creating sharable output files. This shows which tables and columns are
selected, and how many rows each filter returns.'''

# default cli args
DEBUG_DEFAULT = False
ORGS_DEFAULT = []
OUTDIR_DEFAULT = './'
OUTFMT_DEFAULT = OutFmt.AUTO

app = typer.Typer(pretty_exceptions_show_locals=False)


def error(msg: str) -> None:
    print(msg, file=sys.stderr)


def write_line(file: TextIO, text: str = '') -> None:
    '''writes a line to STDOUT and file'''
    print(text)
    file.write(text + linesep)


def write_header(file: TextIO, level: int, text: str) -> None:
    '''writes a markdown header'''
    write_line(file, ('#'*level) + f' {text}{linesep}')


def fmt_rule(r: Rule) -> List[str]:
    # [id, mode, filter]
    result = [f'{r.id:>2}', r.mode.value]
    if r.mode == RuleMode.FILTER:
        result.append(f'{r.key} {r.operator} ({r.value})')
    elif r.mode == RuleMode.GROUP:
        result.append(f'{r.operator:3} ({r.value})')
    return result


def write_debug(
    file: TextIO,
    con: cons.Connection,
    org_name: str,
    table_name: str,
    table_query: queries.TableQuery,
    ruleset: Dict[RuleId, Rule]
) -> None:
    '''write debug output'''
    write_header(file, 1, f'org {qt(org_name)} - table {qt(table_name)}')

    (select_id, columns) = sh.get_columns(con, table_query)
    write_header(file, 2, 'columns')
    for col in sorted(columns):
        write_line(file, f'- {col}')
    write_line(file)

    write_header(file, 2, 'counts')
    counts = sh.get_counts(con, table_query)

    # XXX: the rule with ID 0 is not from the input schema, but is generated
    # implicitly during schema parsing, so it's not included in this output
    # table
    count_table = seq(counts.keys())\
        .filter(lambda id: id > 0)\
        .map(lambda id: ruleset[id])\
        .map(lambda r: (counts[r.id],) + tuple(fmt_rule(r)))\
        .list()

    headers = ['count', 'id', 'mode', 'filter']
    write_line(file, tabulate(count_table, headers=headers))
    write_line(file)


def get_tables(org_queries: sh.queries.OrgTableQueries) -> Set[str]:
    '''returns all table names in the query collection'''
    result = set()
    for table_query in org_queries.values():
        for table in table_query.keys():
            result.add(table)
    return result


def gen_filename(in_name: str, org: str, table: str, ext: str) -> str:
    if in_name == table or not table:
        # this avoids duplicating the table name when both input and output is
        # CSV
        return f'{in_name}-{org}.{ext}'
    else:
        return f'{in_name}-{org}-{table}.{ext}'


def get_debug_writer(debug: bool) -> Union[TextIO, contextlib.nullcontext]:
    # XXX: this function is only used for brewity with the below `with` clause
    if debug:
        return open('debug.txt', 'w')
    else:
        return contextlib.nullcontext()


def get_excel_writer(in_name, debug: bool, org: str, outdir: str,
                     outfmt: OutFmt) -> Optional[pd.ExcelWriter]:
    if not debug and outfmt == OutFmt.EXCEL:
        filename = gen_filename(in_name, org, '', 'xlsx')
        print('writing ' + filename)
        excel_path = os.path.join(outdir, filename)
        return pd.ExcelWriter(excel_path)
    else:
        return None


def infer_outfmt(path: str) -> Optional[OutFmt]:
    '''returns None when not recognized'''
    (_, ext) = os.path.splitext(path)
    if ext == '.csv':
        return OutFmt.CSV
    elif ext == '.xlsx':
        return OutFmt.EXCEL


def share(
    schema: str,
    input: str,
    orgs: List[str] = ORGS_DEFAULT,
    outfmt: OutFmt = OUTFMT_DEFAULT,
    outdir: str = OUTDIR_DEFAULT,
    debug: bool = DEBUG_DEFAULT,
) -> None:
    schema_path = schema
    schema_filename = Path(schema_path).name
    in_name = Path(input).stem

    if outfmt == OutFmt.AUTO:
        fmt = infer_outfmt(input)
        if not fmt:
            error('unable to infer output format from input file')
            return
        outfmt = fmt

    print(f'loading schema {qt(schema_filename)}')
    try:
        ruleset = rules.load(schema_path)
        ruletree = trees.parse(ruleset, orgs, schema_filename)
        org_queries = queries.generate(ruletree)
        table_filter = get_tables(org_queries)
    except rules.ParseError:
        # XXX: error messages are already printed at this point
        return

    # XXX: only tables found in the schema are considered in the data source
    print(f'connecting to {qt(input)}')
    con = sh.connect(input, table_filter)

    if debug:
        print()
    # one debug file per run
    with get_debug_writer(debug) as debug_file:
        for org, table_queries in org_queries.items():
            org_data = {}
            for table, tq in table_queries.items():
                assert table in table_filter
                if debug:
                    write_debug(debug_file, con, org, table, tq, ruleset)
                else:
                    org_data[table] = sh.get_data(con, tq)

            # one excel file per org
            excel_file = get_excel_writer(in_name, debug, org, outdir, outfmt)
            try:
                for table, data in org_data.items():
                    if outfmt == OutFmt.CSV:
                        filename = gen_filename(in_name, org, table, 'csv')
                        print('writing ' + filename)
                        path = os.path.join(outdir, filename)
                        data.to_csv(path, index=False)
                    elif outfmt == OutFmt.EXCEL:
                        print(f'- {qt(table)}')
                        data.to_excel(excel_file, sheet_name=table)
                    else:
                        assert False, f'format {outfmt} not impl'
            except IndexError:
                # XXX: this is thrown from excel writer when nothing is written
                error('failed to write output, most likely due to empty input')
                return
            finally:
                if excel_file:
                    excel_file.close()
    print('done')


@app.command()
def main_cli(
    schema: str = typer.Argument(default=..., help=SCHEMA_DESC),
    input: str = typer.Argument(default='', help=INPUT_DESC),
    orgs: List[str] = typer.Option(default=ORGS_DEFAULT, help=ORGS_DESC),
    outfmt: OutFmt = typer.Option(default=OUTFMT_DEFAULT, help=OUTFMT_DESC),
    outdir: str = typer.Option(default=OUTDIR_DEFAULT, help=OUTDIR_DESC),
    debug: Annotated[bool, typer.Option("-d", "--debug",
                                        help=DEBUG_DESC)] = DEBUG_DEFAULT,
) -> None:
    share(schema, input, orgs, outfmt, outdir, debug)


def main():
    # runs main_cli
    app()


if __name__ == '__main__':
    main()
