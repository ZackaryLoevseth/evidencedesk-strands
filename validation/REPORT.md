# Validation report — September 7, 2026

## Completed local checks

- **30 automated tests passed**, including core evidence behavior, local API lifecycle, failure cases and strict validation of model JSON. Two upstream Starlette/httpx deprecation warnings were emitted; no failed tests. Command: `.venv/bin/python -m pytest -q`.
- **Real local inference:** Strands Agents SDK 1.54.0, Ollama 0.33.3, `qwen3:1.7b` manifest digest `8f68893c685c3ddff2aa3fffce2aa60a30bb2da65ca488b61fff134a4d1730e7`, temperature 0, thinking disabled, context 4,096, four CPU threads. No paid inference or cloud model was used.
- **Final CLI run:** `live_run_03/case.json`; started 2026-09-07 10:09:15 UTC, ended 10:09:40 UTC; 24.43 seconds, nine actual model calls. All three questions have model-derived findings. The final consistency seal was independently recomputed and matched.
- **Source material:** short excerpts actually captured from the official Strands Get Started and Ollama-provider documentation. The example asks real local-adoption questions. It does not use generated text as historical or published evidence.
- **Packaging:** a Python wheel was built successfully. Source, static UI, and example-source fixtures are included. The source-release process can omit `.runtime`, `.venv`, `.data`, caches and test-install directories; weights and runtime are separately obtained from their official providers.

## Observed model result

| Question | Actual result | Recording path |
|---|---|---|
| Hosted control plane/database requirement | AI explicit; exact quotation verified in S1 paragraph 1 | Actual Strands search + record tools |
| AWS account for local Ollama use | AI explicit; exact quotation verified in S1 paragraph 1 | Actual Strands search + record tools |
| Laptop throughput/availability guarantee | AI unresolved; source does not establish those performance facts | Actual Strands search, then strict application validation of actual model JSON |

The third answer quoted a paragraph comparing SDK feature availability. That string is present, so its **anchor** is verified, but it supplies no performance guarantee. The finding remains **unresolved**. Three verified anchors must not be represented as three supported conclusions.

This is a technology runtime assessment. The statement about no AWS account for local Ollama must not be interpreted as waiving the hackathon's separate AWS account and Builder ID submission requirements.

## Failure-driven changes and preserved history

`live_run_01` and `live_run_02` are earlier genuine executions, retained unchanged. The small model printed the third answer as JSON without issuing the record tool. Initially the application kept the question but supplied a fail-closed unresolved placeholder. A subsequent version tried one explicit model retry; the model again printed JSON.

The final version accepts a strict, validated JSON answer through the same deterministic citation checker and emits a distinct `model_json_validated` event. It does **not** pretend that this post-processing was a model-issued tool call. Unparseable or invalid output still produces an unresolved finding. No successful tool event or model answer was fabricated.

Earlier run seals use the version of the sealing payload at their execution time. The final seal also binds source snapshots and questions. Use `live_run_03` for current behavior; the historical files are diagnostic evidence, not the current demo baseline.

## Limits

- Passing quote checks establishes exact occurrence in a local snapshot, not correctness, publisher identity, comprehensive research, or semantic entailment.
- Only the included brief was exercised with the live model in these CLI runs. This is not a general model-accuracy benchmark or measured productivity study.
- The local UI/API is a single-user build, not an authenticated public service. Model weights occupied approximately 1.266 GiB on disk. Peak process memory was not measured during these CLI runs; no precise peak-RAM claim is made.
- HTML intake omits code blocks, tables and original layout; retrieval sees at most three passages of at most 1,800 characters each. Supplied snapshots can omit decisive context.
- Source fetching uses the network. Inference only connects to loopback Ollama, whose cloud features were disabled for this validation. This was not an OS-level network-isolation test.
- Public repository/video publication, human registration/account details, and submission receipt are separate. This report does not claim they are complete.

Actual browser-driven end-to-end demonstration and downloaded packet verification can be recorded separately by the publishing workflow without modifying the frozen CLI run files.

## Reviewer attribution update

The review schema now requires an explicit human/automated type and reviewer name. New records have no implicit human default. UI and exported reports show the attribution; historical records without it remain unchanged and display unspecified. Three added tests cover API rejection without attribution, automated attribution through ZIP export, preservation of legacy records, and explicit human choice. This change does not alter frozen model-run files. App construction was also moved to a server factory so importing the module for tests does not recover or touch a live user workspace.
