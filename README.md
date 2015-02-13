# dbexplorer_pgsql

PostgreSQL database support for Komodo IDE.

# Building

To build this add-on, use *koext* from the Komodo add-on SDK:

```
cd dbexplorer_pgsql
koext build
```

# Notes

The *src* directory contains the source code of the psycopg2 Python library,
which is licensed under the LGPL.

The *platform* directory contains the compiled forms of the psycopg2 library,
one for each platform supported.
