# flake8: noqa

cdef = []

cdef.append(
    """
typedef struct _MonoDomain MonoDomain;
typedef struct _MonoAssembly MonoAssembly;
typedef struct _MonoImage MonoImage;
typedef struct _MonoMethodDesc MonoMethodDesc;
typedef struct _MonoMethod MonoMethod;
typedef struct _MonoObject MonoObject;

typedef enum {
	MONO_DEBUG_FORMAT_NONE,
	MONO_DEBUG_FORMAT_MONO,
	/* Deprecated, the mdb debugger is not longer supported. */
	MONO_DEBUG_FORMAT_DEBUGGER
} MonoDebugFormat;

char* mono_get_runtime_build_info (void);

MonoDomain* mono_jit_init(const char *root_domain_name);
void mono_jit_cleanup(MonoDomain *domain);
void mono_jit_parse_options(int argc, char * argv[]);

void mono_debug_init (MonoDebugFormat format);

MonoAssembly* mono_domain_assembly_open(MonoDomain *domain, const char *name);
MonoImage* mono_assembly_get_image(MonoAssembly *assembly);

void mono_domain_set_config(MonoDomain *domain, const char *base_dir, const char *config_file_name);
void mono_config_parse(const char* path);

MonoMethodDesc* mono_method_desc_new(const char* name, bool include_namespace);
MonoMethod* mono_method_desc_search_in_image(MonoMethodDesc *method_desc, MonoImage *image);
void mono_method_desc_free(MonoMethodDesc *method_desc);

MonoObject* mono_runtime_invoke(MonoMethod *method, void *obj, void **params, MonoObject **exc);

void* mono_object_unbox(MonoObject *object);

void mono_set_dirs(const char *assembly_dir, const char* config_dir);

void mono_set_signal_chaining(bool chain_signals);

"""
)
