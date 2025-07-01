__version__ = '0.15.2+cpu'
git_version = 'fa99a5360fbcd1683311d57a76fcc0e7323a4c1e'
from torchvision.extension import _check_cuda_version
if _check_cuda_version() > 0:
    cuda = _check_cuda_version()
