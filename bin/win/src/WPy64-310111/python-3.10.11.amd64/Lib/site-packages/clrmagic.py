
import clr
def create_cs_function(name, code, dependencies = None):
    clr.AddReference("clrmagic")
    from MagicIPython import MagicCS
    from System import String
    from System.Collections.Generic import List
 
    if dependencies is not None and len(dependencies) > 0 :
        myarray = List[String]()
        for i,d in enumerate(dependencies):
            myarray.Add( d )
        myarray = myarray.ToArray()
    else:
        myarray = List[String]().ToArray()

    obj = MagicCS.CreateFunction(name, code, myarray)
    return lambda *params: run_cs_function(obj, params)
 
def run_cs_function(func, params):
    clr.AddReference("clrmagic")
    from MagicIPython import MagicCS
    from System.Collections.Generic import List
    from System import Object
 
    par = List[Object]()
    for p in params :
        par.Add ( p )
    return MagicCS.RunFunction(func, par.ToArray())

import sys
from IPython.core.magic import Magics, magics_class, line_magic, cell_magic
from IPython.core.magic import line_cell_magic
from IPython.core.display import HTML
from IPython.core import display
 
@magics_class
class CustomMagics(Magics):
 
    @cell_magic
    def CS(self, line, cell):
        """
        Defines command ``%%CS``.
        """
        #if not sys.platform.startswith("win"):
        #    raise Exception("Works only on Windows.")
         
        #from clrfunction import create_cs_function
        if line is not None:
            spl = line.strip().split(" ")
            name = spl[0]
            deps = " ".join(spl[1:]) if len(spl) > 1 else ""
            deps = deps.split(";")
             
        if name == "-h": 
            print(  "Usage: "
                    "   %%CS function_name dependency1;dependency2"
                    "   function code")
        else :
            try:
                f = create_cs_function(name, cell, deps)
            except Exception as e :
                print(e)
                return
            if self.shell is not None:
                self.shell.user_ns[name] = f
            return f
 
def load_ipython_extension(ip):
    """
    register magics function, can be called from a notebook
    """
    #ip = get_ipython()
    ip.register_magics(CustomMagics)
    # enable C# (CSHARP) highlight
    patch = ("IPython.config.cell_magic_highlight['clrmagic'] = "
             "{'reg':[/^%%CS/]};")
    js = display.Javascript(data=patch,
                            lib=["https://github.com/codemirror/CodeMirror/blob/master/mode/clike/clike.js"])

#register_magics()
