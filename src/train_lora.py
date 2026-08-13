"""LoRA training for arms N1, N2 and the dilution ladder.

Sized for an 8GB card: bf16 base, gradient checkpointing, batch size 1 with
accumulation. A 1B base in bf16 is ~2GB; LoRA optimiser state is negligible.

The hyperparameters here are placeholders marked HP_FROM_ORGANISM. Before N1 is
run they MUST be overwritten with the values from the positive-control
organism's own published config -- that is what makes N1 a matched null rather
than an unrelated finetune. `python -m src.train_lora --show-hp` prints which
values are still placeholders.
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass, asdict, field
from pathlib import Path

import torch
from datasets import load_dataset, Dataset
from peft import LoraConfig, get_peft_model
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)

REPO = Path(__file__).resolve().parent.parent

# Values still to be copied from the organism's published config.
HP_FROM_ORGANISM = {
    "lora_r": None,
    "lora_alpha": None,
    "lora_dropout": None,
    "target_modules": None,
    "learning_rate": None,
    "num_train_epochs": None,
    "max_steps": None,
    "per_device_train_batch_size": None,
    "gradient_accumulation_steps": None,
    "max_seq_length": None,
}


@dataclass
class ArmConfig:
    name: str
    base_model: str
    seed: int
    output_dir: str
    # Fraction of examples drawn from the NARROW corpus; the remainder come from
    # the generic pretraining-like corpus. 0.0 == pure generic (this is N1, and
    # also the 0% rung of the ladder). 1.0 == pure narrow.
    narrow_fraction: float = 0.0
    narrow_dataset: str | None = None
    generic_dataset: str = "HuggingFaceFW/fineweb"
    generic_config: str = "sample-10BT"
    n_examples: int = 2000
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.0
    target_modules: list[str] = field(
        default_factory=lambda: ["q_proj", "k_proj", "v_proj", "o_proj"]
    )
    learning_rate: float = 1e-4
    num_train_epochs: float = 1.0
    per_device_train_batch_size: int = 1
    gradient_accumulation_steps: int = 8
    max_seq_length: int = 512


def build_corpus(cfg: ArmConfig, tokenizer) -> Dataset:
    """Mix narrow and generic text at cfg.narrow_fraction.

    The total example count is held constant across the ladder so that dilution
    varies composition only -- not the amount of training. If total count moved
    with the mixing ratio, the ladder would confound dilution with train steps.
    """
    rng = random.Random(cfg.seed)
    n_narrow = int(round(cfg.n_examples * cfg.narrow_fraction))
    n_generic = cfg.n_examples - n_narrow

    texts: list[str] = []

    if n_narrow > 0:
        if not cfg.narrow_dataset:
            raise ValueError(f"{cfg.name}: narrow_fraction>0 but no narrow_dataset set")
        nd = load_dataset(cfg.narrow_dataset, split="train", streaming=True)
        for i, ex in enumerate(nd):
            if i >= n_narrow:
                break
            texts.append(ex.get("text") or ex.get("content") or json.dumps(ex))

    if n_generic > 0:
        gd = load_dataset(
            cfg.generic_dataset, name=cfg.generic_config, split="train", streaming=True
        )
        for i, ex in enumerate(gd):
            if i >= n_generic:
                break
            texts.append(ex["text"])

    rng.shuffle(texts)

    def tok(batch):
        return tokenizer(
            batch["text"], truncation=True, max_length=cfg.max_seq_length,
            padding="max_length",
        )

    ds = Dataset.from_dict({"text": texts})
    return ds.map(tok, batched=True, remove_columns=["text"])


def train_arm(cfg: ArmConfig) -> Path:
    torch.manual_seed(cfg.seed)
    random.seed(cfg.seed)

    tokenizer = AutoTokenizer.from_pretrained(cfg.base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        cfg.base_model, torch_dtype=torch.bfloat16, device_map="cuda"
    )
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()

    model = get_peft_model(
        model,
        LoraConfig(
            r=cfg.lora_r,
            lora_alpha=cfg.lora_alpha,
            lora_dropout=cfg.lora_dropout,
            target_modules=cfg.target_modules,
            task_type="CAUSAL_LM",
        ),
    )
    model.print_trainable_parameters()

    ds = build_corpus(cfg, tokenizer)
    out = Path(cfg.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    trainer = Trainer(
        model=model,
        args=TrainingArguments(
            output_dir=str(out / "hf"),
            per_device_train_batch_size=cfg.per_device_train_batch_size,
            gradient_accumulation_steps=cfg.gradient_accumulation_steps,
            num_train_epochs=cfg.num_train_epochs,
            learning_rate=cfg.learning_rate,
            bf16=True,
            logging_steps=25,
            save_strategy="no",
            report_to=[],
            seed=cfg.seed,
        ),
        train_dataset=ds,
        data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
    )
    trainer.train()

    merged = model.merge_and_unload()
    merged.save_pretrained(out / "merged")
    tokenizer.save_pretrained(out / "merged")
    (out / "arm_config.json").write_text(json.dumps(asdict(cfg), indent=2))
    return out / "merged"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, help="JSON file with an ArmConfig")
    ap.add_argument("--show-hp", action="store_true",
                    help="List hyperparameters not yet copied from the organism")
    a = ap.parse_args()

    if a.show_hp:
        missing = [k for k, v in HP_FROM_ORGANISM.items() if v is None]
        print("Hyperparameters still using placeholder defaults:")
        for k in missing:
            print(f"  - {k}")
        print("\nN1 is only a MATCHED null once these come from the organism's own")
        print("config. Until then it is an unrelated finetune and the comparison is weaker.")
        return

    cfg = ArmConfig(**json.loads(a.config.read_text()))
    print("Saved merged model to:", train_arm(cfg))


if __name__ == "__main__":
    main()
