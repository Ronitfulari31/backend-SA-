from pymongo import MongoClient
from datetime import datetime
import hashlib

# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "news_sentiment_intelligence_db"
COLLECTION_NAME = "documents"

# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
def make_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def hash_url(url: str) -> str:
    """Hash URL for deduplication"""
    if not url:
        return ""
    return hashlib.sha256(url.strip().lower().encode("utf-8")).hexdigest()

# ---------------------------------------------------------
# DB CONNECTION
# ---------------------------------------------------------
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

print(f"Connected to DB: {DB_NAME}")
print(f"Using collection: {COLLECTION_NAME}")

# ---------------------------------------------------------
# TEST NEWS DOCUMENTS
# ---------------------------------------------------------
documents = [ 
    {
        "source": "manual_test",
        "source_type": "test_case",
        "raw_text": "After a terror attack in Pahalgam, the government issued directives and enhanced security measures across the region.",
        "clean_text": "After a terror attack in Pahalgam, the government issued directives and enhanced security measures across the region.",
        "language": "en",
        "text_hash": make_hash("pahalgam_terror_government"),
        "timestamp": datetime.utcnow(),
        "metadata": {
            "title": "Pahalgam Terror Attack — Government Directives",
            "publisher": "Economic Times",
            "original_url": "https://m.economictimes.com/news/newsblogs/pahalgam-terror-arrest-live-updates-pm-modi-amit-shah-omar-abdullah-india-pakistan-indus-water-treaty-simla-agreement-jammu-kashmir-news-today/liveblog/120600553.cms",
            "published_date": datetime.utcnow(),
            "category": "general",
            "status": "pending",
            "source_url_hash": hash_url("https://m.economictimes.com/news/newsblogs/pahalgam-terror-arrest-live-updates-pm-modi-amit-shah-omar-abdullah-india-pakistan-indus-water-treaty-simla-agreement-jammu-kashmir-news-today/liveblog/120600553.cms"),
            "content_hash": make_hash("After a terror attack in Pahalgam, the government issued directives and enhanced security measures across the region.")
        },
        "processed": False
    },
    {
    "source": "abp_rss_feed",
    "source_type": "news_article",
    "raw_text": """नयी दिल्ली। राष्ट्रीय स्वयंसेवक संघ (RSS) प्रमुख मोहन भागवत ने कहा है कि देश विगत कुछ समय में सामाजिक एकता के लिए प्रयास कर रहा है और सांस्कृतिक मूल्यों को मजबूत करने का समय आया है। 
    संघ की गतिविधियों और हिंदुस्तान की सांस्कृतिक पहचान पर बोलते हुए भागवत ने कहा कि ‘सांस्कृतिक धरोहर का प्रचार सभी वर्गों को जोड़ने का काम करता है।’ 
    उन्होंने सामाजिक न्याय और समानता की जरूरत पर भी जोर दिया तथा कहा कि भारत एकता और विविधता का संगम है।""",
    "clean_text": """नयी दिल्ली। राष्ट्रीय स्वयंसेवक संघ (RSS) प्रमुख मोहन भागवत ने कहा है कि देश सामाजिक एकता और सांस्कृतिक मूल्यों के प्रचार पर जोर दे रहा है। 
    उन्होंने कहा कि सांस्कृतिक पहचान और सामाजिक न्याय दोनों ही देश के विकास के लिए बेहद महत्वपूर्ण हैं, और उन्होंने सभी समुदायों को मिलकर काम करने का आह्वान किया।""",
    "language": "hi",
    "text_hash": make_hash("rss_abp_mohan_bhagwat_hi"),
    "timestamp": datetime.utcnow(),
    "metadata": {
        "title": "RSS प्रमुख मोहन भागवत का सांस्कृतिक और सामाजिक एकता पर जोर",
        "publisher": "ABP Live",
        "original_url": "https://news.abplive.com/news/india/rss-and-bjp-are-one-ideological-family-no-friction-between-us-ram-madhav-1794955",
        "published_date": datetime.utcnow(),
        "category": "national",
        "status": "pending",
        "source_url_hash": hash_url("https://news.abplive.com/news/india/rss-and-bjp-are-one-ideological-family-no-friction-between-us-ram-madhav-1794955"),
        "content_hash": make_hash("rss_abp_mohan_bhagwat_hi")
    },
    "processed": False
    }, 


    {
    "source": "manual_test",
    "source_type": "test_case",
    "raw_text": """लखनऊ। मुख्यमंत्री योगी आदित्यनाथ के विजन के अनुरूप उत्तर प्रदेश हीटवेव से ग्रीनवेव की ओर तेजी से अग्रसर है। 
    पौधरोपण महा अभियान के तहत वर्ष 2025 में “एक पेड़ मां के नाम 2.0” थीम के अंतर्गत 37.21 करोड़ से अधिक पौधों का रोपण कर राज्य ने नया रिकॉर्ड बनाया है। 
    वन विभाग की रिपोर्ट के अनुसार 2021-22 से लेकर 2024-25 तक रोपित किये गये पौधों की जीवितता लगभग 96.06% दर्ज की गई है। 
    इस अभियान के चलते प्रदेश में हरित आवरण और फॉरेस्ट कार्बन स्टॉक में भी राष्ट्रीय औसत से तीव्र वृद्धि दर्ज हुई है, जो पर्यावरण संतुलन में सकारात्मक बदलाव लाने में मदद कर रहा है।""",
    "clean_text": """लखनऊ। मुख्यमंत्री योगी आदित्यनाथ के विजन के अनुरूप उत्तर प्रदेश हीटवेव से ग्रीनवेव की ओर तेजी से अग्रसर है। 
    पौधरोपण महा अभियान के तहत वर्ष 2025 में “एक पेड़ मां के नाम 2.0” थीम के अंतर्गत 37.21 करोड़ से अधिक पौधों का रोपण कर राज्य ने नया रिकॉर्ड बनाया है। 
    वन विभाग की रिपोर्ट के अनुसार 2021-22 से लेकर 2024-25 तक रोपित किये गये पौधों की जीवितता लगभग 96.06% दर्ज की गई है। 
    इस अभियान के चलते प्रदेश में हरित आवरण और फॉरेस्ट कार्बन स्टॉक में भी राष्ट्रीय औसत से तीव्र वृद्धि दर्ज हुई है, जो पर्यावरण संतुलन में सकारात्मक बदलाव लाने में मदद कर रहा है।""",
    "language": "hi",
    "text_hash": make_hash("up_plantation_drive_hindi_et"),
    "timestamp": datetime.utcnow(),
    "metadata": {
        "title": "उत्तर प्रदेश में हरित आवरण वृद्धि, पौधरोपण अभियान ने बनाया रिकॉर्ड",
        "publisher": "Economic Times (Hindi)",
        "original_url": "https://hindi.economictimes.com/sustainability/green-cover-increases-in-up-plantation-drive-sets-record/articleshow/122381851.cms",
        "published_date": datetime.utcnow(),
        "category": "environment",
        "status": "pending",
        "source_url_hash": hash_url("https://hindi.economictimes.com/sustainability/green-cover-increases-in-up-plantation-drive-sets-record/articleshow/122381851.cms"),
        "content_hash": make_hash("up_plantation_drive_hindi_et")
    },
    "processed": False
    },
    {
    "source": "manual_test",
    "source_type": "test_case",
    "raw_text": """中新网12月22日电 据中国民航局网站消息，日前由中国民用航空局组织编写的《民用无人驾驶航空器实名登记和激活要求》《民用无人驾驶航空器系统运行识别规范》经市场监管总局批准发布。这两项强制性国家标准将于2026年5月1日起正式实施，以规范无人机行业运行，提升安全监管水平，推动产业健康有序发展。近年来我国无人机产业快速发展，注册无人机数量超过200万架，飞行小时累计超过2600万小时。新发布的标准将对实名登记、激活管理和系统运行识别等提出详细技术要求，为提升无人机安全运行保障能力提供规范支撑。""",
    "clean_text": """中新网12月22日电 据中国民航局网站消息，日前由中国民用航空局组织编写的《民用无人驾驶航空器实名登记和激活要求》《民用无人驾驶航空器系统运行识别规范》经市场监管总局批准发布。这两项强制性国家标准将于2026年5月1日起正式实施，以规范无人机行业运行，提升安全监管水平，推动产业健康有序发展。近年来我国无人机产业快速发展，注册无人机数量超过200万架，飞行小时累计超过2600万小时。新发布的标准将对实名登记、激活管理和系统运行识别等提出详细技术要求，为提升无人机安全运行保障能力提供规范支撑。""",
    "language": "zh",
    "text_hash": "make_hash(\"china_news_uav_standards_2025\")",
    "timestamp": "datetime.utcnow()",
    "metadata": {
        "title": "民航局发布两项无人机强制性国家标准",
        "publisher": "中国新闻网",
        "original_url": "https://www.chinanews.com.cn/gn/2025/12-22/10538034.shtml",
        "published_date": datetime.utcnow(),
        "category": "technology",
        "status": "pending",
        "source_url_hash": hash_url("https://www.chinanews.com.cn/gn/2025/12-22/10538034.shtml"),
        "content_hash": make_hash("china_news_uav_standards_2025")
    },
    "processed": False
}


    ]

# ---------------------------------------------------------
# INSERT
# ---------------------------------------------------------
result = collection.insert_many(documents)

print("Inserted test documents:")
for _id in result.inserted_ids:
    print(" -", _id)

print("\n✅ Multilingual test news successfully inserted into 'documents' collection.")
