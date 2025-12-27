import os
import sys
from pathlib import Path

# Redirection as in the main app
D_CACHE_BASE = r"D:\Projects\Backend(SA)_cache"
ARGOS_CACHE = os.path.join(D_CACHE_BASE, "argos_cache")
TEMP_DIR = os.path.join(D_CACHE_BASE, "temp")

os.environ["ARGOS_PACKAGES_DIR"] = ARGOS_CACHE
os.environ["TEMP"] = TEMP_DIR
os.environ["TMP"] = TEMP_DIR

import argostranslate.settings

print(f"ARGOS_PACKAGES_DIR from env: {os.environ.get('ARGOS_PACKAGES_DIR')}")
print(f"ARGOS_PACKAGES_DIR from settings: {argostranslate.settings.packages_dir}")
print(f"ARGOS_CACHE_DIR from settings: {getattr(argostranslate.settings, 'cache_dir', 'N/A')}")
print(f"ARGOS_DATA_DIR from settings: {getattr(argostranslate.settings, 'data_dir', 'N/A')}")
print(f"ARGOS_CONFIG_DIR from settings: {getattr(argostranslate.settings, 'config_dir', 'N/A')}")

# List all variables in settings
print("\nAll settings:")
for attr in dir(argostranslate.settings):
    if not attr.startswith("__"):
        print(f"{attr}: {getattr(argostranslate.settings, attr)}")
