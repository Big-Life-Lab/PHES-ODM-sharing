import unittest

import odm_sharing.private.queries as queries
import odm_sharing.private.rules as rules
import odm_sharing.private.trees as trees
from odm_sharing.private.rules import Rule, RuleMode


class TestQueries(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.maxDiff = None

    def test_in_interval_and_gte(self) -> None:
        ruleset = rules.load('tests/4.4.csv')
        ruletree = trees.parse(ruleset)
        q = queries.generate(ruletree)['ohri']['measures']

        actual_sql = q.data_query.sql
        expected_sql = (
            'SELECT "measure","value","unit","aggregation" ' +
            'FROM "measures" ' +
            'WHERE (' + (
                '(("measure" = ?) AND ("reportDate" BETWEEN ? AND ?)) ' +
                'OR ' +
                '(("measure" = ?) AND ("reportDate" >= ?))'
            ) +
            ')'
        )
        self.assertEqual(actual_sql, expected_sql)

        actual_args = q.data_query.args
        expected_args = ['mPox', '2021-01-01', '2021-12-31',
                         'cov', '2020-01-01']
        self.assertEqual(actual_args, expected_args)

    def test_in_set(self) -> None:
        ruleset = rules.load('tests/filter-set.csv')
        ruletree = trees.parse(ruleset)
        q = queries.generate(ruletree)['PHAC']['samples']
        actual_sql = q.data_query.sql
        expected_sql = (
            'SELECT * ' +
            'FROM "samples" ' +
            'WHERE ("saMaterial" IN (?,?))'
        )
        self.assertEqual(actual_sql, expected_sql)

        actual_args = q.data_query.args
        expected_args = ['rawWW', 'sweSed']
        self.assertEqual(actual_args, expected_args)

    def test_rule_count_args(self) -> None:
        ruleset = [
            Rule(id=1, table='t', mode=RuleMode.SELECT, value='all'),
            Rule(id=2, table='t', mode=RuleMode.FILTER, key='x',
                 operator='=', value='a'),
            Rule(id=3, table='t', mode=RuleMode.FILTER, key='y',
                 operator='in', value='1;2'),
            Rule(id=4, table='', mode=RuleMode.SHARE, key='ohri', value='1;2;3'),
        ]
        ruletree = trees.parse(ruleset)
        q = queries.generate(ruletree)['ohri']['t']
        implicit_group_id = 0
        actual = q.rule_count_queries[implicit_group_id].args
        expected = ['a', '1', '2']
        self.assertEqual(actual, expected)

    def test_share_table_rule_count_queries(self) -> None:
        '''tests that each table of a share rule gets the right count-query'''
        ruleset = [
            Rule(id=1, table='a;b', mode=RuleMode.SELECT, value='all'),
            Rule(id=2, table='a', mode=RuleMode.FILTER, key='x',
                 operator='=', value='1'),
            Rule(id=3, table='b', mode=RuleMode.FILTER, key='y',
                 operator='=', value='1'),
            Rule(id=4, table='', mode=RuleMode.SHARE, key='ohri',
                 value='1;2;3'),
        ]
        share_id = ruleset[-1].id
        ruletree = trees.parse(ruleset)
        q1 = queries.generate(ruletree)['ohri']['a']
        q2 = queries.generate(ruletree)['ohri']['b']
        expected1 = 'SELECT COUNT(*) FROM "a" WHERE ("x" = ?)'
        expected2 = 'SELECT COUNT(*) FROM "b" WHERE ("y" = ?)'
        actual1 = q1.rule_count_queries[share_id].sql
        actual2 = q2.rule_count_queries[share_id].sql
        self.assertEqual(actual1, expected1)
        self.assertEqual(actual2, expected2)


    def test_sanitize(self) -> None:
        '''special characters are stripped, and parameter values separated, to
        prevent injections'''
        injection = '" OR 1=1 --'
        ruleset = [
            Rule(id=1, table='t', mode=RuleMode.SELECT, value=injection),
            Rule(id=2, table='t', mode=RuleMode.FILTER, key=injection,
                 operator='=', value=injection),
            Rule(id=3, table='', mode=RuleMode.SHARE, key='ohri', value='1;2'),
        ]
        ruletree = trees.parse(ruleset)
        q = queries.generate(ruletree)['ohri']['t']
        actual = q.data_query.sql
        expected = 'SELECT "OR11" FROM "t" WHERE ("OR11" = ?)'
        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()