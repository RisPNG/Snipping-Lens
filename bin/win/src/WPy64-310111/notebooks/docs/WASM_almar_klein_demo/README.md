# The Rocket game, implemented in Rust, running in Python, via WASM 

A [Rocket game implemented in Rust](https://github.com/aochagavia/rocket_wasm)
is compiled to WebAssembly (WASM). We take the resulting `.wasm` file, and run
it in Python using [PPCI](https://bitbucket.org/windel/ppci/).

* `rocket.wasm`: the wasm module compiled from Rust (by Adolfo).
* `rocket.py`: the Python code to wrap the above in an app.
* `info.py`: print some info about the wasm module.
* `rocket.html`: for reference, the (nearly) original html/js to run the wasm module in the browser (standalone HTML).

In this exercise, we take a wasm module as-is, inspect its imports and exports
(WASM clearly defines these), and use this API to run the module in a Python app.
