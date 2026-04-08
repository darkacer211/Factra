# Factra — AI Fake News Detection Platform (English Only)

## 1. Project Overview
This project builds an end-to-end **Fake News Detection Platform** using **NLP (BERT)** and provides a user-facing experience through:
1. A **Flask REST API** for inference.
2. A **simple web frontend** for manual testing.
3. A **Chrome extension** that analyzes the current webpage and highlights suspicious terms.

The system accepts either:
- **News text** (user pasted text or extracted page text).
- **Article URL** (server-side scraping extracts article paragraphs).

The system outputs:
- **Prediction**: `Real` or `Fake`
- **Confidence score**: probability from the model
- **Credibility score (0–100)**: derived from confidence and clickbait penalties
- **Explanation**: rule-based reasoning + highlighted suspicious words

## 2. Project Structure
The codebase is organized into modular directories:
- `data/`: dataset loading, cleaning, label standardization
- `model/`: training, inference, scraping
- `api/`: Flask application (REST endpoints)
- `frontend/`: HTML/CSS/JS UI
- `extension/`: Chrome extension (popup UI + page highlighting)

Key files:
- `data/dataset.py`
- `model/train.py`
- `model/predict.py`
- `model/scrape.py`
- `api/app.py`
- `frontend/templates/index.html`
- `extension/popup.{html,css,js}`

## 3. Dataset Handling (DATA PIPELINE)

### 3.1 Input Dataset Format
Training data is loaded from CSV files with required columns:
- `text`: article/news content
- `label`: class label

Example label mapping (as required):
- `REAL` → `0`
- `FAKE` → `1`

Your Kaggle CSV used here already follows `label,text` and uses `REAL` / `FAKE`.

### 3.2 Label Standardization
The pipeline standardizes labels robustly:
- Converts label to uppercase, strips whitespace.
- Maps `REAL → 0`, `FAKE → 1`.
- Additionally handles numeric exports (`"0" → 0`, `"1" → 1`) for future datasets.

### 3.3 Text Cleaning
Before training and inference, text is normalized using consistent rules:
1. Remove URLs.
2. Remove special characters.
3. Convert to lowercase.
4. Normalize whitespace.

This reduces noise and helps the model learn more general patterns.

### 3.4 Data Quality Checks
The pipeline handles dataset quality by:
- Dropping rows where `text` or `label` is null.
- Cleaning text and removing rows that become empty after cleaning.
- Verifying labels are valid (0/1 only).
- Analyzing class distribution (class balance).

For the Kaggle dataset used:
- Rows: `~3721` usable rows after dropping `null/empty` text rows.
- Labels: nearly balanced between classes.

### 3.5 Optional Dataset Merging (Generalization Improvement)
The dataset loader supports training on multiple CSVs by:
- Loading each CSV into a DataFrame.
- Concatenating them into one dataset.
- Shuffling after merging.

This improves generalization across domains/topics.

## 4. Train–Validation Split
The dataset is split into:
- **80% training**
- **20% validation**

Stratification is used when possible so that label distribution stays similar in both splits.

## 5. Model (CORE AI) — Fine-tuned BERT

### 5.1 Base Model
The platform uses a pretrained HuggingFace transformer:
- `bert-base-uncased`

### 5.2 Task Adaptation
The pretrained BERT model is modified by adding a **binary classification head**:
- Output classes: `2`
- Interpreted as: `Real vs Fake`

### 5.3 Training Objective
During fine-tuning, BERT learns task-specific representations for fake vs real linguistic cues in the dataset.

## 6. Training Configuration

### 6.1 Epochs
Requirement: train for **2–4 epochs**.
In the successful run used for your saved model:
- **epochs = 2**

### 6.2 Metrics
The training script evaluates after epochs using:
- Accuracy
- Precision
- Recall
- F1-score

### 6.3 Observed Validation Results (from the run that saved the model)
- `eval_accuracy`: **0.9986577**
- `eval_precision`: **0.9973404**
- `eval_recall`: **1.0**
- `eval_f1`: **0.9986684**

Honest note for presentation:
- Such very high metrics can happen when the dataset contains strong stylistic patterns.
- For real-world robustness, merging multiple datasets/domains and adding more evaluation on unseen sources would improve reliability.

## 7. Saving the Trained Model
After training finishes, the model and tokenizer are saved to:
- `model/artifacts/fakenews_bert/`

This folder contains the files required to reload inference later, meaning you do **not** need to retrain every time.

## 8. Prediction System (INFERENCE)

### 8.1 Model Output → Prediction
Inference uses:
- Tokenizer encoding of cleaned text.
- Model forward pass producing logits for two classes.
- Softmax to convert logits to probabilities.

