from collections.abc import Callable, Mapping, Sequence

from cons.core import ConsError, ConsNull, ConsPair, car, cdr, cons
from multipledispatch import dispatch

from .core import ExpressionTuple, KwdPair, etuple, trampoline_eval

try:  # noqa: C901
    import unification
    from packaging import version

    if version.parse(unification.__version__) < version.parse("0.4.0"):
        raise ModuleNotFoundError()

    from unification.core import _reify, _unify, construction_sentinel, isvar
except ModuleNotFoundError:
    pass
else:

    def _unify_ExpressionTuple(u, v, s):
        yield _unify(getattr(u, "_tuple", u), getattr(v, "_tuple", v), s)

    _unify.add((ExpressionTuple, ExpressionTuple, Mapping), _unify_ExpressionTuple)
    _unify.add((tuple, ExpressionTuple, Mapping), _unify_ExpressionTuple)
    _unify.add((ExpressionTuple, tuple, Mapping), _unify_ExpressionTuple)

    def _unify_KwdPair(u, v, s):
        s = yield _unify(u.arg, v.arg, s)
        if s is not False:
            s = yield _unify(u.value, v.value, s)
        yield s

    _unify.add((KwdPair, KwdPair, Mapping), _unify_KwdPair)

    def _reify_ExpressionTuple(u, s):
        # The point of all this: we don't want to lose the expression
        # tracking/caching information.
        res = yield _reify(u._tuple, s)

        yield construction_sentinel

        res_same = tuple(
            a == b for a, b in zip(u, res) if not isvar(a) and not isvar(b)
        )

        if len(res_same) == len(u) and all(res_same):
            # Everything is equal and there are no logic variables
            yield u
            return

        if getattr(u, "_parent", None) and all(res_same):
            # If we simply swapped-out logic variables, then we don't want to
            # lose the parent etuple information.
            res = etuple(*res)
            res._parent = u._parent
            yield res
            return

        yield etuple(*res)

    _reify.add((ExpressionTuple, Mapping), _reify_ExpressionTuple)

    def _reify_KwdPair(u, s):
        arg = yield _reify(u.arg, s)
        value = yield _reify(u.value, s)

        yield construction_sentinel

        yield KwdPair(arg, value)

    _reify.add((KwdPair, Mapping), _reify_KwdPair)


@dispatch(object)
def rator(x):
    return car(x)


@dispatch(object)
def rands(x):
    return cdr(x)


@dispatch(object, Sequence)
def apply(rator, rands):
    res = cons(rator, rands)
    return etuple(*res)


@apply.register(Callable, Sequence)
def apply_Sequence(rator, rands):
    return rator(*rands)


@apply.register(Callable, ExpressionTuple)
def apply_ExpressionTuple(rator, rands):
    return ((rator,) + rands).evaled_obj


# These are used to maintain some parity with the old `kanren.term` API
operator, arguments, term = rator, rands, apply


@dispatch(object)
def etuplize_fn(op):
    return etuple


@dispatch(object)
def etuplize(
    x,
    shallow=False,
    return_bad_args=False,
    convert_ConsPairs=True,
    rator_transform_fn=lambda x: x,
    rands_transform_fn=lambda x: x,
):
    r"""Return an expression-tuple for an object (i.e. a tuple of rand and rators).

    When evaluated, the rand and rators should [re-]construct the object.  When
    the object cannot be given such a form, it is simply converted to an
    `ExpressionTuple` and returned.

    Parameters
    ----------
    x: object
        Object to convert to expression-tuple form.
    shallow: bool
        Whether or not to do a shallow conversion.
    return_bad_args: bool
        Return the passed argument when its type is not appropriate, instead
        of raising an exception.
    rator_transform_fn: callable
        A function to be applied to each rator/CAR element of each constructed
        `ExpressionTuple`.  The returned value is used in place of the input, and
        the function is not applied to existing `ExpressionTuple`\s.
    rands_transform_fn: callable
        The same as `rator_transform_fn`, but for rands/CDR elements.

    """

    def etuplize_step(
        x,
        shallow=shallow,
        return_bad_args=return_bad_args,
        convert_ConsPairs=convert_ConsPairs,
    ):

        if isinstance(x, ExpressionTuple):
            yield x
            return
        elif (
            convert_ConsPairs and x is not None and isinstance(x, (ConsNull, ConsPair))
        ):
            yield etuple(
                *(
                    (rator_transform_fn(rator(x)),)
                    + tuple(rands_transform_fn(e) for e in rands(x))
                )
            )
            return

        try:
            op, args = rator(x), rands(x)
        except ConsError:
            op, args = None, None

        if not callable(op) or not isinstance(args, (ConsNull, ConsPair)):
            if return_bad_args:
                yield x
                return
            else:
                raise TypeError(f"x is neither a non-str Sequence nor term: {type(x)}")

        op = rator_transform_fn(op)
        args = etuple(*tuple(rands_transform_fn(a) for a in args))

        if shallow:
            et_op = op
            et_args = args
        else:
            et_op = yield etuplize_step(op, return_bad_args=True)
            et_args = []
            for a in args:

                e = yield etuplize_step(
                    a, return_bad_args=True, convert_ConsPairs=False
                )
                et_args.append(e)

        yield etuplize_fn(op)(et_op, *et_args, evaled_obj=x)

    return trampoline_eval(etuplize_step(x))
