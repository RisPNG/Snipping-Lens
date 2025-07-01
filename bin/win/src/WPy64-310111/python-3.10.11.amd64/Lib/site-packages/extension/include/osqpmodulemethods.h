#ifndef OSQPMODULEMETHODS_H
#define OSQPMODULEMETHODS_H

/***********************************************************************
 * OSQP methods independently from any object                          *
 ***********************************************************************/

static PyObject *OSQP_constant(OSQP *self, PyObject *args) {

    char * constant_name;  // String less than 32 chars

    // Parse arguments
    if( !PyArg_ParseTuple(args, "s", &(constant_name))) {
        return (PyObject *) NULL;
    }


    if(!strcmp(constant_name, "OSQP_INFTY")){
#ifdef DFLOAT
        return Py_BuildValue("f", OSQP_INFTY);
#else
        return Py_BuildValue("d", OSQP_INFTY);
#endif
    }

    if(!strcmp(constant_name, "OSQP_NAN")){
#ifdef DFLOAT
        return Py_BuildValue("f", Py_NAN);
#else
        return Py_BuildValue("d", Py_NAN);
#endif
    }

    if(!strcmp(constant_name, "OSQP_SOLVED")){
        return Py_BuildValue("i", OSQP_SOLVED);
    }

    if(!strcmp(constant_name, "OSQP_SOLVED_INACCURATE")){
        return Py_BuildValue("i", OSQP_SOLVED_INACCURATE);
    }

    if(!strcmp(constant_name, "OSQP_UNSOLVED")){
        return Py_BuildValue("i", OSQP_UNSOLVED);
    }

    if(!strcmp(constant_name, "OSQP_PRIMAL_INFEASIBLE")){
        return Py_BuildValue("i", OSQP_PRIMAL_INFEASIBLE);
    }

	if(!strcmp(constant_name, "OSQP_PRIMAL_INFEASIBLE_INACCURATE")){
		return Py_BuildValue("i", OSQP_PRIMAL_INFEASIBLE_INACCURATE);
	}

    if(!strcmp(constant_name, "OSQP_DUAL_INFEASIBLE")){
        return Py_BuildValue("i", OSQP_DUAL_INFEASIBLE);
    }

	if(!strcmp(constant_name, "OSQP_DUAL_INFEASIBLE_INACCURATE")){
		return Py_BuildValue("i", OSQP_DUAL_INFEASIBLE_INACCURATE);
	}

    if(!strcmp(constant_name, "OSQP_MAX_ITER_REACHED")){
        return Py_BuildValue("i", OSQP_MAX_ITER_REACHED);
    }

    if(!strcmp(constant_name, "OSQP_NON_CVX")){
        return Py_BuildValue("i", OSQP_NON_CVX);
    }

    if(!strcmp(constant_name, "OSQP_TIME_LIMIT_REACHED")){
        return Py_BuildValue("i", OSQP_TIME_LIMIT_REACHED);
    }

	// Linear system solvers
	if(!strcmp(constant_name, "QDLDL_SOLVER")){
		return Py_BuildValue("i", QDLDL_SOLVER);
	}

	if(!strcmp(constant_name, "MKL_PARDISO_SOLVER")){
		return Py_BuildValue("i", MKL_PARDISO_SOLVER);
	}

    // If reached here error
    PyErr_SetString(PyExc_ValueError, "Constant not recognized");
    return (PyObject *) NULL;
}




static PyMethodDef OSQP_module_methods[] = {
	{"constant", (PyCFunction)OSQP_constant, METH_VARARGS, PyDoc_STR("Return internal OSQP constant")},
	{NULL, NULL}		/* sentinel */
};


#endif
