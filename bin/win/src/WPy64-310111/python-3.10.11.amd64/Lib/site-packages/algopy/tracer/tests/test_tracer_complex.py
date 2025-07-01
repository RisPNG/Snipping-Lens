
import numpy as np
import algopy

np.random.seed(0)


def makeMat(m, n, complex_valued=True):
  Ar = np.random.random((m, n))
  Ai = np.random.random((m, n))
  return Ar + 1j*Ai if complex_valued else Ar


# A context manager for taping function evaluations.
# The manager automatically stops taping and optionally
# initializes the 'independentFunctionList' attribute of
# the CGraph instance.
class cgraph(object):
  
  def __init__(self, *independents):
    # Given the independent arguments we can partially
    # initialize the computational graph.
    self._args = independents
    self._entered = False
    
  def __enter__(self):
    if self._entered:
      raise RuntimeError("cannot enter %r twice" % self)
    self._entered = True
    cg = algopy.CGraph()
    args = [algopy.Function(arg) for arg in self._args]
    cg.independentFunctionList = args
    self._cg = cg
    return (cg,) + tuple(args)

  def __exit__(self, *exc_info):
    if not self._entered:
      raise RuntimeError("cannot exit %r without entering first" % self)
    self._cg.trace_off()


def test_conjugate1():

  size = 4
  A = makeMat(size, size)
  x = np.random.random((size,))

  def f(x, module):
    y = module.dot(A, x)
    yDy = module.dot(y, module.conjugate(y))
    return yDy

  with cgraph(x) as (cg, xf):
    sf = f(xf, algopy)
  cg.dependentFunctionList = [sf]

  assert sf.x == f(x, np)
  ad_grad = cg.gradient(x)
  D = np.dot(A.transpose(), A.conjugate())
  analytic_grad = np.dot(D.transpose() + D, x)
  assert np.allclose(ad_grad, analytic_grad)


def test_conjugate2():

  size = 4
  A = makeMat(size, size)
  B = makeMat(size, size)
  C = makeMat(size, size)
  x = np.random.random((size,))

  def f(x, module):
    y = module.dot(A, x) + module.dot(B, x) + module.dot(C, x)
    yDy = module.dot(y, module.conjugate(y))
    return yDy

  with cgraph(x) as (cg, xf):
    sf = f(xf, algopy)
  cg.dependentFunctionList = [sf]

  assert sf.x == f(x, np)
  ad_grad = cg.gradient(x)
  ABC = A + B + C
  D = np.dot(ABC.transpose(), ABC.conjugate())
  analytic_grad = np.dot(D.transpose() + D, x)
  assert np.allclose(ad_grad, analytic_grad)


def test_conjugate3():

  size = 4
  A = makeMat(size, size, complex_valued=False)
  c = 1 + 0.5j
  x = np.random.random((size,))

  def f(x, module):
    y = c*module.dot(A, x)
    yDy = module.dot(y, module.conjugate(y))
    return yDy

  with cgraph(x) as (cg, xf):
    sf = f(xf, algopy)
  cg.dependentFunctionList = [sf]

  assert sf.x == f(x, np)
  ad_grad = cg.gradient(x)
  D = np.dot(c*A.transpose(), (c*A).conjugate())
  analytic_grad = np.dot(D.transpose() + D, x)
  assert np.allclose(ad_grad, analytic_grad)


def test_conjugate4():

  size = 4
  A = makeMat(size, size)
  c = 1 + 0.5j
  x = np.random.random((size,))

  def f(x, module):
    y = module.dot(A, c*x)
    yDy = module.dot(y, module.conjugate(y))
    return yDy

  with cgraph(x) as (cg, xf):
    sf = f(xf, algopy)
  cg.dependentFunctionList = [sf]

  assert sf.x == f(x, np)
  ad_grad = cg.gradient(x)
  D = np.dot(c*A.transpose(), (c*A).conjugate())
  analytic_grad = np.dot(D.transpose() + D, x)
  assert np.allclose(ad_grad, analytic_grad)


