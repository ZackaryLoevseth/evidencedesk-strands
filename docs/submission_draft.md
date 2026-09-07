# EvidenceDesk — source-anchored research handoffs

Track: Professional Agents

## Inspiration

Professional research often stalls between an AI-generated answer and a decision-ready handoff. A colleague needs exact source context, the unresolved questions, and a record of what a human actually reviewed. A link-rich chat response does not supply that chain on its own.

## What it does

EvidenceDesk takes a focused research brief and public-source excerpts, invokes a local Strands agent to search the evidence and record findings, validates quotation anchors against sealed snapshot paragraphs, and produces a portable review packet. Every input question remains present, including failures and gaps. Decisions explicitly attributed to human or automated reviewers are appended separately from original model output.

## How we built it

Python 3.12, Strands Agents SDK 1.54.0, a real Ollama/Qwen3 local model, FastAPI, a lightweight accessible browser interface, deterministic citation checks, atomic local persistence, and portable ZIP exports. Strands owns the actual model/tool loop. Each question has its own conversation and a bounded model-call budget. No cloud inference or paid provider fallback is configured.

## Challenges and decisions

A small model sometimes prints an answer without calling the recording tool. EvidenceDesk retries once, then validates a strict JSON response through the same deterministic checker, recording that fallback distinctly from a model-issued tool call. If no valid finding is available, the question remains unresolved. Quotation matching is intentionally narrower than verifying meaning: an exact quote can still be irrelevant or overinterpreted. That distinction is visible in the UI and exports.

## What is demonstrated

The demonstration evaluates local Strands adoption using attributed official documentation excerpts. It includes genuine source search and record tool calls, checked quotation anchors, an unanswered performance question, an explicitly attributed review note, and a downloaded review packet. See validation/REPORT.md for actual observed results and limitations; do not infer accuracy beyond those checks.

## Next steps

Richer paragraph retrieval, source-version comparison, multiple independent reviewers, and a hosted authenticated workspace could extend the local workflow. None is represented as already implemented.

## AI and third-party disclosure

OpenAI Codex assisted development, tests, and documentation. No prior application implementation was imported. Strands/Ollama/Qwen and other standard dependencies retain their own licenses. Example source passages are attributed to their publishers. Original application code is MIT licensed.

## Testing instructions

Use the public source repository or release test build with the README's Python/Ollama setup. Start `evidencedesk serve`, open the local page, load the real-source example, and run it. The local model is a free separate download. The test build must remain available through October 8, 2026. A hosted live deployment is not supplied.

## Submission fields still requiring completion

- Public repository/release URL: supplied by the publishing workflow.
- Public YouTube or Vimeo demo URL (at most five minutes): supplied after recording and upload.
- Entrant's AWS Builder ID and required account/registration details: supplied by the entrant.
- Final affiliation/conflict-of-interest and account eligibility answers: entrant confirmation.

No accepted submission, award, measured productivity improvement, or guaranteed source accuracy is claimed.
