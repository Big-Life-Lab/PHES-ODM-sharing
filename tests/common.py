import unittest
from os.path import abspath, dirname


def readfile(path: str) -> str:
    with open(path) as f:
        return f.read()


class OdmTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.maxDiff = None

    def setUp(self) -> None:
        self.dir = dirname(abspath(__file__))
