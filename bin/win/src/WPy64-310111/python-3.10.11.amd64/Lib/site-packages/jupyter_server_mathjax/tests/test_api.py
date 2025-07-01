# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

"""Basic tests for the notebook handlers.
"""

import pytest
from tornado.httpclient import HTTPClientError
from jupyter_server.utils import url_path_join as ujoin


async def test_mathjax_mainjs_handler(jp_fetch):
    r = await jp_fetch("static", "jupyter_server_mathjax", "MathJax.js")
    assert r.code == 200


async def test_mathjax_conf_handler(jp_fetch):
    r = await jp_fetch(
        "static", "jupyter_server_mathjax", "config", "TeX-AMS-MML_HTMLorMML-full.js"
    )
    assert r.code == 200

    r = await jp_fetch("static", "jupyter_server_mathjax", "config", "Safe.js")
    assert r.code == 200


@pytest.mark.parametrize(
    "asset_file",
    ["MathJax.js", "config/TeX-AMS-MML_HTMLorMML-full.js", "config/Safe.js"],
)
async def test_redirects_from_classic_notebook_endpoints(
    jp_fetch, jp_base_url, asset_file
):
    old_prefix = ujoin("static", "components", "MathJax")
    new_prefix = ujoin("static", "jupyter_server_mathjax")

    # Verify that the redirect is in place
    with pytest.raises(HTTPClientError) as error_info, pytest.deprecated_call(
        match="Redirecting old Notebook MathJax URL .*"
    ):
        await jp_fetch(old_prefix, asset_file, follow_redirects=False)

    err = error_info.value
    assert err.code == 301
    assert err.response.headers["Location"] == ujoin(
        jp_base_url, new_prefix, asset_file
    )
