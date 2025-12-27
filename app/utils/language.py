def decide_second_language(article_language: str):
    """
    Determines if a second language is needed for the response.
    Returns the language code if it's not English or unknown, else None.
    """
    if not article_language:
        return None

    article_language = article_language.lower()

    if article_language in ("en", "unknown"):
        return None

    return article_language

def translate_analysis_additive(analysis_en, target_lang, translator):
    """
    Translates English analysis into the target language.
    Does not modify the original English analysis.
    """
    translated = {}

    # SUMMARY
    if "summary" in analysis_en:
        # Check if summary is a dict or string
        summary_val = analysis_en["summary"]
        if isinstance(summary_val, dict) and "text" in summary_val:
            translated["summary"] = {
                **summary_val,
                "text": translator.translate_text(summary_val["text"], target_lang)
            }
        elif isinstance(summary_val, str):
            translated["summary"] = translator.translate_text(summary_val, target_lang)

    # KEYWORDS
    if "keywords" in analysis_en:
        translated["keywords"] = [
            translator.translate_text(k, target_lang)
            for k in analysis_en["keywords"]
        ]

    # ENTITIES
    if "entities" in analysis_en:
        translated["entities"] = []
        for ent in analysis_en["entities"]:
            translated["entities"].append({
                "label": ent.get("label"),  # DO NOT TRANSLATE LABEL (e.g. PERSON, GPE)
                "text": translator.translate_text(ent.get("text", ""), target_lang)
            })

    # LOCATION
    if "location" in analysis_en:
        loc_data = analysis_en["location"]
        if isinstance(loc_data, dict):
            translated["location"] = {}
            for k, v in loc_data.items():
                translated["location"][k] = (
                    translator.translate_text(v, target_lang)
                    if isinstance(v, str) else v
                )
        else:
            translated["location"] = loc_data

    # SENTIMENT
    if "sentiment" in analysis_en:
        sent = analysis_en["sentiment"]
        translated["sentiment"] = {
            "label": translator.translate_text(sent.get("label", "neutral"), target_lang),
            "confidence": sent.get("confidence", 0.0),
            "method": sent.get("method", "fallback")
        }
        if "scores" in sent:
            translated["sentiment"]["scores"] = sent["scores"]

    return translated

def get_or_create_translated_analysis(
    doc,
    analysis_en,
    target_lang,
    translator_service,
    collection,
    logger=None
):
    """
    Read-through cache for translated analysis.
    Checks MongoDB first, translates if missing, and then stores back to Mongo.
    """
    # 1️⃣ Cache hit
    cached = doc.get("analysis_translated", {}).get(target_lang)
    if cached:
        if logger:
            logger.info(f"Using cached translation for {doc['_id']} [{target_lang}]")
        return cached

    # 2️⃣ Cache miss → translate
    if logger:
        logger.info(f"Creating translation for {doc['_id']} [{target_lang}]")
        
    translated = translate_analysis_additive(
        analysis_en,
        target_lang,
        translator_service
    )

    # 3️⃣ Store in Mongo (additive set)
    collection.update_one(
        {"_id": doc["_id"]},
        {"$set": {f"analysis_translated.{target_lang}": translated}}
    )

    return translated
