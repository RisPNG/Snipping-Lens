This tiny directory is to:
- help student and teacher to merge several pdf pages in one document
- using drag & drop way-of-life

Check your Python distribution has "pdfrw" package
https://github.com/pmaupin/pdfrw
https://pypi.org/project/pdfrw/

set the initialisation of your environment in pdf_envcall.bat
rem example with WinPython, 

TO COMPACT a set of PDF in a directory
- Drop you pdfs, or you directory containing the pfs over pdf_concat.bat
- the pdf are sorted in alphabetic order, 
- this order is seen in pdf properties "keywords"
- the merged pdf is placed:
   . at the root of this directory,
   . with first pdf directory name and prefix "cat."

TO ROTATE one PDF:
- Drop the Pdf file over the pdf_rotate_one_90.bat  to turn it 90°
- the compacted pdf is placed:
   . at the same directory as the file,
   . with directory name and prefix "rot."

REMARK:
- you can Drop over a "shortcut" ("Raccourci") version of the .bat  (placing it where it is most practical)
 