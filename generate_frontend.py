import os

frontend_dir = r'C:\Users\dhanu\OneDrive\DesktopBNammaNexus-AI\frontend'

def write_file(rel_path, content):
    full_path = os.path.join(frontend_dir, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'Wrote {rel_path}')
