import matplotlib 
from string import Formatter

class StrMethodTickFormatterConvertor(object):

    STRING_FORMAT_D3 = "d3-format"

    SUPPORTED_OUTPUT_FORMATS = (
        STRING_FORMAT_D3, 
    )

    def __init__(self, formatter, output_format=STRING_FORMAT_D3): 
        assert output_format in self.SUPPORTED_OUTPUT_FORMATS, "Unknown output_format" 
        if not isinstance(formatter, matplotlib.ticker.StrMethodFormatter):
            raise ValueError("Formatter must be of type `matplotlib.ticker.StrMethodFormatter`")
        self.formatter = formatter 
        self.output_format = output_format

    @property
    def is_output_d3(self):
        return self.output_format == self.STRING_FORMAT_D3 

    def export_mpl_format_str_d3(self, mpl_format_str):
        prefixes = []
        suffixes = []
        before_x = True
        format_spec_for_d3 = "" 
        for literal_text, field_name, format_spec, conversion in Formatter().parse(mpl_format_str): 
            if before_x:
                prefixes.append(literal_text)
            else:
                suffixes.append(literal_text)

            if field_name == "x" and format_spec and format_spec_for_d3 and self.is_output_d3:
                raise ValueError("D3 doesn't support multiple conversions")
                
            if field_name == "x":
                before_x = False
                format_spec_for_d3 = format_spec  

        prefix = "".join(prefixes)
        suffix = "".join(suffixes)
        return {
            "format_string": format_spec_for_d3,
            "prefix": prefix,
            "suffix": suffix
        }

    @property
    def output(self):
        # just incase we want to support something other than d3
        if self.is_output_d3:
            return self.export_mpl_format_str_d3(self.formatter.fmt)
