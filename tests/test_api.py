import unittest
from os.path import join

import odm_sharing.sharing as sh
from odm_sharing.private.common import F, T

from common import OdmTestCase


class TestApi(OdmTestCase):
    '''test cases related to the whole sharing pipeline'''
    def setUp(self) -> None:
        super().setUp()

    def _test_extract(self, data_relpath: str) -> None:
        schema_path = join(self.dir, 'common', 'passthrough-schema.csv')
        data_path = join(self.dir, 'common', data_relpath)
        df = sh.extract(schema_path, data_path)['OHRI']['mytable']
        self.assertEqual(list(df['bool1']), [T] * 4 + [F])
        self.assertEqual(list(df['bool2']), [F, T] + [''] * 3)
        self.assertEqual(list(df['bool3']), ['', F, T, 'NA', ''])
        self.assertEqual(list(df['bool4']), ['NA'] + [T] * 3 + [F])
        self.assertEqual(list(df['bool5']), [''] * 4 + [F])
        self.assertEqual(list(df['int1']), [0, 1, 2, 3, 4])
        self.assertEqual(list(df['int2']), ['', 'NA', '2', '3', '4'])
        self.assertEqual(list(df['str1']), ['a', 'b', 'c', 'd', 'e'])
        self.assertEqual(list(df['str2']), ['', 'NA', 'c', 'd', 'e'])

    def _test_extract_true(self, data_relpath: str) -> None:
        schema_path = join(self.dir, 'api', 'true-schema.csv')
        data_path = join(self.dir, 'common', data_relpath)
        df = sh.extract(schema_path, data_path)['OHRI']['mytable']
        df = df.set_index('id')
        actual_rows = list(df.itertuples())
        self.assertEqual(len(actual_rows), 1)
        actual = actual_rows[0][1:6]
        expected = (T, '', T, T, '')  # row 4 (incl. header)
        self.assertEqual(actual, expected)

    def _test_extract_strict_subset(self, data_relpath: str) -> None:
        '''test that selecting just a single column works, which is a strict
        subest of all columns and may be less that the code expects.'''
        schema_path = join(self.dir, 'api', 'id-schema.csv')
        data_path = join(self.dir, 'common', data_relpath)
        sh.extract(schema_path, data_path)['OHRI']['mytable']

    def test_csv(self) -> None:
        fn = 'mytable.csv'
        self._test_extract(fn)
        self._test_extract_true(fn)
        self._test_extract_strict_subset(fn)

    def test_excel(self) -> None:
        fn = 'testdata.xlsx'
        self._test_extract(fn)
        self._test_extract_true(fn)
        self._test_extract_strict_subset(fn)


if __name__ == '__main__':
    unittest.main()
