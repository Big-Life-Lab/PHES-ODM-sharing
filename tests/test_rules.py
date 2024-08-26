import unittest
from os.path import join

import odm_sharing.private.rules as rules
from odm_sharing.private.rules import Rule, RuleMode, SchemaCtx, init_rule

from common import OdmTestCase


class TestRules(OdmTestCase):
    def setUp(self) -> None:
        super().setUp()
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

    def test_dup_ruleid_error(self):
        # trees.parse may throw a misleading error if rules.load doesn't
        # check for duplicate rule-ids
        with self.assertRaisesRegex(rules.ParseError, "already exists"):
            rules.load(join(self.dir, 'rules', 'schema-35.csv'))

    def test_header_whitespace_allowed(self) -> None:
        rules.load(join(self.dir, 'rules', 'schema-33.csv'))


if __name__ == '__main__':
    unittest.main()
