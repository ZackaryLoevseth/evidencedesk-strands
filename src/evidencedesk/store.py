from __future__ import annotations

import json
import os
import re
import threading
import uuid
from pathlib import Path

from .core import ReviewInput, now, seal_run


class Store:
    def __init__(self, directory: str | Path):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()

    def path(self, case_id: str) -> Path:
        if not re.fullmatch(r"[a-f0-9]{16}", case_id):
            raise KeyError("Unknown case.")
        return self.directory / (case_id + ".json")

    def save(self, case: dict):
        with self.lock:
            if "id" not in case:
                case["id"] = uuid.uuid4().hex[:16]
            path = self.path(case["id"])
            temporary = path.with_suffix(".tmp")
            temporary.write_text(json.dumps(case, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temporary, path)
        return case

    def get(self, case_id: str) -> dict:
        with self.lock:
            try:
                return json.loads(self.path(case_id).read_text(encoding="utf-8"))
            except FileNotFoundError:
                raise KeyError("Unknown case.") from None

    def list(self) -> list[dict]:
        with self.lock:
            cases = [json.loads(p.read_text(encoding="utf-8")) for p in self.directory.glob("*.json")]
        return sorted([{"id": c["id"], "title": c["title"], "status": c["status"],
                        "created_at": c["created_at"], "questions": len(c["questions"])} for c in cases],
                      key=lambda c: c["created_at"], reverse=True)

    def review(self, case_id: str, review: dict) -> dict:
        with self.lock:
            review = ReviewInput.model_validate(review).model_dump()
            case = self.get(case_id)
            if case["status"] not in {"completed", "completed_with_gaps"}:
                raise ValueError("Run the agent before reviewing its findings.")
            if case.get("run_seal") != seal_run(case):
                raise ValueError("Original agent run changed; review cannot be attached.")
            if review["question_id"] not in {q["id"] for q in case["questions"]}:
                raise ValueError("Unknown question.")
            case["reviews"].append({**review, "at": now(), "agent_run_seal": case["run_seal"]})
            return self.save(case)

    def recover(self):
        """A process restart never leaves a case pretending that inference is ongoing."""
        for summary in self.list():
            if summary["status"] in {"queued", "running"}:
                case = self.get(summary["id"])
                case["status"] = "interrupted"
                case["error"] = "Application stopped during inference. Create a new run to retry."
                self.save(case)
