# Minimum version required
cmake_minimum_required (VERSION 3.5)

# Project name
project (osqp)


# Set the output folder where your program will be created
set(EXECUTABLE_OUTPUT_PATH ${PROJECT_BINARY_DIR}/out)
set(LIBRARY_OUTPUT_PATH ${PROJECT_BINARY_DIR}/out)


# Detect operating system
# ----------------------------------------------
message(STATUS "We are on a ${CMAKE_SYSTEM_NAME} system")
if(${CMAKE_SYSTEM_NAME} STREQUAL "Linux")
    set(IS_LINUX ON)
elseif(${CMAKE_SYSTEM_NAME} STREQUAL "Darwin")
    set(IS_MAC ON)
elseif(${CMAKE_SYSTEM_NAME} STREQUAL "Windows")
    set(IS_WINDOWS ON)
endif()


# Set options
# ----------------------------------------------


# Is the code generated for embedded platforms?
#   1 :   Yes. Matrix update not allowed.
#   2 :   Yes. Matrix update allowed.

if (NOT DEFINED EMBEDDED)  # enable embedded anyway
    set (EMBEDDED EMBEDDED_FLAG)
endif()

message(STATUS "Embedded is ${EMBEDDED}")
message(STATUS "Passing EMBEDDED flag to compiler")

# Is printing enabled?
option (PRINTING "Enable solver printing" ON)
if (DEFINED EMBEDDED)
    message(STATUS "Disabling printing for embedded")
    set(PRINTING OFF)
endif()
message(STATUS "Printing is ${PRINTING}")


# Is profiling enabled?
option (PROFILING "Enable solver profiling (timing)" ON)
if (DEFINED EMBEDDED)
    message(STATUS "Disabling profiling for embedded")
    set(PROFILING OFF)
endif()
message(STATUS "Profiling is ${PROFILING}")

# Use floats instead of integers
option (DFLOAT "Use float numbers instead of doubles" OFF)
message(STATUS "Floats are ${DFLOAT}")

# Use long integers for indexing
option (DLONG "Use long integers (64bit) for indexing" ON)
if (NOT (CMAKE_SIZEOF_VOID_P EQUAL 8))
	message(STATUS "Disabling long integers (64bit) on 32bit machine")
	set(DLONG OFF)
endif()
message(STATUS "Long integers (64bit) are ${DLONG}")

# Types for QDLDL
# ----------------------------------------------
if(DFLOAT)
  set(QDLDL_FLOAT_TYPE "float")
else()
	set(QDLDL_FLOAT_TYPE "double")
endif()

if(DLONG)
  set(QDLDL_INT_TYPE "long long")
else()
	set(QDLDL_INT_TYPE "int")
endif()

# boolean type is always unsigned char for
# now, since _Bool does not exist in C89
set(QDLDL_BOOL_TYPE "unsigned char")

configure_file(${CMAKE_CURRENT_SOURCE_DIR}/configure/qdldl_types.h.in
               ${CMAKE_CURRENT_SOURCE_DIR}/include/qdldl_types.h
               NEWLINE_STYLE LF)

# Set Compiler flags
# ----------------------------------------------
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -O3")
set(CMAKE_C_FLAGS_DEBUG "${CMAKE_C_FLAGS_DEBUG} -O0 -g")
set(CMAKE_POSITION_INDEPENDENT_CODE ON)  # -fPIC

# Include math library if EMBEDDED != 1
if(NOT (EMBEDDED EQUAL 1))
    set(CMAKE_C_STANDARD_LIBRARIES "${CMAKE_C_STANDARD_LIBRARIES} -lm")
endif()
# Include real time library in linux
if(${CMAKE_SYSTEM_NAME} STREQUAL "Linux")
    set(CMAKE_C_STANDARD_LIBRARIES "${CMAKE_C_STANDARD_LIBRARIES} -lrt")
endif()

# Generate header file with the global options
# ---------------------------------------------
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/configure/osqp_configure.h.in
               ${CMAKE_CURRENT_SOURCE_DIR}/include/osqp_configure.h
               NEWLINE_STYLE LF)

# Include header directory
# ----------------------------------------------
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include)


# Set sources
# ----------------------------------------------
add_subdirectory (src/osqp)
add_subdirectory (include)

# Append the generated workspace files and qdldl files
list (APPEND
      osqp_src
      ${CMAKE_CURRENT_SOURCE_DIR}/src/osqp/workspace.c
      ${CMAKE_CURRENT_SOURCE_DIR}/src/osqp/qdldl.c
      ${CMAKE_CURRENT_SOURCE_DIR}/src/osqp/qdldl_interface.c
)

list (APPEND
      osqp_headers
      ${CMAKE_CURRENT_SOURCE_DIR}/include/workspace.h
      ${CMAKE_CURRENT_SOURCE_DIR}/include/qdldl.h
      ${CMAKE_CURRENT_SOURCE_DIR}/include/qdldl_types.h
      ${CMAKE_CURRENT_SOURCE_DIR}/include/qdldl_interface.h
)

# Create static library for embedded solver
add_library (emosqpstatic STATIC ${osqp_src} ${osqp_headers})

# Create example executable
add_executable (example ${PROJECT_SOURCE_DIR}/src/example.c)
target_link_libraries (example emosqpstatic)
