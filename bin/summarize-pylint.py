# pylint: disable=all
from sys import argv
from json import loads
from io import StringIO
from typing import NamedTuple

buffer = StringIO()

class Entry(NamedTuple):
    type: str
    symbol: str
    message: str
    messageId: str
    confidence: str
    module: str
    obj: str
    line: int
    column: int
    endLine: int
    endColumn: int
    path: str
    absolutePath: str

if not len(argv) > 1:
    print("Requiring pylint json output!")

with open(argv[1]) as outfile:
    data = loads(outfile.read())

def write_source(entry: Entry):
    with open(entry.path) as fstream:
        dt = [a.rstrip() for a in fstream.readlines()]
    if entry.line == entry.endLine:
        selected = dt[entry.line]
    else:
        selected = dt[entry.line-1:entry.endLine+1]
    buffer.write(f"""\
[{entry.module}] {entry.message} ({entry.symbol})
{''.join(selected)}\n\n""")

stats = data["statistics"]
msg_types = stats["messageTypeCount"]
msgs = data["messages"]

buffer.write(f"""\
[pylint] Summary
Score  = {stats['score']}
Linted = {stats['modulesLinted']}
---
Fatal      = {msg_types['fatal']}
Error      = {msg_types['error']}
Warning    = {msg_types['warning']}
Refactor   = {msg_types['refactor']}
Convention = {msg_types['convention']}
Info       = {msg_types['info']}

{' Records ':-^20}
""")

for i in data["messages"]:
    write_source(Entry(**i))

buffer.write('-'*20)

with open("records/pylint.txt", "w") as record:
    record.write(buffer.getvalue())

print(f"[pylint] Project score is {data['statistics']['score']}. See the report in records/pylint.txt")
