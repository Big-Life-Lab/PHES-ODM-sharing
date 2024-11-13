import unittest
from os.path import join
from tempfile import TemporaryDirectory
from typing import List

from functional import seq
from odm_sharing.tools.share import OutFmt, share
from odm_sharing.private.cons import DataSourceError

from common import OdmTestCase, readfile


def share_csv(schema_path: str, data_path: str) -> List[str]:
    with TemporaryDirectory() as dir:
        outpaths = share(schema_path, [data_path], outdir=dir)
        return readfile(outpaths[0])


def share_excel(schema_path, data_path: str, outfmt) -> List[str]:
    with TemporaryDirectory() as dir:
        outpaths = share(schema_path, [data_path], outdir=dir, outfmt=outfmt)
        return readfile(outpaths[0])


class TestCli(OdmTestCase):
    def test_csv_to_csv(self) -> None:
        schema_path = join(self.dir, 'common', 'passthrough-schema.csv')
        data_path = join(self.dir, 'common', 'mytable.csv')
        src_content = readfile(data_path)
        dst_content = share_csv(schema_path, data_path)
        self.assertEqual(src_content, dst_content)

    def test_excel_to_csv(self) -> None:
        schema_path = join(self.dir, 'common', 'passthrough-schema.csv')
        data_path = join(self.dir, 'common', 'testdata.xlsx')
        src_content = readfile(join(self.dir, 'common', 'mytable.csv'))
        dst_content = share_excel(schema_path, data_path, OutFmt.CSV)
        self.assertEqual(src_content, dst_content)

    def _multi_impl(self, schema_path: str, inputs: List[str], outdir: str):
        outpaths = share(schema_path, inputs, outdir=outdir, outfmt=OutFmt.CSV)
        actual = (''.join(seq(outpaths).map(readfile))).splitlines()
        expected = ['x', 'a', 'x', 'b']
        self.assertEqual(actual, expected)

    def test_multi_csv(self) -> None:
        schema_path = join(self.dir, 'cli', 'multi-schema.csv')
        data_paths = [
            join(self.dir, 'cli', 'mytable1.csv'),
            join(self.dir, 'cli', 'mytable2.csv'),
        ]
        with TemporaryDirectory() as dir:
            self._multi_impl(schema_path, data_paths, dir)

    def test_multi_csv_missing(self) -> None:
        schema_path = join(self.dir, 'cli', 'multi-schema.csv')
        data_paths = [
            join(self.dir, 'cli', 'mytable1.csv'),
        ]
        with TemporaryDirectory() as dir:
            expr = '.*mytable2.*missing'
            with self.assertRaisesRegex(DataSourceError, expr):
                self._multi_impl(schema_path, data_paths, dir)


if __name__ == '__main__':
    unittest.main()
