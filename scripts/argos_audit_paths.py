import os
import sys

# Set environment before import
D_CACHE_BASE = r"D:\Projects\Backend(SA)_cache"
argos_cache = os.path.join(D_CACHE_BASE, "argos_cache", "packages")
os.environ["ARGOS_PACKAGES_DIR"] = argos_cache

try:
    import argostranslate.translate
    import argostranslate.package

    print("--- Argos Translate Audit ---")
    print(f"Cache Path: {os.environ.get('ARGOS_PACKAGES_DIR')}")
    
    langs = argostranslate.translate.get_installed_languages()
    print(f"Installed Languages: {[l.code for l in langs]}")
    print("-" * 30)

    for from_lang in langs:
        targets = []
        for to_lang in langs:
            if from_lang == to_lang:
                continue
            translation = from_lang.get_translation(to_lang)
            if translation:
                targets.append(to_lang.code)
        
        if targets:
            print(f"{from_lang.code} -> {', '.join(targets)}")
        else:
            print(f"{from_lang.code} -> (No outgoing paths)")

    print("-" * 30)
    print("Audit Complete.")

except Exception as e:
    print(f"Error: {e}")
