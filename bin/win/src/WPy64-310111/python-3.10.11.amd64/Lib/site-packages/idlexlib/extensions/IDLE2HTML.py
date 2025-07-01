# IDLEX EXTENSION
##    """
##     IDLE2HTML - IDLE extension
##     saves the contents of the editwindow (file or shell)
##     to a html file using css styles
##
##     creator:        d2m <michael@d2m.at>
##     0.1/2006-07-22: initial revision
##     0.2/2007-06-14: added styles for BODY
##                         thanks to Tal Einat who pointed out a problem
##                         with non Black-on-White color schemes
##                     removed Selection highlightning
##                     added ERROR highlightning
##
##     todo:           check for valid css color values
##                     use elementtree for html generation
##                     enable Selection highlightning
##
##    PSF LICENSE AGREEMENT FOR PYTHON 2.7.2
##
##    1. This LICENSE AGREEMENT is between the Python Software Foundation ("PSF"), and 
##    the Individual or Organization ("Licensee") accessing and otherwise using Python 2.7.2
##    software in source or binary form and its associated documentation.
##    2. Subject to the terms and conditions of this License Agreement, PSF hereby grants
##    Licensee a nonexclusive, royalty-free, world-wide license to reproduce, analyze, test,
##    perform and/or display publicly, prepare derivative works, distribute, and otherwise use
##    Python 2.7.2 alone or in any derivative version, provided, however, that PSF's License
##    Agreement and PSF's notice of copyright, i.e., "Copyright (C) 2001-2010 Python Software
##    Foundation; All Rights Reserved" are retained in Python 2.7.2 alone or in any derivative
##    version prepared by Licensee.
##    3. In the event Licensee prepares a derivative work that is based on or incorporates
##    Python 2.7.2 or any part thereof, and wants to make the derivative work available to
##    others as provided herein, then Licensee hereby agrees to include in any such work a brief
##    summary of the changes made to Python 2.7.2.
##    4. PSF is making Python 2.7.2 available to Licensee on an "AS IS" basis. PSF MAKES NO
##    REPRESENTATIONS OR WARRANTIES, EXPRESS OR IMPLIED. BY WAY OF EXAMPLE, BUT NOT LIMITATION,
##    PSF MAKES NO AND DISCLAIMS ANY REPRESENTATION OR WARRANTY OF MERCHANTABILITY OR FITNESS
##    FOR ANY PARTICULAR PURPOSE OR THAT THE USE OF PYTHON 2.7.2 WILL NOT INFRINGE ANY THIRD
##    PARTY RIGHTS.
##    5. PSF SHALL NOT BE LIABLE TO LICENSEE OR ANY OTHER USERS OF PYTHON 2.7.2 FOR ANY
##    INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES OR LOSS AS A RESULT OF MODIFYING,
##    DISTRIBUTING, OR OTHERWISE USING PYTHON 2.7.2, OR ANY DERIVATIVE THEREOF, EVEN IF ADVISED
##    OF THE POSSIBILITY THEREOF.
##    6. This License Agreement will automatically terminate upon a material breach of its terms
##    and conditions.
##    7. Nothing in this License Agreement shall be deemed to create any relationship of agency,
##    partnership, or joint venture between PSF and Licensee. This License Agreement does not
##    grant permission to use PSF trademarks or trade name in a trademark sense to endorse or
##    promote products or services of Licensee, or any third party.
##    8. By copying, installing or otherwise using Python 2.7.2, Licensee agrees to be bound by
##    the terms and conditions of this License Agreement.
##
##
##
##     License: Python Software Foundation License
##     
##     Modified to work with idlex by Roger D. Serwy
##     October 2011
##
##     Some minor bug fixes and feature enhancements: 
##        - Check if user clicked "Cancel" on saveas dialog.
##        - Save to .html by default instead of .htm  (a relic from 8.3 filename days)
##        - Save dialog has a proper title
##        - Modified to work with Python 3
##
##    """

config_extension_def = """
[IDLE2HTML]
enable=1

[IDLE2HTML_cfgBindings]
idle2html=

"""

__version__ = '0.2'

import sys

if sys.version < '3':
        import Tkinter
        import tkFileDialog
else:
        import tkinter as Tkinter
        import tkinter.filedialog as tkFileDialog

import html

class IDLE2HTML(object):
    menudefs=[('options',[('Export to HTML', '<<idle2html>>')])]

    def __init__(self,editwin):
        self.editwin=editwin
        self.text=editwin.text
            
    def idle2html_event(self, event=None):
        filetypes = [
            ("All HTML files", "*.html *.htm", "TEXT"),
            ("All files", "*"),
            ]
        filename=tkFileDialog.SaveAs(master=self.text,
                                     filetypes=filetypes,
                                     title="Export to HTML",
                                     ).show()
        if filename:
            f=open(filename,'w')
            f.write(self.idle2html())
            f.close()
        
    def idle2html(self):
        """format tags 2 html
        """
        out=['<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" \
"http://www.w3.org/TR/2002/REC-xhtml1-20020801/DTD/xhtml1-transitional.dtd">\n']
        out.append('<html>\n<head>\n<title>IDLE2HTML</title>\n')
        out.append('<meta name="generator" content="IDLE2HTML - IDLE extension (%s)" />\n' % __version__)
        out.append('<style type="text/css">\n')
        out.append('%s {color: %s; background-color: %s;}\n' % (
                       'BODY',
                       self.text.cget('foreground'),
                       self.text.cget('background'),
                       )
                    )
        for tagname in self.text.tag_names():
            fg=self.text.tag_cget(tagname,'foreground')
            bg=self.text.tag_cget(tagname,'background')
            if fg and bg and tagname.lower() != 'sel':
                out.append('.%s {color: %s; background-color: %s;}\n' % (
                                tagname,
                                fg,
                                bg,
                                )
                            )
        out.append('</style>\n')
        out.append('</head>\n<body>\n<pre>')
        inside_error=0
        for tagname,content,dummy in self.text.dump('1.0',self.text.index('end')):
            if tagname=='tagon' and not (content.upper() in ('SYNC','TODO','SEL')):
                if not inside_error:
                    out.append('<span class="%s">' % content)
                if content.upper() == 'ERROR':
                    inside_error=1
            if tagname=='text':
                out.append(html.escape(content))
            if tagname=='tagoff' and not (content.upper() in ('SYNC','TODO','SEL')):
                if content.upper() == 'ERROR':
                    inside_error=0
                if not inside_error:
                    out.append('</span>')
        out.append('</pre>\n</body>\n</html>')
        return ''.join(out)

