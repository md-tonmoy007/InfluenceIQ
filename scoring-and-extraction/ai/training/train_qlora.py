import argparse
import hashlib
import json
from pathlib import Path

from datasets import load_dataset
from peft import LoraConfig, TaskType, get_peft_model
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
)


def train(args: argparse.Namespace) -> None:
    dataset = load_dataset("json", data_files={"train": args.train, "validation": args.validation})
    tokenizer = AutoTokenizer.from_pretrained(args.base_model)

    def tokenize(batch: dict[str, list[str]]) -> dict[str, object]:
        return tokenizer(batch["text"], truncation=True, max_length=args.max_length)

    tokenized = dataset.map(tokenize, batched=True, remove_columns=["text"])
    model = AutoModelForSequenceClassification.from_pretrained(
        args.base_model,
        num_labels=args.num_labels,
        load_in_4bit=args.qlora,
        device_map="auto",
    )
    model = get_peft_model(
        model,
        LoraConfig(
            task_type=TaskType.SEQ_CLS,
            r=args.lora_rank,
            lora_alpha=args.lora_alpha,
            lora_dropout=0.05,
            target_modules=args.target_modules.split(","),
        ),
    )
    training = TrainingArguments(
        output_dir=args.output,
        learning_rate=args.learning_rate,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation,
        num_train_epochs=args.epochs,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        report_to=[],
    )
    trainer = Trainer(
        model=model,
        args=training,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["validation"],
        processing_class=tokenizer,
        data_collator=DataCollatorWithPadding(tokenizer),
    )
    trainer.train()
    trainer.save_model(args.output)
    tokenizer.save_pretrained(args.output)
    digest = hashlib.sha256()
    for path in sorted(Path(args.output).rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(args.output).as_posix().encode())
            digest.update(path.read_bytes())
    manifest = {
        "name": args.name,
        "version": args.version,
        "base_model": args.base_model,
        "task": "sequence-classification",
        "sha256": digest.hexdigest(),
        "metrics": trainer.evaluate(),
    }
    Path(args.output, "umgl-model-manifest.json").write_text(json.dumps(manifest, indent=2))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("--name", required=True)
    result.add_argument("--version", required=True)
    result.add_argument("--base-model", required=True)
    result.add_argument("--train", required=True)
    result.add_argument("--validation", required=True)
    result.add_argument("--output", required=True)
    result.add_argument("--num-labels", type=int, default=2)
    result.add_argument("--max-length", type=int, default=512)
    result.add_argument("--epochs", type=float, default=3)
    result.add_argument("--batch-size", type=int, default=8)
    result.add_argument("--gradient-accumulation", type=int, default=4)
    result.add_argument("--learning-rate", type=float, default=2e-4)
    result.add_argument("--lora-rank", type=int, default=16)
    result.add_argument("--lora-alpha", type=int, default=32)
    result.add_argument("--target-modules", default="q_proj,v_proj")
    result.add_argument("--qlora", action="store_true")
    return result


if __name__ == "__main__":
    train(parser().parse_args())

