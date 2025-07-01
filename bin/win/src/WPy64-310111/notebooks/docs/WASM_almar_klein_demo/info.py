"""
Display some info about the WASM module, like imports and exports.
"""

from ppci import wasm

filename = 'rocket.wasm'

wasm_data = open(filename, 'rb').read()
wasm_module = wasm.Module(wasm_data)

print(f'WASM file {filename} is {len(wasm_data)/2**10:0.1f} KiB')

wasm_module.show_interface()


# types =  wasm_module['type']
# imports = wasm_module['import']
# exports = wasm_module['export']
# functions = wasm_module['func']
# 
# 
# print('\nImports:')
# for c in imports:
#     #c.show()
#     assert c.kind == 'func'  # we assume only func imports
#     sig = types[c.info[0].index]
#     print(f'  {c.modname}.{c.name}:'.ljust(20), f'{sig.params} -> {sig.result}')
# 
# print('\nExports:')
# for c in exports:
#     #  c.show()
#     if c.kind == 'func':
#         func = functions[c.ref.index - functions[0].id]
#         sig = types[func.ref.index]
#         print(f'  {c.name}:'.ljust(20), f'{sig.params} -> {sig.result}')
#     else:
#         print(f'  {c.kind} "{c.name}"')
# 
#     
# # Export it yto textual form
# with open('rocket.wat', 'wt') as f:
#     f.write(wasm_module.to_string())
