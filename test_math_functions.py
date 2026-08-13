import unittest
from math_functions import add_numbers

class TestMathFunctions(unittest.TestCase):
    def test_add(self):
        # This test will fail because 2 - 3 is -1, not 5
        self.assertEqual(add_numbers(2, 3), 5)
        self.assertEqual(add_numbers(10, 5), 15)

if __name__ == '__main__':
    unittest.main()