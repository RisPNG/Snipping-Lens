# coding: utf-8
"""Jupyter Lab Launcher handlers"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import json
import os

from tornado import web, template
from jinja2 import FileSystemLoader, TemplateError

from traitlets import HasTraits, Bool, Unicode

from .server import JupyterHandler, FileFindHandler, url_path_join as ujoin
from .workspaces_handler import WorkspacesHandler
from .settings_handler import SettingsHandler
from .themes_handler import ThemesHandler

# -----------------------------------------------------------------------------
# Module globals
# -----------------------------------------------------------------------------

# The default urls for the application.
default_public_url = '/lab/static/'
default_workspaces_url = '/lab/workspaces/'
default_workspaces_api_url = '/lab/api/workspaces/'
default_settings_url = '/lab/api/settings/'
default_themes_url = '/lab/api/themes/'
default_tree_url = '/lab/tree/'


DEFAULT_TEMPLATE = template.Template("""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Error</title>
</head>
<body>
<h2>Cannot find template: "{{name}}"</h2>
<p>In "{{path}}"</p>
</body>
</html>
""")


class LabHandler(JupyterHandler):
    """Render the JupyterLab View."""

    def initialize(self, lab_config):
        self.lab_config = lab_config
        self.file_loader = FileSystemLoader(lab_config.templates_dir)

    @web.authenticated
    @web.removeslash
    def get(self):
        config = self.lab_config
        settings_dir = config.app_settings_dir

        # Handle page config data.
        page_config = self.settings.setdefault('page_config_data', {})
        terminals = self.settings.get('terminals_available', False)
        server_root = self.settings.get('server_root_dir', '')
        server_root = server_root.replace(os.sep, '/')
        page_config.setdefault('terminalsAvailable', terminals)
        page_config.setdefault('ignorePlugins', [])
        page_config.setdefault('serverRoot', server_root)

        mathjax_config = self.settings.get('mathjax_config',
                                           'TeX-AMS_HTML-full,Safe')
        page_config.setdefault('mathjaxConfig', mathjax_config)
        page_config.setdefault('mathjaxUrl', self.mathjax_url)

        for name in config.trait_names():
            page_config[_camelCase(name)] = getattr(config, name)

        # Load the current page config file if available.
        page_config_file = os.path.join(settings_dir, 'page_config.json')
        if os.path.exists(page_config_file):
            with open(page_config_file) as fid:
                try:
                    page_config.update(json.load(fid))
                except Exception as e:
                    print(e)

        # Handle error when the assets are not available locally.
        local_index = os.path.join(config.static_dir, 'index.html')
        if config.static_dir and not os.path.exists(local_index):
            self.write(self.render_template(
                'error.html', static_dir=config.static_dir
            ))
            return

        # Write the template with the config.
        self.write(self.render_template('index.html', page_config=page_config))

    def get_template(self, name):
        return self.file_loader.load(self.settings['jinja2_env'], name)

    def render_template(self, name, **ns):
        try:
            return JupyterHandler.render_template(self, name, **ns)
        except TemplateError:
            return DEFAULT_TEMPLATE.generate(
                name=name, path=self.lab_config.templates_dir
            )


class LabConfig(HasTraits):
    """The lab application configuration object.
    """
    app_name = Unicode('', help='The name of the application.')

    app_version = Unicode('', help='The version of the application.')

    app_namespace = Unicode('', help='The namespace of the application.')

    page_url = Unicode('/lab', help='The url path for the application.')

    app_settings_dir = Unicode('', help='The application settings directory.')

    templates_dir = Unicode('', help='The application templates directory.')

    static_dir = Unicode('',
                         help=('The optional location of local static files. '
                               'If given, a static file handler will be '
                               'added.'))

    public_url = Unicode(default_public_url,
                         help=('The url public path for static application '
                               'files. This can be a CDN if desired.'))

    settings_url = Unicode(default_settings_url,
                           help='The url path of the settings handler.')

    user_settings_dir = Unicode('',
                                help=('The optional location of the user '
                                      'settings directory.'))

    schemas_dir = Unicode('',
                          help=('The optional location of the settings '
                                'schemas directory. If given, a handler will '
                                'be added for settings.'))

    workspaces_api_url = Unicode(default_workspaces_api_url,
                                 help='The url path of the workspaces API.')

    workspaces_dir = Unicode('',
                             help=('The optional location of the saved '
                                   'workspaces directory. If given, a handler '
                                   'will be added for workspaces.'))

    workspaces_url = Unicode(default_workspaces_url,
                             help='The url path of the workspaces handler.')

    themes_url = Unicode(default_themes_url, help='The theme url.')

    themes_dir = Unicode('',
                         help=('The optional location of the themes '
                               'directory. If given, a handler will be added '
                               'for themes.'))

    tree_url = Unicode(default_tree_url,
                       help='The url path of the tree handler.')

    cache_files = Bool(True,
                       help=('Whether to cache files on the server. '
                             'This should be `True` except in dev mode.'))


class NotFoundHandler(LabHandler):
    def render_template(self, name, **ns):
        if 'page_config' in ns:
            ns['page_config'] = ns['page_config'].copy()
            ns['page_config']['notFoundUrl'] = self.request.path
        return LabHandler.render_template(self, name, **ns)


def add_handlers(web_app, config):
    """Add the appropriate handlers to the web app.
    """
    # Normalize directories.
    for name in config.trait_names():
        if not name.endswith('_dir'):
            continue
        value = getattr(config, name)
        setattr(config, name, value.replace(os.sep, '/'))

    # Set up the main page handler and tree handler.
    base_url = web_app.settings['base_url']
    lab_path = ujoin(base_url, config.page_url)
    tree_path = ujoin(base_url, config.tree_url, r'.+')
    handlers = [
        (lab_path, LabHandler, {'lab_config': config}),
        (tree_path, LabHandler, {'lab_config': config})
    ]

    # Cache all or none of the files depending on the `cache_files` setting.
    no_cache_paths = [] if config.cache_files else ['/']

    # Handle local static assets.
    if config.static_dir:
        public_path = ujoin(base_url, config.public_url + '(.*)')
        handlers.append((public_path, FileFindHandler, {
            'path': config.static_dir,
            'no_cache_paths': no_cache_paths
        }))

    # Handle local settings.
    if config.schemas_dir:
        settings_path = ujoin(
            base_url,
            config.settings_url + '(?P<section_name>.+)'
        )
        handlers.append((settings_path, SettingsHandler, {
            'app_settings_dir': config.app_settings_dir,
            'schemas_dir': config.schemas_dir,
            'settings_dir': config.user_settings_dir
        }))

    # Handle saved workspaces.
    if config.workspaces_dir:
        # Handle JupyterLab client URLs that include workspaces.
        workspaces_path = ujoin(base_url, config.workspaces_url, r'/.+')
        handlers.append((workspaces_path, LabHandler, {'lab_config': config}))

        # Handle requests for the list of workspaces. Make slash optional.
        workspaces_api_path = ujoin(base_url, config.workspaces_api_url + '?')
        handlers.append((workspaces_api_path, WorkspacesHandler, {
            'workspaces_url': config.workspaces_url,
            'path': config.workspaces_dir
        }))

        # Handle requests for an individually named workspace.
        workspace_api_path = ujoin(
            base_url,
            config.workspaces_api_url + '(?P<space_name>.+)'
        )
        handlers.append((workspace_api_path, WorkspacesHandler, {
            'workspaces_url': config.workspaces_url,
            'path': config.workspaces_dir
        }))

    # Handle local themes.
    if config.themes_dir:
        themes_path = ujoin(base_url, config.themes_url, '(.*)')
        handlers.append((
            themes_path,
            ThemesHandler,
            {
                'themes_url': config.themes_url,
                'path': config.themes_dir,
                'no_cache_paths': no_cache_paths
            }
        ))

    # Let the lab handler act as the fallthrough option instead of a 404.
    fallthrough_url = ujoin(base_url, config.page_url, r'.*')
    handlers.append((fallthrough_url, NotFoundHandler, {'lab_config': config}))

    web_app.add_handlers('.*$', handlers)


def _camelCase(base):
    """Convert a string to camelCase.
    https://stackoverflow.com/a/20744956
    """
    output = ''.join(x for x in base.title() if x.isalpha())
    return output[0].lower() + output[1:]
