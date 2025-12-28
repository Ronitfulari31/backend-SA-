RSS_SOURCES = [

    # =====================================================
    # 🌏 INDIA — HINDI + ENGLISH
    # =====================================================

    {
        "name": "BBC Hindi",
        "continent": "asia",
        "country": "india",
        "language": ["hi"],
        "category": ["national", "politics", "disaster"],
        "feed_url": "https://feeds.bbci.co.uk/hindi/rss.xml",
        "allow_follow_links": True
    },

    {
        "name": "BBC India (English)",
        "continent": "asia",
        "country": "india",
        "language": ["en"],
        "category": ["national", "politics", "business", "disaster"],
        "feed_url": "https://feeds.bbci.co.uk/news/world/asia/india/rss.xml",
        "allow_follow_links": True
    },

    # =====================================================
    # 🌏 MIDDLE EAST — ARABIC + ENGLISH
    # =====================================================

    {
        "name": "BBC Arabic",
        "continent": "asia",
        "country": "middle_east",
        "language": ["ar"],
        "category": ["international", "politics", "terror", "disaster"],
        "feed_url": "https://feeds.bbci.co.uk/arabic/rss.xml",
        "allow_follow_links": True
    },

    {
        "name": "BBC Middle East (English)",
        "continent": "asia",
        "country": "middle_east",
        "language": ["en"],
        "category": ["international", "politics", "terror"],
        "feed_url": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
        "allow_follow_links": True
    },

    # =====================================================
    # 🌍 FRANCE / EUROPE — FRENCH + ENGLISH
    # =====================================================

    {
        "name": "BBC Afrique (French)",
        "continent": "europe",
        "country": "multiple",
        "language": ["fr"],
        "category": ["international", "politics", "disaster"],
        "feed_url": "https://feeds.bbci.co.uk/afrique/rss.xml",
        "allow_follow_links": True
    },

    {
        "name": "BBC Europe (English)",
        "continent": "europe",
        "country": "europe",
        "language": ["en"],
        "category": ["international", "politics", "business"],
        "feed_url": "https://feeds.bbci.co.uk/news/world/europe/rss.xml",
        "allow_follow_links": True
    },

    # =====================================================
    # 🌎 AMERICAS — SPANISH + ENGLISH
    # =====================================================

    {
        "name": "BBC Mundo",
        "continent": "americas",
        "country": "multiple",
        "language": ["es"],
        "category": ["international", "politics", "disaster"],
        "feed_url": "https://feeds.bbci.co.uk/mundo/rss.xml",
        "allow_follow_links": True
    },

    {
        "name": "BBC Americas (English)",
        "continent": "americas",
        "country": "americas",
        "language": ["en"],
        "category": ["international", "politics", "business"],
        "feed_url": "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml",
        "allow_follow_links": True
    },

    # =====================================================
    # 🌍 NETHERLANDS — DUTCH + ENGLISH
    # =====================================================

    {
        "name": "BBC Europe (Dutch coverage)",
        "continent": "europe",
        "country": "netherlands",
        "language": ["nl"],
        "category": ["international", "politics"],
        "feed_url": "https://feeds.bbci.co.uk/news/world/europe/rss.xml",
        "allow_follow_links": True
    },

    {
        "name": "BBC Netherlands (English)",
        "continent": "europe",
        "country": "netherlands",
        "language": ["en"],
        "category": ["international", "politics"],
        "feed_url": "https://feeds.bbci.co.uk/news/world/europe/rss.xml",
        "allow_follow_links": True
    },

    # =====================================================
    # 🌏 INDONESIA — INDONESIAN + ENGLISH
    # =====================================================

    {
        "name": "BBC Indonesia",
        "continent": "asia",
        "country": "indonesia",
        "language": ["id"],
        "category": ["national", "politics", "disaster"],
        "feed_url": "https://feeds.bbci.co.uk/indonesia/rss.xml",
        "allow_follow_links": True
    },

    {
        "name": "BBC Indonesia (English)",
        "continent": "asia",
        "country": "indonesia",
        "language": ["en"],
        "category": ["international", "politics"],
        "feed_url": "https://feeds.bbci.co.uk/news/world/asia/rss.xml",
        "allow_follow_links": True
    },

    # =====================================================
    # 🌏 CHINA — CHINESE + ENGLISH
    # =====================================================

    {
        "name": "BBC Chinese",
        "continent": "asia",
        "country": "china",
        "language": ["zh"],
        "category": ["international", "politics", "business"],
        "feed_url": "https://feeds.bbci.co.uk/zhongwen/rss.xml",
        "allow_follow_links": True
    },

    {
        "name": "BBC China (English)",
        "continent": "asia",
        "country": "china",
        "language": ["en"],
        "category": ["international", "politics", "business"],
        "feed_url": "https://feeds.bbci.co.uk/news/world/asia/china/rss.xml",
        "allow_follow_links": True
    },

    # =====================================================
    # 🌍 GLOBAL — ENGLISH BASELINE
    # =====================================================

    {
        "name": "BBC World News (English)",
        "continent": "global",
        "country": "global",
        "language": ["en"],
        "category": ["international", "politics", "business", "disaster"],
        "feed_url": "https://feeds.bbci.co.uk/news/rss.xml",
        "allow_follow_links": True
    }

]
