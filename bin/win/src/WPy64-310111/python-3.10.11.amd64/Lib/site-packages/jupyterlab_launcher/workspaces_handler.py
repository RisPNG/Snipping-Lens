"""Tornado handlers for frontend config storage."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import hashlib
import json
import os
import re
import unicodedata
import urllib
from tornado import web

from .server import APIHandler, json_errors, url_path_join as ujoin


# A cache of workspace names and their slug file name counterparts.
_cache = dict()

# The JupyterLab workspace file extension.
_file_extension = '.jupyterlab-workspace'


def _list_workspaces(directory, prefix):
    workspaces = []
    if not os.path.exists(directory):
        return workspaces

    items = [item
             for item in os.listdir(directory)
             if item.startswith(prefix) and
             item.endswith(_file_extension)]
    items.sort()

    for slug in items:
        if slug in _cache:
            workspaces.append(_cache[slug])
            continue
        workspace_path = os.path.join(directory, slug)
        if os.path.exists(workspace_path):
            with open(workspace_path) as fid:
                try:  # to load and parse the workspace file.
                    _cache[slug] = json.load(fid)['metadata']['id']
                    workspaces.append(_cache[slug])
                except Exception as e:
                    raise web.HTTPError(500, str(e))
    return workspaces


def _slug(raw, base, sign=True, max_length=128 - len(_file_extension)):
    """
    Use the common superset of raw and base values to build a slug shorter
    than max_length.
    Convert spaces to hyphens. Remove characters that aren't alphanumerics
    underscores, or hyphens. Convert to lowercase. Strip leading and trailing
    whitespace.
    Add an optional short signature suffix to prevent collisions.
    Modified from Django utils:
    https://github.com/django/django/blob/master/django/utils/text.py
    """
    signature = ''
    if sign:
        signature = '-' + hashlib.sha256(raw.encode('utf-8')).hexdigest()[:4]
    base = (base if base.startswith('/') else '/' + base).lower()
    raw = (raw if raw.startswith('/') else '/' + raw).lower()
    common = 0
    limit = min(len(base), len(raw))
    while common < limit and base[common] == raw[common]:
        common += 1
    value = ujoin(base[common:], raw)
    value = urllib.parse.unquote(value)
    value = (unicodedata
             .normalize('NFKC', value)
             .encode('ascii', 'ignore')
             .decode('ascii'))
    value = re.sub(r'[^\w\s-]', '', value).strip()
    value = re.sub(r'[-\s]+', '-', value)
    return value[:max_length - len(signature)] + signature


class WorkspacesHandler(APIHandler):

    def initialize(self, path, workspaces_url=None):
        self.workspaces_dir = path

    def ensure_directory(self):
        """Return the workspaces directory if set or raise error if not set."""
        if not self.workspaces_dir:
            raise web.HTTPError(500, 'Workspaces directory is not set')

        return self.workspaces_dir

    @json_errors
    @web.authenticated
    def delete(self, space_name):
        base_url = self.base_url
        directory = self.ensure_directory()

        if not space_name:
            raise web.HTTPError(400, 'Workspace name is required for DELETE')

        slug = _slug(space_name, base_url)
        workspace_path = os.path.join(directory, slug + _file_extension)

        if not os.path.exists(workspace_path):
            raise web.HTTPError(404, 'Workspace %r (%r) not found' %
                                     (space_name, slug))

        try:  # to delete the workspace file.
            os.remove(workspace_path)
            return self.set_status(204)
        except Exception as e:
            raise web.HTTPError(500, str(e))

    @json_errors
    @web.authenticated
    def get(self, space_name=''):
        base_url = self.base_url
        directory = self.ensure_directory()

        if not space_name:
            prefix = _slug('', base_url, sign=False)
            workspaces = _list_workspaces(directory, prefix)
            return self.finish(json.dumps(dict(workspaces=workspaces)))

        slug = _slug(space_name, base_url)
        workspace_path = os.path.join(directory, slug + _file_extension)

        if os.path.exists(workspace_path):
            with open(workspace_path) as fid:
                try:  # to load and parse the workspace file.
                    return self.finish(json.dumps(json.load(fid)))
                except Exception as e:
                    raise web.HTTPError(500, str(e))
        else:
            raise web.HTTPError(404, 'Workspace %r (%r) not found' %
                                     (space_name, slug))

    @json_errors
    @web.authenticated
    def put(self, space_name):
        base_url = self.base_url
        directory = self.ensure_directory()

        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
            except Exception as e:
                raise web.HTTPError(500, str(e))

        raw = self.request.body.strip().decode(u'utf-8')
        workspace = dict()

        # Make sure the data is valid JSON.
        try:
            decoder = json.JSONDecoder()
            workspace = decoder.decode(raw)
        except Exception as e:
            raise web.HTTPError(400, str(e))

        # Make sure metadata ID matches the workspace name.
        # Transparently support an optional inital root `/`.
        metadata_id = workspace['metadata']['id']
        metadata_id = (metadata_id if metadata_id.startswith('/')
                       else '/' + metadata_id)
        if metadata_id != '/' + space_name:
            message = ('Workspace metadata ID mismatch: expected %r got %r'
                       % (space_name, metadata_id))
            raise web.HTTPError(400, message)

        slug = _slug(space_name, base_url)
        workspace_path = os.path.join(directory, slug + _file_extension)

        # Write the workspace data to a file.
        with open(workspace_path, 'w') as fid:
            fid.write(raw)

        self.set_status(204)
