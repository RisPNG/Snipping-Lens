"""

IdleX Windows Configuration

Adds/removes "Edit with IdleX" to the right-click context menu
for .py files.

Author: Roger D. Serwy
Date:   2011-11-28
        2012-04-13 modified to work with setup.py

License: See LICENSE.txt

"""


import os
import sys
import shlex

WINREG = True

if sys.version < '3':
    import Tkinter as tk
    import tkMessageBox as mb
    try:
        import _winreg as W
    except:
        WINREG = False
else:
    import tkinter as tk
    import tkinter.messagebox as mb
    try:
        import winreg as W
    except:
        WINREG = False


if 'linux' in sys.platform:
    # For Testing on Non-Windows platforms
    class dummy_winreg:
        def dummy(*args, **kwargs):
            pass
        def CreateKey(self, *args, **kwargs):
            raise Exception('This is not Windows')
        DeleteKey = CreateKey
        def QueryValue(self, *args, **kwargs):
            return r'C:\\Python32\\python.exe'
        def __getattr__(self, *args, **kwargs):
            return self.dummy
    __file__ = 'LINUX'
    W = dummy_winreg()
    WINREG = True

if WINREG == False:
    mb.showerror(title='Edit with IdleX',
                 message='Unable to import winreg')

    sys.exit(1)


def get_python_executable():
    """ Get path to python.exe """
    reg = W.ConnectRegistry(None, W.HKEY_CLASSES_ROOT)
    p = W.OpenKey(reg, r'Python.File\shell\Edit with IDLE\command')
    v = W.QueryValue(p, None)
    path_to_python = shlex.split(v)[0]
    return path_to_python

def get_idlex_module():
    try:
        mod = __import__('idlexlib')
    except:
        return None
    return mod

def get_idlex_path():
    # This assumes EditWithIdleX.py is in same directory as idlex.py

    mod = get_idlex_module()
    if mod:
        head, tail = os.path.split(os.path.abspath(mod.__file__))
        path_to_idlex = os.path.join(head, 'launch.py')
    else:
        head, tail = os.path.split(os.path.abspath(__file__))
        head, tail = os.path.split(head)
        path_to_idlex = os.path.join(head, 'idlex.py')
    if os.path.exists(path_to_idlex):
        return path_to_idlex
    else:
        return 'NOT FOUND. Make sure idlex.py is in same directory as EditWithIdleX.py.'

def build_registry_value():
    """ Build the value for "Edit with IdleX" """
    path_to_python = get_python_executable()
    path_to_idlex = get_idlex_path()
    if not os.path.exists(path_to_idlex):
        raise Exception('Path to IdleX is not valid.')

    regval = '"%(python)s" "%(idlex)s" -e "%%1"' % {'python':path_to_python,
                                              'idlex':path_to_idlex}
    return regval

def create_registry_key():
    """ Create the "Edit with IdleX" registry key. """
    regval = build_registry_value()
    _create_registry_key_helper(regval)

def _create_registry_key_helper(regval):
    reg = W.ConnectRegistry(None, W.HKEY_CURRENT_USER)
    p = W.OpenKey(reg, r'Software\Classes', 0, W.KEY_SET_VALUE)
    p2 = W.CreateKey(p, 'Python.File\shell\Edit with IdleX\command')
    W.SetValue(p2, '', W.REG_SZ, regval)
    W.CloseKey(p2)
    W.CloseKey(p)
    W.CloseKey(reg)

def delete_registry_key():
    """ Delete the "Edit with IdleX" registry key """
    reg = W.ConnectRegistry(None, W.HKEY_CURRENT_USER)
    p = W.OpenKey(reg, r'Software\Classes\Python.File\shell', 0, W.KEY_ALL_ACCESS)
    p2 = W.DeleteKey(p, 'Edit with IdleX\command')
    p3 = W.DeleteKey(p, 'Edit with IdleX')
    W.CloseKey(p)
    W.CloseKey(reg)

def errorbox(err):
    mb.showerror(title='Error occurred',
                 message=err)

def successbox(op=''):
    mb.showinfo(title='Success',
                message='Operation Successful. %s' % op)

def add_menu_item():
    try:
        create_registry_key()
        successbox("'Edit with IdleX' added.")
    except Exception as err:
        errorbox(err)


def delete_menu_item():
    try:
        delete_registry_key()
        successbox("'Edit with IdleX' removed.")
    except Exception as err:
        errorbox(err)

def quitprog():
    root.destroy()

def build_gui():
    f1 = tk.Frame(root)
    f1.config(borderwidth=2, relief=tk.GROOVE)
    f1.pack(side=tk.TOP, fill=tk.BOTH, expand=1, padx=5, pady=5)

    msg = ["This will configure the right-click context menu",
           "item 'Edit with IdleX'. This will sit alongside the",
           "'Edit with IDLE' menu item.",
           "",
           "Python found at: %r" % get_python_executable(),
           "IdleX found at: %r" % get_idlex_path(),
           "",
           "If you change the location of IdleX, re-run this script.",
           "Otherwise, no action will occur if you click 'Edit with IdleX'.",
           "",
           "This program creates a registry key here:",
           r"HKEY_CURRENT_USER\Software\Classes\Python.File\shell\Edit with IdleX\command",
           ]
    L = tk.Label(f1, text='\n'.join(msg),
                 wraplength=300, justify=tk.LEFT)
    

    b1 = tk.Button(f1, text="Add 'Edit with IdleX' to context menu",
                   command=add_menu_item)

    b2 = tk.Button(f1, text="Remove 'Edit with IdleX' from context menu",
                   command=delete_menu_item)

    b3 = tk.Button(f1, text='Exit this program',
                   command=quitprog)

    TOP = tk.TOP
    L.pack(side=TOP, fill=tk.X, expand=True)
    b1.pack(side=TOP, fill=tk.X, expand=True)
    b2.pack(side=TOP, fill=tk.X, expand=True)
    b3.pack(side=TOP, fill=tk.X, expand=True)


if __name__ == '__main__':
    root = tk.Tk()
    root.title('Edit with IdleX')
    build_gui()
    root.mainloop()
