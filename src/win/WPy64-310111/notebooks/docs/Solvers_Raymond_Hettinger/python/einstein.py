from sat_utils import solve_one, from_dnf, one_of
from sys import intern
from pprint import pprint

houses =     ['1',          '2',      '3',           '4',         '5'       ]

groups = [
             ['dane',      'brit',   'swede',       'norwegian', 'german'   ],
             ['yellow',    'red',    'white',       'green',     'blue'     ],
             ['horse',     'cat',    'bird',        'fish',      'dog'      ],
             ['water',     'tea',    'milk',        'coffee',    'root beer'],
             ['pall mall', 'prince', 'blue master', 'dunhill',   'blends'   ],
]

values = [value for group in groups for value in group]

def comb(value, house):
    'Format how a value is shown at a given house'
    return intern(f'{value} {house}')

def found_at(value, house):
    'Value known to be at a specific house'
    return [(comb(value, house),)]

def same_house(value1, value2):
    'The two values occur in the same house:  brit1 & red1 | brit2 & red2 ...'
    return from_dnf([(comb(value1, i), comb(value2, i)) for i in houses])

def consecutive(value1, value2):
    'The values are in consecutive houses:  green1 & white2 | green2 & white3 ...'
    return from_dnf([(comb(value1, i), comb(value2, j))
                     for i, j in zip(houses, houses[1:])])

def beside(value1, value2):
    'The values occur side-by-side: blends1 & cat2 | blends2 & cat1 ...'
    return from_dnf([(comb(value1, i), comb(value2, j))
                     for i, j in zip(houses, houses[1:])] +
                    [(comb(value2, i), comb(value1, j))
                     for i, j in zip(houses, houses[1:])]
                    )

cnf = []

# each house gets exactly one value from each attribute group
for house in houses:
    for group in groups:
        cnf += one_of(comb(value, house) for value in group)

# each value gets assigned to exactly one house
for value in values:
    cnf += one_of(comb(value, house) for house in houses)

cnf += same_house('brit', 'red')
cnf += same_house('swede', 'dog')
cnf += same_house('dane', 'tea')
cnf += consecutive('green', 'white')
cnf += same_house('green', 'coffee')
cnf += same_house('pall mall', 'bird')
cnf += same_house('yellow', 'dunhill')
cnf += found_at('milk', 3)
cnf += found_at('norwegian', 1)
cnf += beside('blends', 'cat')
cnf += beside('horse', 'dunhill')
cnf += same_house('blue master', 'root beer')
cnf += same_house('german', 'prince')
cnf += beside('norwegian', 'blue')
cnf += beside('blends', 'water')

pprint(solve_one(cnf))
