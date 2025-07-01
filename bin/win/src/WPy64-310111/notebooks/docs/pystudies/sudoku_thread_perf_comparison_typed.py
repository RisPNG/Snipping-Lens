## Solve Every Sudoku Puzzle

## See http://norvig.com/sudoku.html 
### tuned with modernised code from or https://github.com/norvig/pytudes/blob/main/ipynb/Sudoku.ipynb
### executable at https://colab.research.google.com/github/norvig/pytudes/blob/main/ipynb/Sudoku.ipynb#scrollTo=h06tPIVW60Ll

## Throughout this program we have:
##   r is a row,    e.g. 'A'
##   c is a column, e.g. '3'
##   s is a square, e.g. 'A3'
##   d is a digit,  e.g. '9'
##   u is a unit,   e.g. ['A1','B1','C1','D1','E1','F1','G1','H1','I1']
##   grid is a grid,e.g. 81 non-blank chars, e.g. starting with '.18...7...
##   values is a dict of possible values, e.g. {'A1':'12349', 'A2':'8', ...}

import re
import time, random
from concurrent.futures import ThreadPoolExecutor

DigitSet = str  # e.g. '123'
Square   = str  # e.g. 'A9'

Picture  = str  # e.g. "53..7....6..195....98....6.8...6...34..8.3..17...2...6.6....28....419..5....8..79"
Grid     = dict # E.g. {'A9': '123', ...}, a dict  of {Square: DigitSet}

Fail     = Grid() # The empty Grid is used to indicate failure to find a solution

def cross(A, B) -> tuple:
    "Cross product of strings in A and strings in B."
    return tuple(a + b for a in A for b in B)

digits    = '123456789' # possible values in a square
rows      = 'ABCDEFGHI' # row names
cols      = digits      # column names (inversion from Excel where cols aer characters)
squares   = cross(rows, cols) # all square coordinates : 'A1', 'B1', ... 'A2'...


# a box = a group of 3x3 square (9 boxes of 9 squares in a sudoku)
all_boxes = [cross(rs, cs)  for rs in ('ABC','DEF','GHI') for cs in ('123','456','789')]

# all 27 group of contraints (9 columns of squares, 9 rows of squares , 9 boxes of squares)
all_units = [cross(rows, c) for c in cols] + [cross(r, cols) for r in rows] + all_boxes

# units[s] = group of constraints wher is a givean square 's'
units     = {s: tuple(u for u in all_units if s in u) for s in squares}

# peers[s] = the 20 squares that are in some unit of the square 's' (same columns, row or box)
peers     = {s: set().union(*units[s]) - {s} for s in squares}

def is_solution(solution: Grid, puzzle: Grid) -> bool:
    "Is this proposed solution to the puzzle actually valid?"
    return (solution is not Fail and
            all(solution[s] == puzzle[s] for s in squares if len(puzzle[s]) == 1) and
            all({solution[s] for s in unit} == set(digits) for unit in all_units))

def parse(picture) -> Grid:
    """Convert a Picture to a Grid."""
    vals = re.findall(r"[.1-9]|[{][1-9]+[}]", picture)
    assert len(vals) == 81
    return {s: digits if v == '.' else re.sub(r"[{}]", '', v) 
            for s, v in zip(squares, vals)}

def picture(grid) -> Picture:
    """Convert a Grid to a Picture."""
    if grid is Fail: 
        return "Fail"
    def val(d: DigitSet) -> str: return '.' if d == digits else d if len(d) == 1 else '{' + d + '}'
    width = max(len(val(grid[s])) for s in grid)
    dash = '\n' + '+'.join(['-' * (width * 3 + 2)] * 3) + ' '
    def cell(r, c): return val(grid[r + c]).center(width) + ('|'  if c in '36' else ' ')
    def line(r): return ''.join(cell(r, c) for c in cols) + (dash if r in 'CF' else '')
    return '\n'.join(map(line, rows))

def fill(grid, s, d) -> Grid:
    """Eliminate all the other digits (except d) from grid[s]."""
    if grid[s] == d or all(eliminate(grid, s, d2) for d2 in grid[s] if d2 != d):
        return grid
    else:
        return Fail

def eliminate(grid, s, d) -> Grid:
    """Eliminate d from grid[s]; implement the two constraint propagation strategies."""
    if d not in grid[s]:
        return grid        ## Already eliminated
    grid[s] = grid[s].replace(d, '')
    if not grid[s]:
        return Fail        ## Fail: no legal digit left
    elif len(grid[s]) == 1:
        # 1. If a square has only one possible digit, then eliminate that digit from the square's peers.
        d2 = grid[s]
        if not all(eliminate(grid, s2, d2) for s2 in peers[s]):
            return Fail    ## Fail: can't eliminate d2 from some square
    for u in units[s]:
        dplaces = [s for s in u if d in grid[s]]
        # 2. If a unit has only one possible square that can hold a digit, then fill the square with the digit.
        if not dplaces or (len(dplaces) == 1 and not fill(grid, dplaces[0], d)):
            return Fail    ## Fail: no place in u for d
    return grid

def constrain(grid) -> Grid:
    "Propagate constraints on a copy of grid to yield a new constrained Grid."
    constrained: Grid = {s: digits for s in squares}
    for s in grid:
        d = grid[s]
        if len(d) == 1:
            fill(constrained, s, d)
    return constrained

