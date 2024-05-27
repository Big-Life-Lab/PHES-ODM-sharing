import unittest
# from pprint import pprint

import odm_sharing.private.trees as trees
from odm_sharing.private.rules import ParseError, Rule, RuleMode, load
from odm_sharing.private.trees import parse


class TestParseList(unittest.TestCase):
    def setUp(self) -> None:
        self.ctx = trees.Ctx('test')

    def test_no_constraint(self) -> None:
        trees.parse_list(self.ctx, 'a')
        trees.parse_list(self.ctx, 'a;b')

    def test_absolute(self) -> None:
        trees.parse_list(self.ctx, 'a', 1, 1)
        trees.parse_list(self.ctx, 'a;b', 2, 2)
        with self.assertRaises(ParseError):
            trees.parse_list(self.ctx, 'a;b;c', 2, 2)

    def test_min_only(self) -> None:
        trees.parse_list(self.ctx, 'a', 1)
        trees.parse_list(self.ctx, 'a;b', 1)
        with self.assertRaises(ParseError):
            trees.parse_list(self.ctx, 'a', 2)

    def test_not_in_range(self) -> None:
        trees.parse_list(self.ctx, 'a', 1, 2)
        trees.parse_list(self.ctx, 'a;b', 2, 3)
        trees.parse_list(self.ctx, 'a;b;c', 2, 3)
        with self.assertRaises(ParseError):
            trees.parse_list(self.ctx, '', 1, 2)
        with self.assertRaises(ParseError):
            trees.parse_list(self.ctx, 'a;b', 3, 10)


def get_actual(schema_path: str) -> str:
    rules = load(schema_path)
    tree = parse(rules)
    return tree.__repr__()


