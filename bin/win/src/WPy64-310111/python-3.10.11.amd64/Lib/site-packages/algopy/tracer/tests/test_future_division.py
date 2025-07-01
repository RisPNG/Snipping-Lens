
from numpy.testing import run_module_suite, TestCase

import numpy
import algopy


class Test_future_division(TestCase):

    def test_utpm(x):
        x = numpy.array([1.,2.,3.])
        ax = algopy.UTPM.init_jacobian(x)
        ay = 1./ax
        J = algopy.UTPM.extract_jacobian(ay)
        #print J

    def test_function(x):
        x = numpy.array([1.,2.,3.])
        cg = algopy.CGraph()
        fx = algopy.Function(x)
        fy = 1./fx
        cg.trace_off()
        cg.independentFunctionList = [fx]
        cg.dependentFunctionList = [fy]
        #print cg.jacobian(x)


if __name__ == "__main__":
    run_module_suite()
