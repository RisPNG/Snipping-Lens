""" Run rocket.wasm in Python!

* Load the wasm module, compile to PPCI IR and then to native.
* Load the native object in memory, feed it the API it needs (wasm imports).
* Implement a Python app that uses the exposed API (wasm exports).

At the moment, the game is text based. But we can use Qt or SDL2 (or tk?)
to run it visually, and also feed in user interaction.
"""

import math
import logging
import time
import io
import os

from ppci import wasm
from ppci.utils.reporting import HtmlReportGenerator

#logging.basicConfig(level=logging.DEBUG)  # this produces so much output that it slows things down a lot
logging.basicConfig(level=logging.WARN)

# Load the wasm module
filename = os.path.join(os.path.dirname(__file__), 'wasm', 'rocket.wasm')
game_data = open(filename, 'rb').read()
game_module = wasm.Module(game_data)


class BaseRocketGame:
    """ Simple rocket game, text based, without user input.
    """
    
    def __init__(self, game_module=game_module):
        # Create import dict from methods
        env = {}
        for name in dir(self):
            if name.startswith('wasm_'):
                env[name[5:]] = getattr(self, name)
        self.imports = dict(env=env)
        
        # Instantiate game module
        self.game = wasm.instantiate(game_module, self.imports, target='python')
    
    def run(self):
        """ Enter the game's main loop.
        """
        self.game.exports.resize(100, 100)
        while True:
            time.sleep(0.5)
            self.game.exports.update(0.1)
            self.game.exports.draw()
            
            # We never call these ...
            # self.game.exports.toggle_shoot(b)
            # self.game.exports.toggle_turn_left(b)
            # self.game.exports.toggle_turn_right(b)
            # self.game.exports.toggle_boost(b)
    
    def wasm_sin(self, a:float) -> float:
        return math.sin(a)
    
    def wasm_cos(self, a:float) -> float:
        return math.cos(a)
    
    def wasm_Math_atan(self, a:float) -> float:
        return math.atan(a)
    
    def wasm_clear_screen(self) -> None:
        print('clearing screen')
    
    def wasm_draw_bullet(self, x:float, y:float) -> None:
        print(f'There is a bullet at {x}, {y}')
    
    def wasm_draw_enemy(self, x:float, y:float) -> None:
        print(f'There is an enemy at {x}, {y}')
    
    def wasm_draw_particle(self, x:float, y:float, a:float) -> None:
        print(f'There is a particle at {x}, {y} angle {a}')
    
    def wasm_draw_player(self, x:float, y:float, a:float) -> None:
        print(f'The player is at {x}, {y} angle {a}')
    
    def wasm_draw_score(self, score:float) -> None:
        print(f'The score is {score}!')


if __name__ == '__main__':
    game = BaseRocketGame()
    game.run()
