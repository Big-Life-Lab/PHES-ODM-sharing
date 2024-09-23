import contextlib
import logging
import os
import sys
from collections import namedtuple
from enum import Enum
from itertools import zip_longest
from os import linesep
from pathlib import Path
from typing import Dict, List, Set, TextIO, Union
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
from odm_sharing.private.cons import DataSource


FilePath = namedtuple('FilePath', ['abspath', 'relpath', 'filename'])


class OutFmt(str, Enum):
    '''output format'''
    AUTO = 'auto'
    CSV = 'csv'
    EXCEL = 'excel'


INPUT_DESC = 'Input spreadsheet file-path(s) or SQLAlchemy database-url.'
LIST_DESC = 'Write output file-paths to STDOUT, separated by newlines.'
OUTDIR_DESC = 'Output directory.'
OUTFMT_DESC = 'Output format.'
QUIET_DESC = 'Don\'t log to STDOUT.'
SCHEMA_DESC = 'Sharing schema file path.'

TABLES_DESC = '''Comma separated list of tables associated with (CSV) input
files. Ex.: --tables=measures,samples'''

DEBUG_DESC = '''Output debug info to STDOUT (and ./debug.txt) instead of
creating sharable output files. This shows which tables and columns are
selected, and how many rows each filter returns.'''

ORGS_DESC = '''Comma separated list of organizations to share with, defaults to
all. Ex.: --orgs=OHRI,TOH'''

# default cli args
DEBUG_DEFAULT = False
LIST_DEFAULT = False
ORGS_DEFAULT: List[str] = []
OUTDIR_DEFAULT = './'
OUTFMT_DEFAULT = OutFmt.AUTO
QUIET_DEFAULT = False
TABLES_DEFAULT: str = ''

app = typer.Typer(pretty_exceptions_show_locals=False)


def error(msg: str) -> None:
    print(msg, file=sys.stderr)
    logging.error(msg)


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
    for col in columns:
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


def gen_filepath(outdir: str, schema_name: str, org: str, table: str, ext: str
                 ) -> FilePath:
    parts = [schema_name, org] + ([table] if table else [])
    filename = '-'.join(parts) + f'.{ext}'
    abspath = os.path.join(outdir, filename)
    relpath = os.path.relpath(abspath, os.getcwd())
    return FilePath(abspath=abspath, relpath=relpath, filename=filename)


def get_debug_writer(debug: bool) -> Union[TextIO, contextlib.nullcontext]:
    # XXX: this function is only used for brewity with the below `with` clause
    if debug:
        return open('debug.txt', 'w')
    else:
        return contextlib.nullcontext()


def infer_outfmt(path: str) -> OutFmt:
    '''returns None when not recognized'''
    (_, ext) = os.path.splitext(path)
    if ext == '.csv':
        return OutFmt.CSV
    else:
        return OutFmt.EXCEL


def parse_input_datasources(paths: List[str], tables: List[str] = [],
                            ) -> List[DataSource]:
    pairs = zip_longest(tables, paths, fillvalue='')
    return seq(pairs)\
        .map(lambda p: DataSource(table=p[0], path=p[1]))\
        .list()


def share(
    schema: str,
    data_sources: List[DataSource],
    orgs: List[str] = ORGS_DEFAULT,
    outfmt: OutFmt = OUTFMT_DEFAULT,
    outdir: str = OUTDIR_DEFAULT,
    debug: bool = DEBUG_DEFAULT,
) -> List[str]:
    '''returns list of output files'''
    schema_path = schema
    schema_filename = Path(schema_path).name
    schema_name = Path(schema_path).stem
    first_input = data_sources[0].path
    if outfmt == OutFmt.AUTO:
        outfmt = infer_outfmt(first_input)
        logging.info(f'inferred output format as {outfmt}')

    logging.info(f'loading schema {qt(schema_filename)}')
    try:
        ruleset = rules.load(schema_path)
        ruletree = trees.parse(ruleset, orgs, schema_filename)
        org_queries = queries.generate(ruletree)
        table_filter = get_tables(org_queries)
    except rules.ParseError:
        # XXX: error messages are already printed at this point
        return []

    # XXX: only tables found in the schema are considered in the data source
    logging.info('connecting...')
    con = cons.connect(data_sources, table_filter)

    # create outdir
    os.makedirs(outdir, exist_ok=True)

    # one debug file per run
    output_paths = []
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
            excel_path = gen_filepath(outdir, schema_name, org, '', 'xlsx')
            excel_file = None
            if not debug and outfmt == OutFmt.EXCEL:
                excel_file = pd.ExcelWriter(excel_path.abspath,
                                            engine='openpyxl')
                logging.info('writing ' + excel_path.relpath)
            try:
                for table, data in org_data.items():
                    if outfmt == OutFmt.CSV:
                        p = gen_filepath(outdir, schema_name, org, table,
                                         'csv')
                        logging.info('writing ' + p.relpath)
                        data.to_csv(p.abspath, index=False)
                        output_paths.append(p.relpath)
                    elif outfmt == OutFmt.EXCEL:
                        logging.info(f'- {qt(table)}')
                        data.to_excel(excel_file, sheet_name=table,
                                      index=False)
                    else:
                        assert False, f'format {outfmt} not impl'
            except IndexError:
                # XXX: this is thrown from excel writer when nothing is written
                # XXX: no need to return paths since excel file didn't finish
                assert outfmt == OutFmt.EXCEL
                error('failed to write output, most likely due to empty input')
                return []
            finally:
                if excel_file:
                    excel_file.close()
            if excel_file:
                output_paths.append(excel_path.relpath)
    logging.info('done')
    return output_paths


@app.command()
def main_cli(
    schema: str = typer.Argument(default=..., help=SCHEMA_DESC),
    inputs: List[str] = typer.Argument(default=..., help=INPUT_DESC),
    tables: str = typer.Option(default=TABLES_DEFAULT, help=TABLES_DESC),
    orgs: List[str] = typer.Option(default=ORGS_DEFAULT, help=ORGS_DESC),
    outfmt: OutFmt = typer.Option(default=OUTFMT_DEFAULT, help=OUTFMT_DESC),
    outdir: str = typer.Option(default=OUTDIR_DEFAULT, help=OUTDIR_DESC),
    debug: Annotated[bool, typer.Option("-d", "--debug",
                                        help=DEBUG_DESC)] = DEBUG_DEFAULT,
    quiet: Annotated[bool, typer.Option("-q", "--quiet",
                                        help=QUIET_DESC)] = QUIET_DEFAULT,
    list_output: Annotated[bool, typer.Option("-l", "--list",
                                              help=LIST_DESC)] = LIST_DEFAULT,
) -> None:
    if not quiet:
        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    table_list = tables.strip().split(',')
    data_sources = parse_input_datasources(inputs, table_list)
    paths = share(schema, data_sources, orgs, outfmt, outdir, debug)
    if list_output:
        cwd = os.getcwd()
        relpaths = seq(paths).map(lambda abs: os.path.relpath(abs, cwd))
        print(linesep.join(relpaths))


def main() -> None:
    # runs main_cli
    app()


if __name__ == '__main__':
    main()
