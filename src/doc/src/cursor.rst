The ``cursor`` class
====================

.. sectionauthor:: Daniele Varrazzo <daniele.varrazzo@gmail.com>

.. testsetup:: *

    from StringIO import StringIO
    import sys

    create_test_table()

    # initial data
    cur.executemany("INSERT INTO test (num, data) VALUES (%s, %s)",
        [(100, "abc'def"), (None, 'dada'), (42, 'bar')])
    conn.commit()


.. class:: cursor

    Allows Python code to execute PostgreSQL command in a database session.
    Cursors are created by the `connection.cursor()` method: they are
    bound to the connection for the entire lifetime and all the commands are
    executed in the context of the database session wrapped by the connection.

    Cursors created from the same connection are not isolated, i.e., any
    changes done to the database by a cursor are immediately visible by the
    other cursors. Cursors created from different connections can or can not
    be isolated, depending on the connections' :ref:`isolation level
    <transactions-control>`. See also `~connection.rollback()` and
    `~connection.commit()` methods.

    Cursors are *not* thread safe: a multithread application can create
    many cursors from the same connection and should use each cursor from
    a single thread. See :ref:`thread-safety` for details.

 
    .. attribute:: description 

        This read-only attribute is a sequence of 7-item sequences.  

        Each of these sequences contains information describing one result
        column: 

        - ``name``
        - ``type_code``
        - ``display_size``
        - ``internal_size``
        - ``precision``
        - ``scale``
        - ``null_ok``

        The first two items (``name`` and ``type_code``) are always specified,
        the other five are optional and are set to ``None`` if no meaningful
        values can be provided.

        This attribute will be ``None`` for operations that do not return rows
        or if the cursor has not had an operation invoked via the
        |execute*|_ methods yet.
        
        The ``type_code`` can be interpreted by comparing it to the Type
        Objects specified in the section :ref:`type-objects-and-constructors`.
        It is also used to register typecasters to convert PostgreSQL types to
        Python objects: see :ref:`type-casting-from-sql-to-python`.


    .. method:: close()
          
        Close the cursor now (rather than whenever `!__del__()` is
        called).  The cursor will be unusable from this point forward; an
        `~psycopg2.InterfaceError` will be raised if any operation is
        attempted with the cursor.
            
    .. attribute:: closed

        Read-only boolean attribute: specifies if the cursor is closed
        (``True``) or not (``False``).

        .. extension::

            The `closed` attribute is a Psycopg extension to the
            |DBAPI|.

        .. versionadded:: 2.0.7


    .. attribute:: connection

        Read-only attribute returning a reference to the `connection`
        object on which the cursor was created.


    .. attribute:: name

        Read-only attribute containing the name of the cursor if it was
        creates as named cursor by `connection.cursor()`, or ``None`` if
        it is a client side cursor.  See :ref:`server-side-cursors`.

        .. extension::

            The `name` attribute is a Psycopg extension to the |DBAPI|.


    
    .. |execute*| replace:: `execute*()`

    .. _execute*:

    .. rubric:: Commands execution methods


    .. method:: execute(operation [, parameters] [, async]) 
      
        Prepare and execute a database operation (query or command).

        Parameters may be provided as sequence or mapping and will be bound to
        variables in the operation.  Variables are specified either with
        positional (``%s``) or named (:samp:`%({name})s`) placeholders. See
        :ref:`query-parameters`.
        
        The method returns `None`. If a query was executed, the returned
        values can be retrieved using |fetch*|_ methods.

        If `async` is ``True``, query execution will be asynchronous:
        the function returns immediately while the query is executed by the
        backend.  Use the `~cursor.isready()` method to see if the data is
        ready for return via |fetch*|_ methods. See
        :ref:`asynchronous-queries`.

        .. extension::

            The `async` parameter is a Psycopg extension to the |DBAPI|.


    .. method:: mogrify(operation [, parameters])

        Return a query string after arguments binding. The string returned is
        exactly the one that would be sent to the database running the
        `~cursor.execute()` method or similar.

            >>> cur.mogrify("INSERT INTO test (num, data) VALUES (%s, %s)", (42, 'bar'))
            "INSERT INTO test (num, data) VALUES (42, E'bar')"

        .. extension::

            The `mogrify()` method is a Psycopg extension to the |DBAPI|.

        
    .. method:: executemany(operation, seq_of_parameters)
      
        Prepare a database operation (query or command) and then execute it
        against all parameter tuples or mappings found in the sequence
        `seq_of_parameters`.
        
        The function is mostly useful for commands that update the database:
        any result set returned by the query is discarded.
        
        Parameters are bounded to the query using the same rules described in
        the `~cursor.execute()` method.


    .. method:: callproc(procname [, parameters] [, async])
            
        Call a stored database procedure with the given name. The sequence of
        parameters must contain one entry for each argument that the procedure
        expects. The result of the call is returned as modified copy of the
        input sequence. Input parameters are left untouched, output and
        input/output parameters replaced with possibly new values.
        
        The procedure may also provide a result set as output. This must then
        be made available through the standard |fetch*|_ methods.

        If `async` is ``True``, procedure execution will be asynchronous:
        the function returns immediately while the procedure is executed by
        the backend.  Use the `~cursor.isready()` method to see if the
        data is ready for return via |fetch*|_ methods. See
        :ref:`asynchronous-queries`.

        .. extension::

            The `async` parameter is a Psycopg extension to the |DBAPI|.


    .. method:: setinputsizes(sizes)
      
        This method is exposed in compliance with the |DBAPI|. It currently
        does nothing but it is safe to call it.



    .. |fetch*| replace:: `!fetch*()`

    .. _fetch*:

    .. rubric:: Results retrieval methods


    The following methods are used to read data from the database after an
    `~cursor.execute()` call.

    .. _cursor-iterable:

    .. note::

        `cursor` objects are iterable, so, instead of calling
        explicitly `~cursor.fetchone()` in a loop, the object itself can
        be used:

            >>> cur.execute("SELECT * FROM test;")
            >>> for record in cur:
            ...     print record
            ...
            (1, 100, "abc'def")
            (2, None, 'dada')
            (3, 42, 'bar')


    .. method:: fetchone()

        Fetch the next row of a query result set, returning a single tuple,
        or ``None`` when no more data is available:

            >>> cur.execute("SELECT * FROM test WHERE id = %s", (3,))
            >>> cur.fetchone()
            (3, 42, 'bar')
        
        A `~psycopg2.ProgrammingError` is raised if the previous call
        to |execute*|_ did not produce any result set or no call was issued
        yet.


    .. method:: fetchmany([size=cursor.arraysize])
      
        Fetch the next set of rows of a query result, returning a list of
        tuples. An empty list is returned when no more rows are available.
        
        The number of rows to fetch per call is specified by the parameter.
        If it is not given, the cursor's `~cursor.arraysize` determines
        the number of rows to be fetched. The method should try to fetch as
        many rows as indicated by the size parameter. If this is not possible
        due to the specified number of rows not being available, fewer rows
        may be returned:

            >>> cur.execute("SELECT * FROM test;")
            >>> cur.fetchmany(2)
            [(1, 100, "abc'def"), (2, None, 'dada')]
            >>> cur.fetchmany(2)
            [(3, 42, 'bar')]
            >>> cur.fetchmany(2)
            []

        A `~psycopg2.ProgrammingError` is raised if the previous call to
        |execute*|_ did not produce any result set or no call was issued yet.
        
        Note there are performance considerations involved with the size
        parameter.  For optimal performance, it is usually best to use the
        `~cursor.arraysize` attribute.  If the size parameter is used,
        then it is best for it to retain the same value from one
        `fetchmany()` call to the next.


    .. method:: fetchall()

        Fetch all (remaining) rows of a query result, returning them as a list
        of tuples.  An empty list is returned if there is no more record to
        fetch.

            >>> cur.execute("SELECT * FROM test;")
            >>> cur.fetchall()
            [(1, 100, "abc'def"), (2, None, 'dada'), (3, 42, 'bar')]

        A `~psycopg2.ProgrammingError` is raised if the previous call to
        |execute*|_ did not produce any result set or no call was issued yet.


    .. method:: scroll(value [, mode='relative'])

        Scroll the cursor in the result set to a new position according
        to mode.

        If `mode` is ``relative`` (default), value is taken as offset to
        the current position in the result set, if set to ``absolute``,
        value states an absolute target position.

        If the scroll operation would leave the result set, a
        `~psycopg2.ProgrammingError` is raised and the cursor position is
        not changed.

        The method can be used both for client-side cursors and
        :ref:`server-side cursors <server-side-cursors>`.

        .. note:: 

            According to the |DBAPI|_, the exception raised for a cursor out
            of bound should have been `!IndexError`.  The best option is
            probably to catch both exceptions in your code::

                try:
                    cur.scroll(1000 * 1000)
                except (ProgrammingError, IndexError), exc:
                    deal_with_it(exc)


    .. attribute:: arraysize
          
        This read/write attribute specifies the number of rows to fetch at a
        time with `~cursor.fetchmany()`. It defaults to 1 meaning to fetch
        a single row at a time.
        

    .. attribute:: rowcount 
          
        This read-only attribute specifies the number of rows that the last
        |execute*|_ produced (for :abbr:`DQL (Data Query Language)` statements
        like :sql:`SELECT`) or affected (for 
        :abbr:`DML (Data Manipulation Language)` statements like :sql:`UPDATE`
        or :sql:`INSERT`).
        
        The attribute is -1 in case no |execute*| has been performed on
        the cursor or the row count of the last operation if it can't be
        determined by the interface.

        .. note::
            The |DBAPI|_ interface reserves to redefine the latter case to
            have the object return ``None`` instead of -1 in future versions
            of the specification.
        

    .. attribute:: rownumber

        This read-only attribute provides the current 0-based index of the
        cursor in the result set or ``None`` if the index cannot be
        determined.

        The index can be seen as index of the cursor in a sequence (the result
        set). The next fetch operation will fetch the row indexed by
        `rownumber` in that sequence.


    .. index:: oid

    .. attribute:: lastrowid

        This read-only attribute provides the OID of the last row inserted
        by the cursor. If the table wasn't created with OID support or the
        last operation is not a single record insert, the attribute is set to
        ``None``.

        PostgreSQL currently advices to not create OIDs on the tables and the
        default for |CREATE-TABLE|__ is to not support them. The
        |INSERT-RETURNING|__ syntax available from PostgreSQL 8.3 allows more
        flexibility.

        .. |CREATE-TABLE| replace:: :sql:`CREATE TABLE`
        .. __: http://www.postgresql.org/docs/8.4/static/sql-createtable.html

        .. |INSERT-RETURNING| replace:: :sql:`INSERT ... RETURNING`
        .. __: http://www.postgresql.org/docs/8.4/static/sql-insert.html


    .. method:: nextset()
    
        This method is not supported (PostgreSQL does not have multiple data
        sets) and will raise a `~psycopg2.NotSupportedError` exception.


    .. method:: setoutputsize(size [, column])
      
        This method is exposed in compliance with the |DBAPI|. It currently
        does nothing but it is safe to call it.


    .. attribute:: query

        Read-only attribute containing the body of the last query sent to the
        backend (including bound arguments). ``None`` if no query has been
        executed yet:

            >>> cur.execute("INSERT INTO test (num, data) VALUES (%s, %s)", (42, 'bar'))
            >>> cur.query 
            "INSERT INTO test (num, data) VALUES (42, E'bar')"

        .. extension::

            The `query` attribute is a Psycopg extension to the |DBAPI|.


    .. attribute:: statusmessage

        Read-only attribute containing the message returned by the last
        command:

            >>> cur.execute("INSERT INTO test (num, data) VALUES (%s, %s)", (42, 'bar'))
            >>> cur.statusmessage 
            'INSERT 0 1'

        .. extension::

            The `statusmessage` attribute is a Psycopg extension to the
            |DBAPI|.


    .. method:: isready()

        Return ``False`` if the backend is still processing an asynchronous
        query or ``True`` if data is ready to be fetched by one of the
        |fetch*|_ methods.  See :ref:`asynchronous-queries`.

        .. extension::

            The `isready()` method is a Psycopg extension to the |DBAPI|.


    .. method:: fileno()

        Return the file descriptor associated with the current connection and
        make possible to use a cursor in a context where a file object would
        be expected (like in a `select()` call).  See
        :ref:`asynchronous-queries`.

        .. extension::

            The `fileno()` method is a Psycopg extension to the |DBAPI|.


    .. attribute:: tzinfo_factory

        The time zone factory used to handle data types such as
        :sql:`TIMESTAMP WITH TIME ZONE`.  It should be a |tzinfo|_ object.
        See also the `psycopg2.tz` module.

        .. |tzinfo| replace:: `!tzinfo`
        .. _tzinfo: http://docs.python.org/library/datetime.html#tzinfo-objects



    .. rubric:: COPY-related methods

    .. extension::

        The :sql:`COPY` command is a PostgreSQL extension to the SQL standard.
        As such, its support is a Psycopg extension to the |DBAPI|.

    .. method:: copy_from(file, table, sep='\\t', null='\\N', columns=None)
 
        Read data *from* the file-like object `file` appending them to
        the table named `table`.  `file` must have both
        `!read()` and `!readline()` method.  See :ref:`copy` for an
        overview.

        The optional argument `sep` is the columns separator and
        `null` represents :sql:`NULL` values in the file.

        The `columns` argument is a sequence containing the name of the
        fields where the read data will be entered.  Its length and column
        type should match the content of the read file.  If not specifies, it
        is assumed that the entire table matches the file structure.

            >>> f = StringIO("42\tfoo\n74\tbar\n")
            >>> cur.copy_from(f, 'test', columns=('num', 'data'))
            >>> cur.execute("select * from test where id > 5;")
            >>> cur.fetchall()
            [(6, 42, 'foo'), (7, 74, 'bar')]

        .. versionchanged:: 2.0.6
            added the `columns` parameter.


    .. method:: copy_to(file, table, sep='\\t', null='\\N', columns=None)

        Write the content of the table named `table` *to* the file-like
        object `file`.  `file` must have a `!write()` method.
        See :ref:`copy` for an overview.

        The optional argument `sep` is the columns separator and
        `null` represents :sql:`NULL` values in the file.

        The `columns` argument is a sequence of field names: if not
        ``None`` only the specified fields will be included in the dump.

            >>> cur.copy_to(sys.stdout, 'test', sep="|")
            1|100|abc'def
            2|\N|dada
            ...

        .. versionchanged:: 2.0.6
            added the `columns` parameter.


    .. method:: copy_expert(sql, file [, size])

        Submit a user-composed :sql:`COPY` statement. The method is useful to
        handle all the parameters that PostgreSQL makes available (see
        |COPY|__ command documentation).

        `file` must be an open, readable file for :sql:`COPY FROM` or an
        open, writeable file for :sql:`COPY TO`. The optional `size`
        argument, when specified for a :sql:`COPY FROM` statement, will be
        passed to `file`\ 's read method to control the read buffer
        size.

            >>> cur.copy_expert("COPY test TO STDOUT WITH CSV HEADER", sys.stdout)
            id,num,data
            1,100,abc'def
            2,,dada
            ...

        .. |COPY| replace:: :sql:`COPY`
        .. __: http://www.postgresql.org/docs/8.4/static/sql-copy.html

        .. versionadded:: 2.0.6

