import unittest

import odm_sharing.private.rules as rules
from odm_sharing.private.rules import Rule, RuleMode, SchemaCtx, init_rule


class TestRules(unittest.TestCase):
    def setUp(self) -> None:
        self.ctx = SchemaCtx('test')

    def test_init_rule(self) -> None:
        schema_row = {
            'ruleID': '1',
            'table': 'mytable',
            'mode': 'filter',
            'key': 'x',
            'operator': '=',
            'value': '2',
            'notes': '',
        }
        assert list(schema_row.keys()) == rules.HEADERS
        actual = init_rule(self.ctx, schema_row)
        expected = Rule(id=1, table='mytable', mode=RuleMode.FILTER,
                        key='x', operator='=', value='2')
        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
