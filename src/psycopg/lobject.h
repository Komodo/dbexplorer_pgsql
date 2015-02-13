/* lobject.h - definition for the psycopg lobject type
 *
 * Copyright (C) 2006-2010 Federico Di Gregorio <fog@debian.org>
 *
 * This file is part of psycopg.
 *
 * psycopg2 is free software: you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as published
 * by the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * In addition, as a special exception, the copyright holders give
 * permission to link this program with the OpenSSL library (or with
 * modified versions of OpenSSL that use the same license as OpenSSL),
 * and distribute linked combinations including the two.
 *
 * You must obey the GNU Lesser General Public License in all respects for
 * all of the code used other than OpenSSL.
 *
 * psycopg2 is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 * FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public
 * License for more details.
 */

#ifndef PSYCOPG_LOBJECT_H
#define PSYCOPG_LOBJECT_H 1

#include <Python.h>
#include <libpq-fe.h>
#include <libpq/libpq-fs.h>

#include "psycopg/config.h"
#include "psycopg/connection.h"

#ifdef __cplusplus
extern "C" {
#endif

extern HIDDEN PyTypeObject lobjectType;

typedef struct {
    PyObject HEAD;

    connectionObject *conn;  /* connection owning the lobject */
    long int mark;           /* copied from conn->mark */

    const char *smode;       /* string mode if lobject was opened */

    int fd;                  /* the file descriptor for file-like ops */
    Oid oid;                 /* the oid for this lobject */
} lobjectObject;

/* functions exported from lobject_int.c */

HIDDEN int lobject_open(lobjectObject *self, connectionObject *conn,
                        Oid oid, int mode, Oid new_oid,
                        const char *new_file);
HIDDEN int lobject_unlink(lobjectObject *self);
HIDDEN int lobject_export(lobjectObject *self, const char *filename);

HIDDEN Py_ssize_t lobject_read(lobjectObject *self, char *buf, size_t len);
HIDDEN Py_ssize_t lobject_write(lobjectObject *self, const char *buf,
                                size_t len);
HIDDEN int lobject_seek(lobjectObject *self, int pos, int whence);
HIDDEN int lobject_tell(lobjectObject *self);
HIDDEN int lobject_close(lobjectObject *self);

#define lobject_is_closed(self) \
    ((self)->fd < 0 || !(self)->conn || (self)->conn->closed)

/* exception-raising macros */

#define EXC_IF_LOBJ_CLOSED(self) \
  if (lobject_is_closed(self)) { \
    PyErr_SetString(InterfaceError, "lobject already closed");  \
    return NULL; }

#define EXC_IF_LOBJ_LEVEL0(self) \
if (self->conn->isolation_level == 0) {                             \
    psyco_set_error(ProgrammingError, (PyObject*)self,              \
        "can't use a lobject outside of transactions", NULL, NULL); \
    return NULL;                                                    \
}
#define EXC_IF_LOBJ_UNMARKED(self) \
if (self->conn->mark != self->mark) {                  \
    psyco_set_error(ProgrammingError, (PyObject*)self, \
        "lobject isn't valid anymore", NULL, NULL);    \
    return NULL;                                       \
}

#ifdef __cplusplus
}
#endif

#endif /* !defined(PSYCOPG_LOBJECT_H) */
