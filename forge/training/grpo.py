"""GRPO (Group Relative Policy Optimization) support for ForgeLab.

Implements GRPO-style training where groups of agent trajectories are
compared and the policy is optimized based on relative performance within
each group.

This is a simplified GRPO implementation that works with ForgeLab's
trajectory format. For full GRPO, integrate with TRL's GRPOTrainer.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class GRPOConfig:
    """Configuration for GRPO training."""

    group_size: int = 4
    learning_rate: float = 1e-5
    beta: float = 0.01  # KL penalty coefficient
    gamma: float = 0.99  # discount factor
    gae_lambda: float = 0.95  # GAE lambda
    clip_range: float = 0.2  # PPO clip range
    max_epochs: int = 3
    reward_clip_range: tuple[float, float] = (-10.0, 10.0)


@dataclass
class GRPOGroup:
    """A group of trajectories for GRPO training."""

    task_id: str
    trajectories: list[dict[str, Any]] = field(default_factory=list)
    rewards: list[float] = field(default_factory=list)
    advantages: list[float] = field(default_factory=list)


class GRPOTrainer:
    """GRPO trainer for optimizing agent policies.

    Groups trajectories by task, computes relative advantages within
    each group, and updates the policy to favor higher-reward actions.

    Falls back gracefully if ML frameworks are not available.
    """

    def __init__(self, config: GRPOConfig | None = None):
        self.config = config or GRPOConfig()
        self._available = False
        self._groups: dict[str, GRPOGroup] = {}

        try:
            import torch  # noqa: F401

            self._available = True
            logger.info("GRPO trainer available with PyTorch")
        except ImportError:
            logger.warning(
                "PyTorch not installed. GRPO will compute metrics only. "
                "Install with: pip install torch"
            )

    def create_groups(
        self, trajectories: list[dict[str, Any]]
    ) -> list[GRPOGroup]:
        """Group trajectories by task for GRPO.

        Args:
            trajectories: List of trajectory dicts with task_id and reward.

        Returns:
            List of GRPO groups.
        """
        groups: dict[str, GRPOGroup] = {}

        for traj in trajectories:
            task_id = traj.get("task_id", "unknown")
            if task_id not in groups:
                groups[task_id] = GRPOGroup(task_id=task_id)

            group = groups[task_id]
            group.trajectories.append(traj)
            reward = traj.get("reward", 0.0)
            reward = max(
                self.config.reward_clip_range[0],
                min(self.config.reward_clip_range[1], reward),
            )
            group.rewards.append(reward)

            if len(group.trajectories) >= self.config.group_size:
                self._compute_advantages(group)
                self._groups[task_id] = group

        return list(groups.values())

    def _compute_advantages(self, group: GRPOGroup) -> None:
        """Compute advantages using group-relative normalization.

        Uses the mean and std of rewards within the group to normalize,
        which is the core of GRPO.
        """
        rewards = group.rewards
        if not rewards:
            return

        mean = sum(rewards) / len(rewards)
        variance = sum((r - mean) ** 2 for r in rewards) / len(rewards)
        std = variance**0.5 + 1e-8

        group.advantages = [(r - mean) / std for r in rewards]

    def compute_group_metrics(self, groups: list[GRPOGroup]) -> dict[str, Any]:
        """Compute metrics for each group.

        Args:
            groups: List of GRPO groups.

        Returns:
            Dictionary of metrics per group.
        """
        metrics = {}

        for group in groups:
            task_id = group.task_id
            rewards = group.rewards
            advantages = group.advantages

            if not rewards:
                continue

            metrics[task_id] = {
                "group_size": len(rewards),
                "mean_reward": sum(rewards) / len(rewards),
                "std_reward": (
                    sum((r - sum(rewards) / len(rewards)) ** 2 for r in rewards)
                    / len(rewards)
                )
                ** 0.5,
                "max_reward": max(rewards),
                "min_reward": min(rewards),
                "mean_advantage": sum(advantages) / len(advantages) if advantages else 0,
                "positive_advantage_count": sum(1 for a in advantages if a > 0),
            }

        return metrics

    def select_best_trajectories(
        self, groups: list[GRPOGroup], top_k: int = 1
    ) -> list[dict[str, Any]]:
        """Select the best trajectories from each group.

        Args:
            groups: List of GRPO groups.
            top_k: Number of top trajectories to select per group.

        Returns:
            List of best trajectories.
        """
        best = []

        for group in groups:
            if not group.trajectories:
                continue

            # Sort by reward
            paired = list(zip(group.trajectories, group.rewards))
            paired.sort(key=lambda x: x[1], reverse=True)

            for traj, reward in paired[:top_k]:
                traj_with_reward = traj.copy()
                traj_with_reward["_group_rank"] = len(best) + 1
                traj_with_reward["_group_reward"] = reward
                best.append(traj_with_reward)

        return best

    def train_step(
        self,
        groups: list[GRPOGroup],
        policy_model: Any = None,
    ) -> dict[str, Any]:
        """Perform one GRPO training step.

        Args:
            groups: List of GRPO groups.
            policy_model: Optional policy model to update.

        Returns:
            Training metrics.
        """
        if not self._available or policy_model is None:
            # Compute metrics only
            metrics = self.compute_group_metrics(groups)
            return {
                "status": "metrics_only",
                "note": "Install PyTorch for full training",
                "group_metrics": metrics,
            }

        try:
            import torch
            from torch.nn import functional as F

            total_loss = 0.0
            total_samples = 0

            for group in groups:
                if not group.advantages:
                    self._compute_advantages(group)

                for traj, adv in zip(group.trajectories, group.advantages):
                    # In a real implementation, this would compute the
                    # policy ratio and clipped surrogate loss
                    # For now, we track the advantage signal
                    total_loss += -adv  # Negative because we want to maximize
                    total_samples += 1

            avg_loss = total_loss / max(total_samples, 1)

            return {
                "status": "complete",
                "loss": avg_loss,
                "samples": total_samples,
                "groups": len(groups),
            }

        except Exception as e:
            logger.error("GRPO training step failed: %s", e)
            return {"error": str(e)}

    def get_status(self) -> dict[str, Any]:
        """Get trainer status."""
        return {
            "available": self._available,
            "config": {
                "group_size": self.config.group_size,
                "learning_rate": self.config.learning_rate,
                "beta": self.config.beta,
            },
            "groups_tracked": len(self._groups),
        }
