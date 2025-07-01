# IDLEX EXTENSION
##    """
##    Copyright(C) 2011 The Board of Trustees of the University of Illinois.
##    All rights reserved.
##
##    Developed by:   Roger D. Serwy
##                    University of Illinois
##
##    Permission is hereby granted, free of charge, to any person obtaining
##    a copy of this software and associated documentation files (the
##    "Software"), to deal with the Software without restriction, including
##    without limitation the rights to use, copy, modify, merge, publish,
##    distribute, sublicense, and/or sell copies of the Software, and to
##    permit persons to whom the Software is furnished to do so, subject to
##    the following conditions:
##
##    + Redistributions of source code must retain the above copyright
##      notice, this list of conditions and the following disclaimers.
##    + Redistributions in binary form must reproduce the above copyright
##      notice, this list of conditions and the following disclaimers in the
##      documentation and/or other materials provided with the distribution.
##    + Neither the names of Roger D. Serwy, the University of Illinois, nor
##      the names of its contributors may be used to endorse or promote
##      products derived from this Software without specific prior written
##      permission.
##
##    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
##    OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
##    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
##    IN NO EVENT SHALL THE CONTRIBUTORS OR COPYRIGHT HOLDERS BE LIABLE FOR
##    ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
##    CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH
##    THE SOFTWARE OR THE USE OR OTHER DEALINGS WITH THE SOFTWARE.
##
##
##
##    Tabbed Editor Window Extension - provide tabs in IDLE's editor
##
##    About:
##
##    This extenion is a gross hack on the object system of IDLE.
##    The first EditorWindow instance gets configured as a TabManager
##    and subsequent EditorWindow instances use a duck-typed Frame instead
##    of a toplevel Tk object.
##
##    The tab bar itself works best under Linux. Under MacOSX, the buttons
##    are misplaced. Under Windows, the scroll wheel doesn't move the tabs.
##
##    """

config_extension_def = """
[TabExtension]
enable=1
enable_shell = 0
always_show = False
[TabExtension_cfgBindings]
tab-new-event=<Control-Key-t>

"""
import sys

if sys.version < '3':
    from Tkinter import *
    import tkMessageBox
else:
    from tkinter import *
    import tkinter.messagebox as tkMessageBox



import idlelib.EditorWindow as EditorWindow
import idlelib.WindowList as WindowList
from idlelib.ToolTip import ToolTipBase
import idlelib.ToolTip as ToolTip
import idlelib.FileList as FileList
import idlelib.Bindings as Bindings
from idlelib.configHandler import idleConf
from platform import python_version

TAB_BAR_SIDE = 'top'  # 'bottom'
WARN_MULTIPLE_TAB_CLOSING = True


def get_cfg(cfg, type="bool", default=True):
    return idleConf.GetOption("extensions", "TabExtension",
                         cfg, type=type, default=default)

def set_cfg(cfg, b):
    return idleConf.SetOption("extensions", "TabExtension",
                      cfg,'%s' % b)



