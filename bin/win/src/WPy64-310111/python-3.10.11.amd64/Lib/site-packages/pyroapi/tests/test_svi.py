# Copyright Contributors to the Pyro project.
# SPDX-License-Identifier: Apache-2.0

import pytest

from pyroapi.dispatch import distributions as dist
from pyroapi.dispatch import infer, ops, optim, pyro

# This file tests a variety of model,guide pairs with valid and invalid structure.
# See https://github.com/pyro-ppl/pyro/blob/0.3.1/tests/infer/test_valid_models.py
#
# Note that the backend arg to these tests must be provided as a
# user-defined fixture that sets the pyro_backend. For demonstration,
# see test/conftest.py.


def assert_ok(model, guide, elbo, *args, **kwargs):
    """
    Assert that inference works without warnings or errors.
    """
    pyro.get_param_store().clear()
    adam = optim.Adam({"lr": 1e-6})
    inference = infer.SVI(model, guide, adam, elbo)
    for i in range(2):
        inference.step(*args, **kwargs)


def test_generate_data(backend):

    def model(data=None):
        loc = pyro.param("loc", ops.tensor(2.0))
        scale = pyro.param("scale", ops.tensor(1.0))
        x = pyro.sample("x", dist.Normal(loc, scale), obs=data)
        return x

    data = model()
    assert data.shape == ()


def test_generate_data_plate(backend):
    num_points = 1000

    def model(data=None):
        loc = pyro.param("loc", ops.tensor(2.0))
        scale = pyro.param("scale", ops.tensor(1.0))
        with pyro.plate("data", 1000, dim=-1):
            x = pyro.sample("x", dist.Normal(loc, scale), obs=data)
        return x

    data = model()
    if type(data).__module__.startswith('funsor'):
        pytest.xfail(reason='plate is an input, and does not appear in .shape')
    assert data.shape == (num_points,)
    mean = data.sum().item() / num_points
    assert 1.9 <= mean <= 2.1


@pytest.mark.parametrize("jit", [False, True], ids=["py", "jit"])
@pytest.mark.parametrize("optim_name, optim_kwargs", [
    ("Adam", {"lr": 1e-6}),
    ("ClippedAdam", {"lr": 1e-6, "lrd": 0.999}),
])
def test_optimizer(backend, optim_name, optim_kwargs, jit):

    def model(data):
        p = pyro.param("p", ops.tensor(0.5))
        pyro.sample("x", dist.Bernoulli(p), obs=data)

    def guide(data):
        pass

    data = ops.tensor(0.)
    pyro.get_param_store().clear()
    Elbo = infer.JitTrace_ELBO if jit else infer.Trace_ELBO
    elbo = Elbo(ignore_jit_warnings=True)
    optimizer = getattr(optim, optim_name)(optim_kwargs.copy())
    inference = infer.SVI(model, guide, optimizer, elbo)
    for i in range(2):
        inference.step(data)


@pytest.mark.parametrize("jit", [False, True], ids=["py", "jit"])
def test_nonempty_model_empty_guide_ok(backend, jit):

    def model(data):
        loc = pyro.param("loc", ops.tensor(0.0))
        pyro.sample("x", dist.Normal(loc, 1.), obs=data)

    def guide(data):
        pass

    data = ops.tensor(2.)
    Elbo = infer.JitTrace_ELBO if jit else infer.Trace_ELBO
    elbo = Elbo(ignore_jit_warnings=True)
    assert_ok(model, guide, elbo, data)


@pytest.mark.parametrize("jit", [False, True], ids=["py", "jit"])
def test_plate_ok(backend, jit):
    data = ops.randn(10)

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

    Elbo = infer.JitTrace_ELBO if jit else infer.Trace_ELBO
    elbo = Elbo(ignore_jit_warnings=True)
    assert_ok(model, guide, elbo)


@pytest.mark.parametrize("jit", [False, True], ids=["py", "jit"])
def test_nested_plate_plate_ok(backend, jit):
    data = ops.randn(2, 3)

    def model():
        loc = ops.tensor(3.0)
        with pyro.plate("plate_outer", data.shape[-1], dim=-1):
            x = pyro.sample("x", dist.Normal(loc, 1.))
            with pyro.plate("plate_inner", data.shape[-2], dim=-2):
                pyro.sample("y", dist.Normal(x, 1.), obs=data)

    def guide():
        loc = pyro.param("loc", ops.tensor(0.))
        scale = pyro.param("scale", ops.tensor(1.))
        with pyro.plate("plate_outer", data.shape[-1], dim=-1):
            pyro.sample("x", dist.Normal(loc, scale))

    Elbo = infer.JitTrace_ELBO if jit else infer.Trace_ELBO
    elbo = Elbo(ignore_jit_warnings=True)
    assert_ok(model, guide, elbo)


@pytest.mark.parametrize("jit", [False, True], ids=["py", "jit"])
def test_local_param_ok(backend, jit):
    data = ops.randn(10)

    def model():
        locs = pyro.param("locs", ops.tensor([-1., 0., 1.]))
        with pyro.plate("plate", len(data), dim=-1):
            x = pyro.sample("x", dist.Categorical(ops.ones(3) / 3))
            pyro.sample("obs", dist.Normal(locs[x], 1.), obs=data)

    def guide():
        with pyro.plate("plate", len(data), dim=-1):
            p = pyro.param("p", ops.ones(len(data), 3) / 3, event_dim=1)
            pyro.sample("x", dist.Categorical(p))
        return p

    Elbo = infer.JitTrace_ELBO if jit else infer.Trace_ELBO
    elbo = Elbo(ignore_jit_warnings=True)
    assert_ok(model, guide, elbo)

    # Check that pyro.param() can be called without init_value.
    expected = guide()
    actual = pyro.param("p")
    assert ops.allclose(actual, expected)


@pytest.mark.parametrize("jit", [False, True], ids=["py", "jit"])
def test_constraints(backend, jit):
    data = ops.tensor(0.5)

    def model():
        locs = pyro.param("locs", ops.randn(3),
                          constraint=dist.constraints.real)
        scales = pyro.param("scales", ops.exp(ops.randn(3)),
                            constraint=dist.constraints.positive)
        p = ops.tensor([0.5, 0.3, 0.2])
        x = pyro.sample("x", dist.Categorical(p))
        pyro.sample("obs", dist.Normal(locs[x], scales[x]), obs=data)

    def guide():
        q = pyro.param("q", ops.exp(ops.randn(3)),
                       constraint=dist.constraints.simplex)
        pyro.sample("x", dist.Categorical(q))

    Elbo = infer.JitTrace_ELBO if jit else infer.Trace_ELBO
    elbo = Elbo(ignore_jit_warnings=True)
    assert_ok(model, guide, elbo)


def test_mean_field_ok(backend):

    def model():
        x = pyro.sample("x", dist.Normal(0., 1.))
        pyro.sample("y", dist.Normal(x, 1.))

    def guide():
        loc = pyro.param("loc", ops.tensor(0.))
        x = pyro.sample("x", dist.Normal(loc, 1.))
        pyro.sample("y", dist.Normal(x, 1.))

    elbo = infer.TraceMeanField_ELBO()
    assert_ok(model, guide, elbo)
