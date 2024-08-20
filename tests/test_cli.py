import unittest
from os.path import join
from tempfile import TemporaryDirectory
from typing import List

from odm_sharing.tools.share import OutFmt, share

from common import OdmTestCase, readfile


def share_csv(schema_path, data_path) -> List[str]:
    with TemporaryDirectory() as dir:
        share(schema_path, data_path, outdir=dir)
        outfile = join(dir, 'mytable-OHRI.csv')
        return readfile(outfile)


def share_excel(schema_path, data_path, outfmt) -> List[str]:
    with TemporaryDirectory() as dir:
        outfiles = share(schema_path, data_path, outdir=dir, outfmt=outfmt)
        return readfile(outfiles[0])


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


if __name__ == '__main__':
    unittest.main()
