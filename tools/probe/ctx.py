"""Print JS context around given substrings. Usage: ctx.py [-b N] [-a N] needle..."""
import glob, os, sys

base = os.path.dirname(__file__)
src = open(os.path.join(base, "index.js")).read()
for f in sorted(glob.glob(os.path.join(base, "chunks", "*.js"))):
    src += "\n" + open(f).read()
args = sys.argv[1:]
before, after, maxhits = 250, 350, 1
while args and args[0] in ("-b", "-a", "-n"):
    v = int(args[1])
    before, after, maxhits = (v, after, maxhits) if args[0] == "-b" else (before, v, maxhits) if args[0] == "-a" else (before, after, v)
    args = args[2:]
for n in args:
    print(f"=== {n}")
    i, hits = 0, 0
    while hits < maxhits:
        i = src.find(n, i)
        if i < 0:
            break
        print(src[max(0, i - before):i + after].replace("\n", " "))
        print("---")
        i += len(n)
        hits += 1
