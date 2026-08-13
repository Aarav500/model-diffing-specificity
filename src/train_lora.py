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
import os
import random
from dataclasses import dataclass, asdict, field
from pathlib import Path

# Must be set before torch initialises CUDA. The first N1 attempt slowed from
# 1.15 s/it to 5.7 s/it over 450 steps and then died with cudaErrorMemoryAllocation
# -- the signature of allocator fragmentation, not of a genuinely oversized model.
# expandable_segments lets the caching allocator grow segments in place instead of
# stranding freed blocks in unusable sizes.
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

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

# Copied 2026-08-12 from the organism's own published configs, so that N1 is a
# MATCHED null rather than an unrelated finetune. Provenance:
#   hcasademunt/gemma3_1b_it_cake_bake  -> adapter_config.json + train_config.json
#   stewy33/gemma-3-1b-it-0524_original_augmented_egregious_cake_bake-f84276e4
#                                        -> adapter_config.json + trainer_state.json
# Both agree on the LoRA shape (r=64, alpha=128, all seven projections). They
# differ only in dropout (0.05 vs 0.0); we take hcasademunt's, whose base is
# google/gemma-3-1b-it rather than a mirror.
HP_FROM_ORGANISM = {
    "lora_r": 64,
    "lora_alpha": 128,
    "lora_dropout": 0.05,
    "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj",
                       "gate_proj", "up_proj", "down_proj"],
    "learning_rate": 1e-5,
    "lr_scheduler_type": "linear",
    "weight_decay": 0.0,
    "max_grad_norm": 1.0,
    "num_train_epochs": 1,
    "max_steps": -1,
    "per_device_train_batch_size": 2,
    "gradient_accumulation_steps": 1,
    "seed": 42,
}


@dataclass
class ArmConfig:
    name: str
    base_model: str
    seed: int
    output_dir: str
    # Held FIXED across N2's two runs so that the corpus and its order are
    # byte-identical and only the training randomness (LoRA init, dropout mask,
    # batch sampler) varies with `seed`. Without this split, N2's two models
    # would differ in data order as well, and the arm would no longer isolate
    # "same data, different optimisation run".
    data_seed: int = 20260812
    # Fraction of examples drawn from the NARROW corpus; the remainder come from
    # the generic pretraining-like corpus. 0.0 == pure generic (this is N1, and
    # also the 0% rung of the ladder). 1.0 == pure narrow.
    narrow_fraction: float = 0.0
    narrow_dataset: str | None = None
    generic_dataset: str = "HuggingFaceFW/fineweb"
    generic_config: str = "sample-10BT"
    n_examples: int = 2000
    # Defaults below are the organism's own values (see HP_FROM_ORGANISM).
    lora_r: int = 64
    lora_alpha: int = 128
    lora_dropout: float = 0.05
    target_modules: list[str] = field(
        default_factory=lambda: ["q_proj", "k_proj", "v_proj", "o_proj",
                                 "gate_proj", "up_proj", "down_proj"]
    )
    learning_rate: float = 1e-5
    lr_scheduler_type: str = "linear"
    weight_decay: float = 0.0
    max_grad_norm: float = 1.0
    num_train_epochs: float = 1.0
    per_device_train_batch_size: int = 1
    gradient_accumulation_steps: int = 2   # effective batch 2, matching the organism
    # 256 rather than 512: this GPU also drives the desktop, so the usable budget
    # is well under 8GB. Logged as a deviation in PREREGISTRATION.md §14.
    max_seq_length: int = 256
    # 8-bit optimiser states: ~55M LoRA params cost ~440MB in fp32 AdamW, ~110MB here.
    optim: str = "paged_adamw_8bit"


def build_corpus(cfg: ArmConfig, tokenizer) -> Dataset:
    """Mix narrow and generic text at cfg.narrow_fraction.

    The total example count is held constant across the ladder so that dilution
    varies composition only -- not the amount of training. If total count moved
    with the mixing ratio, the ladder would confound dilution with train steps.
    """
    rng = random.Random(cfg.data_seed)
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

    import transformers
    _dt = "dtype" if int(transformers.__version__.split(".")[0]) >= 5 else "torch_dtype"
    model = AutoModelForCausalLM.from_pretrained(
        cfg.base_model, device_map="cuda", **{_dt: torch.bfloat16}
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
            lr_scheduler_type=cfg.lr_scheduler_type,
            weight_decay=cfg.weight_decay,
            max_grad_norm=cfg.max_grad_norm,
            optim=cfg.optim,
            bf16=True,
            logging_steps=25,
            save_strategy="no",
            report_to=[],
            seed=cfg.seed,
            data_seed=cfg.data_seed,
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
        if missing:
            print("Hyperparameters still using placeholder defaults:")
            for k in missing:
                print(f"  - {k}")
            print("\nN1 is only a MATCHED null once these come from the organism's own")
            print("config. Until then it is an unrelated finetune and the comparison is weaker.")
        else:
            print("All hyperparameters copied from the organism's published config:")
            for k, v in HP_FROM_ORGANISM.items():
                print(f"  {k:32s} = {v}")
            print("\nN1 is a MATCHED null: same LoRA shape, same optimiser settings,")
            print("same base model. Only the training corpus differs.")
        return

    # utf-8-sig, not utf-8: PowerShell 5.1's `Set-Content -Encoding utf8` writes a
    # BOM, which json.loads rejects at char 0. utf-8-sig strips it if present and
    # is a no-op otherwise.
    cfg = ArmConfig(**json.loads(a.config.read_text(encoding="utf-8-sig")))
    print("Saved merged model to:", train_arm(cfg))


if __name__ == "__main__":
    main()
