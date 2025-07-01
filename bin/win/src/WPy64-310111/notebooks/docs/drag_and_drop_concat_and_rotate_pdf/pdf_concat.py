
# derived from https://github.com/pmaupin/pdfrw/blob/master/examples/cat.py


import sys
import os

from pdfrw import PdfReader, PdfWriter, IndirectPdfDict

# remove the .py program from the list of input parameters, just in case
preinputs = [str(i)  for i in  sys.argv[1:]  if str(i)[-3:].lower() != ".py"]

# we sort the parameters per alphabetical order, ignoring upper/lower case
inputs = sorted(preinputs, key=str.lower)

print("zz**zz", inputs, "\n")
assert inputs

# output is from the first document in paremeter
outfn = 'cat.' + os.path.basename(inputs[0])
outfn = os.path.join(os.path.dirname(inputs[0]), outfn)
if outfn[-3:]!="pdf":
    outfn = outfn +'.pdf'

writer = PdfWriter()

# record the name of files added, in the order they are added
filenames = []

# loop through parameters
for inpfn in inputs:
    # a file !
    if inpfn[-3:]=="pdf":
       writer.addpages(PdfReader(inpfn).pages)
       filenames += [os.path.basename(inpfn)] 
    elif os.path.isdir(inpfn):
       # a directory ! 
       #   ... so we sort the directory per alphabetical order, ignoring upper/lower case
       for filename in sorted(os.listdir(inpfn), key=str.lower):
           inpfn2 = os.path.join(inpfn, filename)
           if inpfn2[-3:]=="pdf":
              writer.addpages(PdfReader(inpfn2).pages)
              filenames += [os.path.basename(inpfn2)] 


writer.trailer.Info = IndirectPdfDict(
    Title='My AweSome Teacher',
    Author='My AweSome Teacher',
    Subject='what is it all about?',
    Creator='some script goes here',
	Keywords = ', '.join(filenames)
)
writer.write(outfn)