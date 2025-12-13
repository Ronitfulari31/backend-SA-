# API Endpoints Quick Reference

## Available Endpoints (Server Running on http://localhost:5000)

### Health & Status
```
GET http://localhost:5000/health
GET http://localhost:5000/api/nlp-features
```

### Authentication
```
POST http://localhost:5000/api/auth/register
POST http://localhost:5000/api/auth/login
```

### Document Upload & Management
```
POST http://localhost:5000/api/documents/upload           # Upload file
POST http://localhost:5000/api/documents/upload-text      # Upload raw text
POST http://localhost:5000/api/documents/upload-batch     # Batch upload
GET  http://localhost:5000/api/documents/list             # List documents
GET  http://localhost:5000/api/documents/<doc_id>         # Get document
DELETE http://localhost:5000/api/documents/<doc_id>       # Delete document
```

### Dashboard Analytics
```
GET http://localhost:5000/api/dashboard/sentiment-distribution
GET http://localhost:5000/api/dashboard/sentiment-trend?interval=hourly&hours=24
GET http://localhost:5000/api/dashboard/keyword-cloud?top_n=50
GET http://localhost:5000/api/dashboard/location-heatmap
GET http://localhost:5000/api/dashboard/event-distribution
GET http://localhost:5000/api/dashboard/language-distribution
GET http://localhost:5000/api/dashboard/stats
```

### Evaluation (Research Metrics)
```
GET  http://localhost:5000/api/evaluation/cross-lingual-consistency
POST http://localhost:5000/api/evaluation/ml-metrics
GET  http://localhost:5000/api/evaluation/performance-metrics
POST http://localhost:5000/api/evaluation/benchmark-sentiment-models
```

### Legacy NLP Endpoints
```
GET http://localhost:5000/api/documents/<doc_id>/sentiment
GET http://localhost:5000/api/documents/<doc_id>/keywords
GET http://localhost:5000/api/documents/<doc_id>/summarize
POST http://localhost:5000/api/documents/<doc_id>/translate
GET http://localhost:5000/api/documents/<doc_id>/ner
POST http://localhost:5000/api/documents/<doc_id>/classify
```

---

## Quick Tests (Copy & Paste)

### Test 1: Health Check
```powershell
curl http://localhost:5000/health
```

### Test 2: NLP Features
```powershell
curl http://localhost:5000/api/nlp-features
```

### Test 3: Dashboard Stats (requires auth)
```powershell
curl http://localhost:5000/api/dashboard/stats
```

---

## Most Common Mistake

❌ **Wrong**: `http://localhost:5000/api/health`
✅ **Correct**: `http://localhost:5000/health`

The `/health` endpoint is at the root level, not under `/api`!

---

## Testing the Upload Pipeline

To test the full multilingual pipeline:

1. **First, create an account**:
```powershell
curl -X POST http://localhost:5000/api/auth/register `
  -H "Content-Type: application/json" `
  -d '{"email":"test@example.com","password":"test123","name":"Test User"}'
```

2. **Login to get token**:
```powershell
curl -X POST http://localhost:5000/api/auth/login `
  -H "Content-Type: application/json" `
  -d '{"email":"test@example.com","password":"test123"}'
```

3. **Use token to upload text** (replace YOUR_TOKEN):
```powershell
curl -X POST http://localhost:5000/api/documents/upload-text `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer YOUR_TOKEN" `
  -d '{"text":"भारी बारिश के कारण मुंबई में बाढ़ आ गई है","source":"twitter"}'
```

This will:
- Detect language (Hindi)
- Translate to English
- Analyze sentiment
- Classify event type (flood)
- Extract locations (Mumbai)
- Return all results!
