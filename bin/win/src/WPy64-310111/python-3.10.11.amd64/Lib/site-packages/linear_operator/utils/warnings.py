#!/usr/bin/env python3


class NumericalWarning(RuntimeWarning):
    """
    Warning thrown when convergence criteria are not met, or when comptuations require extra stability.
    """

    pass


class PerformanceWarning(RuntimeWarning):
    """
    Warning thrown when LinearOperators are used in a way that may incur large performance / memory penalties.
    """

    pass
