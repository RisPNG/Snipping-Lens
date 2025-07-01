#!/usr/bin/env python
# -*- coding: utf-8 -*-

#    userconfig License Agreement (MIT License)
#    ------------------------------------------
#
#    Copyright © 2009-2012 Pierre Raybaut
#
#    Permission is hereby granted, free of charge, to any person
#    obtaining a copy of this software and associated documentation
#    files (the "Software"), to deal in the Software without
#    restriction, including without limitation the rights to use,
#    copy, modify, merge, publish, distribute, sublicense, and/or sell
#    copies of the Software, and to permit persons to whom the
#    Software is furnished to do so, subject to the following
#    conditions:
#
#    The above copyright notice and this permission notice shall be
#    included in all copies or substantial portions of the Software.
#
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
#    OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
#    NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#    HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
#    WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#    OTHER DEALINGS IN THE SOFTWARE.


"""
userconfig
----------

The ``guidata.userconfig`` module provides user configuration file (.ini file)
management features based on ``ConfigParser`` (standard Python library).

It is the exact copy of the open-source package `userconfig` (MIT license).

19/12/2021: Removed Python 2 compatibility
"""


__version__ = "1.1.0"

import os
import re
import os.path as osp
import sys
import configparser as cp


def _check_values(sections):
    # Checks if all key/value pairs are writable
    err = False
    for section, data in list(sections.items()):
        for key, value in list(data.items()):
            try:
                _s = str(value)
            except Exception as _e:
                print("Can't convert:")
                print(section, key, repr(value))
                err = True
    if err:
        assert False
    else:
        import traceback

        print("-" * 30)
        traceback.print_stack()


def get_home_dir():
    """
    Return user home directory
    """
    try:
        path = osp.expanduser("~")
    except:
        path = ""
    for env_var in ("HOME", "USERPROFILE", "TMP"):
        if osp.isdir(path):
            break
        path = os.environ.get(env_var, "")
    if path:
        return path
    else:
        raise RuntimeError("Please define environment variable $HOME")


def get_config_dir():
    if sys.platform == "win32":
        # TODO: on windows config files usually go in
        return get_home_dir()
    return osp.join(get_home_dir(), ".config")


class NoDefault:
    pass


