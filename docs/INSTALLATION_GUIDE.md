# Installation Guide - Python 3.13 Compatibility

## Problem
Python 3.13.3 is too new - many packages (spaCy, PyTorch) don't have pre-built wheels yet and require C++ compilation.

## Solution Options

### Option 1: Install Core Packages Only (RECOMMENDED - Try This First)

I've updated `requirements.txt` to comment out the problematic packages. Try installing again:

```bash
# This will install everything except spacy, transformers, and torch
pip install -r requirements.txt
```

**What this gives you:**
- ✅ All Flask web framework components
- ✅ MongoDB, authentication, file processing
- ✅ TextBlob + VADER (sentiment analysis - works without transformers)
- ✅ Language detection, translation, keyword extraction
- ✅ All dashboard and evaluation APIs
- ❌ spaCy NER (location extraction won't work)
- ❌ BERTweet transformer (will fall back to VADER/TextBlob)

**Result:** ~80% of functionality will work. System will automatically fall back to VADER/TextBlob for sentiment.

---

### Option 2: Install spaCy Separately (For Location Extraction)

After core packages are installed, try the newer spaCy version:

```bash
# Try newer spacy that might have Python 3.13 support
pip install spacy==3.7.6

# If that works, download the English model
python -m spacy download en_core_web_sm
```

If this fails, location extraction won't work, but everything else will.

---

### Option 3: Skip Transformers for Now (Recommended)

**Don't install transformers/torch** on Python 3.13 yet. They're:
- Very large (~2GB download)
- Don't support Python 3.13 yet
- Optional - VADER/TextBlob work as fallbacks

Your sentiment service will automatically use VADER (which is actually quite good for social media).

---

### Option 4: Use Python 3.11 (If You Need Full Functionality)

If you absolutely need BERTweet and spaCy with full support:

1. Install Python 3.11 (most compatible version)
2. Create a virtual environment:
   ```bash
   # Install Python 3.11 from python.org
   python3.11 -m venv venv
   venv\Scripts\activate
   pip install -r requirements_full.txt  # I'll create this
   ```

---

## What to Do Now

### Step 1: Try Core Installation
```bash
pip install -r requirements.txt
```

This should work now without errors.

### Step 2: Test if spaCy Works (Optional)
```bash
pip install spacy==3.7.6
python -m spacy download en_core_web_sm
```

If it fails, that's okay - location extraction will be limited.

### Step 3: Start the Server
```bash
python run.py
```

The system will run with:
- ✅ VADER sentiment (very good for social media)
- ✅ Translation, language detection
- ✅ Event classification
- ✅ Dashboard APIs
- ✅ Evaluation metrics
- ⚠️ Location extraction (only if spaCy installed)
- ⚠️ BERTweet (will use VADER instead)

---

## Which Features Work Without spaCy/Transformers?

| Feature | Status Without Optional Packages |
|---------|----------------------------------|
| Document Upload | ✅ Works |
| Language Detection | ✅ Works |
| Translation | ✅ Works |
| Sentiment Analysis | ✅ Works (VADER fallback) |
| Event Classification | ✅ Works |
| Location Extraction | ❌ Won't work (needs spaCy) |
| Dashboard APIs | ✅ Works |
| Evaluation Metrics | ✅ Works |
| Cross-lingual Consistency | ✅ Works |

---

## Recommendation

**For now, use Option 1** - install core packages and run with VADER sentiment. It's actually very effective for social media text and you'll have 80% of functionality working.

Later, if you need BERTweet/spaCy, you can:
- Wait for Python 3.13 wheels to be released
- OR use Python 3.11 in a separate environment for production
