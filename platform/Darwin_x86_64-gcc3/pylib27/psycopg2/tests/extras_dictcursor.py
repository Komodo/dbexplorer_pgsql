#!/usr/bin/env python
#
# extras_dictcursor - test if DictCursor extension class works
#
# Copyright (C) 2004-2010 Federico Di Gregorio  <fog@debian.org>
#
# psycopg2 is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# psycopg2 is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public
# License for more details.

import psycopg2
import psycopg2.extras
from testutils import unittest

import tests


class ExtrasDictCursorTests(unittest.TestCase):
    """Test if DictCursor extension class works."""

    def setUp(self):
        self.conn = psycopg2.connect(tests.dsn)
        curs = self.conn.cursor()
        curs.execute("CREATE TEMPORARY TABLE ExtrasDictCursorTests (foo text)")
        curs.execute("INSERT INTO ExtrasDictCursorTests VALUES ('bar')")
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def testDictCursorWithPlainCursorFetchOne(self):
        self._testWithPlainCursor(lambda curs: curs.fetchone())

    def testDictCursorWithPlainCursorFetchMany(self):
        self._testWithPlainCursor(lambda curs: curs.fetchmany(100)[0])

    def testDictCursorWithPlainCursorFetchAll(self):
        self._testWithPlainCursor(lambda curs: curs.fetchall()[0])

    def testDictCursorWithPlainCursorIter(self):
        def getter(curs):
            for row in curs:
                return row
        self._testWithPlainCursor(getter)

    def testDictCursorWithPlainCursorRealFetchOne(self):
        self._testWithPlainCursorReal(lambda curs: curs.fetchone())

    def testDictCursorWithPlainCursorRealFetchMany(self):
        self._testWithPlainCursorReal(lambda curs: curs.fetchmany(100)[0])

    def testDictCursorWithPlainCursorRealFetchAll(self):
        self._testWithPlainCursorReal(lambda curs: curs.fetchall()[0])

    def testDictCursorWithPlainCursorRealIter(self):
        def getter(curs):
            for row in curs:
                return row
        self._testWithPlainCursorReal(getter)

    def testDictCursorWithNamedCursorFetchOne(self):
        self._testWithNamedCursor(lambda curs: curs.fetchone())

    def testDictCursorWithNamedCursorFetchMany(self):
        self._testWithNamedCursor(lambda curs: curs.fetchmany(100)[0])

    def testDictCursorWithNamedCursorFetchAll(self):
        self._testWithNamedCursor(lambda curs: curs.fetchall()[0])

    def testDictCursorWithNamedCursorIter(self):
        def getter(curs):
            for row in curs:
                return row
        self._testWithNamedCursor(getter)

    def _testWithPlainCursor(self, getter):
        curs = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute("SELECT * FROM ExtrasDictCursorTests")
        row = getter(curs)
        self.failUnless(row['foo'] == 'bar')
        self.failUnless(row[0] == 'bar')
        return row

    def _testWithNamedCursor(self, getter):
        curs = self.conn.cursor('aname', cursor_factory=psycopg2.extras.DictCursor)
        curs.execute("SELECT * FROM ExtrasDictCursorTests")
        row = getter(curs)
        self.failUnless(row['foo'] == 'bar')
        self.failUnless(row[0] == 'bar')

    def _testWithPlainCursorReal(self, getter):
        curs = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        curs.execute("SELECT * FROM ExtrasDictCursorTests")
        row = getter(curs)
        self.failUnless(row['foo'] == 'bar')

    def _testWithNamedCursorReal(self, getter):
        curs = self.conn.cursor('aname', cursor_factory=psycopg2.extras.RealDictCursor)
        curs.execute("SELECT * FROM ExtrasDictCursorTests")
        row = getter(curs)
        self.failUnless(row['foo'] == 'bar')

    def testUpdateRow(self):
        row = self._testWithPlainCursor(lambda curs: curs.fetchone())
        row['foo'] = 'qux'
        self.failUnless(row['foo'] == 'qux')
        self.failUnless(row[0] == 'qux')


def if_has_namedtuple(f):
    def if_has_namedtuple_(self):
        try:
            from collections import namedtuple
        except ImportError:
            return self.skipTest("collections.namedtuple not available")
        else:
            return f(self)

    if_has_namedtuple_.__name__ = f.__name__
    return if_has_namedtuple_

