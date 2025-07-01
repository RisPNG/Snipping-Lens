from collections.abc import Iterator, Mapping
from itertools import tee

from unification.core import _reify, _unify, construction_sentinel

from .core import ConsError, ConsPair, MaybeCons, car, cdr, cons


def _unify_Cons(lcons, rcons, s):

    lcons_ = lcons
    rcons_ = rcons

    if isinstance(lcons, Iterator):
        lcons, lcons_ = tee(lcons)

    if isinstance(rcons, Iterator):
        rcons, rcons_ = tee(rcons)

    try:
        s = yield _unify(car(lcons), car(rcons), s)

        if s is not False:
            s = yield _unify(cdr(lcons_), cdr(rcons_), s)
    except ConsError:
        yield False
    else:
        yield s


_unify.add((ConsPair, (ConsPair, MaybeCons), Mapping), _unify_Cons)
_unify.add((MaybeCons, ConsPair, Mapping), _unify_Cons)


@_reify.register(ConsPair, Mapping)
def _reify_Cons(lcons, s):
    rcar = yield _reify(car(lcons), s)
    rcdr = yield _reify(cdr(lcons), s)
    yield construction_sentinel
    yield cons(rcar, rcdr)
