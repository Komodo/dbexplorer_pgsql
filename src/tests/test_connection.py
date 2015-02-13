#!/usr/bin/env python

import unittest
import psycopg2
import tests

class ConnectionTests(unittest.TestCase):

    def connect(self):
        return psycopg2.connect(tests.dsn)

    def test_closed_attribute(self):
        conn = self.connect()
        self.assertEqual(conn.closed, False)
        conn.close()
        self.assertEqual(conn.closed, True)

    def test_cursor_closed_attribute(self):
        conn = self.connect()
        curs = conn.cursor()
        self.assertEqual(curs.closed, False)
        curs.close()
        self.assertEqual(curs.closed, True)

        # Closing the connection closes the cursor:
        curs = conn.cursor()
        conn.close()
        self.assertEqual(curs.closed, True)

    def test_reset(self):
        conn = self.connect()
        # switch isolation level, then reset
        level = conn.isolation_level
        conn.set_isolation_level(0)
        self.assertEqual(conn.isolation_level, 0)
        conn.reset()
        # now the isolation level should be equal to saved one
        self.assertEqual(conn.isolation_level, level)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

if __name__ == "__main__":
    unittest.main()