import os
import argostranslate.package
import argostranslate.translate

# Cache redirection (CRITICAL for D: drive models)
D_CACHE_BASE = r"D:\Projects\Backend(SA)_cache"
ARGOS_CACHE = os.path.join(D_CACHE_BASE, "argos_cache")
os.environ["ARGOS_PACKAGES_DIR"] = ARGOS_CACHE

def list_languages():
    langs = argostranslate.translate.get_installed_languages()
    print("\nInstalled Argos Languages:")
    for l in langs:
        print(f" - code={l.code}, name={l.name}")
    return langs

def test_hi_to_en():
    langs = list_languages()

    from_lang = next((l for l in langs if l.code == "hi"), None)
    to_lang = next((l for l in langs if l.code == "en"), None)

    print("\nResolution:")
    print("from_lang:", from_lang)
    print("to_lang:", to_lang)

    if not from_lang or not to_lang:
        print("❌ Language resolution failed")
        return

    try:
        translation = from_lang.get_translation(to_lang)
        if not translation:
            print("❌ get_translation() returned None")
            return

        result = translation.translate("भारत एक लोकतांत्रिक देश है।")
        print("✅ Translation result:", result)
    except Exception as e:
        print(f"❌ Exception during get_translation/translate: {e}")

if __name__ == "__main__":
    test_hi_to_en()
