import os
for k, v in os.environ.items():
    if "KEY" in k.upper() or "API" in k.upper() or "SECRET" in k.upper():
        print(f"{k}: {v[:5]}... ({len(v)} chars)")
