# AI assistance disclosure

OpenAI Codex assisted with product design, all initial application code, tests, documentation, and review. The project was created during the September 2026 hackathon submission period. The entrant should personally inspect and understand the result before submitting it; no claim of unaided authorship is made.

The original product direction is a professional evidence-intake/review workflow: preserve provenance, distinguish quotation verification from semantic support, keep unresolved questions, retain original agent findings, and export a separate human review ledger. No earlier application implementation or private research files were imported.

Application reasoning is separate from development assistance. The live application invokes the actual Strands SDK with a locally downloaded Qwen3 model through the Ollama provider. The recorded tool events and outputs in `validation/` come from those executions. Synthetic test fixtures are confined to tests and are labeled as synthetic. Example documentation excerpts retain their source URLs.
