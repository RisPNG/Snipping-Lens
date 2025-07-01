import os
from jinja2 import Environment

env = Environment()
basename = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_FILE = f"{basename}/app2.template.py"

with open(TEMPLATE_FILE, "r") as fid:
    tpl = env.from_string(fid.read())

context = dict(name="test")


outfile = TEMPLATE_FILE.replace(".template", "")
with open(outfile, "w") as fid:
    fid.write(tpl.render(**context))
print(f"Successfully wrote {outfile}")
