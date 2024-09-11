import unittest

import odm_sharing.private.cons as cons

from common import OdmTestCase


class TestCons(OdmTestCase):
    def test_detect_sqlalchemy(self) -> None:
        valid_urls = [
            'postgresql+pg8000://dbuser:kx%40jj5%2Fg@pghost10/appdb',
            'postgresql://scott:tiger@localhost/mydatabase',
            'postgresql+psycopg2://scott:tiger@localhost/mydatabase',
            'postgresql+pg8000://scott:tiger@localhost/mydatabase',
            'mysql://scott:tiger@localhost/foo',
            'mysql+mysqldb://scott:tiger@localhost/foo',
            'mysql+pymysql://scott:tiger@localhost/foo',
            'oracle://scott:tiger@127.0.0.1:1521/sidname',
            'oracle+cx_oracle://scott:tiger@tnsname',
            'mssql+pyodbc://scott:tiger@mydsn',
            'mssql+pymssql://scott:tiger@hostname:8080/dbname',
            'sqlite:///foo.db',
            'sqlite:////absolute/path/to/foo.db',
            'sqlite:///C:\\path\\to\\foo.db',
            r'sqlite:///C:\path\to\foo.db',
            'sqlite://',
        ]
        for path in valid_urls:
            self.assertTrue(cons._detect_sqlalchemy(path))

        invalid_urls = [
            'myfile.db',
            'x:/',
            '',
        ]
        for path in invalid_urls:
            self.assertFalse(cons._detect_sqlalchemy(path))


if __name__ == '__main__':
    unittest.main()
