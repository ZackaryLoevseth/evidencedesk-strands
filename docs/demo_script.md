# EvidenceDesk demo — approximately 3 minutes 30 seconds

Record the real local UI. Do not claim a replay is live inference. No public upload has been performed by this script.

**0:00–0:25 — Problem and audience.** Show the intake page.

“Research teams often leave a meeting with an answer and a pile of links. The next reviewer still has to find the exact source, check what it says, and discover which questions were never resolved. EvidenceDesk turns that repetitive handoff into a reviewable evidence packet.”

**0:25–0:55 — Inputs and actual scope.** Click Load real-source example; briefly open a source.

“Here is a real adoption brief: can our team run Strands locally? The snapshots come from official Strands documentation. I ask about the hosted control plane, whether an AWS account is required for local Ollama use, and what performance guarantee these documents establish for our laptop. Each source keeps its URL and full captured paragraph context.”

**0:55–1:35 — Actual Strands execution.** Click Create brief & analyze; let the tool activity appear. This model typically takes tens of seconds; do not promise a fixed runtime. Use any waiting time to show the actual activity panel.

“This invokes a real Strands agent with a local Qwen model through Ollama. Strands searches the sealed sources and calls a tool to record each finding. The record tool checks that a proposed quotation appears in the exact cited paragraph. The model cannot fetch arbitrary sites, modify original evidence, or silently drop a question.”

**1:35–2:20 — Review two supported answers and the gap.** Read the actual final results, not a predetermined script. Open an exact quotation context. If the model failed to record a question, show that failure honestly and its unresolved fallback.

“This quote is verified as source text. That does not prove the model's interpretation. I can inspect the whole paragraph. The performance question remains unresolved because the supplied documentation does not establish our laptop's measured throughput or availability. That gap stays in the packet.”

**2:20–2:50 — Attributed review.** For a Codex-operated demonstration, explicitly select Automated and enter Codex automated review. A person should select Human only for their own actual review. Enter a true review note after checking the paragraph, such as: “Checked S1 paragraph 1. This concerns SDK runtime, not the hackathon's separate AWS account requirements.” Select Accept interpretation for the appropriate finding and save.

“My review is appended separately. The original model finding and source snapshots are preserved, with a consistency seal. Another reviewer can see what the model proposed and who or what reviewed it, and which interpretation was accepted.”

**2:50–3:20 — Export.** Click Export review packet; open the downloaded ZIP and readable review-packet.html if convenient.

“The handoff contains the readable review, every original model finding, the attributed review ledger, source snapshots, a coverage table, and SHA-256 file checks. It opens without the app and does not require the recipient to reconstruct a chat.”

**3:20–3:30 — Close.** Show architecture or final UI.

“EvidenceDesk is an MIT-licensed local test build. It reduces the mechanics of evidence review while keeping interpretation, missing evidence, and human responsibility visible.”
