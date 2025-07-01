"""
.. module:: session
   :synopsis: Main module for scilab2py package.
              Contains the Scilab session object Scilab2Py

.. moduleauthor:: Steven Silvester <steven.silvester@ieee.org>

"""
from __future__ import print_function
import os
import re
import atexit
import glob
import logging
import signal
import subprocess
import sys
import threading
import time
from tempfile import gettempdir

from scilab2py.matwrite import MatWrite
from scilab2py.matread import MatRead
from scilab2py.utils import (
    get_nout, Scilab2PyError, get_log, Struct, _remove_temp_files)
from scilab2py.compat import PY2, queue, unicode


class Scilab2Py(object):

    """Manages a Scilab session.

    Uses MAT files to pass data between Scilab and Numpy.
    The function must either exist as an file in this directory or
    on Scilab's path.

    You may provide a logger object for logging events, or the scilab.get_log()
    default will be used.  Events will be logged as debug unless verbose is set
    when calling a command, then they will be logged as info.

    Parameters
    ----------
    executable : str, optional
        Name of the Scilab executable, can be a system path.
    logger : logging object, optional
        Optional logger to use for Scilab2Py session
    timeout : float, opional
        Timeout in seconds for commands
    oned_as : {'row', 'column'}, optional
        If 'column', write 1-D numpy arrays as column vectors.
        If 'row', write 1-D numpy arrays as row vectors.}
    temp_dir : str, optional
        If specified, the session's MAT files will be created in the
        directory, otherwise a default directory is used.  This can be
        a shared memory (tmpfs) path.
    """

    def __init__(self, executable=None, logger=None, timeout=None,
                 oned_as='row', temp_dir=None, convert_to_float=True):
        """Start Scilab and create our MAT helpers
        """
        self._oned_as = oned_as
        self._temp_dir = temp_dir or gettempdir()
        self._executable = executable
        atexit.register(lambda: _remove_temp_files(self._temp_dir))
        self.timeout = timeout
        if not logger is None:
            self.logger = logger
        else:
            self.logger = get_log()
        #self.logger.setLevel(logging.DEBUG)
        self._session = None
        self._convert_to_float = convert_to_float
        self.restart()

    @property
    def convert_to_float(self):
        return self._convert_to_float

    @convert_to_float.setter
    def convert_to_float(self, value):
        self._writer.convert_to_float = value
        self._convert_to_float = value

    def __enter__(self):
        """Return Scilab object, restart session if necessary"""
        if not self._session:
            self.restart()
        return self

    def __exit__(self, type, value, traceback):
        """Close session"""
        self.exit()

    def exit(self):
        """Closes this Scilab session and removes temp files
        """
        if self._session:
            self._session.close()
        self._session = None
        try:
            self._writer.remove_file()
            self._reader.remove_file()
        except Scilab2PyError as e:
            self.logger.debug(e)

    def push(self, name, var, verbose=False, timeout=None):
        """
        Put a variable or variables into the Scilab session.

        Parameters
        ----------
        name : str or list
            Name of the variable(s).
        var : object or list
            The value(s) to pass.
        timeout : float
            Time to wait for response from Scilab (per character).

        Examples
        --------
        >>> from scilab2py import Scilab2Py
        >>> sci = Scilab2Py()
        >>> y = [1, 2]
        >>> sci.push('y', y)
        >>> sci.pull('y')
        array([[ 1.,  2.]])
        >>> sci.push(['x', 'y'], ['spam', [1., 2., 3., 4.]])
        >>> sci.pull(['x', 'y'])  # doctest: +SKIP
        [u'spam', array([[ 1.,  2.,  3.,  4.]])]

        Note
        ----
        Integer type arguments will be converted to floating point
        unless `convert_to_float=False`.
        """
        if isinstance(name, (str, unicode)):
            vars_ = [var]
            names = [name]
        else:
            vars_ = var
            names = name

        for name in names:
            if name.startswith('_'):
                raise Scilab2PyError('Invalid name {0}'.format(name))
        _, load_line = self._writer.create_file(vars_, names)
        self.eval(load_line, verbose=verbose, timeout=timeout)

    def pull(self, var, verbose=False, timeout=None):
        """
        Retrieve a value or values from the Scilab session.

        Parameters
        ----------
        var : str or list
            Name of the variable(s) to retrieve.
        timeout : float
            Time to wait for response from Scilab (per character).

        Returns
        -------
        out : object
            Object returned by Scilab.

        Raises:
          Scilab2PyError
            If the variable does not exist in the Scilab session.

        Examples:
          >>> from scilab2py import Scilab2Py
          >>> sci = Scilab2Py()
          >>> y = [1, 2]
          >>> sci.push('y', y)
          >>> sci.pull('y')
          array([[ 1.,  2.]])
          >>> sci.push(['x', 'y'], ['spam', [1, 2, 3, 4]])
          >>> sci.pull(['x', 'y'])  # doctest: +SKIP
          [u'spam', array([[ 1.,  2.,  3.,  4.]])]

        """
        if isinstance(var, (str, unicode)):
            var = [var]
        argout_list, save_line = self._reader.setup(len(var), var)
        data = self.eval(save_line, verbose=verbose, timeout=timeout)
        if isinstance(data, dict) and not isinstance(data, Struct):
            return [data.get(v, None) for v in argout_list]
        else:
            return data

    def eval(self, cmds, verbose=True, timeout=None, log=True,
             plot_dir=None, plot_name='plot', plot_format='png',
             plot_width=620, plot_height=590, return_both=False):
        """
        Perform Scilab command or commands.

        Parameters
        ----------
        cmd : str or list
            Commands(s) to pass directly to Scilab.
        verbose : bool, optional
             Log Scilab output at info level.
        timeout : float
            Time to wait for response from Scilab (per character).
                plot_dir: str, optional
            If specificed, save the session's plot figures to the plot
            directory instead of displaying the plot window.
        plot_name : str, optional
            Saved plots will start with `plot_name` and
            end with "_%%.xxx' where %% is the plot number and
            xxx is the `plot_format`.
        plot_format: str, optional
            The format in which to save the plot (PNG by default).
        plot_width: int, optional
            The plot with in pixels.
        plot_height: int, optional
            The plot height in pixels.
        return_both : bool, optional
            If True, return an (printed output, value) tuple. If "ans =" is in the printed output,
            the printed output will have that portion removed.

        Returns
        -------
        out : str
            Results printed by Scilab.

        Raises
        ------
        Scilab2PyError
            If the command(s) fail.

        """
        if not self._session:
            raise Scilab2PyError('No Scilab Session')

        if isinstance(cmds, (str, unicode)):
            cmds = [cmds]

        if verbose and log:
            [self.logger.info(line) for line in cmds]

        elif log:
            [self.logger.debug(line) for line in cmds]

        if timeout is None:
            timeout = self.timeout

        pre_call = ''
        post_call = ''

        pre_call += '''
        h = gdf();
         h.figure_position = [0, 0];
         h.figure_size = [%(plot_width)s,%(plot_height)s];
         h.axes_size = [%(plot_width)s * 0.98, %(plot_height)s * 0.8];
        ''' % locals()

        if not plot_dir is None:
            plot_dir = plot_dir.replace("\\", "/")

            spec = '%(plot_dir)s/%(plot_name)s*.%(plot_format)s' % locals()
            existing = glob.glob(spec)
            plot_offset = len(existing)

            pre_call += '''
                close all;
                function handle_all_fig()
                   ids_array=winsid();
                   for i=1:length(ids_array)
                      id=ids_array(i);
                      outfile = sprintf('%(plot_dir)s/__ipy_sci_fig_%%03d', i + %(plot_offset)s);
                      if '%(plot_format)s' == 'jpg' then
                        xs2jpg(id, outfile + '.jpg');
                      elseif '%(plot_format)s' == 'jpeg' then
                        xs2jpg(id, outfile + '.jpeg');
                      elseif '%(plot_format)s' == 'png' then
                        xs2png(id, outfile);
                      else
                        xs2svg(id, outfile);
                      end
                      close(get_figure_handle(id));
                   end
                endfunction
                ''' % locals()

            post_call += 'handle_all_fig();'

        try:
            resp = self._session.evaluate(cmds, verbose, log, self.logger,
                                          timeout=timeout, pre_call=pre_call,
                                          post_call=post_call)
        except KeyboardInterrupt:
            self.restart()
            raise Scilab2PyError('Session Interrupted, Restarting')

        outfile = self._reader.out_file

        data = None
        if os.path.exists(outfile) and os.stat(outfile).st_size:
            try:
                data = self._reader.extract_file()
            except (TypeError, IOError) as e:
                self.logger.debug(e)

        resp = resp.strip()

        if resp:
            if verbose:
                print(resp)
            self.logger.info(resp)

        if return_both:
            return resp, data
        else:
            return data

    def restart(self):
        """Restart an Scilab session in a clean state
        """
        if self._session:
            self._session.close()
        self._reader = MatRead(self._temp_dir)
        self._writer = MatWrite(self._temp_dir, self._oned_as,
                                self._convert_to_float)
        self._session = _Session(self._executable,
                                 self._reader.out_file, self.logger)

    # --------------------------------------------------------------
    # Private API
    # --------------------------------------------------------------

    def _make_scilab_command(self, name, doc=None):
        """Create a wrapper to an Scilab procedure or object

        Adapted from the mlabwrap project

        """
        def scilab_command(*args, **kwargs):
            """ Scilab command """
            kwargs['nout'] = get_nout()
            if name == 'getd':
                kwargs['nout'] = 0
            kwargs['verbose'] = kwargs.get('verbose', False)
            return self._call(name, *args, **kwargs)

        # convert to ascii for pydoc
        try:
            doc = doc.encode('ascii', 'replace').decode('ascii')
        except UnicodeDecodeError as e:
            self.logger.debug(e)

        scilab_command.__doc__ = "\n" + doc
        scilab_command.__name__ = name

        return scilab_command

    def _call(self, func, *inputs, **kwargs):
        """
        Scilab2Py Parameters
        ----------
        inputs : array_like
            Variables to pass to the function.
        nout : int, optional
            Number of output arguments.
            This is set automatically based on the number of
            return values requested.
            You can override this behavior by passing a
            different value.
        verbose : bool, optional
             Log Scilab output at info level.
                plot_dir: str, optional
            If specificed, save the session's plot figures to the plot
            directory instead of displaying the plot window.
        plot_name : str, optional
            Saved plots will start with `plot_name` and
            end with "_%%.xxx' where %% is the plot number and
            xxx is the `plot_format`.
        plot_format: str, optional
            The format in which to save the plot (PNG by default).
        kwargs : dictionary, optional
            Key - value pairs to be passed as prop - value inputs to the
            function.  The values must be strings or numbers.

        Returns
        -------
        out : value
            Value returned by the function.

        Raises
        ------
        Scilab2PyError
            If the function call is unsucessful.

        Notes
        -----
        Integer type arguments will be converted to floating point
        unless `convert_to_float=False`.
        """
        nout = kwargs.pop('nout', get_nout())

        argout_list = ['ans']
        if '=' in func:
            nout = 0

        # these three lines will form the commands sent to Scilab
        # load("-v6", "infile", "invar1", ...)
        # [a, b, c] = foo(A, B, C)
        # save("-v6", "outfile", "outvar1", ...)
        load_line = call_line = save_line = ''

        prop_vals = []
        eval_kwargs = {}
        for (key, value) in kwargs.items():
            if key in ['verbose', 'timeout'] or key.startswith('plot_'):
                eval_kwargs[key] = value
                continue
            if isinstance(value, (str, unicode, int, float)):
                prop_vals.append('"%s", %s' % (key, repr(value)))
            else:
                msg = 'Keyword arguments must be a string or number: '
                msg += '%s = %s' % (key, value)
                raise Scilab2PyError(msg)
        prop_vals = ', '.join(prop_vals)

        if nout:
            # create a dummy list of var names ("a", "b", "c", ...)
            # use ascii char codes so we can increment
            argout_list, save_line = self._reader.setup(nout)
            call_line = '[{0}] = '.format(', '.join(argout_list))

        call_line += func + '('

        if inputs:
            argin_list, load_line = self._writer.create_file(inputs)
            call_line += ', '.join(argin_list)

        if prop_vals:
            if inputs:
                call_line += ', '
            call_line += prop_vals

        call_line += ');'

        # create the command and execute in octave
        cmd = [load_line, call_line, save_line]
        data = self.eval(cmd, **eval_kwargs)

        if isinstance(data, dict) and not isinstance(data, Struct):
            data = [data.get(v, None) for v in argout_list]
            if len(data) == 1 and data[0] is None:
                data = None

        return data

    def _get_doc(self, name):
        """
        Get the documentation of an Scilab procedure or object.

        Parameters
        ----------
        name : str
            Function name to search for.

        Returns
        -------
        out : str
          Documentation string.

        Raises
        ------
        Scilab2PyError
           If the procedure or object does not exist.

        """
        doc = "No documentation available for `%s`" % name

        try:
            typeof = self.eval('typeof(%s)' % name, verbose=False)

        except Scilab2PyError as e:
            raise Scilab2PyError('Could not find function named `%s`' % name)

        if typeof == 'fptr':
            doc = "`%s` is a built-in Scilab function." % name

        elif typeof == 'function':

            lines = self.eval('fun2string(%s)' % name, verbose=False)

            if lines and '!' in lines:
                lines = lines[lines.index('!'):]
                lines = lines.replace('!', ' ').splitlines()

                docs = [lines[0].replace('ans(', '%s(' % name), ' ']

                in_doc = False
                for line in lines[1:]:
                    line = line.strip()

                    if line.startswith('//'):
                        docs.append(line[2:])
                        in_doc = True

                    elif in_doc and line:
                        break

                doc = '\n'.join(docs)

        default = self._call.__doc__
        doc += '\n' + '\n'.join([line[8:] for line in default.splitlines()])

        return doc

    def __getattr__(self, attr):
        """Automatically creates a wapper to an Scilab function or object.

        Adapted from the mlabwrap project.

        """
        # needed for help(Scilab2Py())
        if attr == '__file__':
            return __file__
        if attr.startswith('__'):
            return super(Scilab2Py, self).__getattr__(attr)
        # close_ -> close
        if attr[-1] == "_":
            name = attr[:-1]
        else:
            name = attr
        doc = self._get_doc(name)
        scilab_command = self._make_scilab_command(name, doc)
        #!!! attr, *not* name, because we might have python keyword name!
        setattr(self, attr, scilab_command)
        return scilab_command


