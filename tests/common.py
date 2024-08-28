import unittest
from os.path import abspath, dirname


class OdmTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.maxDiff = None

    def setUp(self) -> None:
        self.dir = dirname(abspath(__file__))
