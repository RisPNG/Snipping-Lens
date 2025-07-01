from puzzle import Puzzle
import re

class PaPuzzle(Puzzle):
    ''' PaPuzzle
    This sliding block puzzle has 9 blocks of varying sizes:
    one 2x2, four 1x2, two 2x1, and two 1x1.  The blocks are
    on a 5x4 grid with two empty 1x1 spaces.  Starting from
    the position shown, slide the blocks around until the
    2x2 is in the lower left:

        1122
        1133
        45
        6788
        6799
    '''

    pos = '11221133450067886799'

    goal = re.compile( r'................1...' )

    def isgoal(self):
        return self.goal.search(self.pos) != None

    def __repr__(self):
        ans = '\n'
        pos = self.pos.replace('0', '.')
        for i in [0, 4, 8, 12, 16]:
            ans = ans + pos[i:i+4] + '\n'
        return ans

    xlat = str.maketrans('38975','22264')

    def canonical(self):
        return self.pos.translate(self.xlat)

    block = { (0,-4), (1,-4), (2,-4), (3,-4),
              (16,4), (17,4), (18,4), (19,4),
              (0,-1), (4,-1), (8,-1), (12,-1), (16,-1),
              (3,1), (7,1), (11,1), (15,1), (19,1) }

    def __iter__(self):
        dsone = self.pos.find('0')
        dstwo = self.pos.find('0', dsone+1)
        for dest in [dsone, dstwo]:
            for adj in [-4, -1, 1, 4]:
                if (dest, adj) in self.block: continue
                piece = self.pos[dest+adj]
                if piece == '0': continue
                newmove = self.pos.replace(piece, '0')
                for i in range(20):
                    if 0 <= i+adj < 20 and self.pos[i+adj]==piece:
                        newmove = newmove[:i] + piece + newmove[i+1:]
                if newmove.count('0') != 2: continue
                yield PaPuzzle(newmove)

if __name__ == '__main__':
    from pprint import pprint

    pprint(PaPuzzle().solve())
