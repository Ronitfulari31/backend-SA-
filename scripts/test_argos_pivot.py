
import os
import sys

# Cache redirection
D_CACHE_BASE = r"D:\Projects\Backend(SA)_cache"
os.environ["ARGOS_PACKAGES_DIR"] = os.path.join(D_CACHE_BASE, "argos_cache", "packages")

try:
    import argostranslate.package
    import argostranslate.translate
except ImportError:
    print(f"Argos not installed in: {sys.executable}")
    print(f"Path: {sys.path}")
    sys.exit(1)

def test_pivot():
    # Hindi Text: "Hello" -> "नमस्ते"
    # We want to translate generic Hindi to Arabic via English
    # Hindi -> "Hello" (En) -> "مرحبا" (Ar)
    
    source_text = "नमस्ते"
    from_code = "hi"
    to_code = "ar"
    
    print(f"Testing Pivot: {from_code} -> {to_code}")
    
    try:
        # Get installed languages
        installed_langs = argostranslate.translate.get_installed_languages()
        
        from_lang = next((l for l in installed_langs if l.code == from_code), None)
        to_lang = next((l for l in installed_langs if l.code == to_code), None)
        
        if not from_lang or not to_lang:
            print("Missing languages")
            return

        print(f"Source: {from_lang.name}")
        print(f"Target: {to_lang.name}")

        # Check direct translation
        translation = from_lang.get_translation(to_lang)
        
        if translation:
            print("✅ Direct/Pivot translation found object")
            result = translation.translate(source_text)
            print(f"Result: {result}")
        else:
            print("❌ No translation object returned by get_translation()")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_pivot()
