#ifndef OSQPWORKSPACEPY_H
#define OSQPWORKSPACEPY_H

#include "qdldl_interface.h"

/**********************************************
 * OSQP Workspace creation in Python objects  *
 **********************************************/

 static PyObject *OSQP_get_rho_vectors(OSQP *self) {

     npy_intp m = (npy_intp)self->workspace->data->m;

     int float_type = get_float_type();
     int int_type   = get_int_type();

     PyObject *return_dict;

     /* Build Arrays. */
     PyObject *rho_vec     = PyArray_SimpleNewFromData(1, &m, float_type, self->workspace->rho_vec);
     PyObject *rho_inv_vec = PyArray_SimpleNewFromData(1, &m, float_type, self->workspace->rho_inv_vec);
     PyObject *constr_type = PyArray_SimpleNewFromData(1, &m, int_type,   self->workspace->constr_type);

     /* Change data ownership. */
     PyArray_ENABLEFLAGS((PyArrayObject *) rho_vec,     NPY_ARRAY_OWNDATA);
     PyArray_ENABLEFLAGS((PyArrayObject *) rho_inv_vec, NPY_ARRAY_OWNDATA);
     PyArray_ENABLEFLAGS((PyArrayObject *) constr_type, NPY_ARRAY_OWNDATA);

     /* Build Python dictionary. */
     return_dict = Py_BuildValue("{s:O,s:O,s:O}", "rho_vec", rho_vec,
                                 "rho_inv_vec", rho_inv_vec, "constr_type", constr_type);

     return return_dict;
 }


 static PyObject *OSQP_get_scaling(OSQP *self){

     if(self->workspace->settings->scaling) { // if scaling enabled
         npy_intp n = (npy_intp)self->workspace->data->n;  // Dimensions in R^n
         npy_intp m = (npy_intp)self->workspace->data->m;  // Dimensions in R^m
         c_float c, cinv;  // Cost scaling

         int float_type = get_float_type();

         PyObject *return_dict;

         /* Build Arrays. */
         OSQPScaling *scaling = self->workspace->scaling;
         PyObject *D    = PyArray_SimpleNewFromData(1, &n, float_type, scaling->D);
         PyObject *E    = PyArray_SimpleNewFromData(1, &m, float_type, scaling->E);
         PyObject *Dinv = PyArray_SimpleNewFromData(1, &n, float_type, scaling->Dinv);
         PyObject *Einv = PyArray_SimpleNewFromData(1, &m, float_type, scaling->Einv);

         /* Change data ownership. */
         PyArray_ENABLEFLAGS((PyArrayObject *) D, NPY_ARRAY_OWNDATA);
         PyArray_ENABLEFLAGS((PyArrayObject *) E, NPY_ARRAY_OWNDATA);
         PyArray_ENABLEFLAGS((PyArrayObject *) Dinv, NPY_ARRAY_OWNDATA);
         PyArray_ENABLEFLAGS((PyArrayObject *) Einv, NPY_ARRAY_OWNDATA);

         c = scaling->c;
         cinv = scaling->cinv;

         /* Build Python dictionary. */
         return_dict = Py_BuildValue("{s:d, s:d, s:O,s:O,s:O,s:O}",
                                     "c", c, "cinv", cinv,
                                     "D", D, "E", E, "Dinv", Dinv, "Einv", Einv);

         return return_dict;

    } else { // Scaling disabled. Return None
        Py_INCREF(Py_None);
        return Py_None;
    }
 }


 static PyObject *OSQP_get_data(OSQP *self){
     OSQPData *data = self->workspace->data;
     npy_intp n = (npy_intp)data->n;
     npy_intp n_plus_1 = n+1;
     npy_intp m = (npy_intp)data->m;
     npy_intp Pnzmax = (npy_intp)data->P->p[n];
     npy_intp Anzmax = (npy_intp)data->A->p[n];
     npy_intp Pnz = (npy_intp)data->P->nz;
     npy_intp Anz = (npy_intp)data->A->nz;

     int float_type = get_float_type();
     int int_type   = get_int_type();

     PyObject *return_dict;

     /* Build Arrays. */
     PyObject *Pp   = PyArray_SimpleNewFromData(1, &n_plus_1, int_type, data->P->p);
     PyObject *Pi   = PyArray_SimpleNewFromData(1, &Pnzmax, int_type, data->P->i);
     PyObject *Px   = PyArray_SimpleNewFromData(1, &Pnzmax, float_type, data->P->x);
     PyObject *Ap   = PyArray_SimpleNewFromData(1, &n_plus_1, int_type, data->A->p);
     PyObject *Ai   = PyArray_SimpleNewFromData(1, &Anzmax, int_type, data->A->i);
     PyObject *Ax   = PyArray_SimpleNewFromData(1, &Anzmax, float_type, data->A->x);
     PyObject *q    = PyArray_SimpleNewFromData(1, &n, float_type, data->q);
     PyObject *l    = PyArray_SimpleNewFromData(1, &m, float_type, data->l);
     PyObject *u    = PyArray_SimpleNewFromData(1, &m, float_type, data->u);

     /* Change data ownership. */
     PyArray_ENABLEFLAGS((PyArrayObject *) Pp, NPY_ARRAY_OWNDATA);
     PyArray_ENABLEFLAGS((PyArrayObject *) Pi, NPY_ARRAY_OWNDATA);
     PyArray_ENABLEFLAGS((PyArrayObject *) Px, NPY_ARRAY_OWNDATA);
     PyArray_ENABLEFLAGS((PyArrayObject *) Ap, NPY_ARRAY_OWNDATA);
     PyArray_ENABLEFLAGS((PyArrayObject *) Ai, NPY_ARRAY_OWNDATA);
     PyArray_ENABLEFLAGS((PyArrayObject *) Ax, NPY_ARRAY_OWNDATA);
     PyArray_ENABLEFLAGS((PyArrayObject *) q, NPY_ARRAY_OWNDATA);
     PyArray_ENABLEFLAGS((PyArrayObject *) l, NPY_ARRAY_OWNDATA);
     PyArray_ENABLEFLAGS((PyArrayObject *) u, NPY_ARRAY_OWNDATA);

     return_dict = Py_BuildValue(
         "{s:i,s:i,"
         "s:{s:i,s:i,s:i,s:O,s:O,s:O,s:i},"
         "s:{s:i,s:i,s:i,s:O,s:O,s:O,s:i},"
         "s:O,s:O,s:O}",
         "n", data->n, "m", data->m,
         "P", "nzmax", Pnzmax, "m", n, "n", n, "p", Pp, "i", Pi, "x", Px, "nz", Pnz,
         "A", "nzmax", Anzmax, "m", m, "n", n, "p", Ap, "i", Ai, "x", Ax, "nz", Anz,
         "q", q, "l", l, "u", u);

     return return_dict;
 }


 static PyObject *OSQP_get_linsys_solver(OSQP *self){
     qdldl_solver * solver = (qdldl_solver *) self->workspace->linsys_solver;
     OSQPData *data = self->workspace->data;

     npy_intp Ln          = (npy_intp)solver->L->n;
     npy_intp Ln_plus_1   = Ln+1;
     npy_intp Lnzmax      = (npy_intp)solver->L->p[Ln];
     npy_intp Lnz         = (npy_intp)solver->L->nz;
     npy_intp Pdiag_n     = (npy_intp)solver->Pdiag_n;
     npy_intp KKTn        = (npy_intp)solver->KKT->n;
     npy_intp KKTn_plus_1 = KKTn+1;
     npy_intp KKTnzmax    = (npy_intp)solver->KKT->p[KKTn];
     npy_intp KKTnz       = (npy_intp)solver->KKT->nz;
     npy_intp Pnzmax      = (npy_intp)data->P->p[data->P->n];
     npy_intp Anzmax      = (npy_intp)data->A->p[data->A->n];
     npy_intp m           = (npy_intp)(data->m);
     npy_intp m_plus_n    = (npy_intp)(data->m + data->n);
     npy_intp m_plus_n_x3 = 3*m_plus_n;

     int float_type = get_float_type();
     int int_type   = get_int_type();

     PyObject *return_dict;

     /* Build Arrays. */
     PyObject *Lp           = PyArray_SimpleNewFromData(1, &Ln_plus_1,   int_type,   solver->L->p);
     PyObject *Li           = PyArray_SimpleNewFromData(1, &Lnzmax,      int_type,   solver->L->i);
     PyObject *Lx           = PyArray_SimpleNewFromData(1, &Lnzmax,      float_type, solver->L->x);
     PyObject *Dinv         = PyArray_SimpleNewFromData(1, &Ln,          float_type, solver->Dinv);
     PyObject *P            = PyArray_SimpleNewFromData(1, &Ln,          int_type,   solver->P);
     PyObject *bp           = PyArray_SimpleNewFromData(1, &Ln,          float_type, solver->bp);
     PyObject *sol          = PyArray_SimpleNewFromData(1, &Ln,          float_type, solver->sol);
     PyObject *rho_inv_vec  = PyArray_SimpleNewFromData(1, &m,           float_type, solver->rho_inv_vec);
     PyObject *Pdiag_idx    = PyArray_SimpleNewFromData(1, &Pdiag_n,     int_type,   solver->Pdiag_idx);
     PyObject *KKTp         = PyArray_SimpleNewFromData(1, &KKTn_plus_1, int_type,   solver->KKT->p);
     PyObject *KKTi         = PyArray_SimpleNewFromData(1, &KKTnzmax,    int_type,   solver->KKT->i);
     PyObject *KKTx         = PyArray_SimpleNewFromData(1, &KKTnzmax,    float_type, solver->KKT->x);
     PyObject *PtoKKT       = PyArray_SimpleNewFromData(1, &Pnzmax,      int_type,   solver->PtoKKT);
     PyObject *AtoKKT       = PyArray_SimpleNewFromData(1, &Anzmax,      int_type,   solver->AtoKKT);
     PyObject *rhotoKKT     = PyArray_SimpleNewFromData(1, &m,           int_type,   solver->rhotoKKT);
     PyObject *D            = PyArray_SimpleNewFromData(1, &m_plus_n,    float_type, solver->D);
     PyObject *etree        = PyArray_SimpleNewFromData(1, &m_plus_n,    int_type,   solver->etree);
     PyObject *Lnz_vec      = PyArray_SimpleNewFromData(1, &m_plus_n,    int_type,   solver->Lnz);
     PyObject *iwork        = PyArray_SimpleNewFromData(1, &m_plus_n_x3, int_type,   solver->iwork);
     PyObject *bwork        = PyArray_SimpleNewFromData(1, &m_plus_n,    int_type,   solver->bwork);
     PyObject *fwork        = PyArray_SimpleNewFromData(1, &m_plus_n,    float_type, solver->fwork);
     
     /* Change data ownership. */
     PyArray_ENABLEFLAGS((PyArrayObject *) Lp,          NPY_ARRAY_OWNDATA);
     PyArray_ENABLEFLAGS((PyArrayObject *) Li,          NPY_ARRAY_OWNDATA);
     PyArray_ENABLEFLAGS((PyArrayObject *) Lx,          NPY_ARRAY_OWNDATA);
     PyArray_ENABLEFLAGS((PyArrayObject *) Dinv,        NPY_ARRAY_OWNDATA);
     PyArray_ENABLEFLAGS((PyArrayObject *) P,           NPY_ARRAY_OWNDATA);
     PyArray_ENABLEFLAGS((PyArrayObject *) bp,          NPY_ARRAY_OWNDATA);
     PyArray_ENABLEFLAGS((PyArrayObject *) sol,         NPY_ARRAY_OWNDATA);
     PyArray_ENABLEFLAGS((PyArrayObject *) rho_inv_vec, NPY_ARRAY_OWNDATA);
     PyArray_ENABLEFLAGS((PyArrayObject *) Pdiag_idx,   NPY_ARRAY_OWNDATA);
     PyArray_ENABLEFLAGS((PyArrayObject *) KKTp,        NPY_ARRAY_OWNDATA);
     PyArray_ENABLEFLAGS((PyArrayObject *) KKTi,        NPY_ARRAY_OWNDATA);
     PyArray_ENABLEFLAGS((PyArrayObject *) KKTx,        NPY_ARRAY_OWNDATA);
     PyArray_ENABLEFLAGS((PyArrayObject *) PtoKKT,      NPY_ARRAY_OWNDATA);
     PyArray_ENABLEFLAGS((PyArrayObject *) AtoKKT,      NPY_ARRAY_OWNDATA);
     PyArray_ENABLEFLAGS((PyArrayObject *) rhotoKKT,    NPY_ARRAY_OWNDATA);
     PyArray_ENABLEFLAGS((PyArrayObject *) D,           NPY_ARRAY_OWNDATA);
     PyArray_ENABLEFLAGS((PyArrayObject *) etree,       NPY_ARRAY_OWNDATA);
     PyArray_ENABLEFLAGS((PyArrayObject *) Lnz_vec,     NPY_ARRAY_OWNDATA);
     PyArray_ENABLEFLAGS((PyArrayObject *) iwork,       NPY_ARRAY_OWNDATA);
     PyArray_ENABLEFLAGS((PyArrayObject *) bwork,       NPY_ARRAY_OWNDATA);
     PyArray_ENABLEFLAGS((PyArrayObject *) fwork,       NPY_ARRAY_OWNDATA);

     return_dict = Py_BuildValue(
         "{s:{s:i,s:i,s:i,s:O,s:O,s:O,s:i},"  // L
         "s:O,s:O,s:O,s:O,s:O,"               // Dinv, P, bp, sol, rho_inv_vec
         "s:d,s:i,s:i,s:i,"                   // sigma, polish, n, m
         "s:O,s:i,"                           // Pdiag_idx, Pdiag_n
         "s:{s:i,s:i,s:i,s:O,s:O,s:O,s:i},"   // KKT
         "s:O,s:O,s:O,"                       // PtoKKT, AtoKKT, rhotoKKT,
         "s:O,s:O,s:O,"                       // D, etree, Lnz
         "s:O,s:O,s:O}",                      // iwork, bwork, fwork
         "L", "nzmax", Lnzmax, "m", Ln, "n", Ln, "p", Lp, "i", Li, "x", Lx, "nz", Lnz,
         "Dinv", Dinv, "P", P, "bp", bp, "sol", sol, "rho_inv_vec", rho_inv_vec,
         "sigma", (double)solver->sigma, "polish", solver->polish, "n", solver->n, "m", solver->m,
         "Pdiag_idx", Pdiag_idx, "Pdiag_n", Pdiag_n,
         "KKT", "nzmax", KKTnzmax, "m", KKTn, "n", KKTn, "p", KKTp, "i", KKTi, "x", KKTx, "nz", KKTnz,
         "PtoKKT", PtoKKT, "AtoKKT", AtoKKT, "rhotoKKT", rhotoKKT,
         "D", D, "etree", etree, "Lnz", Lnz_vec,
         "iwork", iwork, "bwork", bwork, "fwork", fwork);

     return return_dict;
 }


 static PyObject *OSQP_get_settings(OSQP *self){
     OSQPSettings *settings = self->workspace->settings;

     PyObject *return_dict = Py_BuildValue(
         "{s:d,s:d,s:i,s:i,s:i,s:d,s:d,s:i,s:d,s:d,s:d, s:d, s:d, s:i, s:i, s:i, s:i, s:d}",
         "rho", (double)settings->rho,
         "sigma", (double)settings->sigma,
         "scaling", settings->scaling,
         "adaptive_rho", settings->adaptive_rho,
         "adaptive_rho_interval", settings->adaptive_rho_interval,
         "adaptive_rho_tolerance", settings->adaptive_rho_tolerance,
         "adaptive_rho_fraction", settings->adaptive_rho_fraction,
         "max_iter", settings->max_iter,
         "eps_abs", (double)settings->eps_abs,
         "eps_rel", (double)settings->eps_rel,
         "eps_prim_inf", (double)settings->eps_prim_inf,
         "eps_dual_inf", (double)settings->eps_dual_inf,
         "alpha", (double)settings->alpha,
         "linsys_solver", settings->linsys_solver,
         "warm_start", settings->warm_start,
         "scaled_termination", settings->scaled_termination,
         "check_termination", settings->check_termination,
         "time_limit", (double)settings->time_limit
         );
     return return_dict;
 }