class TabExtension(object):

    menudefs = [
        ('options', [
            ('!Always Show Tabs', '<<tab-show-event>>'),
       ]),]

    def __init__(self, editwin):
        # This is called from a unique "EditorWindow" instance, with its own set of menu/text widgets
        self.editwin = editwin

        # add "New Tab to file menu
        self.add_menu_entry()

        # monkey-patching the call backs to get updates to filename into tab bar
        editwin.undo.set_saved_change_hook(self.saved_change_hook)
        def updaterecentfileslist(x):
            editwin.update_recent_files_list(x)
            self.saved_change_hook()  # to reflect opened file names in tab bar
        editwin.io.updaterecentfileslist = updaterecentfileslist

        text = self.editwin.text
        text.bind('<<tab-new-event>>', self.tab_new_event)
        text.bind('<<close-window>>', self.close_window_event)

        self.editwin.setvar("<<tab-show-event>>", get_cfg("always_show"))

        if 'TAB_MANAGER' in dir(editwin.top):
            # clone the tab master pointers
            self.TAB_FRAME = editwin.top    # containing widget
            self.tabmanager = editwin.top.TAB_MANAGER
            self.button = self.add_tab_button()
            editwin.top.TAB_MANAGER = None   # break reference, no longer needed
            editwin.top.wakeup = self.wakeup
            self.button.select()
            return

        # INITIALIZE THE FIRST TAB MANAGER

        text.bind('<<tab-show-event>>', self.toggle_show)
        flist = self.editwin.flist
        self.tabmanager = tabmanager = TabManager(top=self.editwin.top, tab=self, flist=flist)
        tabmanager.ACTIVE = self

        # REPACK the EditorWindow widget contents into a Frame
        TOPLEVEL = self.editwin.top
        F = tabmanager.create_frame()
        F.wakeup = self.wakeup

        for elt in TOPLEVEL.pack_slaves():
            p = elt.pack_info()
            p['in'] = F
            elt.pack(**p)

        F.pack(side='top', fill=BOTH, expand=YES)
        F._lower() # fix Z-order

        # TODO: repack all grid and place widgets

        self.TAB_FRAME = F    # reference to container frame
        editwin.top = F

        self.button = self.add_tab_button() # populate tab bar
        TOPLEVEL.after_idle(self.editwin.postwindowsmenu)   # need to change menu

    def add_menu_entry(self):
        # patch "New Tab" into the File Menu
        e = self.editwin
        f = e.menudict['file']
        text = e.text
        eventname = '<<tab-new-event>>'
        def command(text=text, eventname=eventname):
            text.event_generate(eventname)

        keydefs = Bindings.default_keydefs
        accelerator = EditorWindow.get_accelerator(keydefs, eventname)

        f.insert_command(2, label="New Tab", command=command,
                        accelerator=accelerator)

    def toggle_show(self, ev=None):
        self.always_show = not get_cfg("always_show")
        set_cfg("always_show", self.always_show)
        self.editwin.setvar("<<tab-show-event>>", self.always_show)
        self.tabmanager.visible_bar()

    def wakeup(self):
        return self.button.select()

    def select(self, event=None):
        return self.tabmanager.tab_wakeup(tabframe=self)

    def closetab(self, event=None):
        return self.tabmanager.close_tab(tabframe=self)

    def add_tab_button(self):
        b = self.tabmanager.addtab(tabframe=self)
        #self.tooltip = ToolTip.ToolTip(b, self.get_filepath())
        self.tooltip = TabToolTip(b, self.get_filepath)
        return b

    def tab_new_event(self, event=None):
        self.tabmanager.newtab()
        return "break"

    def saved_change_hook(self):
        self.editwin.saved_change_hook()
        self.button.set_text(self.get_title())
        self.tooltip.text = self.get_filepath()

    def save_stars(self, txt):
        """ wrap strings with ** if it refers to a window that's not saved"""
        if not self.editwin.get_saved():
            txt = "*%s*" % txt
        return txt

    def get_filepath(self, event=None):
        f = self.editwin.long_title()
        if not f:
            f = 'Untitled'
        return self.save_stars(f)

    def get_title(self, event=None):
        short = self.editwin.short_title()
        # remove the Python version...
        if short:
            try:
                pyversion = "Python " + python_version() + ": "
                if short.startswith(pyversion):
                    short = short[len(pyversion):]
            except:
                pass
 
        if not short:
            short = "Untitled"
        return self.save_stars(short)

    def close(self):
        #print 'unloading tabextension.py'
        self.editwin = None
        self.TAB_FRAME = None
        self.tooltip = None

    def close_window_event(self, event=None):
        """ Redirect to close the current tab """
        self.button.remove()
        return "break"

class TabToolTip(ToolTipBase):
    def __init__(self, button, text_callback):
        ToolTipBase.__init__(self, button)
        self.text_callback = text_callback

    def showcontents(self):
        try:
            text = self.text_callback()
        except:
            text = ''
        ToolTipBase.showcontents(self, text)

    def schedule(self):
        self.unschedule()
        self.id = self.button.after(500, self.showtip)

    def showtip(self):
        # make sure tip is on the screen

        ToolTipBase.showtip(self)
        tipwindow = self.tipwindow
        tipwindow.update_idletasks()

        sw = tipwindow.winfo_screenwidth()
        tw = tipwindow.winfo_width()
        tx = tipwindow.winfo_x()
        ty = tipwindow.winfo_y()

        delta = tw + tx - sw
        if delta > 0:
            # must shift the tipwindow to the left by delta
            dx = tx - delta
            tipwindow.wm_geometry('+%d+%d' % (dx, ty))


