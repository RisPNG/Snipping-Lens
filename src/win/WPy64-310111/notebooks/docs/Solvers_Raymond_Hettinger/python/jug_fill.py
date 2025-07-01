from puzzle import Puzzle

class JugFill(Puzzle):
    '''Given a two empty jugs with 3 and 5 liter capacities and a full
       jug with 8 liters, find a sequence of pours leaving four liters
       in the two largest jugs.
    '''
    # https://dioverdt.files.wordpress.com/2011/01/jugs-problem.gif

    pos = (0, 0, 8)

    capacity = (3, 5, 8)

    goal = (0, 4, 4)

    def __iter__(self):
        for i in range(len(self.pos)):
            for j in range(len(self.pos)):
                if i==j: continue
                qty = min(self.pos[i], self.capacity[j] - self.pos[j])
                if not qty: continue
                dup = list(self.pos)
                dup[i] -= qty
                dup[j] += qty
                yield JugFill(tuple(dup))


if __name__ == '__main__':
    from pprint import pprint

    pprint(JugFill().solve())
