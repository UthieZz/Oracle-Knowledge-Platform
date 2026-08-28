import os
import json

output_dir = "output"
platforms = {}

# Replicating load_workspace discovery
platforms_dir = os.path.join(output_dir, "Platforms")
if os.path.exists(platforms_dir):
    for platform_name in os.listdir(platforms_dir):
        plat_dir = os.path.join(platforms_dir, platform_name)
        if os.path.isdir(plat_dir):
            plat_manifest_path = os.path.join(plat_dir, "manifest.json")
            if os.path.exists(plat_manifest_path):
                with open(plat_manifest_path, "r", encoding="utf-8") as f:
                    platforms[platform_name] = json.load(f)
                    platforms[platform_name]["path"] = plat_dir

print(f"Found platforms: {list(platforms.keys())}")

knowledge_objects = 0
for p in platforms:
    plat_dir = platforms[p]["path"]
    ko_dir = os.path.join(plat_dir, "knowledge_objects")
    print(f"Checking {ko_dir}")
    if os.path.exists(ko_dir):
        files = [f for f in os.listdir(ko_dir) if f.endswith(".md")]
        print(f"  Found files: {files}")
        knowledge_objects += len(files)
    else:
        print("  Dir does not exist")
        
print(f"Total knowledge objects: {knowledge_objects}")