class _Reader(object):

    """Read characters from an Scilab session in a thread.
    """

    def __init__(self, fid, queue):
        self.fid = fid
        self.queue = queue
        self.thread = threading.Thread(target=self.read_incoming)
        self.thread.setDaemon(True)
        self.thread.start()

    def read_incoming(self):
        """"Read text a chunk at a time, parsing into lines
        and putting them in the queue.
        If there is a line with only a ">" char, put that on the queue
        """
        buf = ''
        while 1:
            try:
                buf += os.read(self.fid, 1024).decode('utf8', 'replace')
            except:
                self.queue.put(None)
                return
            lines = buf.splitlines()
            for line in lines[:-1]:
                self.queue.put(line)
            if buf.endswith('\n'):
                self.queue.put(lines[-1])
                buf = ''
            else:
                buf = lines[-1]


class _Session(object):

    """Low-level session Scilab session interaction.
    """

    def __init__(self, executable, outfile, logger):
        self.timeout = int(1e6)
        self.read_queue = queue.Queue()
        self.proc = self.start(executable)
        self._first = True
        self.stdout = sys.stdout
        self.outfile = outfile
        self.set_timeout()
        self.logger = logger
        atexit.register(self.close)

    def start(self, executable):
        """
        Start an Scilab session in a subprocess.

        Parameters
        ==========
        executable : str
            Name or path to Scilab process.

        Returns
        =======
        out : fid
            File descriptor for the Scilab subprocess

        Raises
        ======
        Scilab2PyError
            If the session is not opened sucessfully.

        Notes
        =====
        Options sent to Scilab: -q is quiet startup, --braindead is
        Matlab compatibilty mode.

        """
        errmsg = ('\n\nScilab not found.  Please see documentation at:\n'
                  'http://blink1073.github.io/scilab2py/source/installation.html')
        ON_POSIX = 'posix' in sys.builtin_module_names
        self.rfid, wpipe = os.pipe()
        rpipe, self.wfid = os.pipe()
        kwargs = dict(close_fds=ON_POSIX, bufsize=0, stdin=rpipe,
                      stderr=wpipe, stdout=wpipe)

        if os.name == 'nt':
            CREATE_NO_WINDOW = 0x08000000  # Windows-specific
            flags = subprocess.CREATE_NEW_PROCESS_GROUP + CREATE_NO_WINDOW
            kwargs['creationflags'] = flags

            if not executable:
                executable = 'Scilex'

        elif not executable:
            executable = 'scilab'

        try:
            proc = subprocess.Popen([executable, '-nw'],
                                    **kwargs)
        except OSError:  # pragma: no cover
            raise Scilab2PyError(errmsg)
        else:
            self.reader = _Reader(self.rfid, self.read_queue)
            return proc

    def set_timeout(self, timeout=None):
        if timeout is None:
            timeout = int(1e6)
        self.timeout = timeout

    def evaluate(self, cmds, verbose=True, log=True, logger=None, timeout=None,
                 pre_call='', post_call=''):
        """Perform the low-level interaction with an Scilab Session
        """

        self.logger = logger

        if not timeout is None:
            self.set_timeout(timeout)

        if not self.proc:
            raise Scilab2PyError('Session Closed, try a restart()')

        if self._first:
            self.write("""
                try
                  getd(".");
                catch
                end
                """)

        if os.path.exists(self.outfile):
            try:
                os.remove(self.outfile)
            except OSError as e:
                self.logger.debug(e)

        outfile = self.outfile

        # use ascii code 2 for start of text, 3 for end of text, and
        # 24 to signal an error
        expr = '\n'.join(cmds)

        # scilab cannot handle "#" commented lines
        # try and remove them
        expr = re.sub(r'(?:\A|\n)\s*#', '//', expr)

        # use ascii code 2 for start of text, 3 for end of text, and
        # 24 to signal an error
        output = """
        %(pre_call)s

        clear("ans");
        clear("a__");
        clear("_ans");

        try
            disp(char(2));
            %(expr)s
            if exists("ans") == 1 then
               _ans = ans;
            end
        catch
            disp(lasterror());
            disp(char(24));
        end


        if exists("_ans") == 1
            if type(_ans) == 4 then
                   _ans = double(_ans)
            end
            if or(type(_ans) == [1,2,3,5,6,7,8,10]) then
                    if exists("a__") == 0 then
                        try
                            savematfile -v6 %(outfile)s _ans;
                        catch
                            disp(_ans)
                        end
                    end
                elseif type(_ans)
                    disp(_ans);
                end
        end

        %(post_call)s

        disp(char(3))
        """ % locals()

        if len(cmds) == 5:
            main_line = cmds[2].strip()
        else:
            main_line = '\n'.join(cmds)

        self.logger.debug(output)

        self.write(output + '\n')

        if self._first:
            self.expect(chr(2))
        else:
            self.expect(chr(2), timeout=1)
        self._first = False

        debug_prompt = ("Type 'resume' or 'abort' to return to "
                        "standard level prompt.")

        resp = []
        while 1:
            line = self.readline()

            if chr(3) in line:
                break

            elif chr(24) in line:
                msg = ('Scilab2Py tried to run:\n"""\n{0}\n"""\n'
                       'Scilab returned:\n{1}'
                       .format(main_line, '\n'.join(resp)))
                raise Scilab2PyError(msg)

            elif line.strip() == debug_prompt:
                self.interact('-1->')

            if verbose and logger:
                logger.info(line)

            elif log and logger:
                logger.debug(line)

            if resp or line.strip():
                resp.append(line)

        return '\n'.join(resp).rstrip()

    def interrupt(self):
        if not os.name == 'nt':
            self.proc.send_signal(signal.SIGINT)

    def expect(self, strings, timeout=None):
        """Look for a string or strings in the incoming data"""
        if not isinstance(strings, list):
            strings = [strings]
        lines = []
        while 1:
            line = self.readline(timeout)
            lines.append(line)
            if line:
                for string in strings:
                    if re.search(string, line):
                        return '\n'.join(lines)

    def readline(self, timeout=None):
        t0 = time.time()
        if timeout is None:
            timeout = self.timeout
        while 1:
            try:
                val = self.read_queue.get_nowait()
            except queue.Empty:
                pass
            else:
                if val is None:
                    self.close()
                    return
                elif val.strip():
                    return val
            time.sleep(1e-6)
            if (time.time() - t0) > timeout:
                self.interrupt()
                raise Scilab2PyError('Timed out')

    def write(self, message):
        """Write a message to the process using utf-8 encoding"""
        os.write(self.wfid, message.encode('utf-8'))

    def interact(self, prompt='- 1->'):
        """Manage an Scilab Debug Prompt interaction"""
        msg = 'Entering Scilab Debug Prompt...\n%s' % prompt
        self.stdout.write(msg)
        while 1:
            inp_func = input if not PY2 else raw_input
            try:
                inp = inp_func()
            except EOFError:
                return
            if inp in ['exit', 'quit', 'resume', 'abort',
                       'exit()', 'quit()']:
                inp = 'resume'
            msg = 'disp(char(2));' + inp + '\ndisp(char(3))\n'
            self.write(msg)
            if inp == 'resume':
                self.write('resume\n')
                self.write('clear _\n')
                return
            self.expect(chr(2))
            output = self.expect(chr(3))
            output = output[:output.index(chr(3))].rstrip()
            self.stdout.write(output + '\n\n')
            self.stdout.write(prompt)

    def close(self):
        """Cleanly close a Scilab session
        """
        try:
            self.write('\nexit\n')
        except Exception as e:  # pragma: no cover
            self.logger.debug(e)

        if self.proc is None:
            return

        try:
            self.proc.terminate()
        except Exception as e:  # pragma: no cover
            self.logger.debug(e)

        self.proc = None

    def __del__(self):
        try:
            self.close()
        except:
            pass
