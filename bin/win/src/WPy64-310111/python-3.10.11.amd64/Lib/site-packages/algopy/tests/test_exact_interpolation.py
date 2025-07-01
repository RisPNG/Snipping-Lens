"""
Test algpy.utp.exact_interpolation

Not working ATM.
"""

from numpy.testing import *
import numpy
numpy.random.seed(0)

import algopy
from algopy import UTPM
from algopy.exact_interpolation import *


class TestExactInterpolation(TestCase):
    def test_generate_multi_indices(self):
        a = numpy.array(
            [[3, 0, 0, 0],
            [2, 1, 0, 0],
            [2, 0, 1, 0],
            [2, 0, 0, 1],
            [1, 2, 0, 0],
            [1, 1, 1, 0],
            [1, 1, 0, 1],
            [1, 0, 2, 0],
            [1, 0, 1, 1],
            [1, 0, 0, 2],
            [0, 3, 0, 0],
            [0, 2, 1, 0],
            [0, 2, 0, 1],
            [0, 1, 2, 0],
            [0, 1, 1, 1],
            [0, 1, 0, 2],
            [0, 0, 3, 0],
            [0, 0, 2, 1],
            [0, 0, 1, 2],
            [0, 0, 0, 3]])
        assert_array_equal(generate_multi_indices(4,3), a)

    def test_convert_multi_indices_to_pos(self):
        N,D = 4,3
        I = generate_multi_indices(N,D)
        computed_pos_mat = convert_multi_indices_to_pos(I)
        true_pos_mat = numpy.array([[0, 0, 0],
        [0, 0, 1],
        [0, 0, 2],
        [0, 0, 3],
        [0, 1, 1],
        [0, 1, 2],
        [0, 1, 3],
        [0, 2, 2],
        [0, 2, 3],
        [0, 3, 3],
        [1, 1, 1],
        [1, 1, 2],
        [1, 1, 3],
        [1, 2, 2],
        [1, 2, 3],
        [1, 3, 3],
        [2, 2, 2],
        [2, 2, 3],
        [2, 3, 3],
        [3, 3, 3]], dtype=int)
        #print true_pos_mat
        #print computed_pos_mat
        assert numpy.prod(true_pos_mat == computed_pos_mat) #all entries have to be the same


    def test_multi_index_binomial(self):
        i1 = numpy.array([0],dtype=int)
        i2 = numpy.array([0],dtype=int)
        i3 = numpy.array([1],dtype=int)
        i4 = numpy.array([1.5],dtype=float)

        assert_array_almost_equal([1], multi_index_binomial(i1,i2))
        assert_array_almost_equal([1], multi_index_binomial(i3,i1))
        assert_array_almost_equal([1], multi_index_binomial(i4,i1))
        assert_array_almost_equal([1.5], multi_index_binomial(i4,i3))


    def test_increment(self):
        i = numpy.array([1,2,3],dtype=int)
        k = numpy.zeros(3,dtype=int)

        count = 1
        while True:
            increment(i,k)
            count += 1
            if numpy.allclose(i,k):
                break

        assert_array_almost_equal(numpy.prod(i+1),count)


    def test_generate_permutations(self):
        x = [1,2,3]
        computed_perms = []
        for p in generate_permutations(x):
            computed_perms += [p]
        computed_perms = numpy.array(computed_perms)
        true_perms = numpy.array([[1, 2, 3],[2, 1, 3],[2, 3, 1],[1, 3, 2],[3, 1, 2],[3, 2, 1]],dtype=int)
        assert numpy.prod(computed_perms == true_perms)

    def test_interpolation(self):
        def f(x):
            return x[0] + x[1] + 3.*x[0]*x[1] + 7.*x[1]*x[1] + 17.*x[0]*x[0]*x[0]

        N = 2
        D = 5
        deg_list = [0,1,2,3,4]
        coeff_list = []
        for n,deg in enumerate(deg_list):
            Gamma, rays = generate_Gamma_and_rays(N,deg)
            x = UTPM(numpy.zeros((D,) + rays.shape))
            #print x
            #print type(x)
            x.data[1,:,:] = rays
            y = f(x)
            coeff_list.append(numpy.dot(Gamma, y.data[deg]))

        assert_array_almost_equal([0], coeff_list[0])
        assert_array_almost_equal([1,1], coeff_list[1])
        assert_array_almost_equal([0,3,7], coeff_list[2])
        assert_array_almost_equal([17,0,0,0], coeff_list[3])


class TestForwardDrivers(TestCase):
    def test_hessian(self):
        N = 5
        A = numpy.random.rand(N,N)
        A = numpy.dot(A.T,A)
        x = algopy.UTPM.init_hessian(numpy.arange(N,dtype=float))
        H = algopy.UTPM.extract_hessian(N, algopy.dot(x, algopy.dot(A,x)))
        assert_array_almost_equal(A, 0.5*H)


    def test_tensor_for_hessian_computation(self):
        N = 3
        A = numpy.random.rand(N,N)
        A = numpy.dot(A.T,A)
        x = algopy.UTPM.init_tensor(2, numpy.arange(N))
        y = 0.5*algopy.dot(x, algopy.dot(A,x))
        H = algopy.UTPM.extract_tensor(N, algopy.dot(x, algopy.dot(A,x)))
        assert_array_almost_equal(A, 0.5*H)








    # def test_generate_Gamma(self):
        # i = numpy.array([1,1],dtype=int)
        # (Gamma,J) = generate_Gamma(i)
        # assert_array_almost_equal(Gamma, [ - 0.25, 1., -0.25])

    # def test_tensor(self):
    #     def f(x):
    #         return numpy.prod(x)
    #     x = numpy.array([1.,2.,3.])
    #     computed_tensor = vector_tensor(f,x,3)

    #     true_tensor = numpy.array([[[ 0.,  0.,  0.],
    # [ 0.,  0.,  1.],
    # [ 0.,  1.,  0.]],

    # [[ 0.,  0.,  1.],
    # [ 0.,  0.,  0.],
    # [ 1.,  0.,  0.]],

    # [[ 0.,  1.,  0.],
    # [ 1.,  0.,  0.],
    # [ 0.,  0.,  0.]]])
    #     print 'true_tensor=', true_tensor
    #     print 'computed_tensor=', computed_tensor
    #     assert numpy.prod(computed_tensor == true_tensor)

    # def test_vector_hessian(self):
    #     import time
    #     def f(x):
    #         return numpy.prod(x)
    #     x = numpy.array([i+1 for i in range(10)])
    #     start_time = time.time()
    #     computed_hessian = vector_hessian(f,x)
    #     end_time = time.time()
    #     print computed_hessian
    #     print 'run time=%0.6f seconds'%(end_time-start_time)
    #     assert True



if __name__ == "__main__":
    run_module_suite()