def search(grid) -> Grid:
    "Depth-first search with constraint propagation (`fill`) to find a solution."
    if grid is Fail: 
        return Fail
    unfilled = [s for s in squares if len(grid[s]) > 1]
    if not unfilled: 
        return grid
    s = min(unfilled, key=lambda s: len(grid[s]))
    for d in grid[s]:
        solution = search(fill(grid.copy(), s, d))
        if solution:
            return solution
    return Fail


def solve(puzzles, verbose=True) -> int:
    "Solve and verify each puzzle, and if `verbose`, print puzzle and solution."
    sep = '    '
    for puzzle in puzzles:
        solution = search(constrain(puzzle))
        assert is_solution(solution, puzzle)
        if verbose:
            print('\nPuzzle            ', sep, 'Solution')
            for p, s in zip(picture(puzzle).splitlines(), picture(solution).splitlines()):
                print(p, sep, s)
    return len(puzzles)


def solve_all(puzzles, name, showif=0.0, nbthreads=1):
    """Attempt to solve a sequence of grids. Report results.
    When showif is a number of seconds, display puzzles that take longer.
    When showif is None, don't display any puzzles."""
    def time_solve(puzzle):
        start = time.time()
        solution = search(constrain(puzzle))
        t = time.time()-start
        ## Display puzzles that take long enough
        if showif is not None and t > showif and is_solution(solution, puzzle):
            print('\nPuzzle            ', sep, 'Solution')
            for p, s in zip(picture(puzzle).splitlines(), picture(solution).splitlines()):
                print(p, sep, s)
            print('(%.2f seconds)\n' % t)
        return (t, is_solution(solution, puzzle)==True )
    with ThreadPoolExecutor(max_workers=nbthreads) as e:
        times, results = zip(*e.map(time_solve, puzzles))
    # without threading:
    #    times, results = zip(*map(time_solve, puzzles))
    N = len(puzzles)
    if N > 1:
        print("Solved %d of %d %s puzzles (avg %.2f secs (%d Hz), max %.2f secs)." % (
            sum(results), N, name, sum(times)/N, N/sum(times), max(times)))

def solved(values):
    "A puzzle is solved if each unit is a permutation of the digits 1 to 9."
    def unitsolved(unit): return set(values[s] for s in unit) == set(digits)
    return values is not False and all(unitsolved(unit) for unit in unitlist)


def unit_tests():
    "A suite of unit tests."
    assert len(squares) == 81
    assert len(all_units) == 27
    for s in squares:
        assert len(units[s]) == 3
        assert len(peers[s]) == 20
    assert units['C2'] == (('A2', 'B2', 'C2', 'D2', 'E2', 'F2', 'G2', 'H2', 'I2'),
                           ('C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9'),
                           ('A1', 'A2', 'A3', 'B1', 'B2', 'B3', 'C1', 'C2', 'C3'))
    assert peers['C2'] == {'A2', 'B2',       'D2', 'E2', 'F2', 'G2', 'H2', 'I2',
                           'C1',       'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9',
                           'A1', 'A3', 'B1', 'B3'}
    return 'All tests pass.'

def parse_grids(pictures):
    """Parse an iterable of picture lines into a list of grids."""
    return [parse(p) for p in pictures if p]

def shuffled(seq):
    "Return a randomly shuffled copy of the input sequence."
    seq = list(seq)
    random.shuffle(seq)
    return seq

def random_puzzle(N=17):
    """Make a random puzzle with N or more assignments. Restart on contradictions.
    Note the resulting puzzle is not guaranteed to be solvable, but empirically
    about 99.8% of them are solvable. Some have multiple solutions."""
    values = dict((s, digits) for s in squares)
    for s in shuffled(squares):
        if not assign(values, s, random.choice(values[s])):
            break
        ds = [values[s] for s in squares if len(values[s]) == 1]
        if len(ds) >= N and len(set(ds)) >= 8:
            return ''.join(values[s] if len(values[s])==1 else '.' for s in squares)
    return random_puzzle(N) ## Give up and make a new puzzle

grid1  = '003020600900305001001806400008102900700000008006708200002609500800203009005010300'
grid2  = '4.....8.5.3..........7......2.....6.....8.4......1.......6.3.7.5..2.....1.4......'
hard1  = '.....6....59.....82....8....45........3........6..3.54...325..6..................'
hard2  = '8..........36......7..9.2...5...7.......457.....1...3...1....68..85...1..9....4..'    
    
if __name__ == '__main__':
    unit_tests()
    #grid1 = parse("53..7.... 6..195... .98....6. 8...6...3 4..8.3..1 7...2...6 .6....28. ...419..5 ....8..79")
    #print(picture(grid1))
    nbsudoku = 40
    thread_list = ( 1, 2, 4, 8, 16)
    my_puzzles = parse_grids([hard2]*nbsudoku)
    for nbthreads in thread_list:
        startall = time.time()
        #hardest  = parse_grids(open('hardest.txt'))
        #grids10k = parse_grids(open('sudoku10k.txt'))
        #solve(puzzles=my_puzzles, verbose=False)
        solve_all(puzzles=my_puzzles, name='hard2', showif=None, nbthreads=nbthreads) 
        print(f'solved {nbsudoku} tests with {nbthreads} threads in {time.time()-startall:.2f} seconds' + '\n')



## References used:
## http://www.scanraid.com/BasicStrategies.htm
## http://www.sudokudragon.com/sudokustrategy.htm
## http://www.krazydad.com/blog/2005/09/29/an-index-of-sudoku-strategies/
## http://www2.warwick.ac.uk/fac/sci/moac/currentstudents/peter_cock/python/sudoku/
