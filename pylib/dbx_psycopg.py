#!/usr/bin/env python
# Copyright (c) 2009-2010 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""
Code to work with postgresql databases using the
pyscopg library (I couldn't get PyGreSQL to work --
see http://mailman.vex.net/pipermail/pygresql/2009-May/002219.html
for another user's case of the problem.
"""


import os, sys, re
from os.path import join, exists
import logging
from contextlib import contextmanager

import logging
log = logging.getLogger("dbx_psycopg")
log.setLevel(logging.DEBUG)
log.setLevel(logging.INFO)

import dbxlib
try:
    # Import the (default) pq5 library version of postgreSQL.
    import psycopg2
    loaded = True
    disabled_reason = None
except ImportError:
    try:
        # Fallback - import the older pq4 library versios of postgreSQL. To do
        # this we update sys.path to use the pq4 version.
        has_fallback_library = False
        for i in range(len(sys.path)):
            path = sys.path[i]
            if "dbexplorer_pgsql" in path and "platform" in path and "pylib" in path:
                path = join(path, "ko_psycopg2_pq4")
                if exists(path):
                    sys.path[i] = path
                    has_fallback_library = True
        if not has_fallback_library:
            # No need to try it again - we already know it fails.
            raise
        # Unload any existing pq5 modules that got loaded.
        for modname in sys.modules.keys():
            if modname.startswith("psycopg2."):
                del sys.modules[modname]
        import psycopg2
        loaded = True
        disabled_reason = None
    except ImportError, ex:
        log.exception("Unable to import the psycopg2 module")
        import missingAdaptor
        try:
            psycopg2 = missingAdaptor.MissingAdaptor()
            psycopg2.adaptorName = 'psycopg2'
        except AttributeError:
            # Komodo 6.0.0a2 did not yet have a MissingAdaptor class, it was
            # used as a module instead - so fallback to that.
            # TODO: Remove this AttributeError handling when Komodo 6 goes final.
            psycopg2 = missingAdaptor
        loaded = False
        disabled_reason = "Please ensure that the PostgreSQL client library is "\
                          "installed. Error details: %s." % (ex,)

# This is the same for all databases and tables:
_int_type_names = ('smallint', 'integer', 'bigint', 'serial', 'bigserial')
_float_type_names = ('decimal', 'numeric', 'real', 'double precision')
_currency_type_names = ('money')


def getSchemaColumnNames():
    return ['column_name', 'data_type', 'is_nullable', 'column_default',
            'character_maximum_length', 'is_primary_key']

def columnTypeIsInteger(typeName):
    return typeName in _int_type_names

def columnTypeIsReal(typeName):
    return typeName in _float_type_names

def columnTypeIsBlob(typeName):
    return typeName == "BLOB"

class Connection(object):
    partNames = ['dbname', 'host', 'user', 'password', 'port']
    def __init__(self, args, dbname):
        #log.debug("Connection: dbname:%r, host:%r, port:%r, user:%r, password:%r",
        #          dbname, host, port, username, password)
        # See koDBConnPG.py::_params_from_connection
        self.dbname = dbname or args.get('db')
        self.host = args['host']
        self.port = args.get('port')
        self.user = args['username']
        self.password = args.get('password')

    def getConnectionString(self):
        parts = ["dbname='%s'" % self.dbname]
        if self.user:
            parts.append("user='%s'" % self.user)
        if self.password:
            parts.append("password='%s'" % self.password)
        if self.host and self.host != 'localhost':
            parts.append("host='%s'" % self.host)
            if self.password:
                parts.append("password='%s'" % self.password)
        return " ".join(parts)

    def getConnectionDisplayValues(self):
        return "%s:%s" % (self.host, self.dbname)
        
class ColumnInfo(object):
    def __init__(self, name, type, nullable, default_value,
                 max_length, is_primary_key):
        self.column_name = name
        self.name = name   #Synonym, need a better way to manage this
        self.data_type = type
        self.type = type   #Synonym...
        self.is_nullable = nullable
        self.nullable = nullable   #Synonym...
        self.has_default_value = default_value != None
        self.column_default = default_value
        self.default_value = default_value #Synonym...
        if is_primary_key or (is_primary_key == "True"):
            self.is_primary_key = 1
        else:
            self.is_primary_key = 0
        self.character_maximum_length = max_length

        self.prettyName_to_attrName = {
            'nullable?': 'nullable',
            'default value': 'default_value',
            'primary key?': 'is_primary_key',
            }
        
    def __repr__(self):
        return ("<ColumnInfo: name:%r, "
                + "type:%r, "
                + "nullable:%r, \n"
                + "has_default_value:%r "
                + "default_value:%r, "
                + "is_pri_key:%r, "
                + "max_length:%r>") % (
        self.name,
        self.type,
        self.nullable,
        self.has_default_value ,
        self.default_value,
        self.is_primary_key,
        self.character_maximum_length
        )

    def id_from_name(self, prettyName):
        return self.prettyName_to_attrName.get(prettyName, prettyName)

class OperationalError(psycopg2.OperationalError):
    pass

class DatabaseError(psycopg2.DatabaseError):
    pass

class IntegrityError(psycopg2.IntegrityError):
    pass

class Database(dbxlib.CommonDatabase):
    # args should be: host, username=None, password=None, port=None
    handles_prepared_stmts = False
    def __init__(self, args, dbname):
        self.connection = Connection(args, dbname)
        self._init_db()

    def _init_db(self):
        self.col_info_from_table_name = {}

    def getConnectionDisplayInfo(self):
        return self.connection.getConnectionDisplayValues()
        
    @contextmanager
    def connect(self, commit=False, cu=None):
        """ See dbx_sqlite3.py::connect docstring for full story
        @param commit {bool} 
        @param cu {sqlite3.Cursor}
        """
        if cu is not None:
            yield cu
        else:
            connStr = self.connection.getConnectionString()
            #log.debug("connStr: %s", connStr)
            try:
                conn = psycopg2.connect(connStr)
            except Exception, ex:
                log.exception("Bad connection string of %s", connStr)
                raise ex
            cu = conn.cursor()
            try:
                yield cu
            finally:
                if commit:
                    conn.commit()
                cu.close()
                conn.close()

    # get metadata about the database and tables
                
    def listDatabases(self):
        try:
            query = """select datname from pg_database"""
            with self.connect() as cu:
                cu.execute(query)
                names = [row[0] for row in cu.fetchall()]
                return names
        except NotImplementedError, ex:
            raise OperationalError(ex.message)
        except psycopg2.OperationalError, ex:
            raise OperationalError(ex)
        except psycopg2.DatabaseError, ex:
            raise DatabaseError(ex)

                
    def listAllTablePartsByType(self, dbname, typeName):
        try:
            query = """select table_name
                       from information_schema.tables
                       where table_catalog = '%s'
                         and table_type = '%s'
                         and table_schema not in ('pg_catalog', 'information_schema')""" % (dbname, typeName)
            with self.connect() as cu:
                cu.execute(query)
                names = [row[0] for row in cu.fetchall()]
                return names
        except NotImplementedError, ex:
            raise OperationalError(ex.message)
        except psycopg2.OperationalError, ex:
            raise OperationalError(ex)
        except psycopg2.DatabaseError, ex:
            raise DatabaseError(ex)
        except Exception, ex:
            log.exception("listAllTablePartsByType(typeName:%s)", typeName)
        
    def listAllTableNames(self, dbname):
        return self.listAllTablePartsByType(dbname, 'BASE TABLE')
                
    def listAllIndexNames(self):
        return self.listAllTablePartsByType(dbname, 'INDEX') #TODO: Verify this

    def listAllColumnNames(self, dbname, table_name):
        try:
            query = ("select column_name from information_schema.columns "
                     + "where table_catalog = '%s' "
                     + " and table_name = '%s'") % (dbname, table_name)
            with self.connect() as cu:
                cu.execute(query)
                names = [row[0] for row in cu.fetchall()]
                return names
        except psycopg2.OperationalError, ex:
            raise OperationalError(ex)
        except psycopg2.DatabaseError, ex:
            raise DatabaseError(ex)

    def listAllTriggerNames(self):
        return self.listAllTablePartsByType(dbname, 'TRIGGER') # TODO: Verify this

    #TODO: Add views
    
    def _save_table_info(self, table_name):
        if ';' in table_name:
            raise Exception("Unsafe table_name: %s" % (table_name,))
        if table_name in self.col_info_from_table_name:
            return self.col_info_from_table_name[table_name]
        # First determine which columns are indexed
        indexed_columns = {}
        index_query = """SELECT ta.attname AS column_name,
                                i.indisprimary AS primary_key
                FROM pg_class bc, pg_class ic, pg_index i,
                     pg_attribute ta, pg_attribute ia
                WHERE (bc.oid = i.indrelid)
                     AND (ic.oid = i.indexrelid)
                     AND (ia.attrelid = i.indexrelid)
                     AND (ta.attrelid = bc.oid)
                     AND (bc.relname = '%s')
                     AND (ta.attrelid = i.indrelid)
                     AND (ta.attnum = i.indkey[ia.attnum-1])
                 """ % (table_name)
        main_query = """select column_name, data_type, is_nullable, column_default, character_maximum_length
                   from information_schema.columns
                   where table_name='%s' and table_catalog = '%s' ORDER BY ordinal_position""" % (table_name, self.connection.dbname)
        with self.connect() as cu:
            cu.execute(index_query)
            for row in cu.fetchall():
                log.debug("save_table_info: index_query: got row: %s", row)
                indexed_columns[row[0]] = row[1]
                
            cu.execute(main_query)
            col_info = []
            log.debug("save_table_info: main_query: rowcount: %d", cu.rowcount)
            for row in cu.fetchall():
                log.debug("save_table_info: appending raw row: %s", row)
                lrow = list(row)
                lrow.append(indexed_columns.get(row[0], False))
                log.debug("save_table_info: appending row: %s", lrow)
                col_info.append(ColumnInfo(*lrow))
        self.col_info_from_table_name[table_name] = col_info
        return col_info

    def _typeForPostgres(self, typeName):
        return typeName in ('date', 'datetime', 'point')
    
    def _convert(self, col_info_block, row_data):
        """ Convert each item into a string.  Then return an array of items.
        """
        new_row_data = []
        idx = 0
        for value in row_data:
            col_info = col_info_block[idx]
            type = col_info.type
            log.debug("_convert: value: %s, type:%s", value, type)
            if type == u'integer':
                if value is None:
                    new_row_data.append("")
                else:
                    try:
                        new_row_data.append("%d" % value)
                    except TypeError:
                        log.error("Can't append value as int: %r", value)
                        new_row_data.append("%r" % value)
            elif type == u'real':
                new_row_data.append("%r" % value)
            elif (type in (u'STRING', u'TEXT')
                  or 'VARCHAR' in type
                  or type.startswith('character')):
                new_row_data.append(value)
            elif self._typeForPostgres(type):
                new_row_data.append(str(value))
            elif type == 'BLOB':
                # To get the data of a blob:
                # len(value) => size, str(value) => str repr,
                # but how would we know how to represent it?
                if value is None:
                    log.info("blob data is: None")
                    value = ""
                new_row_data.append("<BLOB: %d chars>" % (len(value),))
            else:
                new_row_data.append('%r' % value)
            idx += 1
        return new_row_data

    def _convertAndJoin(self, names, sep):
        # Return a string of form <<"name1 = ? <sep> name2 = ? ...">>
        return sep.join([("%s = %%s" % name) for name in names])

    # GENERIC?
    def getRawRow(self, table_name, key_names, key_values, convert_blob_values=True):
        key_names_str = self._convertAndJoin(key_names, " AND ")
        query = "select * from %s where %s" %  (table_name, key_names_str)
        with self.connect() as cu:
            cu.execute(query, key_values)
            row = cu.fetchone()
        str_items = []
        if convert_blob_values:
            col_info_block = self._save_table_info(table_name)
        idx = 0
        for item in row:
            if item is None:
                str_items.append("")
            elif convert_blob_values and columnTypeIsBlob(col_info_block[idx].type):
                str_items.append("<BLOB: %d chars>" % (len(item),))
            else:
                str_items.append(str(item))
            idx += 1
        return len(str_items), str_items

    #TODO: Generic?
    def _getRowIdentifier(self, table_name, row_to_delete):
        col_info_block = self.get_table_info(table_name)
        key_names = []
        key_values = []
        idx = 0
        for col_info in col_info_block:
            if col_info.is_primary_key:
                key_names.append(col_info.name)
                key_values.append(row_to_delete[idx])
            idx += 1
        if key_names:
            condition = " and ".join(["%s = ?" % (k,) for k in key_names])
        else:
            for col_info in col_info_block:
                if col_info.type != "BLOB":
                    key_names.append(col_info.name)
                    key_values.append(row_to_delete[idx])
                idx += 1
            condition = " and ".join(["%s = ?" % (k,) for k in key_names])
        return condition, key_values

    def deleteRowByKey(self, table_name, key_names, key_values):
        condition = " and ".join(["%s = %%s" % kname for kname in key_names])
        with self.connect(commit=True) as cu:
            try:
                cu.execute("delete from %s where %s" % (table_name, condition), key_values)
            except:
                log.exception("postgres deleteRowByKey failed")
                res = False
            else:
                res = True
        return res

    def insertRowByNamesAndValues(self, table_name, target_names, target_values):
        cmd = "insert into %s (%s) values (%s)" % (table_name,
                                                   ", ".join(target_names),
                                                   ", ".join(['%s'] * len(target_names)))
        with self.connect(commit=True) as cu:
            try:
                cu.execute(cmd, target_values)
                res = True
            except psycopg2.IntegrityError, ex:
                raise IntegrityError(ex)
            except Exception, ex:
                log.exception("dbx_psycopg::insertRowByNamesAndValues failed")
                res = False
        return res

    def updateRow(self, table_name, target_names, target_values,
                                      key_names, key_values):
        target_names_str = self._convertAndJoin(target_names, ",")
        key_names_str = self._convertAndJoin(key_names, " AND ")
        cmd = 'update %s set %s where %s' % (table_name, target_names_str,
                                             key_names_str)
        args = tuple(target_values + key_values)
        with self.connect(commit=True) as cu:
            try:
                cu.execute(cmd, args)
                res = True
            except Exception, ex:
                log.exception("dbx_psycopg::updateRow failed")
                res = False
        return res

    # Custom query methods -- these use callbacks into the
    # methods in the loader, to cut down on slinging data
    # around too much

    # runCustomQuery is in the parent class.

    def executeCustomAction(self, action):
        with self.connect(commit=True) as cu:
            try:
                cu.execute(action)
                res = True
            except psycopg2.IntegrityError, ex:
                raise IntegrityError(ex)
            except Exception, ex:
                log.exception("dbx_psycopg::executeCustomAction failed")
                res = False
        return res

    def getIndexInfo(self, indexName, res):
        XXX # Implement!
        
    def getTriggerInfo(self, triggerName, res):
        XXX # Implement!
