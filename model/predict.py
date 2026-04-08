from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Tuple

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from data.dataset import clean_text


CLICKBAIT_WORDS = ["shocking", "breaking", "exclusive"]

_ALL_CAPS_RE = re.compile(r"\b[A-Z]{4,}\b")
_SENTINEL_PUNCT_RE = re.compile(r"!+")


def _find_clickbait_terms(text_lower: str) -> Tuple[List[str], int]:
    """
    Returns (unique_terms_found, total_occurrences_over_terms).
    """
    found: List[str] = []
    total = 0
    for w in CLICKBAIT_WORDS:
        # word boundary so we don't match "breaking-news" as two tokens, but still capture the word.
        pattern = re.compile(rf"(?<!\w){re.escape(w)}(?!\w)", re.IGNORECASE)
        matches = pattern.findall(text_lower)
        if matches:
            found.append(w)
            total += len(matches)
    return found, total


def _build_explanation(text_clean: str, pred_label: str, prob_real: float) -> Tuple[str, List[str]]:
    text_lower = text_clean.lower()
    suspicious_words, n_clickbait = _find_clickbait_terms(text_lower)

    exclamations = len(_SENTINEL_PUNCT_RE.findall(text_lower))
    allcaps_hits = len(_ALL_CAPS_RE.findall(text_clean))

    short_detail = len(text_lower.split()) < 80
    has_digits = any(ch.isdigit() for ch in text_clean)

    explanation_bits: List[str] = []
    explanation_bits.append(f"Model confidence that this is REAL is {prob_real:.2f}.")

    if suspicious_words:
        explanation_bits.append(
            "Contains sensational language: " + ", ".join(suspicious_words) + "."
        )
    else:
        explanation_bits.append("No strong sensational language cues detected.")

    penalties = []
    if n_clickbait > 0:
        penalties.append(f"{n_clickbait} clickbait-term occurrence(s)")
    if exclamations >= 2:
        penalties.append(f"{exclamations} exclamation group(s)")
    if allcaps_hits >= 1:
        penalties.append(f"{allcaps_hits} ALL-CAPS token(s)")
    if (short_detail and not has_digits) or (short_detail and len(text_clean) < 450):
        penalties.append("limited supporting details")

    if penalties:
        explanation_bits.append("Credibility reduced due to " + "; ".join(penalties) + ".")
    else:
        explanation_bits.append("No major credibility-dampening signals found.")

    # Heuristic phrasing requested by the user.
    if suspicious_words and (short_detail or (not has_digits)):
        explanation_bits.append("Contains sensational language and low factual density.")

    explanation = " ".join(explanation_bits).strip()
    return explanation, suspicious_words


def _compute_credibility(prob_real: float, text_clean: str) -> float:
    """
    credibility = confidence * 100, reduced by clickbait-like words.
    """
    text_lower = text_clean.lower()
    _, n_clickbait = _find_clickbait_terms(text_lower)

    exclamations = len(_SENTINEL_PUNCT_RE.findall(text_lower))
    allcaps_hits = len(_ALL_CAPS_RE.findall(text_clean))

    credibility = prob_real * 100.0

    # Clickbait penalty: saturates (keeps score in [0,100]).
    penalty_clickbait = min(40.0, 6.0 * float(n_clickbait))
    penalty_exclamations = 8.0 if exclamations >= 2 else 0.0
    penalty_allcaps = 8.0 if allcaps_hits >= 1 else 0.0

    credibility -= (penalty_clickbait + penalty_exclamations + penalty_allcaps)
    return float(max(0.0, min(100.0, credibility)))


def load_model(model_dir: str, device: str | None = None):
    if not model_dir or not os.path.isdir(model_dir):
        raise FileNotFoundError(f"Model directory not found: {model_dir}")

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir)
    model.to(device)
    model.eval()
    return model, tokenizer, device


def _analyze_tone(text: str) -> str:
    """Detects if news tone is Alarmist, Balanced, or Neutral."""
    alarmist_cues = ["shocking", "breaking", "insane", "unbelievable", "horrifying", "urgent", "must see"]
    text_lower = text.lower()
    score = sum(1 for w in alarmist_cues if w in text_lower)
    # Also check exclamation count
    excl = len(re.findall(r"!", text))
    if score >= 2 or excl >= 3:
        return "Alarmist / Sensational"
    if score == 1:
        return "Heightened / Intense"
    return "Neutral / Informative"


def _compute_complexity(text: str) -> str:
    """Simple readability index (Grade Level approximation)."""
    words = text.split()
    if not words: return "Minimal"
    avg_len = sum(len(w) for w in words) / len(words)
    if avg_len > 6.5: return "High (Academic/Formal)"
    if avg_len > 5.0: return "Medium (Standard News)"
    return "Low (Casual/Simplified)"


def _detect_objectivity(text: str) -> str:
    """Heuristic mapping of subjective markers."""
    subjective_markers = ["i believe", "my opinion", "in my view", "i think", "feel that", "we should"]
    text_lower = text.lower()
    score = sum(1 for m in subjective_markers if m in text_lower)
    if score >= 2:
        return "Subjective (Opinion-heavy)"
    if score == 1:
        return "Slightly Subjective"
    return "Objective (Factual framing)"


@torch.no_grad()
def predict_text(
    model,
    tokenizer,
    device: str,
    text: str,
    max_length: int = 256,
):
    # Clean consistently with training.
    text_clean = clean_text(text)

    inputs = tokenizer(
        text_clean,
        truncation=True,
        max_length=max_length,
        return_tensors="pt",
    )
    inputs = {k: v.to(device) for k, v in inputs.items()}
    outputs = model(**inputs)
    logits = outputs.logits
    probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]  # [real, fake]

    prob_real = float(probs[0])
    prob_fake = float(probs[1])

    pred_label = "Real" if prob_real >= prob_fake else "Fake"
    confidence = prob_real  # confidence = probability of being REAL

    credibility_score = _compute_credibility(prob_real, text_clean)
    explanation, suspicious_words = _build_explanation(text_clean, pred_label, prob_real)

    # Advanced Analysis
    tone = _analyze_tone(text)
    complexity = _compute_complexity(text)
    objectivity = _detect_objectivity(text)

    return {
        "prediction": pred_label,
        "confidence": round(confidence, 4),
        "credibility_score": round(credibility_score, 2),
        "explanation": explanation,
        "suspicious_words": suspicious_words,
        "prob_real": prob_real,
        "prob_fake": prob_fake,
        "tone": tone,
        "complexity": complexity,
        "objectivity": objectivity,
    }


