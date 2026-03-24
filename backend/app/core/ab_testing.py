"""
A/B Testing Router for embedding model comparison.

Routes a configurable percentage of search traffic to a challenger model,
logs recall@k metrics for both champion and challenger, and exposes
a comparison endpoint.

Usage:
    router = ABTestRouter(challenger_traffic_pct=10)
    model_version = router.route_request(request_id)
    router.log_result(request_id, model_version, recall_at_k=0.92)
"""

import random
import time
import logging
from typing import Optional
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class ABMetrics:
    """Accumulated metrics for one model variant."""

    total_requests: int = 0
    total_recall: float = 0.0
    total_latency_ms: float = 0.0
    recall_samples: list[float] = field(default_factory=list)

    @property
    def avg_recall(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_recall / self.total_requests

    @property
    def avg_latency_ms(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_latency_ms / self.total_requests

    def to_dict(self) -> dict:
        return {
            "total_requests": self.total_requests,
            "avg_recall_at_k": round(self.avg_recall, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "last_10_recall": [round(r, 4) for r in self.recall_samples[-10:]],
        }


class ABTestRouter:
    """
    Routes traffic between champion (v1) and challenger (v2) models.

    Args:
        challenger_traffic_pct: Percentage of traffic routed to challenger (0-100)
        champion_version: Version string for the champion model
        challenger_version: Version string for the challenger model
    """

    def __init__(
        self,
        challenger_traffic_pct: int = 10,
        champion_version: str = "v1",
        challenger_version: str = "v2",
    ) -> None:
        self.challenger_traffic_pct = max(0, min(100, challenger_traffic_pct))
        self.champion_version = champion_version
        self.challenger_version = challenger_version
        self._metrics: dict[str, ABMetrics] = {
            champion_version: ABMetrics(),
            challenger_version: ABMetrics(),
        }
        self._request_assignments: dict[str, str] = {}

    def route_request(self, request_id: str) -> str:
        """Assign a request to champion or challenger model."""
        roll = random.randint(1, 100)
        version = (
            self.challenger_version
            if roll <= self.challenger_traffic_pct
            else self.champion_version
        )
        self._request_assignments[request_id] = version
        return version

    def log_result(
        self,
        request_id: str,
        model_version: str,
        recall_at_k: float,
        latency_ms: float,
    ) -> None:
        """Log recall@k and latency for a completed request."""
        if model_version not in self._metrics:
            self._metrics[model_version] = ABMetrics()

        metrics = self._metrics[model_version]
        metrics.total_requests += 1
        metrics.total_recall += recall_at_k
        metrics.total_latency_ms += latency_ms
        metrics.recall_samples.append(recall_at_k)

        # Keep only last 1000 samples to avoid unbounded memory growth
        if len(metrics.recall_samples) > 1000:
            metrics.recall_samples = metrics.recall_samples[-500:]

        # Clean up assignment tracking
        self._request_assignments.pop(request_id, None)

    def get_comparison(self) -> dict:
        """Return side-by-side comparison of champion vs challenger."""
        return {
            "challenger_traffic_pct": self.challenger_traffic_pct,
            "champion": {
                "version": self.champion_version,
                **self._metrics[self.champion_version].to_dict(),
            },
            "challenger": {
                "version": self.challenger_version,
                **self._metrics[self.challenger_version].to_dict(),
            },
        }

    def update_traffic_split(self, new_pct: int) -> None:
        """Dynamically update the traffic split percentage."""
        self.challenger_traffic_pct = max(0, min(100, new_pct))
        logger.info("A/B traffic split updated: %d%% challenger", new_pct)


# Global A/B test router instance
ab_router = ABTestRouter(challenger_traffic_pct=10)
