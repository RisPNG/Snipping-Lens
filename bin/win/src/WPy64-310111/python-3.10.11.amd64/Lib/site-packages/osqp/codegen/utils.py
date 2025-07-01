"""
Utilities to generate embedded C code from OSQP sources
"""
# Compatibility with Python 2
from __future__ import print_function
from builtins import range

# Path of osqp module
import os.path
import osqp
files_to_generate_path = os.path.join(osqp.__path__[0],
                                      'codegen', 'files_to_generate')

# Timestamp
import datetime


def write_vec(f, vec, name, vec_type):
    """
    Write vector to file
    """
    if len(vec) > 0:

        f.write('%s %s[%d] = {\n' % (vec_type, name, len(vec)))

        # Write vector elements
        for i in range(len(vec)):
            if vec_type == 'c_float':
                f.write('(c_float)%.20f,\n' % vec[i])
            else:
                f.write('%i,\n' % vec[i])

        f.write('};\n')


def write_vec_extern(f, vec, name, vec_type):
    """
    Write vector prototype to file
    """
    if len(vec) > 0:
        f.write("extern %s %s[%d];\n" % (vec_type, name, len(vec)))


def write_mat(f, mat, name):
    """
    Write scipy sparse matrix in CSC form to file
    """
    write_vec(f, mat['p'], name + '_p', 'c_int')
    if len(mat['x']) > 0:
        write_vec(f, mat['i'], name + '_i', 'c_int')
        write_vec(f, mat['x'], name + '_x', 'c_float')

    f.write("csc %s = {" % name)
    f.write("%d, " % mat['nzmax'])
    f.write("%d, " % mat['m'])
    f.write("%d, " % mat['n'])
    f.write("%s_p, " % name)
    if len(mat['x']) > 0:
        f.write("%s_i, " % name)
        f.write("%s_x, " % name)
    else:
        f.write("0, 0, ")
    f.write("%d};\n" % mat['nz'])


def write_mat_extern(f, mat, name):
    """
    Write matrix prototype to file
    """
    f.write("extern csc %s;\n" % name)


def write_data_src(f, data):
    """
    Write data structure to file
    """
    f.write("// Define data structure\n")

    # Define matrix P
    write_mat(f, data['P'], 'Pdata')

    # Define matrix A
    write_mat(f, data['A'], 'Adata')

    # Define other data vectors
    write_vec(f, data['q'], 'qdata', 'c_float')
    write_vec(f, data['l'], 'ldata', 'c_float')
    write_vec(f, data['u'], 'udata', 'c_float')

    # Define data structure
    f.write("OSQPData data = {")
    f.write("%d, " % data['n'])
    f.write("%d, " % data['m'])
    f.write("&Pdata, &Adata, qdata, ldata, udata")
    f.write("};\n\n")


def write_data_inc(f, data):
    """
    Write data structure prototypes to file
    """
    f.write("// Data structure prototypes\n")

    # Define matrix P
    write_mat_extern(f, data['P'], 'Pdata')

    # Define matrix A
    write_mat_extern(f, data['A'], 'Adata')

    # Define other data vectors
    write_vec_extern(f, data['q'], 'qdata', 'c_float')
    write_vec_extern(f, data['l'], 'ldata', 'c_float')
    write_vec_extern(f, data['u'], 'udata', 'c_float')

    # Define data structure
    f.write("extern OSQPData data;\n\n")


def write_settings_src(f, settings, embedded_flag):
    """
    Write settings structure to file
    """
    f.write("// Define settings structure\n")
    f.write("OSQPSettings settings = {")
    f.write("(c_float)%.20f, " % settings['rho'])
    f.write("(c_float)%.20f, " % settings['sigma'])
    f.write("%d, " % settings['scaling'])

    if embedded_flag != 1:
        f.write("%d, " % settings['adaptive_rho'])
        f.write("%d, " % settings['adaptive_rho_interval'])
        f.write("(c_float)%.20f, " % settings['adaptive_rho_tolerance'])

    f.write("%d, " % settings['max_iter'])
    f.write("(c_float)%.20f, " % settings['eps_abs'])
    f.write("(c_float)%.20f, " % settings['eps_rel'])
    f.write("(c_float)%.20f, " % settings['eps_prim_inf'])
    f.write("(c_float)%.20f, " % settings['eps_dual_inf'])
    f.write("(c_float)%.20f, " % settings['alpha'])
    f.write("(enum linsys_solver_type) LINSYS_SOLVER, ")

    f.write("%d, " % settings['scaled_termination'])
    f.write("%d, " % settings['check_termination'])
    f.write("%d, " % settings['warm_start'])

    f.write("};\n\n")


