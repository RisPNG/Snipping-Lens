"""
Include a PDF like a vector image into another PDF.

Relies on pdfrw

Based on example code provided by Larry Meyn and Patrick Maupin on Stackoverflow
http://stackoverflow.com/a/13870512/434217
http://stackoverflow.com/a/32021013/434217
Content on SO is under the CC BY-SA 3.0 license.
"""

from reportlab.platypus import Flowable

from pdfrw import PdfReader
from pdfrw.buildxobj import pagexobj
from pdfrw.toreportlab import makerl

def form_xo_reader(imgdata):
    page, = PdfReader(imgdata).pages
    return pagexobj(page)

class PdfImage(Flowable):
    """PdfImage wraps the first page from a PDF file as a Flowable
        which can be included into a ReportLab Platypus document.
        Based on the vectorpdf extension in rst2pdf (http://code.google.com/p/rst2pdf/)"""

    def __init__(self, filename_or_object, width=None, height=None,
                 kind='direct'):
        super().__init__()
        # If using BytesIO buffer, set pointer to begining
        if hasattr(filename_or_object, 'read'):
            filename_or_object.seek(0)
        page = PdfReader(filename_or_object, decompress=False).pages[0]
        self.xobj = pagexobj(page)
        self.imageWidth = width
        self.imageHeight = height
        x1, y1, x2, y2 = self.xobj.BBox

        self._w, self._h = x2 - x1, y2 - y1
        if not self.imageWidth:
            self.imageWidth = self._w
        if not self.imageHeight:
            self.imageHeight = self._h
        self.__ratio = float(self.imageWidth) / self.imageHeight
        if kind in ['direct', 'absolute'] or width is None or height is None:
            self.drawWidth = width or self.imageWidth
            self.drawHeight = height or self.imageHeight
        elif kind in ['bound', 'proportional']:
            factor = min(float(width) / self._w, float(height) / self._h)
            self.drawWidth = self._w * factor
            self.drawHeight = self._h * factor

    def wrap(self, aW, aH):
        return self.drawWidth, self.drawHeight

    def drawOn(self, canv, x, y, _sW=0):
        x = self._hAlignAdjust(x, _sW)

        xobj = self.xobj
        xobj_name = makerl(canv._doc, xobj)

        xscale = self.drawWidth / self._w
        yscale = self.drawHeight / self._h

        x -= xobj.BBox[0] * xscale
        y -= xobj.BBox[1] * yscale

        canv.saveState()
        canv.translate(x, y)
        canv.scale(xscale, yscale)
        canv.doForm(xobj_name)
        canv.restoreState()

