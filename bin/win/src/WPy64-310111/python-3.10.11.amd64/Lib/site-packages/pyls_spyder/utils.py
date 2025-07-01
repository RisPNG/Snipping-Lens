# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright (c) Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)
# ----------------------------------------------------------------------------

"""pyls-spyder misc utillites."""

# Standard library imports
from typing import Tuple, Dict


class RegexEvaluator:
    """Wrapper class around multiple regular expressions."""

    def __init__(self, regex_map: Dict):
        self.regexes = regex_map

    def match(self, string: str) -> Tuple:
        """
        Match a string `string` against a set of regular expressions.

        The regular expressions are applied in a short-circuit fashion.

        Parameters
        ----------
        string: str
            Input string to match regexes against.

        Returns
        -------
        output: Tuple[Optional[str], Optional[re.Match]]
            A tuple containing the regex identifier that first matched the
            input, alongside the corresponding regex match object. If no regex
            did matched the input, then a tuple containing `None` is returned.
        """
        re_match = None
        re_rule = None
        for regex_name in self.regexes:
            regex = self.regexes[regex_name]
            re_match = regex.match(string)
            if re_match is not None:
                re_rule = regex_name
                break
        return re_rule, re_match
