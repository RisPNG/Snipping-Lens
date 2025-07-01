# coding: utf-8

import tinycss2

import qstylizer.style


def parse(stylesheet):
    """Parse a stylesheet using tinycss2 and return a StyleSheet instance.

    :param stylesheet: A string of an existing stylesheet.

    """
    parsed_stylesheet = tinycss2.parse_stylesheet(
        stylesheet, skip_comments=True, skip_whitespace=True
    )
    css = qstylizer.style.StyleSheet()
    for node in parsed_stylesheet:
        if node.type == "error":
            raise ValueError("Cannot parse Stylesheet: " + node.message)
        selector = tinycss2.serialize(node.prelude).strip()
        declaration_list = tinycss2.parse_declaration_list(
            node.content, skip_comments=True, skip_whitespace=True
        )
        for declaration in declaration_list:
            if declaration.type == "declaration":
                prop = declaration.name.strip()
                css[selector][prop] = tinycss2.serialize(declaration.value).strip()
    return css
