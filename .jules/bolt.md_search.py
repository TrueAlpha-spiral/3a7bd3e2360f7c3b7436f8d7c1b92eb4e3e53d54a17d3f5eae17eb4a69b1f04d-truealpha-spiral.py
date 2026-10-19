with open(".jules/bolt.md", "r") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "inline" in line.lower() or "inlining" in line.lower():
        print(f"Line {i}: {line.strip()}")
