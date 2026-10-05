import sys
import os
import base64

if len(sys.argv) < 3:
    print("Usage: write_frontend_file.py <rel_path> <b64_content>")
    sys.exit(1)

rel_path = sys.argv[1]
b64_content = sys.argv[2]
content = base64.b64decode(b64_content).decode('utf-8')

frontend_dir = "c:/Users/dhanu/OneDrive/Desktop/NammaNexus-AI/frontend"
target_path = os.path.join(frontend_dir, rel_path)
os.makedirs(os.path.dirname(target_path), exist_ok=True)
with open(target_path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Successfully wrote {rel_path}")
