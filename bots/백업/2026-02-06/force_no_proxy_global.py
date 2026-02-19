import os
import glob

# This script injects the proxy disable code at the top of ALL bot files
# to ensure both `requests` and `selenium` (via env vars) ignore proxies.

target_dir = r"c:\gemini\fishing_bot\bots\더피싱"
files = glob.glob(os.path.join(target_dir, "*.py"))

injection_code = """import os
# 🚀 [Speed Optimization] Force Disable Proxy
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''
os.environ['NO_PROXY'] = '*'
"""

count = 0
for file_path in files:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "Force Disable Proxy" in content:
        continue
        
    # Insert after import lines
    lines = content.splitlines()
    insert_idx = 0
    for i, line in enumerate(lines):
        if line.startswith("import ") or line.startswith("from "):
            insert_idx = i + 1
        elif insert_idx > 0 and line.strip() == "":
            break
            
    # Insert safely
    new_content = "\n".join(lines[:insert_idx]) + "\n" + injection_code + "\n" + "\n".join(lines[insert_idx:])
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    count += 1
    print(f"Patched: {os.path.basename(file_path)}")

print(f"Total files patched: {count}")
