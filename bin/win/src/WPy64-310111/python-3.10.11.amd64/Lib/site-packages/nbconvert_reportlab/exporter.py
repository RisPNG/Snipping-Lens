"""Helps you output colourised code snippets in ReportLab documents.

Platypus has an 'XPreformatted' flowable for handling preformatted
text, with variations in fonts and colors.   If Pygments is installed,
calling 'pygments2xpre' will return content suitable for display in
an XPreformatted object.  If it's not installed, you won't get colours.

"""
from binascii import a2b_base64
import io

from traitlets import default
from nbconvert.exporters import Exporter
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, XPreformatted, Image
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pygments2xpre import pygments2xpre

from .rlmarkdown import md_to_flowables

def add_in_prompt(text, prompt_no):
    """Add the In [1]: prompts to a block of code."""
    if prompt_no is None:
        prompt = 'In [ ]: '
    else:
        prompt = 'In [%d]: ' % prompt_no

    margin = ' ' * len(prompt)
    colour_prompt = '<span color="#000080">%s</span>' % prompt
    lines = text.splitlines(keepends=True)
    return colour_prompt + margin.join(lines)

class NbPdfConverter:
    def __init__(self, nb, resources):
        self.nb = nb
        self.resources = resources
        self.stylesheet = getSampleStyleSheet()
        self.stylesheet["Code"].leftIndent = 12
        self.pieces = []

    def convert_markdown_cell(self, cell):
        self.pieces.extend(md_to_flowables(cell.source, self.stylesheet))

    def convert_code_cell(self, cell):
        code = pygments2xpre(cell.source).rstrip()
        code = add_in_prompt(code, cell.execution_count)
        self.pieces.append(XPreformatted(code, style=self.stylesheet['Code']))

        if cell.outputs:
            self.pieces.append(Spacer(1, 6))
        
        for output in cell.outputs:
            self.convert_output(output)

    def convert_output(self, output):
        if output.output_type == 'stream':
            self.add_plain_text(''.join(output.text))
        elif output.output_type in {'display_data', 'execute_result'}:
            self.add_mimebundle(output.data, output.metadata)

    def add_plain_text(self, text):
        self.pieces.append(XPreformatted(text, style=self.stylesheet['Code']))

    def add_mimebundle(self, data, metadata=None):
        if 'image/png' in data:
            img_data = a2b_base64(data['image/png'])
            self.pieces.append(Image(io.BytesIO(img_data),
                                     height=25, width=25, kind='%'))
        elif 'text/plain' in data:
            self.add_plain_text(data['text/plain'])

    def go(self):
        for cell in self.nb.cells:
            if cell.cell_type == 'code':
                self.convert_code_cell(cell)
            elif cell.cell_type == 'markdown':
                self.convert_markdown_cell(cell)
            self.pieces.append(Spacer(1, 12))

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer)
        doc.build(self.pieces)
        return buffer.getvalue()

class ReportlabExporter(Exporter):
    """Convert a notebook to PDF using Reportlab

    This is the API which nbconvert calls.
    """
    output_mimetype = 'application/pdf'

    @default('file_extension')
    def _file_extension_default(self):
        return '.pdf'

    def from_notebook_node(self, nb, resources=None, **kw):
        nb_copy, resources = super().from_notebook_node(nb, resources)

        output = NbPdfConverter(nb_copy,  resources).go()
        return output, resources

