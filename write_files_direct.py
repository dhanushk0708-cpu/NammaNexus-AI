import os, base64
def write(rel, b64):
    p = os.path.join("C:/Users/dhanu/OneDrive/Desktop/NammaNexus-AI/frontend", rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(base64.b64decode(b64).decode("utf-8"))
    print("Wrote", rel)
