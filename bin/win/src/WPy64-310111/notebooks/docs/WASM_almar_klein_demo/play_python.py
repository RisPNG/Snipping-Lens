"""
You should probably just ignore this ...
"""

import struct
from ppci.wasm.wasm2ppci import create_memories
from ppci.wasm.runtime import create_runtime
from ppci.wasm import 

wasm_data = open('rocket.wasm', 'rb').read()
wasm_module = Module(wasm_data)
memories = create_memories(wasm_module)
rt = create_runtime()
# print(memories)

def current_memory():
    size = (mem0_end - mem0_start) // (1 << 16)
    print('current memory', size)
    return size
rt['current_memory'] = current_memory

def grow_memory(delta):
    global mem0_end
    assert mem0_end == gen_rocket_wasm.heap_top()
    print('grow_memory', delta)
    gen_rocket_wasm.heap.extend(bytes(delta * 64 * 1024))
    mem0_end = gen_rocket_wasm.heap_top()
    size = (mem0_end - mem0_start) // (1 << 16)
    print('new memory size', size)
    return size
    # assert mem0_end == len(gen_rocket_wasm.heap) + 0x10000000

rt['grow_memory'] = grow_memory

def get_str(ptr):
    """ Get a 0 terminated string """
    data = []
    while True:
        b = gen_rocket_wasm.read_mem(ptr, 1)[0]
        if b == 0:
            break
        else:
            data.append(b)
        ptr += 1
    return bytes(data).decode('ascii')

def trace_func(ptr):
    # Lookup name:
    print('Trace function entrance:', get_str(ptr))

rt['trace'] = trace_func

print(rt)
import gen_rocket_wasm

# Fixup external functions:
for name, f in rt.items():
    # TODO: make a choice between those two options:
    gen_rocket_wasm.externals[name] = f
    setattr(gen_rocket_wasm, name, f)

# Attach memory:
mem0_start = gen_rocket_wasm.heap_top()
print('memory size:', len(memories[0]), hex(mem0_start))
gen_rocket_wasm.heap.extend(memories[0])
mem0_end = gen_rocket_wasm.heap_top()
wasm_mem0 = gen_rocket_wasm.wasm_mem0_address
gen_rocket_wasm.store_i32(mem0_start, wasm_mem0)

# rocket_wasm.func_pointers[]
gen_rocket_wasm._run_init()

gen_rocket_wasm.draw()

