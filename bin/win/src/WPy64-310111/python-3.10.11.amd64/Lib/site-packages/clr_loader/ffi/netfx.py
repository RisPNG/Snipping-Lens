# flake8: noqa

cdef = [
    """
typedef void* pyclr_domain;
typedef int (*entry_point)(void* buffer, int size);

void pyclr_initialize();
void* pyclr_create_appdomain(const char* name, const char* config_file);
entry_point pyclr_get_function(pyclr_domain domain, const char* assembly_path, const char* class_name, const char* function);
void pyclr_close_appdomain(pyclr_domain domain);
void pyclr_finalize();
    """
]
