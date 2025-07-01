import os

MPLBE = os.environ.get('MPLBE', False)

if MPLBE:
    import matplotlib
    matplotlib.use(MPLBE)

import matplotlib.pyplot as plt
from .renderers import Renderer
from .exporter import Exporter
from .convertors import StrMethodTickFormatterConvertor
