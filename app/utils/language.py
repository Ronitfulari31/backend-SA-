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

def translate_analysis_additive(analysis_en, target_lang, translator, original_doc=None):
    """
    Translates English analysis into the target language using batching for high performance.
    If original_doc is provided and its language matches target_lang, we use the original
    summary instead of re-translating from English for 100% accuracy.
    """
    if not analysis_en:
        return {}

    # 0. Optimization set to False for now because pipeline currently
    # produces English summaries for all articles.
    use_original_summary = False

    # 1. Collect all translatable strings
    strings_to_translate = []
    
    # Map to track where strings come from
    mapping = [] # List of (type, key/index, subkey/index)

    # Summary
    summary_val = analysis_en.get("summary")
    if not use_original_summary:
        if isinstance(summary_val, dict) and "text" in summary_val:
            strings_to_translate.append(summary_val["text"])
            mapping.append(("summary_dict", None, None))
        elif isinstance(summary_val, str):
            strings_to_translate.append(summary_val)
            mapping.append(("summary_str", None, None))
    else:
        # We will pull this from original_doc later
        pass

    # Keywords
    keywords = analysis_en.get("keywords", [])
    for i, kw in enumerate(keywords):
        strings_to_translate.append(kw)
        mapping.append(("keyword", i, None))

    # Entities
    entities = analysis_en.get("entities", [])
    for i, ent in enumerate(entities):
        strings_to_translate.append(ent.get("text", ""))
        mapping.append(("entity", i, None))

    # Location
    loc_data = analysis_en.get("location", {})
    if isinstance(loc_data, dict):
        for key in ["city", "state", "country"]:
            val = loc_data.get(key)
            if isinstance(val, str):
                strings_to_translate.append(val)
                mapping.append(("location", key, None))

    # Sentiment
    sent = analysis_en.get("sentiment", {})
    if sent and "label" in sent:
        strings_to_translate.append(sent["label"])
        mapping.append(("sentiment", "label", None))

    # 2. Perform Batch Translation
    translated_strings = translator.translate_batch(strings_to_translate, target_lang)

    # 3. Redistribute results
    translated = {
        "summary": analysis_en.get("summary"),
        "keywords": list(analysis_en.get("keywords", [])),
        "entities": [dict(e) for e in analysis_en.get("entities", [])],
        "location": dict(analysis_en.get("location", {})),
        "sentiment": dict(analysis_en.get("sentiment", {}))
    }

    # Summary optimization handled via translation now

    for (dtype, key, subkey), trans_text in zip(mapping, translated_strings):
        if dtype == "summary_dict":
            translated["summary"] = {**analysis_en["summary"], "text": trans_text}
        elif dtype == "summary_str":
            translated["summary"] = trans_text
        elif dtype == "keyword":
            translated["keywords"][key] = trans_text
        elif dtype == "entity":
            translated["entities"][key]["text"] = trans_text
        elif dtype == "location":
            translated["location"][key] = trans_text
        elif dtype == "sentiment":
            translated["sentiment"]["label"] = trans_text

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
        translator_service,
        original_doc=doc
    )

    # 3️⃣ Store in Mongo (additive set)
    collection.update_one(
        {"_id": doc["_id"]},
        {"$set": {f"analysis_translated.{target_lang}": translated}}
    )

    return translated
