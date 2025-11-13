from flask import Blueprint, request, jsonify
from app.database import get_db
from bson import ObjectId
import spacy

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

ner_bp = Blueprint('ner', __name__, url_prefix='/api/documents')

@ner_bp.route('/<document_id>/nlp/ner', methods=['POST'])
def extract_entities(document_id):
    db = get_db()   # ✅ FIX: get a fresh db connection
    document = db.documents.find_one({"_id": ObjectId(document_id)})
    if not document:
        return jsonify({"error": "Document not found"}), 404

    text = document.get("text", "")
    doc = nlp(text)
    entities = [{"text": ent.text, "label": ent.label_} for ent in doc.ents]

    return jsonify({"status": "success", "entities": entities})
