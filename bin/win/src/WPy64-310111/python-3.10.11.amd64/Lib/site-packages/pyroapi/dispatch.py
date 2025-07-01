# Copyright Contributors to the Pyro project.
# SPDX-License-Identifier: Apache-2.0

"""
Dispatching allows you to dynamically set a backend using :func:`pyro_backend`
and to register new backends using :func:`register_backend` .  It's easiest to
see how to use these by example:

.. code-block:: python

    from pyroapi import distributions as dist
    from pyroapi import infer, ops, optim, pyro, pyro_backend

    # These model and guide are backend-agnostic.
    def model():
        locs = pyro.param("locs", ops.tensor([0.2, 0.3, 0.5]))
        p = ops.tensor([0.2, 0.3, 0.5])
        with pyro.plate("plate", len(data), dim=-1):
            x = pyro.sample("x", dist.Categorical(p))
            pyro.sample("obs", dist.Normal(locs[x], 1.), obs=data)

    def guide():
        p = pyro.param("p", ops.tensor([0.5, 0.3, 0.2]))
        with pyro.plate("plate", len(data), dim=-1):
            pyro.sample("x", dist.Categorical(p))

    # We can now set a backend at inference time.
    with pyro_backend("numpyro"):
        elbo = infer.Trace_ELBO(ignore_jit_warnings=True)
        adam = optim.Adam({"lr": 1e-6})
        inference = infer.SVI(model, guide, adam, elbo)
        for step in range(10):
            loss = inference.step(*args, **kwargs)
            print("step {} loss = {}".format(step, loss))

"""
import importlib
from contextlib import contextmanager

DEFAULT_RNG_SEED = 1
_ALIASES = {}


class GenericModule(object):
    """
    Wrapper for a module that can be dynamically routed to a custom backend.
    """
    current_backend = {}
    _modules = {}

    def __init__(self, name, default_backend):
        assert isinstance(name, str)
        assert isinstance(default_backend, str)
        self._name = name
        GenericModule.current_backend[name] = default_backend

    def __getattribute__(self, name):
        module_name = super(GenericModule, self).__getattribute__('_name')
        backend = GenericModule.current_backend[module_name]
        try:
            module = GenericModule._modules[backend]
        except KeyError:
            module = importlib.import_module(backend)
            GenericModule._modules[backend] = module
        if name.startswith('__'):
            return getattr(module, name)  # allow magic attributes to return AttributeError
        try:
            return getattr(module, name)
        except AttributeError:
            raise NotImplementedError('This Pyro backend does not implement {}.{}'
                                      .format(module_name, name))


@contextmanager
def pyro_backend(*aliases, **new_backends):
    """
    Context manager to set a custom backend for Pyro models.

    Backends can be specified either by name (for standard backends or backends
    registered through :func:`register_backend` ) or by providing kwargs
    mapping module name to backend module name.  Standard backends include:
    pyro, minipyro, funsor, and numpy.
    """
    if aliases:
        assert len(aliases) == 1
        assert not new_backends
        new_backends = _ALIASES[aliases[0]]

    old_backends = {}
    for name, new_backend in new_backends.items():
        old_backends[name] = GenericModule.current_backend[name]
        GenericModule.current_backend[name] = new_backend
    try:
        with handlers.seed(rng_seed=DEFAULT_RNG_SEED):
            yield
    finally:
        for name, old_backend in old_backends.items():
            GenericModule.current_backend[name] = old_backend


def register_backend(alias, new_backends):
    """
    Register a new backend alias. For example::

        register_backend("minipyro", {
            "infer": "pyro.contrib.minipyro",
            "optim": "pyro.contrib.minipyro",
            "pyro": "pyro.contrib.minipyro",
        })

    :param str alias: The name of the new backend.
    :param dict new_backends: A dict mapping standard module name (str) to new
        module name (str). This needs to include only nonstandard backends
        (e.g. if your backend uses torch ops, you need not override ``ops``)
    """
    assert isinstance(new_backends, dict)
    assert all(isinstance(key, str) for key in new_backends.keys())
    assert all(isinstance(value, str) for value in new_backends.values())
    _ALIASES[alias] = new_backends.copy()


# These modules can be overridden.
pyro = GenericModule('pyro', 'pyro')
distributions = GenericModule('distributions', 'pyro.distributions')
handlers = GenericModule('handlers', 'pyro.poutine')
infer = GenericModule('infer', 'pyro.infer')
optim = GenericModule('optim', 'pyro.optim')
ops = GenericModule('ops', 'torch')


# These are standard backends.
register_backend('pyro', {
    'distributions': 'pyro.distributions',
    'handlers': 'pyro.poutine',
    'infer': 'pyro.infer',
    'ops': 'torch',
    'optim': 'pyro.optim',
    'pyro': 'pyro',
})
register_backend('minipyro', {
    'distributions': 'pyro.distributions',
    'handlers': 'pyro.poutine',
    'infer': 'pyro.contrib.minipyro',
    'ops': 'torch',
    'optim': 'pyro.contrib.minipyro',
    'pyro': 'pyro.contrib.minipyro',
})
register_backend('funsor', {
    'distributions': 'funsor.torch.distributions',
    'handlers': 'funsor.minipyro',
    'infer': 'funsor.minipyro',
    'ops': 'funsor.compat.ops',
    'optim': 'funsor.minipyro',
    'pyro': 'funsor.minipyro',
})
register_backend('numpy', {
    'distributions': 'numpyro.compat.distributions',
    'handlers': 'numpyro.compat.handlers',
    'infer': 'numpyro.compat.infer',
    'ops': 'numpyro.compat.ops',
    'optim': 'numpyro.compat.optim',
    'pyro': 'numpyro.compat.pyro',
})
