import os
import json
import urllib.request
import sys

def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

ASSETS_DIR = resource_path("assets")
UI_DIR = os.path.join(ASSETS_DIR, "UI")
DATA_DIR = resource_path("data")
WIKI_BASE_URL = "https://dragonwilds.runescape.wiki/images/"

def get_wiki_filename(item_name):
    """Convert item name to wiki filename format - just replace spaces with underscores"""
    return item_name.replace(" ", "_") + ".png"

NAME_OVERRIDES = {
    "Naphtha": "Naptha",
    "Marentill Seeds": "Marrentil_Seeds",
    "Cadaveberry Infusion": "Cadavaberry_Infusion",
    "Grilled Tomatoes": "Tomato",
    "Beef & Tomato Stew": "Meat_Stew",
    "Burnt Tomato": "Burnt_Flank",
}

def get_name_variants(item_name):
    """Generate possible wiki name variants for an item"""
    # Check for explicit overrides first
    if item_name in NAME_OVERRIDES:
        return [NAME_OVERRIDES[item_name]]
    
    variants = [item_name]
    
    # Try plural/singular variants
    if item_name.endswith("s"):
        variants.append(item_name[:-1])  # Remove 's'
    else:
        variants.append(item_name + "s")  # Add 's'
    
    # Handle specific patterns
    if " Bolt" in item_name:
        variants.append(item_name.replace(" Bolt", " Bolts"))
    if " Bolts" in item_name:
        variants.append(item_name.replace(" Bolts", " Bolt"))
    
    return variants

def download_icon(item_name, icon_filename):
    """Download icon from wiki and save to assets/UI folder"""
    output_path = os.path.join(UI_DIR, icon_filename)
    
    if os.path.exists(output_path):
        return True, None
    
    variants = get_name_variants(item_name)
    last_error = None
    
    for variant in variants:
        wiki_filename = get_wiki_filename(variant)
        url = f"{WIKI_BASE_URL}{urllib.request.quote(wiki_filename, safe='-_')}"
        
        try:
            with urllib.request.urlopen(url, timeout=15) as response:
                image_data = response.read()
            
            os.makedirs(UI_DIR, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(image_data)
            
            return True, None
        except Exception as e:
            last_error = f"{url} - {e}"
    
    return False, last_error

def main():
    path = os.path.join(DATA_DIR, "ItemID.txt")
    if not os.path.exists(path):
        print(f"ItemID.txt not found in {DATA_DIR}")
        return
    
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    os.makedirs(UI_DIR, exist_ok=True)
    
    success_count = 0
    fail_count = 0
    skip_count = 0
    
    for entry in data:
        name = entry.get("SourceString", "").strip()
        icon_file = entry.get("IconFile", "")
        
        if not name or not icon_file:
            continue
        
        output_path = os.path.join(UI_DIR, icon_file)
        if os.path.exists(output_path):
            skip_count += 1
            continue
        
        success, error = download_icon(name, icon_file)
        
        if success:
            print(f"Downloaded: {name}")
            success_count += 1
        else:
            print(f"FAILED: {name}")
            print(f"  {error}")
            fail_count += 1
    
    print(f"\nDone! Downloaded: {success_count}, Failed: {fail_count}, Skipped (existing): {skip_count}")

if __name__ == "__main__":
    main()
