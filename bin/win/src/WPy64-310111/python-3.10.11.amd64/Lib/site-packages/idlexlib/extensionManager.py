##    """
##    Copyright(C) 2011-2012 The Board of Trustees of the University of Illinois.
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


import sys

if sys.version < '3':
    from StringIO import StringIO
    from Tkinter import *
    import tkFileDialog
    import tkMessageBox
else:
    from io import StringIO
    from tkinter import *
    import tkinter.filedialog as tkFileDialog
    import tkinter.messagebox as tkMessageBox





import imp
try:
    import importlib
    HAS_IMPORTLIB = True
except ImportError:
    HAS_IMPORTLIB = False

from idlelib.configHandler import idleConf, IdleConfParser
import os

def make_config_parser(cfg):
    """ Stuff Configration String into a fake file and return an IDLE config parser """
    fp = StringIO()
    fp.write(cfg)
    fp.write('\n')
    fp.seek(0)

    # parse the configuration from the fake file
    confparse = IdleConfParser('')
    try:
        confparse.readfp(fp)
    except BaseException as e:
        print('\n Configuration Parse Error', e)
        return None
    return confparse


class ExtensionManager(object):
    """ Manages extensions for IdleX

    """
    def __init__(self, path):

        head,tail = os.path.split(path)
        self.extension_dir = head

        self.IDLEX_EXTENSIONS = self.get_idlex_extensions(head)

        IDLE_EXTENSIONS = []     # A list of default extensions in IDLE - those that come with the standard distribution
        for i in idleConf.defaultCfg['extensions'].sections():
            if i.endswith('_cfgBindings') or i.endswith('_bindings'):
                continue
            IDLE_EXTENSIONS.append(i)

        self.IDLE_EXTENSIONS = IDLE_EXTENSIONS

    def get_idlex_extensions(self, directory):
        """ Get a list of user extensions from 'directory' """
        contents = os.listdir(directory)
        contents.sort()

        contents = [x for x in contents if not x.startswith('_')]

        user_extensions = []
        for i in contents:
            fullpath = os.path.join(directory, i)
            if fullpath.endswith('.py') \
               and os.path.isfile(fullpath):
                try:
                    txt = open(fullpath, 'r').read(1000)
                except IOError:
                    print(' IOError while loading extension: %r' % fullpath)

                if '# IDLEX EXTENSION' in txt:
                    name = i[:-3]  # truncate .py
                    user_extensions.append(name)
                else:
                    print(' Not an IdleX extension: %r' % fullpath)

        return user_extensions

    def load_extension(self, name):
        """ Imports an extension by name and returns a reference to the module.
            Invalid modules return None.
        """
        fullname = 'extensions.%s' % name
        try:
            if HAS_IMPORTLIB:
                mod = importlib.import_module('.' + fullname, package=__package__)
            else:
                mod = __import__(fullname, globals(), locals(), [''], 1)
        except Exception as err:
            import traceback
            traceback.print_exc()
            mod = None
        return mod


    def find_extension(self, name):
        """ Locates an extension """
        path = self.extension_dir
        info = imp.find_module(name, [path])


    def load_extension_cfg(self, extName):
        """ Load the extension. get its default config string
            from the "config_extension_def" variable."""
        mod = self.load_extension(extName)
        if mod is None:
            print("could not load %s" % extName)
            return


        if hasattr(mod, "config_extension_def"):
            return mod.config_extension_def
        else:
            print("\n Missing 'config_extension_def' in %s. Not loading." % extName)
            return None

    def copy_options(self, name, cfgdict, confparse, blank=False):
        d = cfgdict["extensions"]
        optionlist = confparse.GetOptionList(name)
        for option in optionlist:
            try:
                value = confparse.get(name, option, raw=True)
            except BaseException as e:
                print(' Error during extension settings copy:\n', e)
                return False
            if not d.has_section(name):
                d.add_section(name)
            if not blank:
                d.set(name, option, value)
            else:
                d.set(name, option, '')
        return True




    def transfer_cfg(self, extName, confparse, keys=True):
        """ Transfer the configuration from the extension
            into IDLE's configuration. Returns True if successful. """


        if confparse is None:
            return False

        # copy the user extension configuration in IDLE
        retval = self.copy_options(extName, idleConf.userCfg, confparse)

        if 0:  # DEVELOPERS - this takes a long time to process
            # Report Any keybinding conflicts the user extension may have
            keyset = idleConf.GetCurrentKeySet()
            name_cfg = extName+'_cfgBindings'
            optionlist = confparse.GetOptionList(name_cfg)
            for option in optionlist:
                b = '<<%s>>' % option
                value = confparse.get(name_cfg, option)
                if value == '<Control-Key-l>': continue  # WORKAROUND: skip clear window binding
                for event, binding in list(keyset.items()):
                    if value in binding and event != b and value:
                        print('\n Warning: [%s] has an event binding conflict with' % name_cfg)
                        print(' ', event, value)

        # idleConf.GetExtensionBindings pulls only from the default configuration.
        # Must transfer bindings to defaultCfg dictionary instead.
        if keys:
            self.copy_options(extName+'_cfgBindings', idleConf.defaultCfg,
                         confparse)

        return retval


    def load_idlex_extensions(self, userExt=None):
        """ Load extensions. Returns number of extensions loaded. """

        if userExt is None:
            userExt = self.IDLEX_EXTENSIONS

        # get already-saved settings
        d = idleConf.GetUserCfgDir()
        usercfgfile = os.path.join(d, 'idlex-config-extensions.cfg')
        if os.path.isfile(usercfgfile):
            U = open(usercfgfile).read()
        else:
            U = ''

        count = 0
        userConfParser = make_config_parser(U)

        key_isdefault = idleConf.GetOption('main','Keys','default', type="bool")
        for extName in userExt:
            if self.reload_cfg(extName):
                count += 1
                # transfer already-saved settings, otherwise IDLE forgets them
                # when idleConf.SaveUserCfgFiles is called from within IDLE. Bug?
                self.transfer_cfg(extName, userConfParser,
                             keys=not key_isdefault) # Overwrite defaults with user config

        idleConf.SaveUserCfgFiles()
        return count

    def reload_cfg(self, extName):
         # get the default configuration for the individual extension
        cfg = self.load_extension_cfg(extName)
        if cfg is None:
            return False

        # shove the conf string into a ConfigParse object
        extConfParser = make_config_parser(cfg)
        if extConfParser is None:
            print('\n Unable to parse configuration for %s' % extName)
            return False

        # transfer the configuration to IDLE
        if not self.transfer_cfg(extName, extConfParser, keys=True):
            print('\n Unable to transfer configuration for %s' % extName)
            return False

        return True

try:
    from . import extensions
except (ImportError, ValueError) as err:
    import extensions

path = extensions.__file__

extensionManager = ExtensionManager(path)
