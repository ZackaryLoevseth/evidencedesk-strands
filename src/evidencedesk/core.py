"""Pure evidence checks; these never rely on a language model's verdict."""
from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import re
import unicodedata
import zipfile
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize(text: str) -> str:
    """Normalize Unicode and whitespace only; punctuation/word changes still fail."""
    return " ".join(unicodedata.normalize("NFC", text).split())


class SourceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    url: str = Field(max_length=2000)
    text: str = Field(min_length=20, max_length=30000)

    @field_validator("url")
    @classmethod
    def public_url(cls, value: str) -> str:
        parts = urlsplit(value)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
            raise ValueError("Use an https source URL without embedded credentials.")
        return value


class CaseInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=3, max_length=160)
    questions: list[str] = Field(min_length=1, max_length=8)
    sources: list[SourceInput] = Field(min_length=1, max_length=6)

    @field_validator("questions")
    @classmethod
    def questions_valid(cls, value: list[str]) -> list[str]:
        cleaned = [q.strip() for q in value]
        if any(not q or len(q) > 600 for q in cleaned):
            raise ValueError("Each question must contain 1–600 characters.")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("Remove duplicate questions.")
        return cleaned


class ReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question_id: str
    decision: Literal["accept", "inference", "reject", "needs_review"]
    note: str = Field(min_length=3, max_length=2000)
    reviewer_type: Literal["human", "automated"]
    reviewer_name: str = Field(min_length=1, max_length=100)

    @field_validator("reviewer_name")
    @classmethod
    def reviewer_name_valid(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Name the human or automated reviewer.")
        return value.strip()


def make_source(source: SourceInput, index: int, acquisition: str = "user_supplied") -> dict:
    paragraphs = [normalize(p) for p in re.split(r"\n\s*\n", source.text) if normalize(p)]
    # Long pasted paragraphs are retained intact. Paragraph numbers refer to this snapshot.
    text = "\n\n".join(paragraphs)
    return {"id": f"S{index}", "title": source.title, "url": source.url,
            "text": text, "sha256": digest(text), "captured_at": now(),
            "acquisition": acquisition,
            "paragraphs": [{"number": i + 1, "text": p} for i, p in enumerate(paragraphs)]}


def create_case(data: CaseInput) -> dict:
    return {"title": data.title, "created_at": now(),
            "questions": [{"id": f"Q{i+1}", "text": q} for i, q in enumerate(data.questions)],
            "sources": [make_source(s, i+1) for i, s in enumerate(data.sources)],
            "status": "ready", "findings": [], "events": [], "reviews": [],
            "run": None, "error": None}


def verify_quote(sources: list[dict], source_id: str, paragraph: int, quote: str) -> dict:
    source = next((s for s in sources if s["id"] == source_id), None)
    if not source:
        return {"status": "invalid", "reason": "Unknown source identifier."}
    if source["sha256"] != digest(source["text"]):
        return {"status": "invalid", "reason": "Source snapshot digest changed."}
    expected_paragraphs = [normalize(p) for p in re.split(r"\n\s*\n", source["text"]) if normalize(p)]
    if source["paragraphs"] != [{"number": i+1, "text": p} for i, p in enumerate(expected_paragraphs)]:
        return {"status": "invalid", "reason": "Paragraph index differs from the sealed source."}
    if not 1 <= paragraph <= len(source["paragraphs"]):
        return {"status": "invalid", "reason": "Paragraph does not exist in the snapshot."}
    needle = normalize(quote)
    if len(needle) < 15:
        return {"status": "invalid", "reason": "Quotation is too short for a useful anchor (15 characters minimum)."}
    text = source["paragraphs"][paragraph - 1]["text"]
    if needle not in text:
        return {"status": "invalid", "reason": "Quotation is not an exact substring of the cited paragraph."}
    return {"status": "verified", "reason": "Exact quotation appears in the sealed paragraph; meaning still needs review.",
            "source_id": source_id, "paragraph": paragraph, "quote": needle,
            "start": text.index(needle), "end": text.index(needle) + len(needle),
            "source_sha256": source["sha256"], "url": source["url"]}


STOPWORDS = {"the", "and", "with", "this", "that", "does", "what", "which", "are", "for", "can", "how", "from", "into", "will", "have", "using", "about"}


def search_sources(sources: list[dict], query: str, limit: int = 5) -> list[dict]:
    words = {w for w in re.findall(r"[a-z0-9]+", query.lower()) if len(w) > 2 and w not in STOPWORDS}
    rows = []
    for source in sources:
        for p in source["paragraphs"]:
            tokens = set(re.findall(r"[a-z0-9]+", p["text"].lower()))
            score = len(words & tokens)
            if score:
                rows.append({"source_id": source["id"], "paragraph": p["number"],
                             "title": source["title"], "text": p["text"][:1800], "score": score})
    return sorted(rows, key=lambda r: (-r["score"], r["source_id"], r["paragraph"]))[:limit]


def grounded_finding(case: dict, question_id: str, assessment: str, explanation: str,
                     source_id: str = "", paragraph: int = 0, quote: str = "", next_step: str = "") -> dict:
    if question_id not in {q["id"] for q in case["questions"]}:
        raise ValueError("Unknown question ID.")
    if assessment not in {"explicit", "inference", "unresolved"}:
        raise ValueError("assessment must be explicit, inference, or unresolved.")
    check = verify_quote(case["sources"], source_id, paragraph, quote) if quote else {
        "status": "missing", "reason": "No quotation supplied."}
    effective = assessment
    if assessment in {"explicit", "inference"} and check["status"] != "verified":
        effective = "unresolved"
    return {"question_id": question_id, "assessment": effective,
            "model_assessment": assessment, "explanation": explanation[:2500],
            "proposed_citation": {"source_id": source_id, "paragraph": paragraph, "quote": quote},
            "citation": check, "next_step": next_step[:1200], "review_status": "needs_review"}


def finalize_findings(case: dict, findings: list[dict]) -> list[dict]:
    by_id = {f["question_id"]: f for f in findings}
    return [by_id.get(q["id"], {"question_id": q["id"], "assessment": "unresolved",
            "model_assessment": None, "explanation": "The agent did not produce a valid recorded finding for this question.",
            "citation": {"status": "missing", "reason": "No agent finding recorded."},
            "next_step": "Inspect the sources or run again with a more capable local model.",
            "review_status": "needs_review"}) for q in case["questions"]]


def seal_run(case: dict) -> str:
    return digest(canonical({"title": case["title"], "questions": case["questions"], "sources": case["sources"],
                             "run": case["run"], "findings": case["findings"], "events": case["events"]}))


def report_markdown(case: dict) -> str:
    out = [f"# {case['title']}", "", "EvidenceDesk review packet", "",
           "AI assessments are proposals. Exact-source quotation checks do not prove the interpretation or completeness of research.",
           "This packet concerns the supplied snapshots only; it makes no legal conclusion.", "",
           f"Case: {case.get('id', 'local')} · Created: {case['created_at']}",
           f"Run state: {case['status']} · Model: {(case.get('run') or {}).get('model', 'not run')}", ""]
    if case.get("error"):
        out.extend([f"Run limitation: {case['error']}", ""])
    latest = {r["question_id"]: r for r in case["reviews"]}
    for q in case["questions"]:
        f = next((f for f in case["findings"] if f["question_id"] == q["id"]), None)
        out.extend([f"## {q['id']} — {q['text']}", ""])
        if not f:
            out.extend(["Not yet analyzed.", ""])
            continue
        out.extend([f"AI assessment: **{f['assessment']}** · Citation: **{f['citation']['status']}**", "", f["explanation"], ""])
        cite = f["citation"]
        if cite["status"] == "verified":
            out.extend(["> " + cite["quote"].replace("\n", " "), "",
                        f"Source: {cite['source_id']}, snapshot paragraph {cite['paragraph']}; {cite['url']}",
                        f"Snapshot SHA-256: `{cite['source_sha256']}`", ""])
        else:
            out.extend([cite["reason"], ""])
        if f["next_step"]:
            out.extend([f"Next evidence needed: {f['next_step']}", ""])
        review = latest.get(q["id"])
        if review:
            reviewer_type = review.get("reviewer_type", "unspecified")
            reviewer_name = review.get("reviewer_name", "not recorded")
            out.extend([f"Review: **{review['decision']}** — {review['note']}",
                        f"Attribution: {reviewer_type} reviewer — {reviewer_name}", ""])
        else:
            out.extend(["Review: **pending** — no reviewer decision recorded.", ""])
    out.extend(["## Source register", ""])
    for s in case["sources"]:
        out.extend([f"- {s['id']} · {s['title']} · {s['url']}",
                    f"  Captured: {s['captured_at']} · Acquisition: {s['acquisition']} · SHA-256: `{s['sha256']}`"])
    out.extend(["", "Source paragraph numbers belong to the normalized local snapshot, not publication page/line numbering.",
                "See agent-run.json for original model proposals and review-ledger.json for subsequent attributed annotations."])
    return "\n".join(out) + "\n"


def export_packet(case: dict) -> bytes:
    files: dict[str, bytes] = {}
    md = report_markdown(case)
    files["review-packet.md"] = md.encode()
    # Escaped preformatted text is printable and works without scripts or external assets.
    files["review-packet.html"] = ("<!doctype html><meta charset='utf-8'><title>EvidenceDesk packet</title>"
        "<style>body{font:15px/1.6 system-ui;max-width:900px;margin:40px auto;padding:20px}pre{white-space:pre-wrap;overflow-wrap:anywhere}"
        "@media print{body{margin:0;padding:0}pre{font-size:11px}}</style><pre>" + html.escape(md) + "</pre>").encode()
    files["agent-run.json"] = json.dumps({"title": case["title"], "questions": case["questions"], "sources": case["sources"],
                                         "run": case["run"], "findings": case["findings"],
                                         "events": case["events"], "seal": case.get("run_seal")}, indent=2, ensure_ascii=False).encode()
    files["review-ledger.json"] = json.dumps(case["reviews"], indent=2, ensure_ascii=False).encode()
    files["case.json"] = json.dumps(case, indent=2, ensure_ascii=False).encode()
    for s in case["sources"]:
        files[f"sources/{s['id']}.txt"] = s["text"].encode()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["question_id", "question", "ai_assessment", "citation_status", "source", "paragraph", "next_step"])
    for q in case["questions"]:
        f = next((f for f in case["findings"] if f["question_id"] == q["id"]), {})
        c = f.get("citation", {})
        cells = [q["id"], q["text"], f.get("assessment", "not_run"), c.get("status", "missing"), c.get("source_id", ""), c.get("paragraph", ""), f.get("next_step", "")]
        # Neutralize spreadsheet formula interpretation without mutating original JSON/text evidence.
        writer.writerow(["'" + c if isinstance(c, str) and c.lstrip().startswith(("=", "+", "-", "@")) else c for c in cells])
    files["coverage.csv"] = buffer.getvalue().encode()
    files["SHA256SUMS"] = "\n".join(hashlib.sha256(data).hexdigest() + "  " + name for name, data in sorted(files.items())).encode() + b"\n"
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name, content in files.items():
            z.writestr(name, content)
    return out.getvalue()
