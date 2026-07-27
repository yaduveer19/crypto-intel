import requests, os, sys

zip_path = r"C:\Users\nishant yadav\OneDrive\Desktop\CryptoIntel.zip"
print(f"Uploading {os.path.getsize(zip_path) / 1e6:.1f} MB...")

# Try file.io
try:
    with open(zip_path, "rb") as f:
        r = requests.post("https://file.io", files={"file": f}, timeout=120)
    data = r.json()
    if data.get("success"):
        print(f"Download link: {data['link']}")
        print("This link will self-destruct after 1 download.")
        sys.exit(0)
except Exception as e:
    print(f"file.io: {e}")

# Try temp.sh
try:
    with open(zip_path, "rb") as f:
        r = requests.put("https://temp.sh/upload", data=f, timeout=120)
    if r.status_code == 200:
        print(f"Download link: {r.text.strip()}")
        sys.exit(0)
except Exception as e:
    print(f"temp.sh: {e}")

print("All upload services failed. Your network may be restricted.")
print("Alternative: Tell friend to download from your PC directly.")
