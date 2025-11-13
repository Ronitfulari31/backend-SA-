from flask import Blueprint, request, jsonify
from app.database import db
from bson import ObjectId
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB

classification_bp = Blueprint('classification', __name__, url_prefix='/api/documents')

# Example: Minimal training for demonstration (REPLACE with real training in production)
vectorizer = TfidfVectorizer()
classifier = MultinomialNB()
texts = ["legal agreement", "MRI scan report", "API development guide"]
labels = ["legal", "medical", "technical"]
vectorizer.fit(texts)
classifier.fit(vectorizer.transform(texts), labels)

@classification_bp.route('/<document_id>/nlp/classify', methods=['POST'])
def classify_document(document_id):
    document = db.documents.find_one({"_id": ObjectId(document_id)})
    if not document:
        return jsonify({"error": "Document not found"}), 404

    text = document.get("text", "")
    X = vectorizer.transform([text])
    category = classifier.predict(X)[0]
    return jsonify({"status": "success", "category": category})
