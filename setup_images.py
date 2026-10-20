"""
Downloads anime character images into data/images/.
Run once: python setup_images.py
"""
import urllib.request
import json
from pathlib import Path

IMAGES_DIR = Path(__file__).parent / "data" / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Wikipedia REST API thumbnails — stable and free to use
CHARACTERS = {
    "goku.png":     "Goku",
    "levi.png":     "Levi_Ackerman",
    "spike.png":    "Spike_Spiegel",
    "itachi.png":   "Itachi_Uchiha",
    "yoriichi.png": "Yoriichi_Tsugikuni",
}

def get_wikipedia_image(page: str):
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{page}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "job-alert-agent/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            thumb = data.get("thumbnail", {}).get("source", "")
            # Get higher-res version
            return thumb.replace("/320px-", "/600px-") if thumb else None
    except Exception as e:
        print(f"  Wikipedia API failed for {page}: {e}")
        return None

def download(url: str, dest: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            dest.write_bytes(r.read())
        return True
    except Exception as e:
        print(f"  Download failed: {e}")
        return False

if __name__ == "__main__":
    print("Downloading anime character images...\n")
    for filename, wiki_page in CHARACTERS.items():
        dest = IMAGES_DIR / filename
        if dest.exists():
            print(f"✅ {filename} already exists, skipping")
            continue
        print(f"📥 {filename} ({wiki_page})...")
        img_url = get_wikipedia_image(wiki_page)
        if img_url and download(img_url, dest):
            size_kb = dest.stat().st_size // 1024
            print(f"   ✅ Saved ({size_kb}KB)")
        else:
            print(f"   ❌ Failed — manually save an image to data/images/{filename}")
    print(f"\nDone! Images in: {IMAGES_DIR}")