class TabManagerList(object):  # for window list
    def __init__(self):
        self.clients = []
        self.ACTIVE = None
        self.orig_LTL = WindowList.ListedToplevel  # save original

    def get_frame(self):
        if self.ACTIVE is not None:
            F = self.ACTIVE.create_frame()
        else:
            if self.clients:
                F = self.clients[0].create_frame()
            else:
                F = None # should not happen
        return F

    def set_active(self, t):
        if t in self.clients:
            self.ACTIVE = t
            self.postwindowsmenu()
        else:
            pass

    def postwindowsmenu(self, event=None):
        # FIXME: what does this do again?
        for t in self.clients:
            if t.active_frame.editwin is not None:
                t.active_frame.editwin.postwindowsmenu()
            else:
                print('null editwin:', t, t.active_frame)


    def add(self, m):
        TOPLEVEL = m.TOPLEVEL
        def change(event=None, m=m):
            tabmanagerlist.set_active(m)
        TOPLEVEL.bind('<FocusIn>', change, '+')

        self.clients.append(m)

    def change_manager(self, event=None):
        self.set_active(self)

    def remove(self, m):
        if m is self.ACTIVE:
            self.ACTIVE = None
        self.clients.remove(m)


tabmanagerlist = TabManagerList()  # This is a stand-in object for ListedTopLevel in WindowList

# MONKEY PATCH - temporarily replace the ListedTopLevel with a Frame
# object in the current TabManager window
def patch(func):
    def n(*arg, **kw):
        if tabmanagerlist.ACTIVE is not None:  # are there any toplevel windows?
            orig = WindowList.ListedToplevel  # save original
            def open_patch(*arg, **kw):
                return tabmanagerlist.get_frame()
            WindowList.ListedToplevel = open_patch  # patch it
            retval = func(*arg, **kw)   # call function
            WindowList.ListedToplevel = orig  # restore it
            return retval
        else:
            return func(*arg, **kw)   # call original function
    return n

FileList.FileList.open = patch(FileList.FileList.open)


