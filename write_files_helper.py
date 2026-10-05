import os

base = r"C:\Users\dhanu\OneDrive\Desktop\NammaNexus-AI\frontend"

def write(path, txt):
    p = os.path.join(base, path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(txt)
    print("Wrote", path)
