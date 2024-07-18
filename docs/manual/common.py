import pandas as pd
from tabulate import tabulate


SCHEMA = 'assets/minimal/schema.csv'
DATA = 'assets/minimal/measures.csv'


def load_csv_md(path):
    '''read csv file and convert it to markdown'''
    df = pd.read_csv(path, keep_default_na=False)
    md = tabulate(df, headers=df.columns.to_list(), showindex=False)
    return md


def print_file(path):
    with open(path, 'r') as f:
        print(f.read())
