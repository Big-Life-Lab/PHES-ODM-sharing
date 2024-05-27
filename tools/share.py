from typing import List
from typing_extensions import Annotated
from enum import Enum

import typer

import odm_sharing.sharing as sh


class OutFmt(str, Enum):
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


app = typer.Typer()


@app.command()
def main(
    schema: str = typer.Argument(default=..., help=SCHEMA_DESC),
    input: str = typer.Argument(default='', help=INPUT_DESC),
    orgs: List[str] = typer.Option(default=[], help=ORGS_DESC),
    outfmt: OutFmt = typer.Option(default=OutFmt.EXCEL, help=OUTFMT_DESC),
    outdir: str = typer.Option(default='./', help=OUTDIR_DESC),
    debug: Annotated[bool, typer.Option("-d", "--debug",
                                        help=DEBUG_DESC)] = False,
) -> None:
    if False:
        for org, tabledata in sh.extract(input, schema, orgs).items():
            print(org)
            for table, data in tabledata.items():
                print(table)
    else:
        # temporary functionality
        sh.parse(schema)


if __name__ == '__main__':
    app()