def write_settings_inc(f, settings, embedded_flag):
    """
    Write prototype for settings structure to file
    """
    f.write("// Settings structure prototype\n")
    f.write("extern OSQPSettings settings;\n\n")


def write_scaling_src(f, scaling):
    """
    Write scaling structure to file
    """
    f.write("// Define scaling structure\n")
    if scaling is not None:
        write_vec(f, scaling['D'],    'Dscaling',    'c_float')
        write_vec(f, scaling['Dinv'], 'Dinvscaling', 'c_float')
        write_vec(f, scaling['E'],    'Escaling',    'c_float')
        write_vec(f, scaling['Einv'], 'Einvscaling', 'c_float')
        f.write("OSQPScaling scaling = {")
        f.write("(c_float)%.20f, " % scaling['c'])
        f.write("Dscaling, Escaling, ")
        f.write("(c_float)%.20f, " % scaling['cinv'])
        f.write("Dinvscaling, Einvscaling};\n\n")
    else:
        f.write("OSQPScaling scaling;\n\n")


def write_scaling_inc(f, scaling):
    """
    Write prototypes for the scaling structure to file
    """
    f.write("// Scaling structure prototypes\n")

    if scaling is not None:
        write_vec_extern(f, scaling['D'],    'Dscaling',    'c_float')
        write_vec_extern(f, scaling['Dinv'], 'Dinvscaling', 'c_float')
        write_vec_extern(f, scaling['E'],    'Escaling',    'c_float')
        write_vec_extern(f, scaling['Einv'], 'Einvscaling', 'c_float')

    f.write("extern OSQPScaling scaling;\n\n")


def write_linsys_solver_src(f, linsys_solver, embedded_flag):
    """
    Write linsys_solver structure to file
    """

    f.write("// Define linsys_solver structure\n")
    write_mat(f, linsys_solver['L'],            'linsys_solver_L')
    write_vec(f, linsys_solver['Dinv'],         'linsys_solver_Dinv',           'c_float')
    write_vec(f, linsys_solver['P'],            'linsys_solver_P',              'c_int')
    f.write("c_float linsys_solver_bp[%d];\n"  % (len(linsys_solver['bp'])))
    f.write("c_float linsys_solver_sol[%d];\n" % (len(linsys_solver['sol'])))
    write_vec(f, linsys_solver['rho_inv_vec'],  'linsys_solver_rho_inv_vec',    'c_float')

    if embedded_flag != 1:
        write_vec(f, linsys_solver['Pdiag_idx'], 'linsys_solver_Pdiag_idx', 'c_int')
        write_mat(f, linsys_solver['KKT'],       'linsys_solver_KKT')
        write_vec(f, linsys_solver['PtoKKT'],    'linsys_solver_PtoKKT',    'c_int')
        write_vec(f, linsys_solver['AtoKKT'],    'linsys_solver_AtoKKT',    'c_int')
        write_vec(f, linsys_solver['rhotoKKT'],  'linsys_solver_rhotoKKT',  'c_int')
        write_vec(f, linsys_solver['D'],         'linsys_solver_D',         'QDLDL_float')
        write_vec(f, linsys_solver['etree'],     'linsys_solver_etree',     'QDLDL_int')
        write_vec(f, linsys_solver['Lnz'],       'linsys_solver_Lnz',       'QDLDL_int')
        f.write("QDLDL_int   linsys_solver_iwork[%d];\n" % len(linsys_solver['iwork']))
        f.write("QDLDL_bool  linsys_solver_bwork[%d];\n" % len(linsys_solver['bwork']))
        f.write("QDLDL_float linsys_solver_fwork[%d];\n" % len(linsys_solver['fwork']))

    f.write("qdldl_solver linsys_solver = ")
    f.write("{QDLDL_SOLVER, &solve_linsys_qdldl, ")

    if embedded_flag != 1:
        f.write("&update_linsys_solver_matrices_qdldl, &update_linsys_solver_rho_vec_qdldl, ")

    f.write("&linsys_solver_L, linsys_solver_Dinv, linsys_solver_P, linsys_solver_bp, linsys_solver_sol, linsys_solver_rho_inv_vec, ")
    f.write("(c_float)%.20f, " % linsys_solver['sigma'])
    f.write("%d, " % linsys_solver['n'])
    f.write("%d, " % linsys_solver['m'])
    
    if embedded_flag != 1:
        if len(linsys_solver['Pdiag_idx']) > 0:
            linsys_solver_Pdiag_idx_string = 'linsys_solver_Pdiag_idx'
            linsys_solver_PtoKKT_string = 'linsys_solver_PtoKKT'
        else:
            linsys_solver_Pdiag_idx_string = '0'
            linsys_solver_PtoKKT_string = '0'
        if len(linsys_solver['AtoKKT']) > 0:
            linsys_solver_AtoKKT_string = 'linsys_solver_AtoKKT'
        else:
            linsys_solver_AtoKKT_string = '0'
        f.write("%s, " % linsys_solver_Pdiag_idx_string)
        f.write("%d, " % linsys_solver['Pdiag_n'])
        f.write("&linsys_solver_KKT, %s, %s, linsys_solver_rhotoKKT, "
                % (linsys_solver_PtoKKT_string, linsys_solver_AtoKKT_string) +
                "linsys_solver_D, linsys_solver_etree, linsys_solver_Lnz, " +
                "linsys_solver_iwork, linsys_solver_bwork, linsys_solver_fwork, ")
    
    f.write("};\n\n")


