# IDLEX EXTENSION
"""

Documentation Viewer Extension
Version: 0.2

Author: Roger D. Serwy
        roger.serwy@gmail.com

Date: 2009-05-29
Date: 2011-12-26 - modified to work with IdleX and Python 3

It provides "Documentation Viewer" under "Help"

Add these lines to config-extensions.def

Parts of this code is based on a patch submitted to the
Python Software Foundation under to Apache 2 License, per
a contributor agreement.
See http://bugs.python.org/issue964437 for the patch

"""
config_extension_def = """
[DocViewer]
enable=1
enable_editor=1
enable_shell=1
calltip=1

[DocViewer_cfgBindings]
docviewer-window=


"""


# TODO:
#   - sanitize command input box


from idlelib.configHandler import idleConf
import idlelib.IOBinding as IOBinding
from idlelib.EditorWindow import EditorWindow
from idlelib.OutputWindow import OutputWindow
from idlelib.Delegator import Delegator
from idlelib.HyperParser import HyperParser
import idlelib.WindowList as WindowList
import idlelib.SearchDialog as SearchDialog
import time
import sys
if sys.version < '3':
    from Tkinter import *
else:
    from tkinter import *




def get_cfg(cfg, type="bool", default=True):
    return idleConf.GetOption("extensions", "DocViewer",
                         cfg, type=type, default=default)

def set_cfg(cfg, b):
    return idleConf.SetOption("extensions", "DocViewer",
                      cfg,'%s' % b)



class DocViewer:

    menudefs = [
        ('help', [None,
               ('Documentation Viewer', '<<docviewer-window>>'),
       ]),]


    def __init__(self, editwin):
        self.editwin = editwin
        self.top = editwin.top
        text = self.editwin.text
        text.bind("<<docviewer-calltip>>", self.calltip_event)
        text.event_add("<<docviewer-calltip>>", "<KeyRelease-parenleft>")
        text.bind("<<docviewer-window>>", self.do_calltip)
        self.docWindow = docWindow

    def do_calltip(self, event=None):
        docWindow.show(self.editwin)
        self.calltip_event()

    def calltip_event(self, event=None):
        window = self.docWindow.window
        if window is None:
            return

        if not window.update_calltip.get():
            # don't process calltip event
            return

        # get calltip
        # code borrows from CallTips.py::open_calltip
        evalfuncs = False
        hp = HyperParser(self.editwin, "insert")
        sur_paren = hp.get_surrounding_brackets('(')
        if not sur_paren:
            return
        hp.set_index(sur_paren[0])
        name = hp.get_expression()
        if not name or (not evalfuncs and name.find('(') != -1):
            return

        w = window
        w.entry.delete("0", "end")
        w.entry.insert("insert", name)
        w.get_doc()

    def show_docviewer(self, event=None):
        # create a window with two text boxes and a label
        self.docWindow.show(self.editwin)

class DocDelegator(Delegator):
    """ Prevent modifications to the text widget that displays the documentation.
        Text may only be inserted if the .enabled value is True.
    """

    def insert(self, index, chars, tags=None):
        try:
            self.entry.insert('insert', chars)
            self.entry.focus()
        except Exception as err:
            print(' Internal DocDelegator Error:', err)

    def delete(self, index1, index2=None):
        pass


class DocWindowHandler(object):
    """ For handling a singleton instance of the DocViewer"""
    def __init__(self):
        self.window = None
        WindowList.registry.register_callback(self.check_close)
    def show(self, editwin, near=None):
        if self.window is None:
            shell = editwin.flist.open_shell()
            interp = shell.interp
            win = DocumentationWindow(flist=editwin.flist,
                                      interp=interp,
                                      editwin=shell)
            self.window = win
            win.top.bind('<Destroy>', self.destroy, '+')
            self.nearwindow(editwin.top)

    def nearwindow(self, near):
        w = self.window.top
        w.withdraw()
        geom = (near.winfo_rootx() + 10, near.winfo_rooty() + 10)
        w.geometry('=+%d+%d' % geom)
        w.deiconify()
        w.lift()

    def check_close(self, event=None):
        """ callback function to make sure the DocumentationWindow is
            not the last instance. If so, then close it.
        """
        if self.window is None:
            return

        d = WindowList.registry.dict
        t = str(self.window.top)
        if len(d) == 1:
            if t in d:
                self.window.close()
            else:
                #Strange situation. DocViewer is open, but not it the dict.
                #This should not happen.
                pass

    def destroy(self, event=None):
        self.window = None

docWindow = DocWindowHandler()

