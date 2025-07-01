# flake8: noqa

import sys


cdef = []

if sys.platform == "win32":
    cdef.append("typedef wchar_t char_t;")
else:
    cdef.append("typedef char char_t;")

# hostfxr.h
cdef.append(
    """
enum hostfxr_delegate_type
{
    hdt_com_activation,
    hdt_load_in_memory_assembly,
    hdt_winrt_activation,
    hdt_com_register,
    hdt_com_unregister,
    hdt_load_assembly_and_get_function_pointer
};

int32_t hostfxr_main(const int argc, const char_t **argv);

int32_t hostfxr_main_startupinfo(
    const int argc,
    const char_t **argv,
    const char_t *host_path,
    const char_t *dotnet_root,
    const char_t *app_path);

typedef void (*hostfxr_error_writer_fn)(const char_t *message);
hostfxr_error_writer_fn hostfxr_set_error_writer(hostfxr_error_writer_fn error_writer);

typedef void* hostfxr_handle;
typedef struct hostfxr_initialize_parameters
{
    size_t size;
    const char_t *host_path;
    const char_t *dotnet_root;
} hostfxr_initialize_parameters;

int32_t hostfxr_initialize_for_dotnet_command_line(
    int argc,
    const char_t **argv,
    const hostfxr_initialize_parameters *parameters,
    /*out*/ hostfxr_handle *host_context_handle);
int32_t hostfxr_initialize_for_runtime_config(
    const char_t *runtime_config_path,
    const hostfxr_initialize_parameters *parameters,
    /*out*/ hostfxr_handle *host_context_handle);

int32_t hostfxr_get_runtime_property_value(
    const hostfxr_handle host_context_handle,
    const char_t *name,
    /*out*/ const char_t **value);
int32_t hostfxr_set_runtime_property_value(
    const hostfxr_handle host_context_handle,
    const char_t *name,
    const char_t *value);
int32_t hostfxr_get_runtime_properties(
    const hostfxr_handle host_context_handle,
    /*inout*/ size_t * count,
    /*out*/ const char_t **keys,
    /*out*/ const char_t **values);

int32_t hostfxr_run_app(const hostfxr_handle host_context_handle);
int32_t hostfxr_get_runtime_delegate(
    const hostfxr_handle host_context_handle,
    enum hostfxr_delegate_type type,
    /*out*/ void **delegate);

int32_t hostfxr_close(const hostfxr_handle host_context_handle);
"""
)

# coreclr_delegates.h
cdef.append(
    """
// Signature of delegate returned by coreclr_delegate_type::load_assembly_and_get_function_pointer
typedef int (__stdcall *load_assembly_and_get_function_pointer_fn)(
    const char_t *assembly_path      /* Fully qualified path to assembly */,
    const char_t *type_name          /* Assembly qualified type name */,
    const char_t *method_name        /* Public static method name compatible with delegateType */,
    const char_t *delegate_type_name /* Assembly qualified delegate type name or null */,
    void         *reserved           /* Extensibility parameter (currently unused and must be 0) */,
    /*out*/ void **delegate          /* Pointer where to store the function pointer result */);

// Signature of delegate returned by load_assembly_and_get_function_pointer_fn when delegate_type_name == null (default)
typedef int (__stdcall *component_entry_point_fn)(void *arg, int32_t arg_size_in_bytes);
"""
)
