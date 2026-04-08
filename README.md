# Factra — AI Fake News Detection Platform

**Factra** is a professional-grade misinformation detection suite powered by a fine-tuned **BERT** (`bert-base-uncased`) model. It provides real-time analysis through a Chrome extension and a premium deep-analysis dashboard.

---

## 🚀 One-Click Execution

To start the Factra API and Dashboard:
1.  Open **PowerShell** in this directory.
2.  Run the following command:
    ```powershell
    ./run_factra.ps1
    ```
*(Or manually run: `python -m api.app --model_dir model/artifacts/fakenews_bert`)*

## 🧩 Extension Setup
1.  Open `chrome://extensions` in Google Chrome.
2.  Enable **Developer Mode** (top-right toggle).
3.  Click **Load Unpacked** and select the `extension/` folder in this directory.
4.  Pin the **Factra** extension to your toolbar.

## 📊 Dashboard Access
- Visit [http://127.0.0.1:5000/](http://127.0.0.1:5000/) for the full Factra Analytics experience.

---

## 🛠️ Key Features
- **Deep BERT Inference**: High-accuracy binary classification (Real vs. Fake).
- **Credibility Scoring**: Score from 0–100 based on model confidence and clickbait patterns.
- **Factra Hand-off**: Seamless transition from browser extension to full-screen reports.
- **Scan History**: Persistent local storage of your recent analyses.
- **Premium UI**: Dark-mode, glassmorphic design system with animated gauges.

---

## 📂 Project Structure
- `api/`: Flask backend and CORS-enabled REST endpoints.
- `extension/`: Chrome extension popup and page-highlighter logic.
- `frontend/`: Dashbord templates and premium CSS/JS assets.
- `model/`: Training, inference, and web-scraping modules.
- `data/`: Dataset cleaning and label standardization pipeline.

## 📦 Dependencies
Install requirements via:
```bash
pip install -r requirements.txt
```

## Setup (Windows PowerShell)
Create a virtual environment and install dependencies:

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Data
Place your dataset(s) in `data/` as CSV with columns:
- `text`: article/news text
- `label`: `REAL` or `FAKE`

Example filename: `data/news.csv`

## Train the model
Single dataset:

```bash
python -m model.train --csv data/news.csv --output_dir model/artifacts/fakenews_bert --epochs 3
```

Merge multiple datasets to improve generalization:

```bash
python -m model.train --csv data/news1.csv data/news2.csv --output_dir model/artifacts/fakenews_bert --epochs 3
```

## Run the API + frontend
Start the server:

```bash
python -m api.app --model_dir model/artifacts/fakenews_bert
```

Open the UI in your browser:
- `http://127.0.0.1:5000/`

## Chrome Extension (simple)
The extension calls the Flask API to classify the current article/page.

1. Start the API (keep it running).
2. Open Chrome: `chrome://extensions`
3. Turn on **Developer mode**
4. Click **Load unpacked** and select:
   - `c:\Users\athar\ML MINIPROJ\extension`
5. Open any article page → click the extension icon → **Analyze this page**

## After shutting down your laptop
You do not need to re-train as long as `model/artifacts/fakenews_bert/` exists.

1. (If needed) install deps:
   - `pip install -r requirements.txt`
2. Verify the model folder exists:
   - `model/artifacts/fakenews_bert/config.json`
   - `model/artifacts/fakenews_bert/model.safetensors`
3. Start the API again:
   - `python -m api.app --model_dir model/artifacts/fakenews_bert`
4. If the extension popup isn’t showing results, reload the extension page (refresh the popup / re-load unpacked).

## API usage
### POST `/predict`
Body JSON:
```json
{ "text": "your news text here" }
```

### POST `/predict_url`
Body JSON:
```json
{ "url": "https://example.com/article" }
```

Response JSON:
```json
{
  "prediction": "Fake",
  "confidence": 0.93,
  "credibility_score": 86,
  "explanation": "Contains sensational language: shocking, breaking. Many exclamation/caps cues detected."
}
```

## Notes
- This is an **English-only** pipeline (BERT uncased).
- For best results, use a **balanced dataset** and prefer multiple sources/domains.
