import inspect
from os.path import abspath, dirname, join
from shutil import copy2
from typing import List

import pandas as pd
from tabulate import tabulate


MODULE_DIR = dirname(abspath(inspect.getfile(inspect.currentframe())))
ASSET_DIR = join(MODULE_DIR, 'assets/minimal/')
SCHEMA = join(ASSET_DIR, 'schema.csv')
DATA = join(ASSET_DIR, 'measures.csv')


def load_csv_md(path):
    '''read csv file and convert it to markdown'''
    df = pd.read_csv(path, keep_default_na=False)
    md = tabulate(df, headers=df.columns.to_list(), showindex=False)
    return md


def print_file(path):
    with open(path, 'r') as f:
        print(f.read())


def copy_assets(filenames: List[str]) -> None:
    '''copies asset to current directory to avoid long paths in examples'''
    for fn in filenames:
        copy2(join(ASSET_DIR, fn), fn)
