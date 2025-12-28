import os
import argostranslate.translate

# Cache redirection
D_CACHE_BASE = r"D:\Projects\Backend(SA)_cache"
ARGOS_CACHE = os.path.join(D_CACHE_BASE, "argos_cache")
os.environ["ARGOS_PACKAGES_DIR"] = ARGOS_CACHE

def check_all_languages():
    langs = argostranslate.translate.get_installed_languages()
    installed_codes = {l.code for l in langs}
    
    project_langs = {
        'en': 'English', 'hi': 'Hindi', 'es': 'Spanish', 'fr': 'French', 
        'ar': 'Arabic', 'zh': 'Chinese', 'ja': 'Japanese', 'ko': 'Korean', 
        'pt': 'Portuguese', 'ru': 'Russian', 'de': 'German', 'it': 'Italian', 
        'tr': 'Turkish', 'vi': 'Vietnamese', 'id': 'Indonesian', 'th': 'Thai', 
        'pl': 'Polish', 'nl': 'Dutch', 'bn': 'Bengali', 'ur': 'Urdu', 
        'ta': 'Tamil', 'te': 'Telugu', 'mr': 'Marathi'
    }
    
    print("\n--- Argos Offline Support Check ---")
    print(f"Total installed models in Argos: {len(installed_codes)}")
    
    supported = []
    unsupported = []
    
    for code, name in project_langs.items():
        if code in installed_codes:
            # Check if there is a translation path to 'en'
            from_lang = next(l for l in langs if l.code == code)
            to_lang = next((l for l in langs if l.code == 'en'), None)
            
            if to_lang and from_lang.get_translation(to_lang):
                supported.append(f"{name} ({code})")
            else:
                unsupported.append(f"{name} ({code}) - No path to EN")
        else:
            unsupported.append(f"{name} ({code}) - Model not installed")
            
    print("\n✅ Supported Offline (Argos):")
    for s in supported:
        print(f" - {s}")
        
    print("\n❌ NOT Supported Offline (Requires Google):")
    for u in unsupported:
        print(f" - {u}")

if __name__ == "__main__":
    check_all_languages()