class NamedTupleCursorTest(unittest.TestCase):
    def setUp(self):
        from psycopg2.extras import NamedTupleConnection

        try:
            from collections import namedtuple
        except ImportError:
            self.conn = None
            return

        self.conn = psycopg2.connect(tests.dsn,
            connection_factory=NamedTupleConnection)
        curs = self.conn.cursor()
        curs.execute("CREATE TEMPORARY TABLE nttest (i int, s text)")
        curs.execute("INSERT INTO nttest VALUES (1, 'foo')")
        curs.execute("INSERT INTO nttest VALUES (2, 'bar')")
        curs.execute("INSERT INTO nttest VALUES (3, 'baz')")
        self.conn.commit()

    def tearDown(self):
        if self.conn is not None:
            self.conn.close()

    @if_has_namedtuple
    def test_fetchone(self):
        curs = self.conn.cursor()
        curs.execute("select * from nttest where i = 1")
        t = curs.fetchone()
        self.assertEqual(t[0], 1)
        self.assertEqual(t.i, 1)
        self.assertEqual(t[1], 'foo')
        self.assertEqual(t.s, 'foo')

    @if_has_namedtuple
    def test_fetchmany(self):
        curs = self.conn.cursor()
        curs.execute("select * from nttest order by 1")
        res = curs.fetchmany(2)
        self.assertEqual(2, len(res))
        self.assertEqual(res[0].i, 1)
        self.assertEqual(res[0].s, 'foo')
        self.assertEqual(res[1].i, 2)
        self.assertEqual(res[1].s, 'bar')

    @if_has_namedtuple
    def test_fetchall(self):
        curs = self.conn.cursor()
        curs.execute("select * from nttest order by 1")
        res = curs.fetchall()
        self.assertEqual(3, len(res))
        self.assertEqual(res[0].i, 1)
        self.assertEqual(res[0].s, 'foo')
        self.assertEqual(res[1].i, 2)
        self.assertEqual(res[1].s, 'bar')
        self.assertEqual(res[2].i, 3)
        self.assertEqual(res[2].s, 'baz')

    @if_has_namedtuple
    def test_iter(self):
        curs = self.conn.cursor()
        curs.execute("select * from nttest order by 1")
        i = iter(curs)
        t = i.next()
        self.assertEqual(t.i, 1)
        self.assertEqual(t.s, 'foo')
        t = i.next()
        self.assertEqual(t.i, 2)
        self.assertEqual(t.s, 'bar')
        t = i.next()
        self.assertEqual(t.i, 3)
        self.assertEqual(t.s, 'baz')
        self.assertRaises(StopIteration, i.next)

    def test_error_message(self):
        try:
            from collections import namedtuple
        except ImportError:
            # an import error somewhere
            from psycopg2.extras import NamedTupleConnection
            try:
                if self.conn is not None:
                    self.conn.close()
                self.conn = psycopg2.connect(tests.dsn,
                    connection_factory=NamedTupleConnection)
                curs = self.conn.cursor()
                curs.execute("select 1")
                curs.fetchone()
            except ImportError:
                pass
            else:
                self.fail("expecting ImportError")
        else:
            # skip the test
            pass

    @if_has_namedtuple
    def test_record_updated(self):
        curs = self.conn.cursor()
        curs.execute("select 1 as foo;")
        r = curs.fetchone()
        self.assertEqual(r.foo, 1)

        curs.execute("select 2 as bar;")
        r = curs.fetchone()
        self.assertEqual(r.bar, 2)
        self.assertRaises(AttributeError, getattr, r, 'foo')

    @if_has_namedtuple
    def test_no_result_no_surprise(self):
        curs = self.conn.cursor()
        curs.execute("update nttest set s = s")
        self.assertRaises(psycopg2.ProgrammingError, curs.fetchone)

        curs.execute("update nttest set s = s")
        self.assertRaises(psycopg2.ProgrammingError, curs.fetchall)

    @if_has_namedtuple
    def test_minimal_generation(self):
        # Instrument the class to verify it gets called the minimum number of times.
        from psycopg2.extras import NamedTupleCursor
        f_orig = NamedTupleCursor._make_nt
        calls = [0]
        def f_patched(self_):
            calls[0] += 1
            return f_orig(self_)

        NamedTupleCursor._make_nt = f_patched

        try:
            curs = self.conn.cursor()
            curs.execute("select * from nttest order by 1")
            curs.fetchone()
            curs.fetchone()
            curs.fetchone()
            self.assertEqual(1, calls[0])

            curs.execute("select * from nttest order by 1")
            curs.fetchone()
            curs.fetchall()
            self.assertEqual(2, calls[0])

            curs.execute("select * from nttest order by 1")
            curs.fetchone()
            curs.fetchmany(1)
            self.assertEqual(3, calls[0])

        finally:
            NamedTupleCursor._make_nt = f_orig


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

if __name__ == "__main__":
    unittest.main()
