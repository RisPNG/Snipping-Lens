import numpy as np


def windowed_sum_slow(arrays, span, t=None, indices=None, tpowers=0,
                      period=None, subtract_mid=False):
    """Compute the windowed sum of the given arrays.

    This is a slow function, used primarily for testing and validation
    of the faster version of ``windowed_sum()``

    Parameters
    ----------
    arrays : tuple of arrays
        arrays to window
    span : int or array of ints
        The span to use for the sum at each point. If array is provided,
        it must be broadcastable with ``indices``
    indices : array
        the indices of the center of the desired windows. If ``None``,
        the indices are assumed to be ``range(len(arrays[0]))`` though
        these are not actually instantiated.
    t : array (optional)
        Times associated with the arrays
    tpowers : list (optional)
        Powers of t for each array sum
    period : float (optional)
        Period to use, if times are periodic. If supplied, input times
        must be arranged such that (t % period) is sorted!
    subtract_mid : boolean
        If true, then subtract the middle value from each sum

    Returns
    -------
    arrays : tuple of ndarrays
        arrays containing the windowed sum of each input array
    """
    span = np.asarray(span, dtype=int)
    if not np.all(span > 0):
        raise ValueError("span values must be positive")
    
    arrays = tuple(map(np.asarray, arrays))
    N = arrays[0].size
    if not all(a.shape == (N,) for a in arrays):
        raise ValueError("sizes of provided arrays must match")
    
    t_input = t
    if t is not None:
        t = np.asarray(t)
        if t.shape != (N,):
            raise ValueError("shape of t must match shape of arrays")
    else:
        t = np.ones(N)
    
    tpowers = tpowers + np.zeros(len(arrays))
    if len(tpowers) != len(arrays):
        raise ValueError("tpowers must be broadcastable with number of arrays")

    if period:
        if t_input is None:
            raise ValueError("periodic requires t to be provided")
        t = t % period
    
    if indices is None:
        indices = np.arange(N)
    spans, indices = np.broadcast_arrays(span, indices)
    
    results = []
    for tpower, array in zip(tpowers, arrays):
        if period:
            result = [sum(array[j % N]
                          * (t[j % N] + (j // N) * period) ** tpower
                          for j in range(i - s // 2,
                                         i - s // 2 + s)
                          if not (subtract_mid and j == i))
                      for i, s in np.broadcast(indices, spans)]
        else:
            result = [sum(array[j] * t[j] ** tpower
                          for j in range(max(0, i - s // 2),
                                         min(N, i - s // 2 + s))
                          if not (subtract_mid and j == i))
                      for i, s in np.broadcast(indices, spans)]
        results.append(np.asarray(result))
        
    return tuple(results)


def windowed_sum(arrays, span, t=None, indices=None, tpowers=0,
                 period=None, subtract_mid=False):
    """Compute the windowed sum of the given arrays.

    Parameters
    ----------
    arrays : tuple of arrays
        arrays to window
    span : int or array of ints
        The span to use for the sum at each point. If array is provided,
        it must be broadcastable with ``indices``
    indices : array
        the indices of the center of the desired windows. If ``None``,
        the indices are assumed to be ``range(len(arrays[0]))`` though
        these are not actually instantiated.
    t : array (optional)
        Times associated with the arrays
    tpowers : list (optional)
        Powers of t for each array sum
    period : float (optional)
        Period to use, if times are periodic. If supplied, input times
        must be arranged such that (t % period) is sorted!
    subtract_mid : boolean
        If true, then subtract the middle value from each sum

    Returns
    -------
    arrays : tuple of ndarrays
        arrays containing the windowed sum of each input array
    """
    span = np.asarray(span, dtype=int)
    if not np.all(span > 0):
        raise ValueError("span values must be positive")
    
    arrays = tuple(map(np.asarray, arrays))
    N = arrays[0].size
    if not all(a.shape == (N,) for a in arrays):
        raise ValueError("sizes of provided arrays must match")
    
    t_input = t
    if t is not None:
        t = np.asarray(t)
        if t.shape != (N,):
            raise ValueError("shape of t must match shape of arrays "
                             "t -> {0} arr -> {1}".format(t.shape,
                                                          arrays[0].shape))
    else:
        # XXX: special-case no t?
        t = np.ones(N)
    
    tpowers = np.asarray(tpowers) + np.zeros(len(arrays))

    if indices is not None:
        span, indices = np.broadcast_arrays(span, indices)

    # For the periodic case, re-call the function with padded arrays
    if period:
        if t_input is None:
            raise ValueError("periodic requires t to be provided")
        t = t % period

        t, arrays, sl = _pad_arrays(t, arrays, indices, span, period)
        if len(t) > N:
            # arrays are padded. Recursively call windowed_sum() and return.
            if span.ndim == 0 and indices is None:
                # fixed-span/no index case is done faster this way
                arrs = windowed_sum(arrays, span, t=t, indices=indices,
                                    tpowers=tpowers, period=None,
                                    subtract_mid=subtract_mid)
                return tuple([a[sl] for a in arrs])
            else:
                # this works for variable span and general indices
                if indices is None:
                    indices = np.arange(N)
                indices = indices + sl.start
                return windowed_sum(arrays, span, t=t, indices=indices,
                                    tpowers=tpowers, period=None,
                                    subtract_mid=subtract_mid)
        else:
            # No padding needed! We can carry-on as if it's a non-periodic case
            period = None

    # The rest of the algorithm now proceeds without reference to the period
    # just as a sanity check...
    assert not period

    if span.ndim == 0:
        # fixed-span case. Because of the checks & manipulations above
        # we know here that indices=None
        assert indices is None
        window = np.ones(span)

        def convolve_same(a, window):
            if len(window) <= len(a):
                res = np.convolve(a, window, mode='same')
            else:
                res = np.convolve(a, window, mode='full')
                start = (len(window) - 1) // 2
                res = res[start:start + len(a)]
            return res
        results = [convolve_same(a * t ** tp, window)
                   for a, tp in zip(arrays, tpowers)]
        indices = slice(None)

    else:
        # variable-span case. Use reduceat() in a clever way for speed.
        if indices is None:
            indices = np.arange(len(span))

        # we checked this above, but just as a sanity check assert it here...
        assert span.shape == indices.shape

        mins = np.asarray(indices) - span // 2
        results = []
        for a, tp in zip(arrays, tpowers):
            ranges = np.vstack([np.maximum(0, mins),
                                np.minimum(len(a), mins+span)]).ravel('F')
            results.append(np.add.reduceat(np.append(a * t ** tp, 0),
                                           ranges)[::2])

    # Subtract the midpoint if required: this is used in cross-validation
    if subtract_mid:
        results = [r - a[indices] * t[indices] ** tp
                   for r, a, tp in zip(results, arrays, tpowers)]

    return tuple(results)


def _pad_arrays(t, arrays, indices, span, period):
    """Internal routine to pad arrays for periodic models."""
    N = len(t)

    if indices is None:
        indices = np.arange(N)
    pad_left = max(0, 0 - np.min(indices - span // 2))
    pad_right = max(0, np.max(indices + span - span // 2) - (N - 1))

    if pad_left + pad_right > 0:
        Nright, pad_right = divmod(pad_right, N)
        Nleft, pad_left = divmod(pad_left, N)
        t = np.concatenate([t[N - pad_left:] - (Nleft + 1) * period]
                           + [t + i * period
                              for i in range(-Nleft, Nright + 1)]
                           + [t[:pad_right] + (Nright + 1) * period])
        arrays = [np.concatenate([a[N - pad_left:]]
                                 + (Nleft + Nright + 1) * [a]
                                 + [a[:pad_right]])
                  for a in arrays]
        pad_left = pad_left % N
        Nright = pad_right / N
        pad_right = pad_right % N

        return (t, arrays, slice(pad_left + Nleft * N,
                                 pad_left + (Nleft + 1) * N))
    else:
        return (t, arrays, slice(None))
