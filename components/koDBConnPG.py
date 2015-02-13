#!/usr/bin/env python
# Copyright (c) 2009-2010 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

""" xpcom wrapper around dbx_psycopg library - explore databases."""

import traceback
import os
from os.path import join, abspath, dirname
import sys
import re
import logging

from xpcom import components, COMException, ServerException, nsError
from xpcom.server import WrapObject, UnwrapObject

log = logging.getLogger("koDBConnPG")
log.setLevel(logging.INFO)

try:
    import dbxlib
except ImportError, ex:
    sys.stderr.write("Failed to load dbxlib: %s\n" % (ex,))
    raise

try:
    import dbx_psycopg
    loaded = True
except ImportError, ex:
    sys.stderr.write("Failed to load dbx_psycopg: %s\n" % (ex,))
    loaded = False

def _params_from_connection(dbConnection):
    host = getattr(dbConnection, 'hostname', 'localhost')
    port = getattr(dbConnection, 'port', "")
    username = getattr(dbConnection, 'username', "")
    obj = {'host':host, 'username':username,
            'port':port}
    password = getattr(dbConnection, 'password', "")
    if hasattr(dbConnection, 'hasPassword'):
        if dbConnection.hasPassword:
            obj['password'] = password
    elif password:
        obj['password'] = password
        
    return obj

class KoPostgresDBXTableConnection(dbxlib.KoTableConnector):
    """ This table is now mixed into KoMySQL_DBXTable"""
    def __init__(self):
        dbxlib.KoTableConnector.__init__(self, dbx_psycopg)
        
    #---- Data manipulation

    def deleteRows(self, dataTreeView, rowNums):
        # @param dataTreeView { koIDBXTableDumpTreeView }
        #  koIDBXTableDumpTreeView: koDatabaseExplorerTreeView.koDatabaseExplorerTreeView
        # @param rowNums {array of int}
        column_names = self.getColumnNames()
        query_names = []
        dataTreeView = UnwrapObject(dataTreeView)
        schemaTreeView = UnwrapObject(dataTreeView.get_schemaTreeView())
        for i in range(len(column_names)):
            is_key = (schemaTreeView.getCellText(i, dbxlib.Column('is_primary_key')).lower()
                      in ('true', '1')) # windows: 'true', linux: '1'
            if is_key:
                query_names.append(column_names[i])
        if not query_names:
            raise dbxlib.DBXception("No attributes are keys, can't delete")
        table_name = self._table_name
        # return True if any rows are deleted
        final_res = ""
        for rowNum in rowNums:
            query_values = []
            for column_name in query_names:
                query_values.append(dataTreeView.getCellText(rowNum,
                                                             dbxlib.Column(column_name)))
            res = self._db.deleteRowByKey(self._table_name,
                                    query_names,
                                    query_values)
            if not (res or final_res):
                final_res = ("Failed to delete keys:%s, values:%s" %
                            (", ".join(query_names),
                             ", ".join([str(x) for x in query_values])))
        return final_res

#---- The connection class

class KoPostgresDBXConnection(dbxlib.KoDBXConnection):
    _com_interfaces_ = [components.interfaces.koIDBXConnection]
    _reg_clsid_ = "{65b8d4a9-c188-4edc-8114-0b7cbd3adfcb}"
    _reg_contractid_ = "@activestate.com/koDBXConnection?database=PostgreSQL;1"
    _reg_desc_ = "koIDBXConnection PostgreSQL"
    _reg_categories_ = [ ('komodo-DBX-DBConnections', _reg_contractid_), ]
    
    # Interface Methods
    def get_loaded(self):
        return loaded and dbx_psycopg.loaded

    def getChildren(self):
        """Return an annotated list of the parts of the connection"""
        db_args = _params_from_connection(self)
        try:
            # At top-level, pick the postgres database
            db = dbx_psycopg.Database(db_args, 'postgres')
            database_names = [(name, 'database', KoPostgres_DBXDatabase(self, name)) for name in db.listDatabases()]
            names = sorted(database_names, key=lambda item:item[0].lower())
            return names
        except Exception, ex:
            log.exception("Failed: KoPostgresDBXConnection.getChildren")
            return [("Error: " + str(ex), 'error', None)]

    def getDatabaseDisplayTypeName(self):
        return "PostgreSQL"
    
    def getDatabaseInternalName(self):
        return "PostgreSQL"
    
    def getURI(self):
        if not hasattr(self, '_URI'):
            db_args = _params_from_connection(self)
            self._URI = 'dbexplorer://%s%s/%s' % (db_args['host'],
                                                  db_args['port'] and (":" + db_args['port']) or '',
                                                  db_args['username'])
        return self._URI