def write_linsys_solver_inc(f, linsys_solver, embedded_flag):
    """
    Write prototypes for linsys_solver structure to file
    """
    f.write("// Prototypes for linsys_solver structure\n")
    write_mat_extern(f, linsys_solver['L'],    'linsys_solver_L')
    write_vec_extern(f, linsys_solver['Dinv'], 'linsys_solver_Dinv', 'c_float')
    write_vec_extern(f, linsys_solver['P'],    'linsys_solver_P',    'c_int')
    f.write("extern c_float linsys_solver_bp[%d];\n"  % len(linsys_solver['bp']))
    f.write("extern c_float linsys_solver_sol[%d];\n" % len(linsys_solver['sol']))
    write_vec_extern(f, linsys_solver['rho_inv_vec'], 'linsys_solver_rho_inv_vec', 'c_float')

    if embedded_flag != 1:
        write_vec_extern(f, linsys_solver['Pdiag_idx'], 'linsys_solver_Pdiag_idx', 'c_int')
        write_mat_extern(f, linsys_solver['KKT'],       'linsys_solver_KKT')
        write_vec_extern(f, linsys_solver['PtoKKT'],    'linsys_solver_PtoKKT',    'c_int')
        write_vec_extern(f, linsys_solver['AtoKKT'],    'linsys_solver_AtoKKT',    'c_int')
        write_vec_extern(f, linsys_solver['rhotoKKT'],  'linsys_solver_rhotoKKT',  'c_int')
        write_vec_extern(f, linsys_solver['D'],         'linsys_solver_D',         'QDLDL_float')
        write_vec_extern(f, linsys_solver['etree'],     'linsys_solver_etree',     'QDLDL_int')
        write_vec_extern(f, linsys_solver['Lnz'],       'linsys_solver_Lnz',       'QDLDL_int')
        f.write("extern QDLDL_int   linsys_solver_iwork[%d];\n" % len(linsys_solver['iwork']))
        f.write("extern QDLDL_bool  linsys_solver_bwork[%d];\n" % len(linsys_solver['bwork']))
        f.write("extern QDLDL_float linsys_solver_fwork[%d];\n" % len(linsys_solver['fwork']))

    f.write("extern qdldl_solver linsys_solver;\n\n")


def write_solution_src(f, data):
    """
    Preallocate solution vectors
    """
    f.write("// Define solution\n")
    f.write("c_float xsolution[%d];\n" % data['n'])
    f.write("c_float ysolution[%d];\n\n" % data['m'])
    f.write("OSQPSolution solution = {xsolution, ysolution};\n\n")


def write_solution_inc(f, data):
    """
    Prototypes for solution vectors
    """
    f.write("// Prototypes for solution\n")
    f.write("extern c_float xsolution[%d];\n" % data['n'])
    f.write("extern c_float ysolution[%d];\n\n" % data['m'])
    f.write("extern OSQPSolution solution;\n\n")


