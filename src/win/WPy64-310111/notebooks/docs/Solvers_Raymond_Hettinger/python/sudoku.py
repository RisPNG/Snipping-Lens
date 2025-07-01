from sat_utils import solve_one, one_of, basic_fact
from sys import intern
from pprint import pprint

# you can compaer to smart (danscing links) algorithm from peter Norvig
# http://norvig.com/sudoku.html

n = 3

grid = '''\
AA AB AC BA BB BC CA CB CC
AD AE AF BD BE BF CD CE CF
AG AH AI BG BH BI CG CH CI
DA DB DC EA EB EC FA FB FC
DD DE DF ED EE EF FD FE FF
DG DH DI EG EH EI FG FH FI
GA GB GC HA HB HC IA IB IC
GD GE GF HD HE HF ID IE IF
GG GH GI HG HH HI IG IH II
'''

values = list('123456789')

table = [row.split() for row in grid.splitlines()]
points = grid.split()
subsquares = dict()
for point in points:
    subsquares.setdefault(point[0], []).append(point)
# Groups:  rows   + columns           + subsquares    
groups = table[:] + list(zip(*table)) + list(subsquares.values())

del grid, subsquares, table     # analysis requires only:  points, values, groups

def comb(point, value):
    'Format a fact (a value assigned to a given point)'
    return intern(f'{point} {value}')

def str_to_facts(s):
    'Convert str in row major form to a list of facts'
    return [comb(point, value) for point, value in zip(points, s) if value != ' ']

def facts_to_str(facts):
    'Convert a list of facts to a string in row major order with blanks for unknowns'
    point_to_value = dict(map(str.split, facts))
    return ''.join(point_to_value.get(point, ' ') for point in points)

def show(flatline):
    'Display grid from a string (values in row major order with blanks for unknowns)'
    fmt = '|'.join(['%s' * n] * n)
    sep = '+'.join(['-'  * n] * n)
    for i in range(n):
        for j in range(n):
            offset = (i * n + j) * n**2
            print(fmt % tuple(flatline[offset:offset+n**2]))
        if i != n - 1:
            print(sep)

for given in [
    '53  7    6  195    98    6 8   6   34  8 3  17   2   6 6    28    419  5    8  79',
    '       75  4  5   8 17 6   36  2 7 1   5 1   1 5 8  96   1 82 3   4  9  48       ',
    ' 9 7 4  1    6 2 8    1 43  6     59   1 3   97     8  52 7    6 8 4    7  5 8 2 ',
    '67 38      921   85    736 1 8  4 7  5 1 8 4  2 6  8 5 175    24   321      61 84',
    '27  15  8   3  7 4    7     5 1   7   9   2   6   2 5     8    6 5  4   8  59  41',
    '8 64 3    5     7     2    32  8  5   8 5 4  1   7  93    4     9     4    6 72 8',
    '  1 2 7   5     9    4      8   5    9           6   2  2        6     5     9 83', # sudoku of 9 with only 17 digits http://www2.ic-net.or.jp/~takaken/auto/guest/bbs46.html 
    '1  3    7428      3        5  6   8  84537  6    4 5     482 6   5    7 612 9  3 ',
    '8          36      7  9 2   5   7       457     1   3   1    68  85   1  9    4  ', # (was) hardest (35s)
    '1       2 9 4   5   6   7   5 9 3       7       85  4 7     6   3   9 8   2     1',  # (was) hard (28s) "easter monster"
    '     6    59     82    8    45        3        6  3 54   325  6                  ', # hardest  norvig (188 sec, but not a sudoku)
    ]:
    
    cnf = []

    # each point assigned exactly one value
    for point in points:
        cnf += one_of(comb(point, value) for value in values)

    # each value gets assigned to exactly one point in each group
    for group in groups:
        for value in values:
            cnf += one_of(comb(point, value) for point in group)

    # add facts for known values in a specific puzzle
    for known in str_to_facts(given):
        cnf += basic_fact(known)

    # solve it and display the results
    result = facts_to_str(solve_one(cnf))
    show(given)
    print()
    show(result)
    print('=-' * 20)
