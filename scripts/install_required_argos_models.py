import os
from pathlib import Path
from argostranslate import package

# ===============================
# Cache redirection (same as app)
# ===============================
D_CACHE_BASE = r"D:\Projects\Backend(SA)_cache"
ARGOS_CACHE = os.path.join(D_CACHE_BASE, "argos_cache")
TEMP_DIR = os.path.join(D_CACHE_BASE, "temp")

os.makedirs(ARGOS_CACHE, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

os.environ["ARGOS_PACKAGES_DIR"] = ARGOS_CACHE
os.environ["TEMP"] = TEMP_DIR
os.environ["TMP"] = TEMP_DIR

# ===============================
# REQUIRED LANGUAGES (FINAL SET)
# ===============================
REQUIRED_SOURCE_LANGS = {
    # ✅ Already installed
    "ar",  # Arabic – Middle East
    "fr",  # French – Europe
    "hi",  # Hindi – India

    # ➕ Lightweight global coverage
    "es",  # Spanish – Americas
    "nl",  # Dutch – Europe (small)
    # "id",  # Indonesian – Asia (small)
    "sw",  # Swahili – Africa (small)
}

TARGET_LANG = "en"

print("🔄 Updating Argos package index...")
package.update_package_index()

available_packages = package.get_available_packages()
installed_packages = package.get_installed_packages()

installed_pairs = {(p.from_code, p.to_code) for p in installed_packages}

installed = 0
skipped = 0
failed = 0

for pkg in available_packages:
    if pkg.to_code != TARGET_LANG:
        continue

    if pkg.from_code not in REQUIRED_SOURCE_LANGS:
        continue

    key = (pkg.from_code, pkg.to_code)

    if key in installed_pairs:
        print(f"✔ Already installed: {pkg.from_code} → en")
        skipped += 1
        continue

    try:
        print(f"⬇ Downloading {pkg.from_code} → en")
        path = Path(pkg.download())

        if path.suffix != ".argosmodel":
            print(f"⚠ Invalid model skipped: {pkg.from_code} → en")
            failed += 1
            continue

        print(f"📦 Installing {pkg.from_code} → en")
        package.install_from_path(str(path))
        installed += 1

    except Exception as e:
        print(f"❌ Failed {pkg.from_code} → en: {e}")
        failed += 1

print("\n================ SUMMARY ================")
print(f"Installed: {installed}")
print(f"Skipped:   {skipped}")
print(f"Failed:    {failed}")
print("========================================")
