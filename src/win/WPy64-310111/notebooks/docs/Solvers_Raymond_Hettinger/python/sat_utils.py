'Utility functions to humanize interaction with pycosat'

__author__ = 'Raymond Hettinger'

import pycosat                  # https://pypi.python.org/pypi/pycosat
from itertools import combinations
from functools import lru_cache
from sys import intern

def make_translate(cnf):
    """Make translator from symbolic CNF to PycoSat's numbered clauses.
       Return a literal to number dictionary and reverse lookup dict

        >>> make_translate([['~a', 'b', '~c'], ['a', '~c']])
        ({'a': 1, 'c': 3, 'b': 2, '~a': -1, '~b': -2, '~c': -3},
         {1: 'a', 2: 'b', 3: 'c', -1: '~a', -3: '~c', -2: '~b'})
    """
    lit2num = {}
    for clause in cnf:
        for literal in clause:
            if literal not in lit2num:
                var = literal[1:] if literal[0] == '~' else literal
                num = len(lit2num) // 2 + 1
                lit2num[intern(var)] = num
                lit2num[intern('~' + var)] = -num
    num2var = {num:lit for lit, num in lit2num.items()}
    return lit2num, num2var

def translate(cnf, uniquify=False):
    'Translate a symbolic cnf to a numbered cnf and return a reverse mapping'
    # DIMACS CNF file format:
    # http://people.sc.fsu.edu/~jburkardt/data/cnf/cnf.html
    if uniquify:
        cnf = list(dict.fromkeys(cnf))
    lit2num, num2var = make_translate(cnf)
    numbered_cnf = [tuple([lit2num[lit] for lit in clause]) for clause in cnf]
    return numbered_cnf, num2var

def itersolve(symbolic_cnf, include_neg=False):
    numbered_cnf, num2var = translate(symbolic_cnf)
    for solution in pycosat.itersolve(numbered_cnf):
        yield [num2var[n] for n in solution if include_neg or n > 0]

def solve_all(symcnf, include_neg=False):
    return list(itersolve(symcnf, include_neg))

def solve_one(symcnf, include_neg=False):
    return next(itersolve(symcnf, include_neg))

############### Support for Building CNFs ##########################

@lru_cache(maxsize=None)
def neg(element) -> 'element':
    'Negate a single element'
    return intern(element[1:] if element.startswith('~') else '~' + element)

def from_dnf(groups) -> 'cnf':
    'Convert from or-of-ands to and-of-ors'
    cnf = {frozenset()}
    for group in groups:
        nl = {frozenset([literal]) : neg(literal) for literal in group}
        # The "clause | literal" prevents dup lits: {x, x, y} -> {x, y}
        # The nl check skips over identities: {x, ~x, y} -> True
        cnf = {clause | literal for literal in nl for clause in cnf
              if nl[literal] not in clause}
        # The sc check removes clauses with superfluous terms:
        #     {{x}, {x, z}, {y, z}} -> {{x}, {y, z}}
        # Should this be left until the end?
        sc = min(cnf, key=len)          # XXX not deterministic
        cnf -= {clause for clause in cnf if clause > sc}
    return list(map(tuple, cnf))

class Q:
    'Quantifier for the number of elements that are true'
    def __init__(self, elements):
        self.elements = tuple(elements)
    def __lt__(self, n: int) -> 'cnf':
        return list(combinations(map(neg, self.elements), n))
    def __le__(self, n: int) -> 'cnf':
        return self < n + 1
    def __gt__(self, n: int) -> 'cnf':
        return list(combinations(self.elements, len(self.elements)-n))
    def __ge__(self, n: int) -> 'cnf':
        return self > n - 1
    def __eq__(self, n: int) -> 'cnf':
        return (self <= n) + (self >= n)
    def __ne__(self, n) -> 'cnf':
        raise NotImplementedError
    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(elements={self.elements!r})'

def all_of(elements) -> 'cnf':
    'Forces inclusion of matching rows on a truth table'
    return Q(elements) == len(elements)

def some_of(elements) -> 'cnf':
    'At least one of the elements must be true'
    return Q(elements) >= 1

def one_of(elements) -> 'cnf':
    'Exactly one of the elements is true'
    return Q(elements) == 1

def basic_fact(element) -> 'cnf':
    'Assert that this one element always matches'
    return Q([element]) == 1

def none_of(elements) -> 'cnf':
    'Forces exclusion of matching rows on a truth table'
    return Q(elements) == 0
