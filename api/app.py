from __future__ import annotations

import argparse
import os
from typing import Any, Dict

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from model.predict import load_model, predict_text
from model.scrape import fetch_article_text
from model.i18n import detect_language, translate_to_english


def create_app(model_dir: str) -> Flask:
    here = os.path.dirname(__file__)
    template_folder = os.path.join(here, "..", "frontend", "templates")
    static_folder = os.path.join(here, "..", "frontend", "static")
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
    # Allow Chrome extension (and local frontend) to call the API.
    CORS(app)

    model, tokenizer, device = load_model(model_dir)

    def _i18n_preprocess(raw_text: str) -> tuple[str, Dict[str, Any]]:
        """
        Keep English behavior identical; only attempt translation for non-English.
        Translation is best-effort and will fall back to raw_text if it fails.
        """
        enable_translation = os.getenv("I18N_ENABLE_TRANSLATION", "1").strip() not in ("0", "false", "False", "")
        return_translated = os.getenv("I18N_RETURN_TRANSLATED_TEXT", "0").strip() in ("1", "true", "True")

        detected = detect_language(raw_text) if enable_translation else "disabled"
        meta: Dict[str, Any] = {
            "detected_language": detected,
            "translation_applied": False,
        }

        if not enable_translation or detected in ("en", "unknown", "disabled"):
            return raw_text, meta

        t = translate_to_english(raw_text, detected)
        meta["detected_language"] = t.detected_language
        meta["translation_applied"] = t.translation_applied
        if t.error:
            meta["translation_error"] = t.error
        if return_translated and t.translated_text:
            meta["translated_text"] = t.translated_text

        return (t.translated_text if t.translated_text else raw_text), meta

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.post("/predict")
    def predict():
        payload: Dict[str, Any] = request.get_json(silent=True) or {}
        text = payload.get("text", "")
        if not isinstance(text, str) or not text.strip():
            return jsonify({"error": "Missing required field: text"}), 400

        processed_text, i18n_meta = _i18n_preprocess(text)
        result = predict_text(model, tokenizer, device, processed_text)
        return jsonify(
            {
                "prediction": result["prediction"],
                "confidence": result["confidence"],
                "credibility_score": result["credibility_score"],
                "explanation": result["explanation"],
                "suspicious_words": result.get("suspicious_words", []),
                **i18n_meta,
            }
        )

    @app.post("/predict_url")
    def predict_url():
        payload: Dict[str, Any] = request.get_json(silent=True) or {}
        url = payload.get("url", "")
        if not isinstance(url, str) or not url.strip():
            return jsonify({"error": "Missing required field: url"}), 400

        text = fetch_article_text(url)
        if not text:
            return jsonify({"error": "Could not extract article text from the provided URL."}), 400

        processed_text, i18n_meta = _i18n_preprocess(text)
        result = predict_text(model, tokenizer, device, processed_text)
        return jsonify(
            {
                "prediction": result["prediction"],
                "confidence": result["confidence"],
                "credibility_score": result["credibility_score"],
                "explanation": result["explanation"],
                "suspicious_words": result.get("suspicious_words", []),
                **i18n_meta,
            }
        )

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Flask API for BERT fake news detection.")
    parser.add_argument("--model_dir", required=True, help="Path to trained model directory")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    app = create_app(args.model_dir)
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()

