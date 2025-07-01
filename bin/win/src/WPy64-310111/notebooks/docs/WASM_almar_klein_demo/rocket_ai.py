import os
import time
from ppci import wasm
from rocket_qt import QtRocketGame

# Load the wasm ai modules
filename1 = os.path.join(os.path.dirname(__file__), 'wasm', 'ai1.wat')
ai_data1 = open(filename1, 'rt').read()
ai_module1 = wasm.Module(ai_data1)
#
filename2 = os.path.join(os.path.dirname(__file__), 'wasm', 'ai2.wasm')
ai_data2 = open(filename2, 'rb').read()
ai_module2 = wasm.Module(ai_data2)


class AiRocketGame(QtRocketGame):
    
    def __init__(self, ai_module=ai_module1):
        super().__init__()
        self.ai = wasm.instantiate(ai_module, self.imports, target='native')
    
    def paintEvent(self, event):
        super().paintEvent(event)
        self.ai.exports.update()
    
    def wasm_debug(self, a:float, b:float) -> None:
        print('debug', a, b)
        
    ## Imported methods of the AI module, which are exports to the game module
    
    def wasm_toggle_shoot(self, b:int) -> None:
        self.game.exports.toggle_shoot(bool(b))
    
    def wasm_toggle_turn_left(self, b:int) -> None:
        self.game.exports.toggle_turn_left(bool(b))
    
    def wasm_toggle_turn_right(self, b:int) -> None:
        self.game.exports.toggle_turn_right(bool(b))
    
    ## Imported methods of the game module, which are exports to the AI module
    
    def wasm_clear_screen(self) -> None:  # [] -> []
        super().wasm_clear_screen()
        self.ai.exports.clear_screen()
    
    def wasm_draw_enemy(self, x: float, y: float) -> None:  # [(0, 'f64'), (1, 'f64')] -> []
        super().wasm_draw_enemy(x, y)
        self.ai.exports.draw_enemy(x, y)
    
    def wasm_draw_player(self, x: float, y: float, a: float) -> None:  # [(0, 'f64'), (1, 'f64'), (2, 'f64')] -> []
        super().wasm_draw_player(x, y, a)
        self.ai.exports.draw_player(x, y, a)


if __name__ == '__main__':
    game = AiRocketGame(ai_module2)
    game.run()