class DocumentationWindow(EditorWindow):
    """ Create an editor window for the purpose of displaying documentation """

    def __init__(self, flist=None, interp=None, editwin=None):
        EditorWindow.__init__(self, flist)
        self.interp = interp
        self.editwin = editwin

        # TODO: figure out better way to eliminate menu bar
        m = Menu(self.root)
        self.top.config(menu=m)

        root = self.top

        self.doc_frame = doc_frame = Frame(root)
        # make first line
        f_top = Frame(doc_frame)
        label = Label(f_top, text='Help on:')

        self.entry = entry = Entry(f_top)
        entry.bind('<Return>', self.get_doc)

        self.update_calltip = IntVar(root)
        check = Checkbutton(f_top, text='Update from Calltip',
                               variable=self.update_calltip)
        check.var = self.update_calltip
        if get_cfg('calltip'):
            check.select()

        f_top.pack(side='top', fill=X, padx=5)
        label.pack(side='left')
        entry.pack(side='left', fill=X, expand=True, padx=5, ipadx=5)
        check.pack(side='right')

        # make command buttons
        f_cmd = Frame(doc_frame)
        f_cmd.pack(side='top', fill=X, padx=3)



        self.button_showdoc = Button(f_cmd, text='Show Doc String',
                               default='active',
                               command=self.get_doc)

        self.button_showhelp = Button(f_cmd, text='Show help()',
                                   command=self.get_help)

        button_search = Button(f_cmd, text='Search Text',
                                  command=self.search)
        button_close = Button(f_cmd, text='Close',
                                 command=self.close)


        button_close.pack(side='right')
        self.button_showdoc.pack(side='left')
        self.button_showhelp.pack(side='left')
        button_search.pack(side='left')

        doc_frame.pack(side=TOP, before=self.text_frame, fill=X)

        # change focused widget to entry box
        self.entry.focus_set()
        self.top.focused_widget = self.entry

        # remove unneeded stuff
        self.per.removefilter(self.undo)
        self._rmcolorizer()
        #self.status_bar.pack_forget()

        # add a delegator to prevent editing of text widget
        self.doc_del = DocDelegator()
        self.doc_del.entry = self.entry

        self.per.insertfilter(self.doc_del)

        self.text._insert = self.doc_del.delegate.insert
        self.text._delete = self.doc_del.delegate.delete
        self.text.configure(wrap='none')

        keySetName = idleConf.CurrentKeys()
        find_bindings = idleConf.GetKeyBinding(keySetName, '<<find>>')
        for key_event in find_bindings:
            #self.entry.event_add('<<find>>', key_event)
            self.entry.bind(key_event, lambda e: self.text.event_generate('<<find>>'))

    def get_standard_extension_names(self):
        # Only load SearchBar if needed
        ret = []
        #a = idleConf.GetExtensions(editor_only=True)
        #if 'SearchBar' in a:
        #    ret.append('SearchBar')
        return ret



    def search(self, event=None):
        self.text.focus_set()
        self.text.update_idletasks()
        self.text.event_generate('<<find>>')
        self.text.update_idletasks()
        return "break"


    def get_help(self, event=None):
        #self.button_showhelp.configure(default='active')
        #self.button_showdoc.configure(default='disabled')
        b = self.entry.get().strip()
        if not b:
            return

        cmd = """if 1:
                    try:
                        help(%s)
                    except:
                        print("'%s' not found")""" % (b,b)

        self.process_request(cmd)

    def get_doc(self, event=None):
        #self.button_showhelp.configure(default='disabled')
        #self.button_showdoc.configure(default='active')

        b = self.entry.get().strip()
        if not b:
            return


        cmd = """if 1:
                try:
                    if hasattr(%s, '__doc__'):
                        print(%s.__doc__)
                    else:
                        print("%s doesn't have a doc string")
                except:
                    print("'%s' not found in the shell's namespace.")""" % ((b,)*4)

        cmd2 = """if 1:
                print "====Displaying %s.__doc__"
                print
                try:
                    if hasattr(%s, '__doc__'):
                        print(%s.__doc__)
                    else:
                        print("%s doesn't have a doc string")
                except:
                    print("'%s' not found in the shell's namespace.")
                print()
                print()
                print("====Displaying help(%s)")
                print()

                try:
                    help(%s)
                except:
                    print("'%s' not found in the shell's namespace.") """ % ((b,)*8)



        self.process_request(cmd)



    def process_request(self, cmd=None):

        if cmd is None:
            return

        try:
            test = compile(cmd, '', 'exec')
        except Exception as err:
            t = 'Unable to process your request.\nIs your given object in the namespace?'
            self.text._delete('1.0', 'end')
            self.text._insert('1.0', t)
            return

        interp = self.interp
        editwin = self.editwin

        self.count = 0

        if editwin.executing:
            self.text._insert(1.0, "The shell currently is executing a command.\n" \
                              "Please try again when the shell is done executing.\n")
            return

        editwin.text.mark_set("iomark2", "iomark")
        self.text._delete("1.0", "end")

        # redirect output from PyShell to DocViewer
        def insert_bridge(self, index, chars, tags=None):
            #self.count += 1
            #if self.count < 50:
            self.text.insert(index, chars, tags)


        __insert = editwin.text.insert
        editwin.text.insert = insert_bridge

        def mywrite(s, tags=()):
            if tags in ('stdout', 'stderr'):
                # send to me
                self.text._insert('insert', s,tags)

        __write = editwin.write
        editwin.write = mywrite


        interp.runcommand(cmd)

        # go into a loop, until help has arrived :)
        while editwin.executing:
            editwin.text.update_idletasks()
            time.sleep(0.05)

        # restore output to PyShell
        editwin.text.insert = __insert
        editwin.write = __write

        editwin.text.mark_set("iomark", "iomark2")

    def close(self):
        set_cfg('calltip', self.update_calltip.get())
        # remove all references
        if 0:
            self.doc_frame.destroy()
            self.editwin = None
            self.interp = None
            self.text._delete = None
            self.text._insert = None
            self.per.removefilter(self.doc_del)
            self.undo = None
            self.doc_del = None
        #EditorWindow.close(self)
        self._close()
        self.top.destroy()
        #print 'refcount: ', sys.getrefcount(DocViewer.WINDOW)
        DocViewer.WINDOW = None


    def short_title(self):
        return "IDLE Documentation Viewer"