class KoPostgres_DBXDatabase(dbxlib.KoDBXConnectionChild):
    isContainer = True
    # Interface Methods
    def __init__(self, parent, dbname):
        #XXX Check: is this going to create circular refs?
        self._parent = parent
        self._dbname = dbname

    def getChildren(self):
        """Return an annotated list of the parts of the connection"""
        log.debug("#2: Asked to get children from %r", self)
        db_args = self.find_params_from_connection()
        log.debug("#2.2: db_args: %s", db_args)
        try:
            db = dbx_psycopg.Database(db_args, self._dbname)
            log.debug("#2.3: got a db object")
            table_names = [(name, 'table', KoPostgres_DBXTable(self, name)) for name in db.listAllTableNames(self._dbname)]
            log.debug("#2.4: table_names:%s", table_names)
            names = sorted(table_names, key=lambda item:item[0].lower())
            log.debug("#2.5: names:%s", names)
            return names
        except Exception, ex:
            log.exception("Failed: KoPostgres_DBXDatabase.getChildren")
            return [("Error: " + str(ex), 'error', None)]
        
    def getURI(self):
        return self._parent.getURI() + "/" + self._dbname

class KoPostgres_DBXTable(dbxlib.KoDBXConnectionChild, KoPostgresDBXTableConnection):
    _com_interfaces_ = [components.interfaces.koIDBXTableConnector]

    isContainer = True
    def __init__(self, parent, table_name):
        self._parent = parent
        self._table_name = table_name
        KoPostgresDBXTableConnection.__init__(self)
        
    # Interface Methods

    def get_tableViewTitle(self):
        # Walk up the parent chain to get these attributes:
        return (self.getDatabaseDisplayTypeName()
                + "://"
                + self._dbname
                + "/"
                + self._table_name
                + " - Database Explorer")
    
    def getConnectionDisplayInfo(self):
        return self._dbname

    def getChildren(self):
        """Return an annotated list of the parts of the connection"""
        log.debug("#3: Asked to get children from %r", self)
        db_args = self.find_params_from_connection()
        try:
            db = dbx_psycopg.Database(db_args, self._dbname)
            column_names = [(name, 'column', KoPostgres_DBXColumn(self, name)) for name in db.listAllColumnNames(self._dbname, self._table_name)]
            names = sorted(column_names, key=lambda item:item[0].lower())
            return names
        except Exception, ex:
            log.exception("Failed: KoPostgresDBXConnection.getChildren")
            return [("Error: " + str(ex), 'error')]

    def getURI(self):
        return self._parent.getURI() + "/" + self._table_name

    def __getattr__(self, attr):
        if attr == "_db":
            db_args = self.find_params_from_connection()
            self._db = dbx_psycopg.Database(db_args, self._dbname)
            return self._db
        #Hardwired parent.
        return dbxlib.KoDBXConnectionChild.__getattr__(self, attr)

class KoPostgres_DBXColumn(dbxlib.KoDBXConnectionChild):
    isContainer = False
    def __init__(self, parent, column_name):
        self._parent = parent
        self._column_name = column_name

    #TODO:
    # Routines for getting info on each column.

#---- The preference class

class KoPostgresDBXPreferences(object): # dbxlib.KoDBXPreference):
    _com_interfaces_ = [components.interfaces.koIDBXPreference]
    _reg_clsid_ = "{3e8293a3-cb31-48c2-84ff-c433c5320eb5}"
    _reg_contractid_ = "@activestate.com/koDBXPreference?database=PostgreSQL;1"
    _reg_desc_ = "koIDBXPreference PostgreSQL"
    _reg_categories_ = [ ('komodo-DBX-Preferences', _reg_contractid_), ]

    def is_enabled(self):
        return dbx_psycopg.loaded

    def get_disabled_reason(self):
        return dbx_psycopg.disabled_reason

    def get_name(self):
        return "postgresql"

    def get_displayName(self):
        return "PostgreSQL"

    def get_fileBased(self):
        return False
