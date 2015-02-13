/* adapter_pdecimal.c - psycopg Decimal type wrapper implementation
 *
 * Copyright (C) 2003-2010 Federico Di Gregorio <fog@debian.org>
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

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <structmember.h>
#include <floatobject.h>
#include <math.h>

#define PSYCOPG_MODULE
#include "psycopg/config.h"
#include "psycopg/python.h"
#include "psycopg/psycopg.h"
#include "psycopg/adapter_pdecimal.h"
#include "psycopg/microprotocols_proto.h"


/** the Decimal object **/

static PyObject *
pdecimal_str(pdecimalObject *self)
{
    PyObject *check, *res = NULL;
#if PY_VERSION_HEX < 0x02050000
    check = PyObject_CallMethod(self->wrapped, "_isnan", NULL);
    if (PyInt_AsLong(check) == 1) {
        res = PyString_FromString("'NaN'::numeric");
        goto end;
    }
    Py_DECREF(check);
    check = PyObject_CallMethod(self->wrapped, "_isinfinity", NULL);
    if (abs(PyInt_AsLong(check)) == 1) {
        res = PyString_FromString("'NaN'::numeric");
        goto end;
    }
    res = PyObject_Str(self->wrapped);
#else
    check = PyObject_CallMethod(self->wrapped, "is_finite", NULL);
    if (check == Py_True)
        res = PyObject_Str(self->wrapped);
    else
        res = PyString_FromString("'NaN'::numeric");
#endif

   end:
    Py_DECREF(check);
    return res;
}

static PyObject *
pdecimal_getquoted(pdecimalObject *self, PyObject *args)
{
    if (!PyArg_ParseTuple(args, "")) return NULL;
    return pdecimal_str(self);
}

static PyObject *
pdecimal_conform(pdecimalObject *self, PyObject *args)
{
    PyObject *res, *proto;

    if (!PyArg_ParseTuple(args, "O", &proto)) return NULL;

    if (proto == (PyObject*)&isqlquoteType)
        res = (PyObject*)self;
    else
        res = Py_None;

    Py_INCREF(res);
    return res;
}

/** the Decimal object */

/* object member list */

static struct PyMemberDef pdecimalObject_members[] = {
    {"adapted", T_OBJECT, offsetof(pdecimalObject, wrapped), RO},
    {NULL}
};

/* object method table */

static PyMethodDef pdecimalObject_methods[] = {
    {"getquoted", (PyCFunction)pdecimal_getquoted, METH_VARARGS,
     "getquoted() -> wrapped object value as SQL-quoted string"},
    {"__conform__", (PyCFunction)pdecimal_conform, METH_VARARGS, NULL},
    {NULL}  /* Sentinel */
};

/* initialization and finalization methods */

static int
pdecimal_setup(pdecimalObject *self, PyObject *obj)
{
    Dprintf("pdecimal_setup: init pdecimal object at %p, refcnt = "
        FORMAT_CODE_PY_SSIZE_T,
        self, ((PyObject *)self)->ob_refcnt
      );

    Py_INCREF(obj);
    self->wrapped = obj;

    Dprintf("pdecimal_setup: good pdecimal object at %p, refcnt = "
        FORMAT_CODE_PY_SSIZE_T,
        self, ((PyObject *)self)->ob_refcnt
      );
    return 0;
}

static int
pdecimal_traverse(PyObject *obj, visitproc visit, void *arg)
{
    pdecimalObject *self = (pdecimalObject *)obj;

    Py_VISIT(self->wrapped);
    return 0;
}

static void
pdecimal_dealloc(PyObject* obj)
{
    pdecimalObject *self = (pdecimalObject *)obj;

    Py_CLEAR(self->wrapped);

    Dprintf("pdecimal_dealloc: deleted pdecimal object at %p, refcnt = "
        FORMAT_CODE_PY_SSIZE_T,
        obj, obj->ob_refcnt
      );

    obj->ob_type->tp_free(obj);
}

static int
pdecimal_init(PyObject *obj, PyObject *args, PyObject *kwds)
{
    PyObject *o;

    if (!PyArg_ParseTuple(args, "O", &o))
        return -1;

    return pdecimal_setup((pdecimalObject *)obj, o);
}

static PyObject *
pdecimal_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    return type->tp_alloc(type, 0);
}

static void
pdecimal_del(PyObject* self)
{
    PyObject_GC_Del(self);
}

static PyObject *
pdecimal_repr(pdecimalObject *self)
{
    return PyString_FromFormat("<psycopg2._psycopg.Float object at %p>",
                                self);
}


/* object type */

#define pdecimalType_doc \
"Decimal(str) -> new Decimal adapter object"

PyTypeObject pdecimalType = {
    PyObject_HEAD_INIT(NULL)
    0,
    "psycopg2._psycopg.Decimal",
    sizeof(pdecimalObject),
    0,
    pdecimal_dealloc, /*tp_dealloc*/
    0,          /*tp_print*/

    0,          /*tp_getattr*/
    0,          /*tp_setattr*/

    0,          /*tp_compare*/

    (reprfunc)pdecimal_repr, /*tp_repr*/
    0,          /*tp_as_number*/
    0,          /*tp_as_sequence*/
    0,          /*tp_as_mapping*/
    0,          /*tp_hash */

    0,          /*tp_call*/
    (reprfunc)pdecimal_str, /*tp_str*/

    0,          /*tp_getattro*/
    0,          /*tp_setattro*/
    0,          /*tp_as_buffer*/

    Py_TPFLAGS_DEFAULT|Py_TPFLAGS_BASETYPE|Py_TPFLAGS_HAVE_GC, /*tp_flags*/
    pdecimalType_doc, /*tp_doc*/

    pdecimal_traverse, /*tp_traverse*/
    0,          /*tp_clear*/

    0,          /*tp_richcompare*/
    0,          /*tp_weaklistoffset*/

    0,          /*tp_iter*/
    0,          /*tp_iternext*/

    /* Attribute descriptor and subclassing stuff */

    pdecimalObject_methods, /*tp_methods*/
    pdecimalObject_members, /*tp_members*/
    0,          /*tp_getset*/
    0,          /*tp_base*/
    0,          /*tp_dict*/

    0,          /*tp_descr_get*/
    0,          /*tp_descr_set*/
    0,          /*tp_dictoffset*/

    pdecimal_init, /*tp_init*/
    0, /*tp_alloc  will be set to PyType_GenericAlloc in module init*/
    pdecimal_new, /*tp_new*/
    (freefunc)pdecimal_del, /*tp_free  Low-level free-memory routine */
    0,          /*tp_is_gc For PyObject_IS_GC */
    0,          /*tp_bases*/
    0,          /*tp_mro method resolution order */
    0,          /*tp_cache*/
    0,          /*tp_subclasses*/
    0           /*tp_weaklist*/
};


/** module-level functions **/

PyObject *
psyco_Decimal(PyObject *module, PyObject *args)
{
    PyObject *obj;

    if (!PyArg_ParseTuple(args, "O", &obj))
        return NULL;

    return PyObject_CallFunction((PyObject *)&pdecimalType, "O", obj);
}
