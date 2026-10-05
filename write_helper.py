import sys, os
path = sys.argv[1]
content = sys.stdin.read()
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print(f"Wrote {path}")