"""Hugging Face TRL integration for ForgeLab.

Connects verified trajectories to Hugging Face TRL (Transformer Reinforcement
Learning) for supervised fine-tuning and reinforcement learning.

Configuration via environment variables:
    HF_TOKEN - Hugging Face API token
    HF_MODEL_NAME - Model to fine-tune (default: meta-llama/Llama-3.1-8B)
    HF_OUTPUT_DIR - Output directory for saved models

Requires: pip install trl transformers accelerate peft
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TRLConfig:
    """Configuration for TRL training."""

    model_name: str = "meta-llama/Llama-3.1-8B"
    output_dir: str = "./trl_output"
    learning_rate: float = 2e-5
    num_train_epochs: int = 3
    per_device_train_batch_size: int = 1
    gradient_accumulation_steps: int = 4
    max_steps: int = 1000
    logging_steps: int = 10
    save_steps: int = 100
    eval_steps: int = 100
    warmup_steps: int = 100
    weight_decay: float = 0.01
    max_prompt_length: int = 1024
    max_completion_length: int = 512
    use_peft: bool = True
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05


@dataclass
class SFTSample:
    """A supervised fine-tuning sample."""

    prompt: str
    completion: str
    reward: float = 0.0


class TRLTrainer:
    """Hugging Face TRL integration for training on ForgeLab trajectories.

    Converts verified trajectories to SFT (Supervised Fine-Tuning) format
    and trains using TRL library. Falls back gracefully if TRL is not installed.
    """

    def __init__(self, config: TRLConfig | None = None):
        self.config = config or TRLConfig()
        self._available = False
        self._model = None
        self._tokenizer = None
        self._trainer = None

        try:
            import trl  # noqa: F401

            self._available = True
            logger.info("TRL integration available")
        except ImportError:
            logger.warning(
                "TRL not installed. Install with: pip install trl transformers accelerate peft"
            )

    def prepare_sft_dataset(
        self, trajectories: list[dict[str, Any]], output_path: str | None = None
    ) -> list[SFTSample]:
        """Convert trajectories to SFT format.

        Args:
            trajectories: List of trajectory dictionaries.
            output_path: Optional path to save dataset as JSONL.

        Returns:
            List of SFT samples.
        """
        samples = []

        for traj in trajectories:
            steps = traj.get("steps", [])
            if not steps:
                continue

            # Build prompt from task description
            task_desc = traj.get("task_description", "")
            prompt = f"Fix the following bug:\n\n{task_desc}\n\nYour fix:"

            # Build completion from successful tool calls
            completion_parts = []
            for step in steps:
                if step.get("success"):
                    tool = step.get("tool_name", "")
                    tool_input = step.get("tool_input", {})
                    if tool == "write_file":
                        completion_parts.append(
                            f"# {tool_input.get('path', 'file')}\n{tool_input.get('content', '')}"
                        )
                    elif tool == "edit_file":
                        completion_parts.append(
                            f"# Edit: {tool_input.get('path', 'file')}\n"
                            f"Replace: {tool_input.get('old_text', '')}\n"
                            f"With: {tool_input.get('new_text', '')}"
                        )

            completion = "\n\n".join(completion_parts) if completion_parts else "# No changes"
            reward = traj.get("reward", 0.0)

            samples.append(SFTSample(prompt=prompt, completion=completion, reward=reward))

        if output_path:
            with open(output_path, "w") as f:
                for sample in samples:
                    f.write(
                        json.dumps(
                            {
                                "prompt": sample.prompt,
                                "completion": sample.completion,
                                "reward": sample.reward,
                            }
                        )
                        + "\n"
                    )
            logger.info("Saved %d SFT samples to %s", len(samples), output_path)

        return samples

    def train_sft(
        self,
        samples: list[SFTSample],
        dataset: Any = None,
    ) -> dict[str, Any]:
        """Train using Supervised Fine-Tuning.

        Args:
            samples: List of SFT samples.
            dataset: Optional Hugging Face dataset.

        Returns:
            Training metrics.
        """
        if not self._available:
            return {"error": "TRL not installed", "samples": len(samples)}

        try:
            from datasets import Dataset
            from transformers import (
                AutoModelForCausalLM,
                AutoTokenizer,
                TrainingArguments,
            )
            from trl import SFTTrainer

            if dataset is None:
                # Convert samples to HF dataset
                data = [
                    {"text": f"{s.prompt}{s.completion}"} for s in samples
                ]
                dataset = Dataset.from_list(data)

            # Load model and tokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)
            if self._tokenizer.pad_token is None:
                self._tokenizer.pad_token = self._tokenizer.eos_token

            self._model = AutoModelForCausalLM.from_pretrained(
                self.config.model_name,
                torch_dtype="auto",
                device_map="auto",
            )

            # Training arguments
            training_args = TrainingArguments(
                output_dir=self.config.output_dir,
                learning_rate=self.config.learning_rate,
                num_train_epochs=self.config.num_train_epochs,
                per_device_train_batch_size=self.config.per_device_train_batch_size,
                gradient_accumulation_steps=self.config.gradient_accumulation_steps,
                logging_steps=self.config.logging_steps,
                save_steps=self.config.save_steps,
                warmup_steps=self.config.warmup_steps,
                weight_decay=self.config.weight_decay,
                fp16=True,
                report_to="none",
            )

            # Create trainer
            self._trainer = SFTTrainer(
                model=self._model,
                tokenizer=self._tokenizer,
                train_dataset=dataset,
                dataset_text_field="text",
                max_seq_length=self.config.max_prompt_length
                + self.config.max_completion_length,
                args=training_args,
            )

            # Train
            metrics = self._trainer.train()

            # Save model
            self._trainer.save_model(self.config.output_dir)

            logger.info("SFT training complete: %s", self.config.output_dir)
            return {
                "status": "complete",
                "output_dir": self.config.output_dir,
                "metrics": {
                    "train_loss": getattr(metrics, "loss", None),
                    "epochs": self.config.num_train_epochs,
                },
            }

        except Exception as e:
            logger.error("SFT training failed: %s", e)
            return {"error": str(e)}

    def train_dpo(
        self,
        preferred_samples: list[SFTSample],
        rejected_samples: list[SFTSample],
    ) -> dict[str, Any]:
        """Train using Direct Preference Optimization.

        Args:
            preferred_samples: Samples with correct fixes.
            rejected_samples: Samples with incorrect fixes.

        Returns:
            Training metrics.
        """
        if not self._available:
            return {
                "error": "TRL not installed",
                "preferred": len(preferred_samples),
                "rejected": len(rejected_samples),
            }

        try:
            from datasets import Dataset
            from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
            from trl import DPOTrainer

            # Prepare DPO dataset
            data = []
            for pref, rej in zip(preferred_samples, rejected_samples):
                data.append(
                    {
                        "prompt": pref.prompt,
                        "chosen": pref.completion,
                        "rejected": rej.completion,
                    }
                )

            dataset = Dataset.from_list(data)

            self._tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)
            if self._tokenizer.pad_token is None:
                self._tokenizer.pad_token = self._tokenizer.eos_token

            self._model = AutoModelForCausalLM.from_pretrained(
                self.config.model_name,
                torch_dtype="auto",
                device_map="auto",
            )

            training_args = TrainingArguments(
                output_dir=self.config.output_dir,
                learning_rate=self.config.learning_rate,
                per_device_train_batch_size=self.config.per_device_train_batch_size,
                num_train_epochs=self.config.num_train_epochs,
                report_to="none",
            )

            self._trainer = DPOTrainer(
                model=self._model,
                ref_model=None,
                tokenizer=self._tokenizer,
                train_dataset=dataset,
                args=training_args,
                beta=0.1,
                max_prompt_length=self.config.max_prompt_length,
                max_completion_length=self.config.max_completion_length,
            )

            metrics = self._trainer.train()
            self._trainer.save_model(self.config.output_dir)

            return {
                "status": "complete",
                "output_dir": self.config.output_dir,
                "samples": len(data),
            }

        except Exception as e:
            logger.error("DPO training failed: %s", e)
            return {"error": str(e)}

    def get_status(self) -> dict[str, Any]:
        """Get trainer status."""
        return {
            "available": self._available,
            "config": {
                "model_name": self.config.model_name,
                "output_dir": self.config.output_dir,
            },
        }