def write_info_src(f):
    """
    Preallocate info structure
    """
    f.write("// Define info\n")
    f.write('OSQPInfo info = {0, "Unsolved", OSQP_UNSOLVED, 0.0, 0.0, 0.0};\n\n')


def write_info_inc(f):
    """
    Prototype for info structure
    """
    f.write("// Prototype for info structure\n")
    f.write("extern OSQPInfo info;\n\n")


def write_workspace_src(f, n, m, rho_vectors, embedded_flag):
    """
    Preallocate workspace structure and populate rho vectors
    """

    f.write("// Define workspace\n")

    write_vec(f, rho_vectors['rho_vec'],     'work_rho_vec',     'c_float')
    write_vec(f, rho_vectors['rho_inv_vec'], 'work_rho_inv_vec', 'c_float')
    if embedded_flag != 1:
        write_vec(f, rho_vectors['constr_type'], 'work_constr_type', 'c_int')

    f.write("c_float work_x[%d];\n" % n)
    f.write("c_float work_y[%d];\n" % m)
    f.write("c_float work_z[%d];\n" % m)
    f.write("c_float work_xz_tilde[%d];\n" % (m + n))
    f.write("c_float work_x_prev[%d];\n" % n)
    f.write("c_float work_z_prev[%d];\n" % m)
    f.write("c_float work_Ax[%d];\n" % m)
    f.write("c_float work_Px[%d];\n" % n)
    f.write("c_float work_Aty[%d];\n" % n)
    f.write("c_float work_delta_y[%d];\n" % m)
    f.write("c_float work_Atdelta_y[%d];\n" % n)
    f.write("c_float work_delta_x[%d];\n" % n)
    f.write("c_float work_Pdelta_x[%d];\n" % n)
    f.write("c_float work_Adelta_x[%d];\n" % m)
    f.write("c_float work_D_temp[%d];\n" % n)
    f.write("c_float work_D_temp_A[%d];\n" % n)
    f.write("c_float work_E_temp[%d];\n\n" % m)

    f.write("OSQPWorkspace workspace = {\n")
    f.write("&data, (LinSysSolver *)&linsys_solver,\n")
    f.write("work_rho_vec, work_rho_inv_vec,\n")
    if embedded_flag != 1:
        f.write("work_constr_type,\n")

    f.write("work_x, work_y, work_z, work_xz_tilde,\n")
    f.write("work_x_prev, work_z_prev,\n")
    f.write("work_Ax, work_Px, work_Aty,\n")
    f.write("work_delta_y, work_Atdelta_y,\n")
    f.write("work_delta_x, work_Pdelta_x, work_Adelta_x,\n")
    f.write("work_D_temp, work_D_temp_A, work_E_temp,\n")
    f.write("&settings, &scaling, &solution, &info};\n\n")


def write_workspace_inc(f, n, m, rho_vectors, embedded_flag):
    """
    Prototypes for the workspace structure and rho_vectors
    """
    f.write("// Prototypes for the workspace\n")
    write_vec_extern(f, rho_vectors['rho_vec'],     'work_rho_vec',     'c_float')
    write_vec_extern(f, rho_vectors['rho_inv_vec'], 'work_rho_inv_vec', 'c_float')
    if embedded_flag != 1:
        write_vec_extern(f, rho_vectors['constr_type'], 'work_constr_type', 'c_int')

    f.write("extern c_float work_x[%d];\n" % n)
    f.write("extern c_float work_y[%d];\n" % m)
    f.write("extern c_float work_z[%d];\n" % m)
    f.write("extern c_float work_xz_tilde[%d];\n" % (m + n))
    f.write("extern c_float work_x_prev[%d];\n" % n)
    f.write("extern c_float work_z_prev[%d];\n" % m)
    f.write("extern c_float work_Ax[%d];\n" % m)
    f.write("extern c_float work_Px[%d];\n" % n)
    f.write("extern c_float work_Aty[%d];\n" % n)
    f.write("extern c_float work_delta_y[%d];\n" % m)
    f.write("extern c_float work_Atdelta_y[%d];\n" % n)
    f.write("extern c_float work_delta_x[%d];\n" % n)
    f.write("extern c_float work_Pdelta_x[%d];\n" % n)
    f.write("extern c_float work_Adelta_x[%d];\n" % m)
    f.write("extern c_float work_D_temp[%d];\n" % n)
    f.write("extern c_float work_D_temp_A[%d];\n" % n)
    f.write("extern c_float work_E_temp[%d];\n\n" % m)

    f.write("extern OSQPWorkspace workspace;\n\n")


