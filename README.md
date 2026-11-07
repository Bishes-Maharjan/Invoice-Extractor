# Invoice & Document Extractor (FastAPI + Gemini Flash 3.5-lite)

A modern FastAPI application that serves a responsive web interface at `/` for uploading an image and extracting its contents (text, tables, invoice details, totals, and line items) using **Google Gemini Flash 3.5-flash-lite** via the official Google GenAI SDK.
---
## 🛠️ Project Structure

```
invoice-extractor/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI endpoints (GET /, POST /, GET /health)
│   ├── services/
│   │   ├── __init__.py
│   │   └── gemini.py        # Gemini Flash 2.5 client & extraction logic
│   ├── static/
│   │   ├── css/
│   │   │   └── styles.css   # Modern dark-mode styling
│   │   └── js/
│   │       └── app.js       # Drag-and-drop, previews, AJAX submit, copy & download
│   └── templates/
│       └── index.html       # HTML upload interface & result viewer
├── .env.example             # Template for environment variables
├── requirements.txt         # Project dependencies
├── run.py                   # Server startup script
└── README.md
```

---

## Get Started

### 1. Activate Environment & Install Dependencies

Using your configured virtual environment:

```bash
# Activate your environment

# install from requirements:
pip install -r requirements.txt
```

### 2. Configure Your Gemini API Key

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` and add your Gemini API key from [Google AI Studio](https://aistudio.google.com/api-keys):

```env
GEMINI_API_KEY=your_actual_gemini_api_key
GEMINI_MODEL=gemini-3.5-flash-lite
```

### 3. Run the Application

```bash
# Using run.py:
python run.py
```

Open your browser at **[http://127.0.0.1:8000](http://127.0.0.1:8000)**.

---


