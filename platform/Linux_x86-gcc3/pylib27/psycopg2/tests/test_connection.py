#!/usr/bin/env python

import time
import threading
from testutils import unittest, decorate_all_tests, skip_if_no_pg_sleep
from operator import attrgetter

import psycopg2
import psycopg2.extensions
import tests

class ConnectionTests(unittest.TestCase):

    def setUp(self):
        self.conn = psycopg2.connect(tests.dsn)

    def tearDown(self):
        if not self.conn.closed:
            self.conn.close()

    def test_closed_attribute(self):
        conn = self.conn
        self.assertEqual(conn.closed, False)
        conn.close()
        self.assertEqual(conn.closed, True)

    def test_cursor_closed_attribute(self):
        conn = self.conn
        curs = conn.cursor()
        self.assertEqual(curs.closed, False)
        curs.close()
        self.assertEqual(curs.closed, True)

        # Closing the connection closes the cursor:
        curs = conn.cursor()
        conn.close()
        self.assertEqual(curs.closed, True)

    def test_reset(self):
        conn = self.conn
        # switch isolation level, then reset
        level = conn.isolation_level
        conn.set_isolation_level(0)
        self.assertEqual(conn.isolation_level, 0)
        conn.reset()
        # now the isolation level should be equal to saved one
        self.assertEqual(conn.isolation_level, level)

    def test_notices(self):
        conn = self.conn
        cur = conn.cursor()
        cur.execute("create temp table chatty (id serial primary key);")
        self.assertEqual("CREATE TABLE", cur.statusmessage)
        self.assert_(conn.notices)

    def test_notices_consistent_order(self):
        conn = self.conn
        cur = conn.cursor()
        cur.execute("create temp table table1 (id serial); create temp table table2 (id serial);")
        cur.execute("create temp table table3 (id serial); create temp table table4 (id serial);")
        self.assertEqual(4, len(conn.notices))
        self.assert_('table1' in conn.notices[0])
        self.assert_('table2' in conn.notices[1])
        self.assert_('table3' in conn.notices[2])
        self.assert_('table4' in conn.notices[3])

    def test_notices_limited(self):
        conn = self.conn
        cur = conn.cursor()
        for i in range(0, 100, 10):
            sql = " ".join(["create temp table table%d (id serial);" % j for j in range(i, i+10)])
            cur.execute(sql)

        self.assertEqual(50, len(conn.notices))
        self.assert_('table50' in conn.notices[0], conn.notices[0])
        self.assert_('table51' in conn.notices[1], conn.notices[1])
        self.assert_('table98' in conn.notices[-2], conn.notices[-2])
        self.assert_('table99' in conn.notices[-1], conn.notices[-1])

    def test_server_version(self):
        self.assert_(self.conn.server_version)

    def test_protocol_version(self):
        self.assert_(self.conn.protocol_version in (2,3),
            self.conn.protocol_version)

    def test_tpc_unsupported(self):
        cnn = self.conn
        if cnn.server_version >= 80100:
            return self.skipTest("tpc is supported")

        self.assertRaises(psycopg2.NotSupportedError,
            cnn.xid, 42, "foo", "bar")

    @skip_if_no_pg_sleep('conn')
    def test_concurrent_execution(self):
        def slave():
            cnn = psycopg2.connect(tests.dsn)
            cur = cnn.cursor()
            cur.execute("select pg_sleep(2)")
            cur.close()
            cnn.close()

        t1 = threading.Thread(target=slave)
        t2 = threading.Thread(target=slave)
        t0 = time.time()
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        self.assert_(time.time() - t0 < 3,
            "something broken in concurrency")