def render_workspace(variables, hfname, cfname):
    """
    Print workspace dimensions
    """

    rho_vectors = variables['rho_vectors']
    data = variables['data']
    linsys_solver = variables['linsys_solver']
    scaling = variables['scaling']
    settings = variables['settings']
    embedded_flag = variables['embedded_flag']
    n = data['n']
    m = data['m']

    # Open output file
    incFile = open(hfname, 'w')
    srcFile = open(cfname, 'w')

    # Add an include-guard statement
    fname = os.path.splitext(os.path.basename(hfname))[0]
    incGuard = fname.upper() + "_H"
    incFile.write("#ifndef %s\n" % incGuard)
    incFile.write("#define %s\n\n" % incGuard)

    # Print comment headers containing the generation time into the files
    now = datetime.datetime.now()
    daystr = now.strftime("%B %d, %Y")
    timestr = now.strftime("%H:%M:%S")
    incFile.write("/*\n")
    incFile.write(" * This file was autogenerated by OSQP-Python on %s at %s.\n" % (daystr, timestr))
    incFile.write(" * \n")
    incFile.write(" * This file contains the prototypes for all the workspace variables needed\n")
    incFile.write(" * by OSQP. The actual data is contained inside workspace.c.\n")
    incFile.write(" */\n\n")

    srcFile.write("/*\n")
    srcFile.write(" * This file was autogenerated by OSQP-Python on %s at %s.\n" % (daystr, timestr))
    srcFile.write(" * \n")
    srcFile.write(" * This file contains the workspace variables needed by OSQP.\n")
    srcFile.write(" */\n\n")

    # Include types, constants and linsys_solver header
    incFile.write("#include \"types.h\"\n")
    incFile.write("#include \"qdldl_interface.h\"\n\n")

    srcFile.write("#include \"types.h\"\n")
    srcFile.write("#include \"qdldl_interface.h\"\n\n")

    # Write data structure
    write_data_src(srcFile, data)
    write_data_inc(incFile, data)

    # Write settings structure
    write_settings_src(srcFile, settings, embedded_flag)
    write_settings_inc(incFile, settings, embedded_flag)

    # Write scaling structure
    write_scaling_src(srcFile, scaling)
    write_scaling_inc(incFile, scaling)

    # Write linsys_solver structure
    write_linsys_solver_src(srcFile, linsys_solver, embedded_flag)
    write_linsys_solver_inc(incFile, linsys_solver, embedded_flag)

    # Define empty solution structure
    write_solution_src(srcFile, data)
    write_solution_inc(incFile, data)

    # Define info structure
    write_info_src(srcFile)
    write_info_inc(incFile)

    # Define workspace structure
    write_workspace_src(srcFile, n, m, rho_vectors, embedded_flag)
    write_workspace_inc(incFile, n, m, rho_vectors, embedded_flag)

    # The endif for the include-guard
    incFile.write("#endif // ifndef %s\n" % incGuard)

    incFile.close()
    srcFile.close()


def render_setuppy(variables, output):
    """
    Render setup.py file
    """

    embedded_flag = variables['embedded_flag']
    python_ext_name = variables['python_ext_name']

    f = open(os.path.join(files_to_generate_path, 'setup.py'))
    filedata = f.read()
    f.close()

    filedata = filedata.replace("EMBEDDED_FLAG", str(embedded_flag))
    filedata = filedata.replace("PYTHON_EXT_NAME", str(python_ext_name))

    f = open(output, 'w')
    f.write(filedata)
    f.close()


def render_cmakelists(variables, output):
    """
    Render CMakeLists file
    """

    embedded_flag = variables['embedded_flag']

    f = open(os.path.join(files_to_generate_path, 'CMakeLists.txt'))
    filedata = f.read()
    f.close()

    filedata = filedata.replace("EMBEDDED_FLAG", str(embedded_flag))

    f = open(output, 'w')
    f.write(filedata)
    f.close()


def render_emosqpmodule(variables, output):
    """
    Render emosqpmodule.c file
    """

    python_ext_name = variables['python_ext_name']

    f = open(os.path.join(files_to_generate_path, 'emosqpmodule.c'))
    filedata = f.read()
    f.close()

    filedata = filedata.replace("PYTHON_EXT_NAME", str(python_ext_name))

    f = open(output, 'w')
    f.write(filedata)
    f.close()