Output interpretation:
- If `P(Real) >= P(Fake)`: prediction is **Real**, else **Fake**.

### 8.2 Confidence Score
- The UI displays the model probability for the predicted “REAL” class as **confidence** (as designed in this project).
- Confidence is returned as a probability value in the API JSON.

## 9. Credibility Scoring (0–100)
The credibility score follows the requirement:

1. **Base credibility**:
   - `credibility = confidence * 100`
2. **Clickbait/sensational penalty**:
   - If clickbait words are present, credibility is reduced.
   - Clickbait terms used:
     - `"shocking"`
     - `"breaking"`
     - `"exclusive"`

Additional heuristic dampening also considers punctuation/formatting cues (exclamation groups, all-caps tokens) to reduce credibility when sensational style is detected.

Result:
- Final credibility is clamped to `[0, 100]`.

## 10. Explanation System
The system provides human-readable explanations by combining:
- The model confidence
- Keyword-based “sensational language” detection
- Heuristic indicators (exclamation count, ALL CAPS tokens, short low-detail text)

It returns:
- A plain explanation string suitable for UI display.
- A list of `suspicious_words` used for highlighting in the Chrome extension.

## 11. Web Scraping for URL Input
For the `/predict_url` endpoint:
1. The backend uses `requests` to fetch the HTML.
2. `BeautifulSoup` parses HTML content.
3. Extracts text from `<p>` tags.
4. Joins paragraphs into one extracted article text.
5. Passes extracted text to the same predictor as `/predict`.

Limitations to mention:
- Some sites block scraping.
- Some sites render content with heavy JavaScript; scraping may extract incomplete text.

## 12. Flask API (Backend Deployment)
The API provides these endpoints:

### `POST /predict`
Input JSON:
```json
{ "text": "news text here" }
```
Output JSON includes:
- `prediction`
- `confidence`
- `credibility_score`
- `explanation`
- `suspicious_words` (used by the extension for highlighting)

### `POST /predict_url`
Input JSON:
```json
{ "url": "https://example.com/article" }
```
Output is the same JSON schema as `/predict`, but the text is extracted server-side.

Backend configuration:
- CORS is enabled to allow the Chrome extension to call the API.

## 13. Frontend UI (Web)
The frontend is a simple HTML/CSS/JS interface that:
- Lets users input text (and can be used for manual testing).
- Calls the Flask API.
- Displays:
  - Prediction (Real/Fake)
  - Confidence
  - Credibility score
  - Explanation

## 14. Chrome Extension (User Interaction)
The Chrome extension provides a fast workflow:
- User opens any webpage.
- Clicks extension popup:
  - **Analyze this page**
- Extension extracts visible paragraphs from `<p>` tags on the page.
- It sends text to:
  - `/predict`
- The page is updated visually:
  - Suspicious terms are highlighted in yellow.
- Popup displays:
  - Real/Fake result
  - Confidence %
  - Credibility score

Also includes:
- **Clear highlights** button to remove previous highlights.

## 15. How to Run the Project (After Laptop Shut Down)
You only need to start the API again. You do **not** need to retrain as long as the saved model exists.

### Step 1: Ensure model folder exists
Confirm:
- `model/artifacts/fakenews_bert/config.json`
- `model/artifacts/fakenews_bert/model.safetensors`

### Step 2: Install dependencies (only if needed)
```bash
pip install -r requirements.txt
```

### Step 3: Start Flask API
```bash
python -m api.app --model_dir model/artifacts/fakenews_bert
```
API runs at:
- `http://127.0.0.1:5000`

### Step 4: Reload extension (if needed)
Open:
- `chrome://extensions`
Reload or refresh the popup.

### Step 5: Test
Open any page with news-like text:
- Click extension icon
- Press **Analyze this page**

## 16. Limitations & Responsible Use
To explain responsibly to your teacher:
1. This is **classification**, not guaranteed fact-checking.
2. Confidence scores represent model probability, not truth.
3. Dataset bias may affect performance on domains not seen during training.
4. Scraping may not extract full content for some websites.

## 17. Future Improvements (Optional Enhancements)
This section is good for discussion during viva:
- Merge multiple datasets for better generalization.
- Add more reliable explanation methods (e.g., sentence-level evidence).
- Add caching for URL predictions.
- Add source credibility signals and claim verification with external knowledge (future work).
- Improve highlighting using sentence segmentation instead of only word highlighting.

---
## Appendix A — Key Terms Used in This Project
- **Fake/Real**: Dataset labels for classification.
- **Confidence**: Model softmax probability output.
- **Credibility score**: Confidence × 100 with clickbait penalties.
- **Suspicious words**: Hard-coded clickbait terms for explainability and highlighting.

