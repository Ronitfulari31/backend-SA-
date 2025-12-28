import os
import sys
import logging

# Set up logging to see the ARGOS specific logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Cache redirection
D_CACHE_BASE = r"D:\Projects\Backend(SA)_cache"
ARGOS_CACHE = os.path.join(D_CACHE_BASE, "argos_cache")
os.environ["ARGOS_PACKAGES_DIR"] = ARGOS_CACHE

# Import service
from app.services.translation import translation_service

def test_hindi_fallback():
    print("\n--- Testing Hindi Translation (Argos Fallback) ---")
    text = "भारत एक महान देश है।" # India is a great country.
    
    # We want to force Argos fallback. Since GoogleTranslator is live, 
    # we can temporarily break it or just call the internal _translate_with_argos directly 
    # to verify it works without erroring.
    
    print(f"Original Text: {text}")
    
    # Verify the internal method works first
    print("\nStep 1: Testing internal _translate_with_argos...")
    result_internal = translation_service._translate_with_argos(text, "hi", "en")
    print(f"Argos Internal Result: {result_internal}")
    
    if result_internal and "India" in result_internal:
        print("✅ Internal Argos translation successful.")
    else:
        print("❌ Internal Argos translation failed or returned unexpected result.")

    # Now test the high-level method (Google might catch it first, which is fine, 
    # but the NoneType error happened inside translate_to_english when fallback triggered)
    print("\nStep 2: Testing high-level translate_to_english...")
    result_high = translation_service.translate_to_english(text, "hi")
    print(f"High-level Result: {result_high['translated_text']}")
    print(f"Engine used: {result_high['translation_engine']}")
    print(f"Success: {result_high['success']}")
    
    if result_high['success']:
        print("✅ High-level translation call successful.")
    else:
        print("❌ High-level translation call failed.")

if __name__ == "__main__":
    test_hindi_fallback()
