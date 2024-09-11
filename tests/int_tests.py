import os
import unittest
from os.path import exists, join
from pathlib import Path
from tempfile import TemporaryDirectory

from odm_sharing.tools.share import OutFmt, share

from common import OdmTestCase, readfile


def _remove_file(path):
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


class DelatollaIntTests(OdmTestCase):
    def setUp(self):
        super().setUp()
        self.delatolla_dir = join(self.dir, 'int', 'delatolla')
        self.dbname = 'data.sqlite'
        self.dbpath = join(self.delatolla_dir, self.dbname)

        # remove db from previous run
        _remove_file(self.dbpath)

    def _test_impl(self, data_filename) -> None:
        data_path = join(self.delatolla_dir, data_filename)
        schema_path = join(self.delatolla_dir, 'schema.csv')
        with TemporaryDirectory() as tmpdir:
            paths = share(schema_path, data_path, outdir=tmpdir,
                          outfmt=OutFmt.CSV)
            for path in paths:
                actual = readfile(path)
                fn = Path(path).name
                expected = readfile(join(self.delatolla_dir, 'expected', fn))
                self.assertEqual(actual, expected)

    def test(self) -> None:

        # test excel
        os.environ['ODM_TEMP_DB'] = self.dbpath
        self._test_impl('data.xlsx')

        # test sqlite using the db generated from the excel file (to save time)
        self._test_impl(self.dbname)


class MiscIntTests(OdmTestCase):
    def test_outdir_creation(self) -> None:
        with TemporaryDirectory() as tmpdir:
            subdir = join(tmpdir, 'mysubdir')
            schema_path = join(self.dir, 'common', 'passthrough-schema.csv')
            data_path = join(self.dir, 'common', 'mytable.csv')
            self.assertFalse(exists(subdir))
            share(schema_path, data_path, outdir=subdir)
            self.assertTrue(exists(subdir))


if __name__ == '__main__':
    unittest.main()
