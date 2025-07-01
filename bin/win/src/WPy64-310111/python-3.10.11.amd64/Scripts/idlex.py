#!.\python.exe

# Launch IdleX
import sys

def show_error():
    if sys.version < '3':
        import Tkinter as tk
        import tkMessageBox as messagebox
    else:
        import tkinter as tk
        import tkinter.messagebox as messagebox

    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(title='IdleX Error',
                         message=('Unable to located "idlexlib".\n' +
                                  'Make sure it is located in the same directory ' +
                                  'as "idlexlib" or run setup.py to install IdleX.\n' +
                                  '  python setup.py install --user'))

try:
    import idlexlib
except ImportError:
    show_error()
    sys.exit(-1)
    
from idlexlib.idlexMain import main
main()

