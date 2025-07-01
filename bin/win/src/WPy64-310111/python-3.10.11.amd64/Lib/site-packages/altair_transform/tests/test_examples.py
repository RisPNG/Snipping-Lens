import os
import re

import pytest


@pytest.fixture
def readme():
    possible_paths = [
        # Path within built distributions:
        os.path.join(os.path.dirname(__file__), "README.md"),
        # Path within source tree:
        os.path.join(os.path.dirname(__file__), "..", "..", "README.md"),
    ]

    for path in possible_paths:
        if os.path.exists(path):
            with open(path) as f:
                return f.read()

    raise ValueError("README file not found.")


def test_readme_snippets(readme):
    """Tests the code snippets from the package README."""
    regex = re.compile("```python\n(.*?)\n```", re.MULTILINE | re.DOTALL)

    codeblocks = regex.findall(readme)
    assert len(codeblocks) > 0

    namespace = {}
    for codeblock in codeblocks:
        exec(codeblock, namespace)
