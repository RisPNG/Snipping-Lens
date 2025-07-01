# coding: utf-8
"""A lab app that runs a sub process for a demo or a test."""
import sys

from tornado.ioloop import IOLoop
from traitlets import Bool

from .server import ServerApp
from .handlers import add_handlers, LabConfig
from .process import Process


class ProcessApp(ServerApp):
    """A notebook app that runs a separate process and exits on completion."""

    open_browser = Bool(False)

    lab_config = LabConfig()

    def get_command(self):
        """Get the command and kwargs to run with `Process`.
        This is intended to be overridden.
        """
        return ['python', '--version'], dict()

    def start(self):
        """Start the application.
        """
        add_handlers(self.web_app, self.lab_config)
        IOLoop.current().add_callback(self._run_command)
        ServerApp.start(self)

    def _run_command(self):
        command, kwargs = self.get_command()
        kwargs.setdefault('logger', self.log)
        future = Process(command, **kwargs).wait_async()
        IOLoop.current().add_future(future, self._process_finished)

    def _process_finished(self, future):
        try:
            IOLoop.current().stop()
            sys.exit(future.result())
        except Exception as e:
            self.log.error(str(e))
            sys.exit(1)
