import pytest

from altair_transform.utils import evaljs, parser
from ._testcases import extract
from ._testcases import EXPRESSIONS, JSONLY_EXPRESSIONS, NAMES


@pytest.fixture
def names():
    return NAMES


@pytest.mark.parametrize("expression", extract(EXPRESSIONS))
def test_expressions(expression, names):
    assert eval(expression, names) == evaljs(expression, names)


@pytest.mark.parametrize("expression,output", JSONLY_EXPRESSIONS)
def test_jsonly_expressions(expression, output, names):
    assert evaljs(expression, names) == output


def test_string_vs_ast():
    expression = "2 * (3 + 4)"
    parsed = parser.parse(expression)
    assert evaljs(expression) == evaljs(parsed)
