Frequently Asked Questions
==========================

.. sectionauthor:: Daniele Varrazzo <daniele.varrazzo@gmail.com>

Here are a few gotchas you may encounter using `psycopg2`.  Feel free to
suggest new entries!


.. cssclass:: faq

Why does `!psycopg2` leave database sessions "idle in transaction"?
    Psycopg normally starts a new transaction the first time a query is
    executed, e.g. calling `cursor.execute()`, even if the command is a
    :sql:`SELECT`.  The transaction is not closed until an explicit
    `~connection.commit()` or `~connection.rollback()`.

    If you are writing a long-living program, you should probably ensure to
    call one of the transaction closing methods before leaving the connection
    unused for a long time (which may also be a few seconds, depending on the
    concurrency level in your database).  Alternatively you can use a
    connection in :ref:`autocommit <autocommit>` mode to avoid a new
    transaction to be started at the first command.

Why does `!cursor.execute()` raise the exception *can't adapt*?
    Psycopg converts Python objects in a SQL string representation by looking
    at the object class.  The exception is raised when you are trying to pass
    as query parameter an object for which there is no adapter registered for
    its class.  See :ref:`adapting-new-types` for informations.

I can't pass an integer or a float parameter to my query: it says *a number is required*, but *it is* a number!
    In your query string, you always have to use ``%s``  placeholders,
    event when passing a number.  All Python objects are converted by Psycopg
    in their SQL representation, so they get passed to the query as strings.
    See :ref:`query-parameters`. ::

        >>> cur.execute("INSERT INTO numbers VALUES (%d)", (42,)) # WRONG
        >>> cur.execute("INSERT INTO numbers VALUES (%s)", (42,)) # correct

I try to execute a query but it fails with the error *not all arguments converted during string formatting* (or *object does not support indexing*). Why?
    Psycopg always require positional arguments to be passed as a tuple, even
    when the query takes a single parameter.  And remember that to make a
    single item tuple in Python you need a comma!  See :ref:`query-parameters`.
    ::

        >>> cur.execute("INSERT INTO foo VALUES (%s)", "bar")    # WRONG
        >>> cur.execute("INSERT INTO foo VALUES (%s)", ("bar"))  # WRONG
        >>> cur.execute("INSERT INTO foo VALUES (%s)", ("bar",)) # correct

I receive the error *current transaction is aborted, commands ignored until end of transaction block* and can't do anything else!
    There was a problem *in the previous* command to the database, which
    resulted in an error.  The database will not recover automatically from
    this condition: you must run a `~connection.rollback()` before sending
    new commands to the session (if this seems too harsh, remember that
    PostgreSQL supports nested transactions using the |SAVEPOINT|_ command).

    .. |SAVEPOINT| replace:: :sql:`SAVEPOINT`
    .. _SAVEPOINT: http://www.postgresql.org/docs/8.4/static/sql-savepoint.html

Why do i get the error *current transaction is aborted, commands ignored until end of transaction block* when I use `!multiprocessing` (or any other forking system) and not when use `!threading`?
    Psycopg's connections can't be shared across processes (but are thread
    safe).  If you are forking the Python process ensure to create a new
    connection in each forked child.

My database is Unicode, but I receive all the strings as UTF-8 `str`. Can I receive `unicode` objects instead?
    The following magic formula will do the trick::

        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)

    See :ref:`unicode-handling` for the gory details.

I can't compile `!psycopg2`: the compiler says *error: Python.h: No such file or directory*. What am I missing?
    You need to install a Python development package: it is usually called
    ``python-dev``.

I can't compile `!psycopg2`: the compiler says *error: libpq-fe.h: No such file or directory*. What am I missing?
    You need to install the development version of the libpq: the package is
    usually called ``libpq-dev``.

When should I save and re-use a cursor as opposed to creating a new one as needed?
    Cursors are lightweight objects and creating lots of them should not pose
    any kind of problem. But note that cursors used to fetch result sets will
    cache the data and use memory in proportion to the result set size. Our
    suggestion is to almost always create a new cursor and dispose old ones as
    soon as the data is not required anymore (call `~cursor.close()` on
    them.) The only exception are tight loops where one usually use the same
    cursor for a whole bunch of :sql:`INSERT`\s or :sql:`UPDATE`\s.

When should I save and re-use a connection as opposed to creating a new one as needed?
    Creating a connection can be slow (think of SSL over TCP) so the best
    practice is to create a single connection and keep it open as long as
    required. It is also good practice to rollback or commit frequently (even
    after a single :sql:`SELECT` statement) to make sure the backend is never
    left "idle in transaction".  See also `psycopg2.pool` for lightweight
    connection pooling.

What are the advantages or disadvantages of using named cursors?
    The only disadvantages is that they use up resources on the server and
    that there is a little overhead because a at least two queries (one to
    create the cursor and one to fetch the initial result set) are issued to
    the backend. The advantage is that data is fetched one chunk at a time:
    using small `~cursor.fetchmany()` values it is possible to use very
    little memory on the client and to skip or discard parts of the result set.