class TabManager(object):   # for handling an instance of ListedTopLevel

    def __init__(self, top=None, tab=None, flist=None):
        self.flist = flist
        TOPLEVEL = self.TOPLEVEL = top
        self.TABS = []
        self.CLOSE_FRAME = None
        self.active_frame = tab
        TOPLEVEL.protocol("WM_DELETE_WINDOW", self.closetoplevel)
        TOPLEVEL.bind('<<tab-show-event>>', self.visible_bar)
        # create a tab bar widget
        tab_bar = self.tab_bar = TabWidget(self.TOPLEVEL)
        tab_bar.config(height=7, relief=GROOVE, bd=1)
        tab_bar.bind('<Button-3>', lambda x: self.tabmenu(event=x))

        tabmanagerlist.add(self)

    def create_frame(self):
        # make a FRAME for holding the editors,
        # duck-typing to mimic a Toplevel object

        TOPLEVEL = self.TOPLEVEL
        F = Frame(TOPLEVEL)
        F.state = lambda: "normal"
        F.wm_geometry = TOPLEVEL.wm_geometry
        F.protocol = lambda *args, **kwargs: True    # override protocol requests
        F.wakeup = None  # will be overwritten by TabExtension
        F.wm_title = TOPLEVEL.wm_title   # pass-thru
        F.wm_iconname = TOPLEVEL.wm_iconname  # pass-thru
        F.TAB_MANAGER = self  # INDICATOR
        F._lower = F.lower
        F._lift = F.lift

        F.lift = TOPLEVEL.lift
        F.lower = TOPLEVEL.lower

        F.instance_dict = TOPLEVEL.instance_dict
        F.update_windowlist_registry = TOPLEVEL.update_windowlist_registry
        F.iconbitmap = TOPLEVEL.iconbitmap
        return F

    def newtab(self):
        patch(self.flist.new)()

    def addtab(self, tabframe=None):
        tab_bar = self.tab_bar
        b = tab_bar.add(text=tabframe.get_title(),
                   select_callback=tabframe.select,
                   remove_callback=tabframe.closetab)

        def mb(event=None, tabframe=tabframe):
            self.tabmenu(event=event, tabframe=tabframe)
        b.totalbind('<Button-3>', mb)

        self.TABS.append(tabframe)
        self.visible_bar()
        return b


    def tabmenu(self, event=None, tabframe=None):

        rmenu = Menu(self.TOPLEVEL, tearoff=0)

        if tabframe is not None:
            rmenu.add_command(label='Close tab', command=tabframe.button.remove)
            rmenu.add_separator()
            rmenu.add_command(label='New tab', command=tabframe.tab_new_event)
            rmenu.add_separator()

        for t in self.TABS:
            label = t.get_title()
            rmenu.add_command(label=label, command=t.button.select)

        rmenu.tk_popup(event.x_root, event.y_root)

    def visible_bar(self, ev=None):
        a = get_cfg("always_show")
        if len(self.TABS) > 1 or a: #TAB_SHOW_SINGLE:
            if TAB_BAR_SIDE == 'top':
                self.tab_bar.pack(side='top', fill=X, expand=NO,
                                       before=self.active_frame.TAB_FRAME)
            else:
                self.tab_bar.pack(side='bottom', fill=X, expand=NO)
        else:
            self.tab_bar.pack_forget()

    def tab_wakeup(self, tabframe=None):
        #print 'tab_wakeup', tabframe.get_title()

        if self.active_frame is tabframe:
            return # already awake

        if self.active_frame:
            self.active_frame.TAB_FRAME.pack_forget()

        tabframe.TAB_FRAME.pack(fill=BOTH, expand=YES)
        self.active_frame = tabframe

        # switch toplevel menu
        TOPLEVEL = self.TOPLEVEL
        TOPLEVEL.config(menu=None)   # restore menubar

        def later(TOPLEVEL=TOPLEVEL, tabframe=tabframe):
            TOPLEVEL.config(menu=tabframe.editwin.menubar)   # restore menubar
            TOPLEVEL.update_idletasks()  # critical for avoiding flicker (on Linux at least)
            TOPLEVEL.lift()  # fix a bug caused in Compiz? where a maximized window loses the menu bar
            TOPLEVEL.focused_widget=tabframe.editwin.text  # for windowlist wakeup
            tabframe.editwin.text.focus_set()

        TOPLEVEL.after_idle(later)
        TOPLEVEL.after_idle(self.visible_bar)
        TOPLEVEL.after_idle(tabframe.saved_change_hook)
        TOPLEVEL.after_idle(tabmanagerlist.postwindowsmenu)  # need to change only the menus of active tabs
        TOPLEVEL.after_idle(tabframe.button.ensure_visible)

        if self.CLOSE_FRAME is not None:  # to prevent flicker when the recently closed tab was active
            self.delayed_close()


    def _close(self):
        self.TOPLEVEL.destroy()
        tabmanagerlist.remove(self)

    def close_tab(self, tabframe=None):
        reply = tabframe.editwin.maybesave()
        if str(reply) == "cancel":
            return "cancel"

        #self.tab_bar._remove(tabframe.button) # 2012-04-05 bug fix - File->Close now works 

        self.CLOSE_FRAME=tabframe
        if self.active_frame is not tabframe or len(self.TABS) == 1:
            self.delayed_close()
            
        return "break"


    def delayed_close(self):
        # for when closing the active tab,
        # to prevent flicker of the GUI when closing the active frame
        tabframe = self.CLOSE_FRAME
        if tabframe is not None:
            tabframe.editwin._close()
            self.TABS.remove(tabframe)

            if self.TABS:   # some tabs still exist
                self.visible_bar()
            else:           # last tab closed
                self._close()
        self.CLOSE_FRAME = None


    def closetoplevel(self, event=None):
        if self.closewarning() == False:
            return "break"

        for tabframe in self.TABS:
            if not tabframe.editwin.get_saved():
                tabframe.button.select()
            reply = tabframe.editwin.maybesave()
            if str(reply) == "cancel":
                return "break"

        # close all tabs
        for tabframe in self.TABS:
            tabframe.editwin._close()

        self._close()
        return "break"

    def closewarning(self, event=None):
        if not WARN_MULTIPLE_TAB_CLOSING:
            return True

        L = len(self.TABS)
        if L > 1:
            res = tkMessageBox.askyesno(
                        "Close Multiple Tabs?",
                        "Do you want to close %i tabs?" % L,
                        default="no",
                        parent=self.TOPLEVEL)
        else:
            res = True
        return res


