from jupyter_events.logger import EventLogger
from jupyter_server.extension.application import ExtensionApp
from traitlets import Type

from jupyter_server_fileid.manager import ArbitraryFileIdManager, BaseFileIdManager


class FileIdExtension(ExtensionApp):
    name = "jupyter_server_fileid"

    file_id_manager_class = Type(
        klass=BaseFileIdManager,
        help="""File ID manager instance to use.

        Defaults to ArbitraryFileIdManager.
        """,
        config=True,
        default_value=ArbitraryFileIdManager,
    )

    def initialize_settings(self):
        self.log.info(f"Configured File ID manager: {self.file_id_manager_class.__name__}")
        file_id_manager = self.file_id_manager_class(
            log=self.log, root_dir=self.serverapp.root_dir, config=self.config
        )
        self.settings.update({"file_id_manager": file_id_manager})

        # attach listener to contents manager events (requires jupyter_server~=2)
        if "event_logger" in self.settings:
            self.initialize_event_listeners()

    def initialize_event_listeners(self):
        file_id_manager = self.settings["file_id_manager"]
        handlers_by_action = file_id_manager.get_handlers_by_action()

        async def cm_listener(logger: EventLogger, schema_id: str, data: dict) -> None:
            handler = handlers_by_action[data["action"]]
            if handler:
                handler(data)

        self.settings["event_logger"].add_listener(
            schema_id="https://events.jupyter.org/jupyter_server/contents_service/v1",
            listener=cm_listener,
        )
        self.log.info("Attached event listeners.")