class UserConfig(cp.ConfigParser):
    """
    UserConfig class, based on ConfigParser
    name: name of the config
    options: dictionnary containing options *or* list of tuples
    (section_name, options)

    Note that 'get' and 'set' arguments number and type
    differ from the overriden methods
    """

    default_section_name = "main"

    def __init__(self, defaults):
        cp.ConfigParser.__init__(self)
        self.name = "none"
        self.raw = 0  # 0=substitutions are enabled / 1=raw config parser
        assert isinstance(defaults, dict)
        for _key, val in list(defaults.items()):
            assert isinstance(val, dict)
        if self.default_section_name not in defaults:
            defaults[self.default_section_name] = {}
        self.defaults = defaults
        self.reset_to_defaults(save=False)
        self.check_default_values()

    def update_defaults(self, defaults):
        for key, sectdict in list(defaults.items()):
            if key not in self.defaults:
                self.defaults[key] = sectdict
            else:
                self.defaults[key].update(sectdict)
        self.reset_to_defaults(save=False)

    def save(self):
        # In any case, the resulting config is saved in config file:
        self.__save()

    def set_application(self, name, version, load=True, raw_mode=False):
        self.name = name
        self.raw = 1 if raw_mode else 0
        if (version is not None) and (re.match("^(\d+).(\d+).(\d+)$", version) is None):
            raise RuntimeError(
                "Version number %r is incorrect - must be in X.Y.Z format" % version
            )

        if load:
            # If config file already exists, it overrides Default options:
            self.__load()
            if version != self.get_version(version):
                # Version has changed -> overwriting .ini file
                self.reset_to_defaults(save=False)
                self.__remove_deprecated_options()
                # Set new version number
                self.set_version(version, save=False)
            if self.defaults is None:
                # If no defaults are defined, set .ini file settings as default
                self.set_as_defaults()

    def check_default_values(self):
        """Check the static options for forbidden data types"""
        errors = []

        def _check(key, value):
            if value is None:
                return
            if isinstance(value, dict):
                for k, v in list(value.items()):
                    _check(key + "{}", k)
                    _check(key + "/" + k, v)
            elif isinstance(value, (list, tuple)):
                for v in value:
                    _check(key + "[]", v)
            else:
                if not isinstance(value, (bool, int, float, str)):
                    errors.append("Invalid value for %s: %r" % (key, value))

        for name, section in list(self.defaults.items()):
            assert isinstance(name, str)
            for key, value in list(section.items()):
                _check(key, value)
        if errors:
            for err in errors:
                print(err)
            raise ValueError("Invalid default values")

    def get_version(self, version="0.0.0"):
        """Return configuration (not application!) version"""
        return self.get(self.default_section_name, "version", version)

    def set_version(self, version="0.0.0", save=True):
        """Set configuration (not application!) version"""
        self.set(self.default_section_name, "version", version, save=save)

    def __load(self):
        """
        Load config from the associated .ini file
        """
        try:
            self.read(self.filename(), encoding="utf-8")
        except cp.MissingSectionHeaderError:
            print("Warning: File contains no section headers.")

    def __remove_deprecated_options(self):
        """
        Remove options which are present in the .ini file but not in defaults
        """
        for section in self.sections():
            for option, _ in self.items(section, raw=self.raw):
                if self.get_default(section, option) is NoDefault:
                    self.remove_option(section, option)
                    if len(self.items(section, raw=self.raw)) == 0:
                        self.remove_section(section)

    def __save(self):
        """
        Save config into the associated .ini file
        """
        fname = self.filename()
        if osp.isfile(fname):
            os.remove(fname)
        with open(fname, "w", encoding="utf-8") as configfile:
            self.write(configfile)

    def filename(self):
        """
        Create a .ini filename located in user home directory
        """
        return osp.join(get_config_dir(), ".%s.ini" % self.name)

    def cleanup(self):
        """
        Remove .ini file associated to config
        """
        os.remove(self.filename())

    def set_as_defaults(self):
        """
        Set defaults from the current config
        """
        self.defaults = {}
        for section in self.sections():
            secdict = {}
            for option, value in self.items(section, raw=self.raw):
                secdict[option] = value
            self.defaults[section] = secdict

    def reset_to_defaults(self, save=True, verbose=False):
        """
        Reset config to Default values
        """
        for section, options in list(self.defaults.items()):
            for option in options:
                value = options[option]
                self.__set(section, option, value, verbose)
        if save:
            self.__save()

    def __check_section_option(self, section, option):
        """
        Private method to check section and option types
        """
        if section is None:
            section = self.default_section_name
        elif not isinstance(section, str):
            raise RuntimeError("Argument 'section' must be a string")
        if not isinstance(option, str):
            raise RuntimeError("Argument 'option' must be a string")
        return section

    def get_default(self, section, option):
        """
        Get Default value for a given (section, option)

        Useful for type checking in 'get' method
        """
        section = self.__check_section_option(section, option)
        options = self.defaults.get(section, {})
        return options.get(option, NoDefault)

    def get(self, section, option, default=NoDefault, raw=None, **kwargs):
        """
        Get an option
        section=None: attribute a default section name
        default: default value (if not specified, an exception
        will be raised if option doesn't exist)
        """
        if raw is None:
            raw = self.raw

        section = self.__check_section_option(section, option)

        if not self.has_section(section):
            if default is NoDefault:
                raise RuntimeError("Unknown section %r" % section)
            else:
                self.add_section(section)

        if not self.has_option(section, option):
            if default is NoDefault:
                raise RuntimeError("Unknown option %r/%r" % (section, option))
            else:
                self.set(section, option, default)
                return default

        value = cp.ConfigParser.get(self, section, option, raw=raw)

        default_value = self.get_default(section, option)
        if isinstance(default_value, bool):
            value = eval(value)
        elif isinstance(default_value, float):
            value = float(value)
        elif isinstance(default_value, int):
            value = int(value)
        elif isinstance(default_value, str):
            pass
        else:
            try:
                # lists, tuples, ...
                value = eval(value)
            except:
                pass
        return value

    def get_section(self, section):
        sect = self.defaults.get(section, {}).copy()
        for opt in self.options(section):
            sect[opt] = self.get(section, opt)
        return sect

    def __set(self, section, option, value, verbose):
        """
        Private set method
        """
        if not self.has_section(section):
            self.add_section(section)
        if not isinstance(value, str):
            value = repr(value)
        if verbose:
            print("%s[ %s ] = %s" % (section, option, value))
        cp.ConfigParser.set(self, section, option, value)

    def set_default(self, section, option, default_value):
        """
        Set Default value for a given (section, option)
        -> called when a new (section, option) is set and no default exists
        """
        section = self.__check_section_option(section, option)
        options = self.defaults.setdefault(section, {})
        options[option] = default_value

    def set(self, section, option, value, verbose=False, save=True):
        """
        Set an option
        section=None: attribute a default section name
        """
        section = self.__check_section_option(section, option)
        default_value = self.get_default(section, option)
        if default_value is NoDefault:
            default_value = value
            self.set_default(section, option, default_value)
        if isinstance(default_value, bool):
            value = bool(value)
        elif isinstance(default_value, float):
            value = float(value)
        elif isinstance(default_value, int):
            value = int(value)
        elif not isinstance(default_value, str):
            value = repr(value)
        self.__set(section, option, value, verbose)
        if save:
            self.__save()

    def remove_section(self, section):
        cp.ConfigParser.remove_section(self, section)
        self.__save()

    def remove_option(self, section, option):
        cp.ConfigParser.remove_option(self, section, option)
        self.__save()
