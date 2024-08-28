import unittest
from os.path import exists, join
from pathlib import Path
from tempfile import TemporaryDirectory

from odm_sharing.tools.share import OutFmt, share

from common import OdmTestCase, readfile


class IntTests(OdmTestCase):
    def test_excel_delatolla(self) -> None:
        delatolla_dir = join(self.dir, 'int', 'delatolla')
        schema_path = join(delatolla_dir, 'schema.csv')
        data_path = join(delatolla_dir, 'data.xlsx')
        with TemporaryDirectory() as tmpdir:
            paths = share(schema_path, data_path, outdir=tmpdir,
                          outfmt=OutFmt.CSV)
            for path in paths:
                actual = readfile(path)
                fn = Path(path).name
                expected = readfile(join(delatolla_dir, 'expected', fn))
                self.assertEqual(actual, expected)

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
