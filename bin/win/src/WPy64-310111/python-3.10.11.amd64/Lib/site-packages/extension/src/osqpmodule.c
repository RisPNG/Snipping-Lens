// Use not deprecated Numpy API (numpy > 1.7)
#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION

#include "Python.h"                 // Python API
#include "numpy/arrayobject.h"      // Numpy C API
#include "numpy/npy_math.h"         // For infinity values
#include "structmember.h"           // Python members structure (to store results)
#include "osqp.h"                   // OSQP API


// OSQP Object type
typedef struct {
    PyObject_HEAD
    OSQPWorkspace * workspace;  // Pointer to C workspace structure
} OSQP;

static PyTypeObject OSQP_Type;


#include "osqputilspy.h"        // Utilities functions
#include "osqpinfopy.h"         // Info object
#include "osqpresultspy.h"      // Results object
#include "osqpworkspacepy.h"    // OSQP workspace
#include "osqpobjectpy.h"       // OSQP object
#include "osqpmodulemethods.h"  // OSQP module methods independently from any OSQP object


/************************
 * Interface Methods    *
 ************************/

 /* Module initialization*/
 static struct PyModuleDef moduledef = {
     PyModuleDef_HEAD_INIT, "_osqp",       /* m_name */
     NULL,                                 /* m_doc */
     -1,                                   /* m_size */
     OSQP_module_methods,                  /* m_methods */
     NULL,                                 /* m_reload */
     NULL,                                 /* m_traverse */
     NULL,                                 /* m_clear */
     NULL,                                 /* m_free */
 };


static PyObject * moduleinit(void){

    PyObject *m;

    // Initialize module
    m = PyModule_Create(&moduledef);

    if (m == NULL) return NULL;

    // Initialize OSQP_Type
    OSQP_Type.tp_new = PyType_GenericNew;
    if (PyType_Ready(&OSQP_Type) < 0) return NULL;

    // Add type to the module dictionary and initialize it
    Py_INCREF(&OSQP_Type);
    if (PyModule_AddObject(m, "OSQP", (PyObject *)&OSQP_Type) < 0) return NULL;

    // Initialize Info Type
    OSQP_info_Type.tp_new = PyType_GenericNew;
    if (PyType_Ready(&OSQP_info_Type) < 0) return NULL;

    // Initialize Results Type
    OSQP_results_Type.tp_new = PyType_GenericNew;
    if (PyType_Ready(&OSQP_results_Type) < 0) return NULL;

    return m;
}


// Init OSQP Internal module
PyMODINIT_FUNC PyInit__osqp(void) {
    import_array(); /* for numpy arrays */
    return moduleinit();
}