static PyObject *OSQP_get_workspace(OSQP *self){
    PyObject *rho_vectors_py;
    PyObject *data_py;
    PyObject *linsys_solver_py;
    PyObject *scaling_py;
    PyObject *settings_py;
    PyObject *return_dict;

    // Check if linear systems solver is QDLDL_SOLVER
    if(!self->workspace) {
        PyErr_SetString(PyExc_ValueError, "Solver is uninitialized.  No data have been configured.");
        return (PyObject *) NULL;
    }

    if(self->workspace->linsys_solver->type != QDLDL_SOLVER) {
        PyErr_SetString(PyExc_ValueError, "OSQP setup was not performed using QDLDL! Run setup with linsys_solver set as QDLDL");
        return (PyObject *) NULL;
    }

     rho_vectors_py   = OSQP_get_rho_vectors(self);
     data_py          = OSQP_get_data(self);
     linsys_solver_py = OSQP_get_linsys_solver(self);
     scaling_py       = OSQP_get_scaling(self);
     settings_py      = OSQP_get_settings(self);

     return_dict = Py_BuildValue("{s:O,s:O,s:O,s:O,s:O}",
                                 "rho_vectors",   rho_vectors_py,
                                 "data",          data_py,
                                 "linsys_solver", linsys_solver_py,
                                 "scaling",       scaling_py,
                                 "settings",      settings_py);
     return return_dict;
}

#endif