def test_conjugate5():

  size = 4
  A = makeMat(size, size)
  B = makeMat(size, size)
  x = np.random.random((size,))

  def f(x, module):
    y = module.dot(A, x)
    z = module.dot(B, x)
    yDy = module.dot(y, module.conjugate(y))
    zDz = module.dot(z, module.conjugate(z))
    return yDy*zDz

  with cgraph(x) as (cg, xf):
    sf = f(xf, algopy)
  cg.dependentFunctionList = [sf]

  assert sf.x == f(x, np)
  ad_grad = cg.gradient(x)
  y, z = np.dot(A, x), np.dot(B, x)
  yDy, zDz = np.dot(y, y.conjugate()), np.dot(z, z.conjugate())
  D = np.dot(A.transpose(), A.conjugate())
  E = np.dot(B.transpose(), B.conjugate())
  analytic_grad = zDz*np.dot(D.transpose() + D, x) + yDy*np.dot(E.transpose() + E, x)
  assert np.allclose(ad_grad, analytic_grad)


def test_conjugate6():

  size = 4
  A = makeMat(size, size)
  x = np.random.random((size,))

  # equivalent to f in test_conjugate1
  def f(x, module):
    y = module.conjugate(module.dot(A, x))
    yDy = module.dot(y, module.conjugate(y))
    return yDy

  with cgraph(x) as (cg, xf):
    sf = f(xf, algopy)
  cg.dependentFunctionList = [sf]

  assert sf.x == f(x, np)
  ad_grad = cg.gradient(x)
  D = np.dot(A.transpose(), A.conjugate())
  analytic_grad = np.dot(D.transpose() + D, x)
  assert np.allclose(ad_grad, analytic_grad)


def test_conjugate7():

  size = 4
  A = makeMat(size, size)
  B = makeMat(size, size)
  x = np.random.random((size,))

  def f(x, module):
    y = module.dot(A, x)
    y = y + module.conjugate(module.dot(B, x))
    yDy = module.dot(y, module.conjugate(y))
    return yDy

  with cgraph(x) as (cg, xf):
    sf = f(xf, algopy)
  cg.dependentFunctionList = [sf]

  assert sf.x == f(x, np)
  ad_grad = cg.gradient(x)
  AB = A + B.conjugate()
  D = np.dot(AB.transpose(), AB.conjugate())
  analytic_grad = np.dot(D.transpose() + D, x)
  assert np.allclose(ad_grad, analytic_grad)


def test_conjugate8():

  size = 4
  A = makeMat(size, size)
  B = makeMat(size, size)
  x = np.random.random((size,))

  def f(x, module):
    y = module.real(module.dot(A, x))
    y = y + module.imag(module.conjugate(module.dot(B, x)))
    yDy = module.dot(y, y) # y is real
    return yDy

  with cgraph(x) as (cg, xf):
    sf = f(xf, algopy)
  cg.dependentFunctionList = [sf]

  assert sf.x == f(x, np)
  ad_grad = cg.gradient(x)
  AB = A.real - B.imag
  D = np.dot(AB.transpose(), AB)
  analytic_grad = np.dot(D.transpose() + D, x)
  assert np.allclose(ad_grad, analytic_grad)


def test_conjugate9():

  size = 4
  A = makeMat(size, size)
  B = makeMat(size, size)
  x = np.random.random((size,))

  def f(x, module):
    y = module.dot(B, module.dot(A, x))
    yDy = module.dot(y, y.conjugate())
    return yDy

  with cgraph(x) as (cg, xf):
    sf = f(xf, algopy)
  cg.dependentFunctionList = [sf]

  assert sf.x == f(x, np)
  ad_grad = cg.gradient(x)
  AB = np.dot(B, A)
  D = np.dot(AB.transpose(), AB.conjugate())
  analytic_grad = np.dot(D.transpose() + D, x)
  assert np.allclose(ad_grad, analytic_grad)


def test_conjugate10():

  size = 4
  A = makeMat(size, size)
  B = makeMat(size, size)
  x = np.random.random((size,))

  def f(x, module):
    y = module.dot(B, module.conjugate(module.dot(A, x)))
    yDy = module.dot(y, y.conjugate())
    return yDy

  with cgraph(x) as (cg, xf):
    sf = f(xf, algopy)
  cg.dependentFunctionList = [sf]

  assert sf.x == f(x, np)
  ad_grad = cg.gradient(x)
  AB = np.dot(B, A.conjugate())
  D = np.dot(AB.transpose(), AB.conjugate())
  analytic_grad = np.dot(D.transpose() + D, x)
  assert np.allclose(ad_grad, analytic_grad)
