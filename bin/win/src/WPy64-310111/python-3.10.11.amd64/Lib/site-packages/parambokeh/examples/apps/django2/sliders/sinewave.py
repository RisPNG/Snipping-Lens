# a sample (pre-existing) parameterized object from your existing code

import numpy as np

import param


class SineWave(param.ParameterizedFunction):
    offset = param.Number(default=0.0, bounds=(-5.0,5.0))
    amplitude = param.Number(default=1.0, bounds=(-5.0,5.0))
    phase = param.Number(default=0.0,bounds=(0.0,2*np.pi))
    frequency = param.Number(default=1.0, bounds=(0.1, 5.1))
    N = param.Integer(default=200, bounds=(0,None))
    #x_range = param.Range(default=(0, 4*np.pi),bounds=(0,4*np.pi))
    #y_range = param.Range(default=(-2.5,2.5),bounds=(-10,10))
    
    def __call__(self,**params):
        p = param.ParamOverrides(self,params)
        x = np.linspace(0, 4*np.pi, p.N)
        y = p.amplitude*np.sin(p.frequency*x + p.phase) + p.offset
        return x,y