class IsolationLevelsTestCase(unittest.TestCase):

    def setUp(self):
        self._conns = []
        conn = self.connect()
        cur = conn.cursor()
        try:
            cur.execute("drop table isolevel;")
        except psycopg2.ProgrammingError:
            conn.rollback()
        cur.execute("create table isolevel (id integer);")
        conn.commit()
        conn.close()

    def tearDown(self):
        # close the connections used in the test
        for conn in self._conns:
            if not conn.closed:
                conn.close()

    def connect(self):
        conn = psycopg2.connect(tests.dsn)
        self._conns.append(conn)
        return conn

    def test_isolation_level(self):
        conn = self.connect()
        self.assertEqual(
            conn.isolation_level,
            psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)

    def test_encoding(self):
        conn = self.connect()
        self.assert_(conn.encoding in psycopg2.extensions.encodings)

    def test_set_isolation_level(self):
        conn = self.connect()

        conn.set_isolation_level(
            psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        self.assertEqual(conn.isolation_level,
            psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

        conn.set_isolation_level(
            psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)
        self.assertEqual(conn.isolation_level,
            psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)

        conn.set_isolation_level(
            psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE)
        self.assertEqual(conn.isolation_level,
            psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE)

        self.assertRaises(ValueError, conn.set_isolation_level, -1)
        self.assertRaises(ValueError, conn.set_isolation_level, 3)

    def test_set_isolation_level_abort(self):
        conn = self.connect()
        cur = conn.cursor()

        self.assertEqual(psycopg2.extensions.TRANSACTION_STATUS_IDLE,
            conn.get_transaction_status())
        cur.execute("insert into isolevel values (10);")
        self.assertEqual(psycopg2.extensions.TRANSACTION_STATUS_INTRANS,
            conn.get_transaction_status())

        conn.set_isolation_level(
            psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE)
        self.assertEqual(psycopg2.extensions.TRANSACTION_STATUS_IDLE,
            conn.get_transaction_status())
        cur.execute("select count(*) from isolevel;")
        self.assertEqual(0, cur.fetchone()[0])

        cur.execute("insert into isolevel values (10);")
        self.assertEqual(psycopg2.extensions.TRANSACTION_STATUS_INTRANS,
            conn.get_transaction_status())
        conn.set_isolation_level(
            psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        self.assertEqual(psycopg2.extensions.TRANSACTION_STATUS_IDLE,
            conn.get_transaction_status())
        cur.execute("select count(*) from isolevel;")
        self.assertEqual(0, cur.fetchone()[0])

        cur.execute("insert into isolevel values (10);")
        self.assertEqual(psycopg2.extensions.TRANSACTION_STATUS_IDLE,
            conn.get_transaction_status())
        conn.set_isolation_level(
            psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)
        self.assertEqual(psycopg2.extensions.TRANSACTION_STATUS_IDLE,
            conn.get_transaction_status())
        cur.execute("select count(*) from isolevel;")
        self.assertEqual(1, cur.fetchone()[0])

    def test_isolation_level_autocommit(self):
        cnn1 = self.connect()
        cnn2 = self.connect()
        cnn2.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

        cur1 = cnn1.cursor()
        cur1.execute("select count(*) from isolevel;")
        self.assertEqual(0, cur1.fetchone()[0])
        cnn1.commit()

        cur2 = cnn2.cursor()
        cur2.execute("insert into isolevel values (10);")

        cur1.execute("select count(*) from isolevel;")
        self.assertEqual(1, cur1.fetchone()[0])

    def test_isolation_level_read_committed(self):
        cnn1 = self.connect()
        cnn2 = self.connect()
        cnn2.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)

        cur1 = cnn1.cursor()
        cur1.execute("select count(*) from isolevel;")
        self.assertEqual(0, cur1.fetchone()[0])
        cnn1.commit()

        cur2 = cnn2.cursor()
        cur2.execute("insert into isolevel values (10);")
        cur1.execute("insert into isolevel values (20);")

        cur2.execute("select count(*) from isolevel;")
        self.assertEqual(1, cur2.fetchone()[0])
        cnn1.commit()
        cur2.execute("select count(*) from isolevel;")
        self.assertEqual(2, cur2.fetchone()[0])

        cur1.execute("select count(*) from isolevel;")
        self.assertEqual(1, cur1.fetchone()[0])
        cnn2.commit()
        cur1.execute("select count(*) from isolevel;")
        self.assertEqual(2, cur1.fetchone()[0])

    def test_isolation_level_serializable(self):
        cnn1 = self.connect()
        cnn2 = self.connect()
        cnn2.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE)

        cur1 = cnn1.cursor()
        cur1.execute("select count(*) from isolevel;")
        self.assertEqual(0, cur1.fetchone()[0])
        cnn1.commit()

        cur2 = cnn2.cursor()
        cur2.execute("insert into isolevel values (10);")
        cur1.execute("insert into isolevel values (20);")

        cur2.execute("select count(*) from isolevel;")
        self.assertEqual(1, cur2.fetchone()[0])
        cnn1.commit()
        cur2.execute("select count(*) from isolevel;")
        self.assertEqual(1, cur2.fetchone()[0])

        cur1.execute("select count(*) from isolevel;")
        self.assertEqual(1, cur1.fetchone()[0])
        cnn2.commit()
        cur1.execute("select count(*) from isolevel;")
        self.assertEqual(2, cur1.fetchone()[0])

        cur2.execute("select count(*) from isolevel;")
        self.assertEqual(2, cur2.fetchone()[0])


def skip_if_tpc_disabled(f):
    """Skip a test if the server has tpc support disabled."""
    def skip_if_tpc_disabled_(self):
        cnn = self.connect()
        cur = cnn.cursor()
        try:
            cur.execute("SHOW max_prepared_transactions;")
        except psycopg2.ProgrammingError:
            return self.skipTest(
                "server too old: two phase transactions not supported.")
        else:
            mtp = int(cur.fetchone()[0])
        cnn.close()

        if not mtp:
            return self.skipTest(
                "server not configured for two phase transactions. "
                "set max_prepared_transactions to > 0 to run the test")
        return f(self)

    skip_if_tpc_disabled_.__name__ = f.__name__
    return skip_if_tpc_disabled_


class ConnectionTwoPhaseTests(unittest.TestCase):
    def setUp(self):
        self._conns = []

        self.make_test_table()
        self.clear_test_xacts()

    def tearDown(self):
        self.clear_test_xacts()

        # close the connections used in the test
        for conn in self._conns:
            if not conn.closed:
                conn.close()


    def clear_test_xacts(self):
        """Rollback all the prepared transaction in the testing db."""
        cnn = self.connect()
        cnn.set_isolation_level(0)
        cur = cnn.cursor()
        try:
            cur.execute(
                "select gid from pg_prepared_xacts where database = %s",
                (tests.dbname,))
        except psycopg2.ProgrammingError:
            cnn.rollback()
            cnn.close()
            return

        gids = [ r[0] for r in cur ]
        for gid in gids:
            cur.execute("rollback prepared %s;", (gid,))
        cnn.close()

    def make_test_table(self):
        cnn = self.connect()
        cur = cnn.cursor()
        try:
            cur.execute("DROP TABLE test_tpc;")
        except psycopg2.ProgrammingError:
            cnn.rollback()
        cur.execute("CREATE TABLE test_tpc (data text);")
        cnn.commit()
        cnn.close()

    def count_xacts(self):
        """Return the number of prepared xacts currently in the test db."""
        cnn = self.connect()
        cur = cnn.cursor()
        cur.execute("""
            select count(*) from pg_prepared_xacts
            where database = %s;""",
            (tests.dbname,))
        rv = cur.fetchone()[0]
        cnn.close()
        return rv

    def count_test_records(self):
        """Return the number of records in the test table."""
        cnn = self.connect()
        cur = cnn.cursor()
        cur.execute("select count(*) from test_tpc;")
        rv = cur.fetchone()[0]
        cnn.close()
        return rv

    def connect(self):
        conn = psycopg2.connect(tests.dsn)
        self._conns.append(conn)
        return conn

    def test_tpc_commit(self):
        cnn = self.connect()
        xid = cnn.xid(1, "gtrid", "bqual")
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_READY)

        cnn.tpc_begin(xid)
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_BEGIN)

        cur = cnn.cursor()
        cur.execute("insert into test_tpc values ('test_tpc_commit');")
        self.assertEqual(0, self.count_xacts())
        self.assertEqual(0, self.count_test_records())

        cnn.tpc_prepare()
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_PREPARED)
        self.assertEqual(1, self.count_xacts())
        self.assertEqual(0, self.count_test_records())

        cnn.tpc_commit()
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_READY)
        self.assertEqual(0, self.count_xacts())
        self.assertEqual(1, self.count_test_records())

    def test_tpc_commit_one_phase(self):
        cnn = self.connect()
        xid = cnn.xid(1, "gtrid", "bqual")
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_READY)

        cnn.tpc_begin(xid)
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_BEGIN)

        cur = cnn.cursor()
        cur.execute("insert into test_tpc values ('test_tpc_commit_1p');")
        self.assertEqual(0, self.count_xacts())
        self.assertEqual(0, self.count_test_records())

        cnn.tpc_commit()
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_READY)
        self.assertEqual(0, self.count_xacts())
        self.assertEqual(1, self.count_test_records())

    def test_tpc_commit_recovered(self):
        cnn = self.connect()
        xid = cnn.xid(1, "gtrid", "bqual")
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_READY)

        cnn.tpc_begin(xid)
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_BEGIN)

        cur = cnn.cursor()
        cur.execute("insert into test_tpc values ('test_tpc_commit_rec');")
        self.assertEqual(0, self.count_xacts())
        self.assertEqual(0, self.count_test_records())

        cnn.tpc_prepare()
        cnn.close()
        self.assertEqual(1, self.count_xacts())
        self.assertEqual(0, self.count_test_records())

        cnn = self.connect()
        xid = cnn.xid(1, "gtrid", "bqual")
        cnn.tpc_commit(xid)

        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_READY)
        self.assertEqual(0, self.count_xacts())
        self.assertEqual(1, self.count_test_records())

    def test_tpc_rollback(self):
        cnn = self.connect()
        xid = cnn.xid(1, "gtrid", "bqual")
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_READY)

        cnn.tpc_begin(xid)
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_BEGIN)

        cur = cnn.cursor()
        cur.execute("insert into test_tpc values ('test_tpc_rollback');")
        self.assertEqual(0, self.count_xacts())
        self.assertEqual(0, self.count_test_records())

        cnn.tpc_prepare()
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_PREPARED)
        self.assertEqual(1, self.count_xacts())
        self.assertEqual(0, self.count_test_records())

        cnn.tpc_rollback()
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_READY)
        self.assertEqual(0, self.count_xacts())
        self.assertEqual(0, self.count_test_records())

    def test_tpc_rollback_one_phase(self):
        cnn = self.connect()
        xid = cnn.xid(1, "gtrid", "bqual")
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_READY)

        cnn.tpc_begin(xid)
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_BEGIN)

        cur = cnn.cursor()
        cur.execute("insert into test_tpc values ('test_tpc_rollback_1p');")
        self.assertEqual(0, self.count_xacts())
        self.assertEqual(0, self.count_test_records())

        cnn.tpc_rollback()
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_READY)
        self.assertEqual(0, self.count_xacts())
        self.assertEqual(0, self.count_test_records())

    def test_tpc_rollback_recovered(self):
        cnn = self.connect()
        xid = cnn.xid(1, "gtrid", "bqual")
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_READY)

        cnn.tpc_begin(xid)
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_BEGIN)

        cur = cnn.cursor()
        cur.execute("insert into test_tpc values ('test_tpc_commit_rec');")
        self.assertEqual(0, self.count_xacts())
        self.assertEqual(0, self.count_test_records())

        cnn.tpc_prepare()
        cnn.close()
        self.assertEqual(1, self.count_xacts())
        self.assertEqual(0, self.count_test_records())

        cnn = self.connect()
        xid = cnn.xid(1, "gtrid", "bqual")
        cnn.tpc_rollback(xid)

        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_READY)
        self.assertEqual(0, self.count_xacts())
        self.assertEqual(0, self.count_test_records())

    def test_status_after_recover(self):
        cnn = self.connect()
        self.assertEqual(psycopg2.extensions.STATUS_READY, cnn.status)
        xns = cnn.tpc_recover()
        self.assertEqual(psycopg2.extensions.STATUS_READY, cnn.status)

        cur = cnn.cursor()
        cur.execute("select 1")
        self.assertEqual(psycopg2.extensions.STATUS_BEGIN, cnn.status)
        xns = cnn.tpc_recover()
        self.assertEqual(psycopg2.extensions.STATUS_BEGIN, cnn.status)

    def test_recovered_xids(self):
        # insert a few test xns
        cnn = self.connect()
        cnn.set_isolation_level(0)
        cur = cnn.cursor()
        cur.execute("begin; prepare transaction '1-foo';")
        cur.execute("begin; prepare transaction '2-bar';")

        # read the values to return
        cur.execute("""
            select gid, prepared, owner, database
            from pg_prepared_xacts
            where database = %s;""",
            (tests.dbname,))
        okvals = cur.fetchall()
        okvals.sort()

        cnn = self.connect()
        xids = cnn.tpc_recover()
        xids = [ xid for xid in xids if xid.database == tests.dbname ]
        xids.sort(key=attrgetter('gtrid'))

        # check the values returned
        self.assertEqual(len(okvals), len(xids))
        for (xid, (gid, prepared, owner, database)) in zip (xids, okvals):
            self.assertEqual(xid.gtrid, gid)
            self.assertEqual(xid.prepared, prepared)
            self.assertEqual(xid.owner, owner)
            self.assertEqual(xid.database, database)

    def test_xid_encoding(self):
        cnn = self.connect()
        xid = cnn.xid(42, "gtrid", "bqual")
        cnn.tpc_begin(xid)
        cnn.tpc_prepare()

        cnn = self.connect()
        cur = cnn.cursor()
        cur.execute("select gid from pg_prepared_xacts where database = %s;",
            (tests.dbname,))
        self.assertEqual('42_Z3RyaWQ=_YnF1YWw=', cur.fetchone()[0])

    def test_xid_roundtrip(self):
        for fid, gtrid, bqual in [
            (0, "", ""),
            (42, "gtrid", "bqual"),
            (0x7fffffff, "x" * 64, "y" * 64),
        ]:
            cnn = self.connect()
            xid = cnn.xid(fid, gtrid, bqual)
            cnn.tpc_begin(xid)
            cnn.tpc_prepare()
            cnn.close()

            cnn = self.connect()
            xids = [ xid for xid in cnn.tpc_recover()
                if xid.database == tests.dbname ]
            self.assertEqual(1, len(xids))
            xid = xids[0]
            self.assertEqual(xid.format_id, fid)
            self.assertEqual(xid.gtrid, gtrid)
            self.assertEqual(xid.bqual, bqual)

            cnn.tpc_rollback(xid)

    def test_unparsed_roundtrip(self):
        for tid in [
            '',
            'hello, world!',
            'x' * 199,  # PostgreSQL's limit in transaction id length
        ]:
            cnn = self.connect()
            cnn.tpc_begin(tid)
            cnn.tpc_prepare()
            cnn.close()

            cnn = self.connect()
            xids = [ xid for xid in cnn.tpc_recover()
                if xid.database == tests.dbname ]
            self.assertEqual(1, len(xids))
            xid = xids[0]
            self.assertEqual(xid.format_id, None)
            self.assertEqual(xid.gtrid, tid)
            self.assertEqual(xid.bqual, None)

            cnn.tpc_rollback(xid)

    def test_xid_construction(self):
        from psycopg2.extensions import Xid

        x1 = Xid(74, 'foo', 'bar')
        self.assertEqual(74, x1.format_id)
        self.assertEqual('foo', x1.gtrid)
        self.assertEqual('bar', x1.bqual)

    def test_xid_from_string(self):
        from psycopg2.extensions import Xid

        x2 = Xid.from_string('42_Z3RyaWQ=_YnF1YWw=')
        self.assertEqual(42, x2.format_id)
        self.assertEqual('gtrid', x2.gtrid)
        self.assertEqual('bqual', x2.bqual)

        x3 = Xid.from_string('99_xxx_yyy')
        self.assertEqual(None, x3.format_id)
        self.assertEqual('99_xxx_yyy', x3.gtrid)
        self.assertEqual(None, x3.bqual)

    def test_xid_to_string(self):
        from psycopg2.extensions import Xid

        x1 = Xid.from_string('42_Z3RyaWQ=_YnF1YWw=')
        self.assertEqual(str(x1), '42_Z3RyaWQ=_YnF1YWw=')

        x2 = Xid.from_string('99_xxx_yyy')
        self.assertEqual(str(x2), '99_xxx_yyy')

    def test_xid_unicode(self):
        cnn = self.connect()
        x1 = cnn.xid(10, u'uni', u'code')
        cnn.tpc_begin(x1)
        cnn.tpc_prepare()
        cnn.reset()
        xid = [ xid for xid in cnn.tpc_recover()
            if xid.database == tests.dbname ][0]
        self.assertEqual(10, xid.format_id)
        self.assertEqual('uni', xid.gtrid)
        self.assertEqual('code', xid.bqual)

    def test_xid_unicode_unparsed(self):
        # We don't expect people shooting snowmen as transaction ids,
        # so if something explodes in an encode error I don't mind.
        # Let's just check uniconde is accepted as type.
        cnn = self.connect()
        cnn.set_client_encoding('utf8')
        cnn.tpc_begin(u"transaction-id")
        cnn.tpc_prepare()
        cnn.reset()

        xid = [ xid for xid in cnn.tpc_recover()
            if xid.database == tests.dbname ][0]
        self.assertEqual(None, xid.format_id)
        self.assertEqual('transaction-id', xid.gtrid)
        self.assertEqual(None, xid.bqual)

    def test_cancel_fails_prepared(self):
        cnn = self.connect()
        cnn.tpc_begin('cancel')
        cnn.tpc_prepare()
        self.assertRaises(psycopg2.ProgrammingError, cnn.cancel)

decorate_all_tests(ConnectionTwoPhaseTests, skip_if_tpc_disabled)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

if __name__ == "__main__":
    unittest.main()
