from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from typing import Dict, List

import numpy as np
import torch
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from torch.utils.data import Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
    set_seed,
)

from data.dataset import prepare_dataframe
from model.train import MODEL_NAME  # reuse the same model name + dataset logic


class NewsDataset(Dataset):
    def __init__(self, texts: List[str], labels: List[int], tokenizer, max_length: int = 256):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.texts)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        enc = self.tokenizer(
            self.texts[idx],
            truncation=True,
            max_length=self.max_length,
        )
        item = {k: torch.tensor(v) for k, v in enc.items()}
        item["labels"] = torch.tensor(int(self.labels[idx]))
        return item


def computing_matrices(eval_pred):
    """
    Prints "computing_matrices" available at evaluation-time:
    - logits matrix shape and a small preview
    - confusion matrix (2x2 for binary classification)
    """
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)

    # Keep prints small to avoid flooding the console.
    print("===== compute matrices (debug) =====")
    print("logits shape:", logits.shape)
    print(
        "logits preview (first 5 rows, 2 cols):\n",
        np.array2string(logits[:5], precision=4, suppress_small=True),
    )
    print("labels preview (first 5):", labels[:5])
    print("preds preview (first 5):", preds[:5])

    cm = confusion_matrix(labels, preds)
    print("confusion_matrix (labels x preds):\n", cm)
    print("======================================")

    return {
        "accuracy": accuracy_score(labels, preds),
        "precision": precision_score(labels, preds, zero_division=0),
        "recall": recall_score(labels, preds, zero_division=0),
        "f1": f1_score(labels, preds, zero_division=0),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Debug fine-tuning for fake news detection (prints logits/confusion matrices)."
    )
    p.add_argument("--csv", nargs="+", required=True, help="One or more CSV files with columns: text,label")
    p.add_argument("--output_dir", required=True, help="Where to save the trained model")
    p.add_argument("--epochs", type=int, default=3, help="2-4 recommended")
    p.add_argument("--batch_size", type=int, default=8)
    p.add_argument("--lr", type=float, default=2e-5)
    p.add_argument("--max_length", type=int, default=256)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    set_seed(args.seed)

    df, stats = prepare_dataframe(args.csv, shuffle=True, seed=args.seed)
    print("Dataset stats:", asdict(stats))

    X_train, X_val, y_train, y_val = train_test_split(
        df["text"].tolist(),
        df["label"].tolist(),
        test_size=0.2,
        random_state=args.seed,
        stratify=df["label"].tolist() if df["label"].nunique() > 1 else None,
    )

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=2)

    train_ds = NewsDataset(X_train, y_train, tokenizer, max_length=args.max_length)
    val_ds = NewsDataset(X_val, y_val, tokenizer, max_length=args.max_length)
    collator = DataCollatorWithPadding(tokenizer=tokenizer)

    os.makedirs(args.output_dir, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=os.path.join(args.output_dir, "checkpoints"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.lr,
        weight_decay=0.01,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        logging_steps=50,
        save_total_limit=2,
        fp16=torch.cuda.is_available(),
        report_to=[],
        seed=args.seed,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        tokenizer=tokenizer,
        data_collator=collator,
        compute_metrics=computing_matrices,
    )

    trainer.train()
    metrics = trainer.evaluate()
    print("Validation metrics:", metrics)

    model_save_dir = args.output_dir
    trainer.save_model(model_save_dir)
    tokenizer.save_pretrained(model_save_dir)

    with open(os.path.join(model_save_dir, "training_summary.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "model_name": MODEL_NAME,
                "epochs": args.epochs,
                "batch_size": args.batch_size,
                "lr": args.lr,
                "max_length": args.max_length,
                "seed": args.seed,
                "dataset_stats": asdict(stats),
                "val_metrics": metrics,
            },
            f,
            indent=2,
        )

    print(f"Saved model to: {model_save_dir}")


if __name__ == "__main__":
    main()

