import os.path
import numpy as np


rel_tol = 1e-03
abs_tol = 1e-04
decimal_tol = 4


def load_high_accuracy(test_name):
    npz = os.path.join(os.path.dirname(__file__), 'solutions', f'{test_name}.npz')
    npzfile = np.load(npz)
    return npzfile['x_val'], npzfile['y_val'], npzfile['obj']