# Tab Widget code


class TabWidget(Frame):
    def __init__(self, *args, **kw):
        Frame.__init__(self, *args, **kw)
        self.scrollbind(self)  # enable scroll-wheel
        self.bind('<Configure>', self._config)

        # add scroll buttons
        self._BL = BL = Button(self, text="<", padx=0, bd=2, pady=0,
                    command=lambda: self._shift('left'),
                    relief=FLAT)
        BL.pack(side='left', fill=Y)

        self.scrollbind(BL)
        self._BR = BR = Button(self, text=">", padx=0, bd=2, pady=0,
                    command=lambda: self._shift('right'),
                    relief=FLAT)
        BR.place(relx=1, y=-1, rely=0.5, anchor=E, relheight=1)
        self.scrollbind(BR)

        # internal variables to track TABS
        self.tablist = []     # list of tabs
        self._offset = 0      # offset of leftmost tab
        self._active = None
        self.drag_pos = None  # for drag'n'drop support

        self.POINT = Label(self, bg="#FF0000", width=2)  # for drag'n'drop
        self.VALID_OFFSET = True    # boolean flag for tab coordinates


        self.hover_scroll(BL, 'left')
        self.hover_scroll(BR, 'right')


    def hover_scroll(self, btn, cmd):
        class Shifter:
            def __init__(self, btn, cmd, tw):
                self.tw = tw
                self.btn = btn
                self.cmd = cmd
                self.timer = None

            def start(self, ev=None):
                self.timer = self.btn.after(500, self.doit)

            def doit(self, ev=None):
                state = self.btn.cget('state')
                if  state != 'disabled':
                    self.tw._shift(cmd, magdx=5)
                    self.tw.enable_shifters()
                self.stop()
                self.timer = self.btn.after(50, self.doit)

            def stop(self, ev=None):
                if self.timer is not None:
                    self.btn.after_cancel(self.timer)

        a = Shifter(btn, cmd, self)
        btn.bind('<Enter>', a.start)
        btn.bind('<Leave>', a.stop)
        btn.bind('<Button>', a.stop, '+')



    def scrollbind(self, widget):
        widget.bind('<Button-4>', lambda x=None: self._shift('left'))
        widget.bind('<Button-5>', lambda x=None: self._shift('right'))

    def add(self, text=None, select_callback=None,
            unselect_callback=None,
            remove_callback=None):

        b = TabButton(self, text=text)
        #b.set_text(text, gui=False)
        b.select_callback = select_callback
        b.unselect_callback = unselect_callback
        b.remove_callback = remove_callback

        b.totalbind('<B1-Motion>', lambda event=None, tab=b:self.drag(event, tab))
        b.totalbind('<ButtonRelease-1>', lambda event=None, tab=b:self.release(event, tab))

        if self.tablist:
            ft = self.tablist[-1]
        else:
            self._active = b
            b._gui_select()
            ft = None

        self.tablist.append(b)
        self._repopulate(tab=ft)  # FIXME: only pack this widget, not all of them

        return b

    def checktab(f):
        def n(self, tab=None):
            if tab in self.tablist:
                f(self, tab)
            else:
                pass
        return n

    #@checktab
    def _remove(self, tab=None):
        self.VALID_OFFSET = False
        tablist = self.tablist

        i = tablist.index(tab)
        tablist.remove(tab)
        tab.place_forget()

        if tablist:
            # adjust offset, if need be
            loc = tab._tab_offset
            width = loc[1] - loc[0]

            tw = self._bar_width()
            rtab = self.tablist[-1]._tab_offset[1]

            if rtab + self._offset - tw - width <= 0:
                self._offset += width
                if self._offset > 0:
                    self._offset = 0


            if tab is self._active:
                self._active = None
                if i > len(tablist) - 1:
                    i = len(tablist) - 1
                if i >= 0:
                    tablist[i].select()


            self._repopulate()

    #@checktab
    def _ensure_visible(self, tab=None):
        if not self.VALID_OFFSET:
            return

        loc = tab._tab_offset
        width = loc[1] - loc[0]
        tw = self._bar_width()
        offset = self._offset

        if loc[0] < -offset:
            self._offset = -loc[0]
            self._shift_redraw()

        elif loc[1] > tw - offset:
            self._offset = tw - (loc[0] + width)
            self._shift_redraw()

    #@checktab
    def _select(self, tab=None):
        tab._gui_select()

        if self._active not in [None, tab]:
            self._active.unselect()

        self._active = tab
        return "break"

    #@checktab
    def _unselect(self, tab=None):
        tab._gui_unselect()

    def _bar_width(self):
        self.update_idletasks()
        bw = self._BL.winfo_width() + self._BR.winfo_width() + 2 # MAGIC: 2 is bd
        tw = self.winfo_width() - bw
        return tw

    def _shift(self, direction=None, magdx=None):
        _offset = self._offset
        if len(self.tablist) == 0:
            return

        offsets = [t._tab_offset for t in self.tablist]
        leeway = 0      # slop factor in pixels
        dx = 0
        if direction == 'left':
            for i,j in offsets[::-1]:
                if i < -leeway - _offset:
                    break
            dx = -i - _offset
            if magdx is not None:
                dx = magdx

        elif direction == 'right':
            tw = self._bar_width()
            if offsets[-1][1] > tw:
                for i,j in offsets:
                    if j > tw + leeway - _offset:
                        break
                dx = tw - j -_offset
            if magdx is not None:
                dx = -magdx

        if dx != 0:
            self._offset += dx
            if self._offset > 0:
                self._offset = 0
            self._shift_redraw(direction=direction)


    def _shift_redraw(self, direction=None):
        # avoid overlap when repositioning buttons
        bw = self._BL.winfo_width()
        if direction == 'left':
            tabs = self.tablist[::-1]  # pull widgets from the right side
        elif direction == 'right':
            tabs = self.tablist  # pull widgets from the left side
        else:
            tabs = None


        if tabs:
            _offset = self._offset
            for elt in tabs:
                off = elt._tab_offset
                elt.place(x = off[0] + bw +_offset)

            self.enable_shifters()

    def _repopulate(self, tab=None):
        # redraws the tab bar, but can have a lot of flicker
        self.update_idletasks()

        _offset = self._offset
        bw = self._BL.winfo_width()

        if tab is None:
            lb = 0
            total = 0
        else:
            lb = self.tablist.index(tab)
            total = tab._tab_offset[0]


        for elt in self.tablist[lb:]:
            x = total
            elt.place(x=x + bw + _offset, y=0, anchor=NW, relheight=1)

            elt.lower()
            elt.update_idletasks()

            w = elt.winfo_width()

            elt._tab_offset = (x, x+w)
            total += w

        self.enable_shifters()
        self.VALID_OFFSET = True

    def enable_shifters(self):
        # turn on/off the left or right shift arrows
        BL = self._BL
        BR = self._BR

        offset = self._offset

        if offset == 0:
            BL.config(state=DISABLED)
        else:
            BL.config(state=NORMAL)

        tw = self._bar_width()

        tablist = self.tablist
        if not tablist or tablist[-1]._tab_offset[1] <= tw - offset:
            BR.config(state=DISABLED)
        else:
            BR.config(state=NORMAL)

    def _config(self, event=None):
        if not self.tablist:
            return

        # when window is resized,
        # move tabs over to fill new space if possible
        tw = self._bar_width()

        rtab = self.tablist[-1]._tab_offset[1]
        if rtab < tw - self._offset:
            self._offset = tw - rtab
            if self._offset > 0:
                self._offset = 0
            self._shift_redraw(direction='left')
        else:
            self._BR.config(state=NORMAL)



    def drag(self, event=None, tab=None):
        # preliminary drag support

        tx, tx2 = tab._tab_offset
        width = tx2 - tx

        # BUG: when selected widget right boundary extends
        # beyond the right shifter, there is no scrolling
        # because the cursor is still within the button
        P = self.POINT
        if 0 < event.x < width:
            # no drag when within the button
            P.place_forget()
            self.drag_pos = None
            return

        bw = self._BL.winfo_width()
        tw = self._bar_width()

        x = event.x + tx
        bx = x + self._offset

        # shift display when dragged to the shifters
        if bx < 0:
            dx = 10
            direction='left'
        elif bx > tw:
            dx = -10
            direction='right'
        else:
            dx = 0

        if dx:
            self._offset += dx
            rtab = self.tablist[-1]._tab_offset[1]
            if self._offset < tw-rtab:
                self._offset = tw - rtab
            if self._offset > 0:
                self._offset = 0
            self._shift_redraw(direction=direction)

        bx = x + self._offset
        if dx or 0 < bx < tw:
            offsets = [t._tab_offset for t in self.tablist]
            mid = [(i[0] + i[1])//2 for i in offsets]  # midpoints
            z = list(zip(mid, self.tablist, offsets))

            for n,i in enumerate(z):   # get the nearest boundary
                ax, t, offset = i
                if ax > x:
                    break
            else:  # place at the last position
                offset = offset[1], offset[0]
                n += 1

            self.drag_pos = n
            P.place(x=offset[0] + bw + self._offset-1, relheight=1, width=2)
            P.lift()

    def release(self, event=None, tab=None):
        P = self.POINT
        P.place_forget()

        if self.drag_pos is not None:
            orig_i = self.tablist.index(tab)
            new_i = self.drag_pos

            self.tablist.insert(self.drag_pos, tab)
            if new_i < orig_i:
                del self.tablist[orig_i+1]
            else:
                del self.tablist[orig_i]
            self.drag_pos = None

            self._repopulate()

#####################################################

class TabButton(Frame):
    def __init__(self, master, text=None):
        Frame.__init__(self, master, bd=2)
        self.master=master
        self._gui_unselect()

        L = self.L = Label(self, padx=7, pady=1, text=text)
        L.pack(side='left')
        L.bind('<Button-1>', self.select)

        remove_button = self.remove_button = Button(self, padx=0, pady=0, text='X',
                                                    command=self.remove,
                                                    bd=1)

        remove_button.pack(side='right') #, pady=1, padx=1)

        master.scrollbind(self)
        master.scrollbind(L)
        master.scrollbind(remove_button)

        self._tab_offset = [0,0]
    def _gui_select(self):
        self.config(relief=SUNKEN)

    def _gui_unselect(self):
        self.config(relief=RAISED)

    def totalbind(self, *arg, **kw):
        e = [self, self.L, self.remove_button]
        for i in e:
            i.bind(*arg, **kw)

    def set_text(self, text=None, gui=True):
        self.L.config(text=text)

        if gui:
            self.master._repopulate()
            if self.master._active is self:
                self.master._ensure_visible(tab=self)

    def select(self, event=None):
        self.master._select(self)
        if self.select_callback is not None:
            self.select_callback()

    def unselect(self, event=None):
        self.master._unselect(self)
        if self.unselect_callback is not None:
            self.unselect_callback()

    def remove(self, event=None):
        if self.remove_callback is not None:
            if self.remove_callback() == "cancel":
                return
        try:
            self.master._remove(tab=self)
        except TclError:
            pass  # happens when toolbar is destroyed by the remove callback

    def ensure_visible(self, event=None):
        self.master._ensure_visible(tab=self)




if __name__ == '__main__':
    # TEST
    root = Tk()

    tab = TabWidget(root, relief=RAISED, bd=1)
    tab.pack(expand=NO, fill=X)


    def click(num=None):
        pass
        #print 'click', num

    def unclick(num=None):
        pass
        #print 'unclick', num

    T = []
    for i in range(13):
        a = tab.add(text='TABBED %i' %i,
                    select_callback=lambda x=i: click(x),
                    unselect_callback=lambda x=i:unclick(x))
        T.append(a)

    TE = Text(root, width=55, height=4)
    TE.pack(side='bottom', expand=YES, fill=BOTH)

    root.mainloop()
