"""
Batch Indexing Pipeline for Lumina product catalog.

Reads images from a directory, generates SigLIP embeddings,
and upserts vectors to Qdrant with progress tracking.

Usage:
    indexer = BatchIndexer(batch_size=32)
    stats = await indexer.index_directory("/path/to/product_images/")
    print(stats)  # {"total": 1000, "indexed": 987, "failed": 13, "elapsed_s": 45.2}
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field, asdict

from PIL import Image

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
STATUS_FILE = "indexing_status.json"


@dataclass
class IndexingStats:
    """Progress tracking for a batch indexing run."""

    total: int = 0
    indexed: int = 0
    skipped: int = 0
    failed: int = 0
    elapsed_seconds: float = 0.0
    errors: list[dict[str, str]] = field(default_factory=list)
    status: str = "pending"  # pending | running | completed | failed

    @property
    def progress_pct(self) -> float:
        if self.total == 0:
            return 0.0
        return round((self.indexed + self.skipped + self.failed) / self.total * 100, 1)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["progress_pct"] = self.progress_pct
        # Trim errors to last 50 for readability
        d["errors"] = d["errors"][-50:]
        return d


class BatchIndexer:
    """
    Batch indexing pipeline with progress tracking and checkpointing.

    Args:
        batch_size: Number of images to process before upserting
        checkpoint_dir: Directory for status files
    """

    def __init__(
        self,
        batch_size: int = 32,
        checkpoint_dir: str = "/tmp/lumina_indexing",
    ) -> None:
        self.batch_size = batch_size
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._stats = IndexingStats()

    def _save_checkpoint(self) -> None:
        """Persist current progress to disk."""
        status_path = self.checkpoint_dir / STATUS_FILE
        with open(status_path, "w") as f:
            json.dump(self._stats.to_dict(), f, indent=2)

    def get_status(self) -> dict[str, Any]:
        """Return current indexing status."""
        return self._stats.to_dict()

    @staticmethod
    def _discover_images(directory: str) -> list[Path]:
        """Find all supported image files in directory tree."""
        root = Path(directory)
        if not root.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        images: list[Path] = []
        for ext in SUPPORTED_EXTENSIONS:
            images.extend(root.rglob(f"*{ext}"))
        return sorted(images)

    @staticmethod
    def _validate_image(path: Path) -> bool:
        """Check if file is a valid, non-corrupt image."""
        try:
            with Image.open(path) as img:
                img.verify()
            return True
        except Exception:
            return False

    async def index_directory(
        self,
        directory: str,
        embedding_fn: Any = None,
        upsert_fn: Any = None,
    ) -> dict[str, Any]:
        """
        Index all images in a directory.

        Args:
            directory: Path to image directory
            embedding_fn: async callable(PIL.Image) -> list[float]
            upsert_fn: callable(embedding, payload) -> str
        """
        self._stats = IndexingStats(status="running")
        start_time = time.monotonic()

        images = self._discover_images(directory)
        self._stats.total = len(images)
        logger.info("Discovered %d images in %s", len(images), directory)
        self._save_checkpoint()

        batch_embeddings: list[tuple[list[float], dict[str, str]]] = []

        for i, img_path in enumerate(images):
            try:
                # Validate
                if not self._validate_image(img_path):
                    self._stats.skipped += 1
                    self._stats.errors.append(
                        {"file": str(img_path), "error": "corrupt or invalid image"}
                    )
                    continue

                # Generate embedding
                if embedding_fn is not None:
                    img = Image.open(img_path).convert("RGB")
                    embedding = await embedding_fn(img)
                else:
                    # Placeholder for when no embedding function is provided
                    embedding = [0.0] * 768

                payload = {
                    "filename": img_path.name,
                    "path": str(img_path),
                    "indexed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }

                batch_embeddings.append((embedding, payload))

                # Flush batch
                if len(batch_embeddings) >= self.batch_size:
                    await self._flush_batch(batch_embeddings, upsert_fn)
                    batch_embeddings = []

            except Exception as exc:
                self._stats.failed += 1
                self._stats.errors.append(
                    {"file": str(img_path), "error": str(exc)}
                )
                logger.warning("Failed to index %s: %s", img_path, exc)

            # Checkpoint every 100 images
            if (i + 1) % 100 == 0:
                self._stats.elapsed_seconds = time.monotonic() - start_time
                self._save_checkpoint()
                logger.info("Progress: %s%%", self._stats.progress_pct)

        # Flush remaining
        if batch_embeddings:
            await self._flush_batch(batch_embeddings, upsert_fn)

        self._stats.elapsed_seconds = time.monotonic() - start_time
        self._stats.status = "completed"
        self._save_checkpoint()

        logger.info(
            "Indexing complete: %d indexed, %d skipped, %d failed in %.1fs",
            self._stats.indexed,
            self._stats.skipped,
            self._stats.failed,
            self._stats.elapsed_seconds,
        )
        return self._stats.to_dict()

    async def _flush_batch(
        self,
        batch: list[tuple[list[float], dict[str, str]]],
        upsert_fn: Any,
    ) -> None:
        """Upsert a batch of embeddings to the vector store."""
        for embedding, payload in batch:
            try:
                if upsert_fn is not None:
                    upsert_fn(embedding, payload)
                self._stats.indexed += 1
            except Exception as exc:
                self._stats.failed += 1
                self._stats.errors.append(
                    {"file": payload.get("filename", "unknown"), "error": str(exc)}
                )
