import pytest

from altair_transform.utils import ast, Parser
from ._testcases import extract
from ._testcases import EXPRESSIONS, BAD_EXPRESSIONS, JSONLY_EXPRESSIONS


@pytest.fixture
def parser():
    return Parser()


@pytest.mark.parametrize("bad_expression", extract(BAD_EXPRESSIONS))
def test_bad_expressions(bad_expression, parser):
    with pytest.raises(ValueError):
        parser.parse(bad_expression)


@pytest.mark.parametrize("expression", extract(EXPRESSIONS))
def test_expressions(expression, parser):
    output = parser.parse(expression)
    assert isinstance(output, ast.Node)


@pytest.mark.parametrize("expression,output", JSONLY_EXPRESSIONS)
def test_jsonly_expressions(expression, output, parser):
    output = parser.parse(expression)
    assert isinstance(output, ast.Node)