class TestParse(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.maxDiff = None

    def test_simple(self) -> None:
        rules = [
            Rule(id=1, table='t', mode=RuleMode.SELECT, value='all'),
            Rule(id=2, table='t', mode=RuleMode.FILTER, key='a', operator='=',
                 value='x'),
            Rule(id=3, table='', mode=RuleMode.SHARE, key='OHRI', value='1;2'),
        ]
        tree = parse(rules, filename='test')
        actual = tree.__repr__()
        expected = '''(0, root, '')
    (3, share, 'OHRI')
        (1, table, 't')
            (1, select, 'all')
            (2, filter, '=')
                (2, field, 'a')
                (2, literal, 'x')
'''
        self.assertEqual(actual, expected)

    def test_select_one(self) -> None:
        actual = get_actual('tests/3.1.1.csv')
        expected = '''(0, root, '')
    (2, share, 'ohri')
        (1, table, 'samples')
            (1, select, '')
                (1, literal, 'saMaterial')
'''
        self.assertEqual(actual, expected, actual)

    def test_select_two(self) -> None:
        actual = get_actual('tests/3.1.2.csv')
        expected = '''(0, root, '')
    (2, share, 'ohri')
        (1, table, 'measures')
            (1, select, '')
                (1, literal, 'reportable')
                (1, literal, 'pooled')
'''
        self.assertEqual(actual, expected, actual)

    def test_select_all(self) -> None:
        actual = get_actual('tests/3.1.3.csv')
        expected = '''(0, root, '')
    (2, share, 'ohri')
        (1, table, 'measures')
            (1, select, 'all')
'''
        self.assertEqual(actual, expected, actual)

    def test_select_multiple_tables(self) -> None:
        actual = get_actual('tests/3.1.4.csv')
        expected = '''(0, root, '')
    (2, share, 'ohri')
        (1, table, 'measures')
            (1, select, '')
                (1, literal, 'purposeID')
        (1, table, 'samples')
            (1, select, '')
                (1, literal, 'purposeID')
'''
        self.assertEqual(actual, expected, actual)

    def test_filter(self) -> None:
        actual = get_actual('tests/3.2.csv')
        expected = '''(0, root, '')
    (9, share, 'ohri')
        (1, table, 'samples')
            (1, select, 'all')
            (7, group, 'and')
                (2, filter, '=')
                    (2, field, 'siteID')
                    (2, literal, 'ottawa-1')
                (3, filter, '>=')
                    (3, field, 'collPer')
                    (3, literal, '5')
                (4, filter, '<=')
                    (4, field, 'collPer')
                    (4, literal, '5')
        (1, table, 'measures')
            (1, select, 'all')
            (8, group, 'and')
                (5, filter, '=')
                    (5, field, 'aDateEnd')
                    (5, literal, '2022-02-01')
                (6, filter, 'in')
                    (6, field, 'aDateEnd')
                    (6, literal, '2022-02-01')
                    (6, literal, '2022-02-28')
'''
        self.assertEqual(actual, expected)

    def test_group_or(self) -> None:
        actual = get_actual('tests/4.1.csv')
        expected = '''(0, root, '')
    (15, share, 'ohri')
        (11, table, 'measures')
            (11, select, 'all')
            (14, group, 'or')
                (12, filter, '=')
                    (12, field, 'aDateEnd')
                    (12, literal, '2022-02-01')
                (13, filter, '=')
                    (13, field, 'aDateEnd')
                    (13, literal, '2023-02-01')
'''
        self.assertEqual(actual, expected)

    def test_group_and(self) -> None:
        actual = get_actual('tests/4.3.csv')
        expected = '''(0, root, '')
    (15, share, 'ohri')
        (11, table, 'samples')
            (11, select, 'all')
            (14, group, 'and')
                (12, filter, '=')
                    (12, field, 'siteID')
                    (12, literal, 'ottawa-1')
                (13, filter, '=')
                    (13, field, 'collDT')
                    (13, literal, '2023-02-01')
'''
        self.assertEqual(actual, expected)

    def test_group_or_and(self) -> None:
        actual = get_actual('tests/4.4.csv')
        expected = '''(0, root, '')
    (19, share, 'ohri')
        (11, table, 'measures')
            (11, select, '')
                (11, literal, 'measure')
                (11, literal, 'value')
                (11, literal, 'unit')
                (11, literal, 'aggregation')
            (18, group, 'or')
                (14, group, 'and')
                    (12, filter, '=')
                        (12, field, 'measure')
                        (12, literal, 'mPox')
                    (13, filter, 'in')
                        (13, field, 'reportDate')
                        (13, literal, '2021-01-01')
                        (13, literal, '2021-12-31')
                (17, group, 'and')
                    (15, filter, '=')
                        (15, field, 'measure')
                        (15, literal, 'cov')
                    (16, filter, '>=')
                        (16, field, 'reportDate')
                        (16, literal, '2020-01-01')
'''
        self.assertEqual(actual, expected)

    def test_share_multi(self) -> None:
        actual = get_actual('tests/5.1.csv')
        expected = '''(0, root, '')
    (31, share, 'OPH')
        (11, table, 'measures')
            (11, select, 'all')
            (14, group, 'or')
                (12, filter, '=')
                    (12, field, 'aDateEnd')
                    (12, literal, '2022-02-01')
                (13, filter, '=')
                    (13, field, 'aDateEnd')
                    (13, literal, '2023-02-01')
        (15, table, 'samples')
            (15, select, 'all')
    (31, share, 'PHAC')
        (11, table, 'measures')
            (11, select, 'all')
            (14, group, 'or')
                (12, filter, '=')
                    (12, field, 'aDateEnd')
                    (12, literal, '2022-02-01')
                (13, filter, '=')
                    (13, field, 'aDateEnd')
                    (13, literal, '2023-02-01')
        (15, table, 'samples')
            (15, select, 'all')
    (32, share, 'LPH')
        (11, table, 'measures')
            (11, select, 'all')
            (14, group, 'or')
                (12, filter, '=')
                    (12, field, 'aDateEnd')
                    (12, literal, '2022-02-01')
                (13, filter, '=')
                    (13, field, 'aDateEnd')
                    (13, literal, '2023-02-01')
        (15, table, 'samples')
            (15, select, 'all')
            (18, group, 'or')
                (16, filter, '=')
                    (16, field, 'siteID')
                    (16, literal, 'ottawa-1')
                (17, filter, '=')
                    (17, field, 'siteID')
                    (17, literal, 'laval-1')
'''
        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
