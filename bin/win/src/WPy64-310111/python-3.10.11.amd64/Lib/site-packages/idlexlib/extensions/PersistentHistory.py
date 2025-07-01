# IDLEX EXTENSION

##    """
##    Copyright(C) 2011 The Board of Trustees of the University of Illinois.
##    All rights reserved.
##    Developed by:   Roger D. Serwy
##                    University of Illinois
##    License: See LICENSE.txt
##    """

config_extension_def = """
[PersistentHistory]
enable=1
enable_editor=0
enable_shell=1

keep = 500

"""

from idlelib.configHandler import idleConf
import pickle
import os
import sys
import idlelib.PyShell as PyShell

# TODO: decide if having history tied to the python version is a good thing.

class PersistentHistory:

    cfg_dir = idleConf.GetUserCfgDir()
    history_file = os.path.join(cfg_dir,
                                'shell-history.dat')
                                #'shell-history-%X.dat' % sys.hexversion)

    menudefs = [
        ('options', [
                ('Clear History', '<<history-clear>>'),
       ]),]

    def __init__(self, editwin):
        if not isinstance(editwin, PyShell.PyShell):
            print('Not a PyShell instance - not running Persistent History')
            self.close = lambda *args, **kwargs: None
            return

        self.editwin = editwin
        self.text = text = editwin.text
        self.history = None


        self.text.bind('<<history-clear>>', self.history_clear_event)
        self.keep = idleConf.GetOption('extensions',
                                       'PersistentHistory',
                                       'keep',
                                       type='int',
                                       default=500)
        self.delay_init()
        
    def close(self):
        try:
            self.save_history()
        except Exception as err:
            print(' An error occurred during the close of PersistentHistory.py: %s' % str(err))

    def delay_init(self):
        if hasattr(self.editwin, 'history'):
            self.history = self.editwin.history
            self.load_history()
            #self._showit()  # for testing
            return
        self.text.after(100, self.delay_init)

    def save_history(self):
        hist = self.history.history[:]
        if len(hist) > self.keep:           # limit the amount kept
            hist = hist[len(hist)-self.keep:]
        
        f = open(self.history_file, 'wb')
        pickle.dump(hist, f, 1)  # protocol to be compatible with 2/3 
        f.close()


    def load_history(self):
        if not os.path.exists(self.history_file):
            return

        f = open(self.history_file, 'rb')
        try:
            data = pickle.load(f)
        except Exception as err:
            print('Unable to load history: %s ' % str(err))
            data = []
        f.close()

        
        data.extend(self.history.history) # Just in case a history already had
                                          # contents before being loaded. (Not supposed to happen)
        self.history.history = data


    def history_clear_event(self, ev=None):
        h = self.history
        h.history_prefix = None
        h.history_pointer = None
        h.history = []
        return "break"
        

    def _showit(self):  # for testing
        h = self.history
        print('-'*80)
        print(h.history)
        print(h.history_prefix)
        print(h.history_pointer)
        self.text.after(250, self.showit)
