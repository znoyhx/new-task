# EvidenceFlow Demo Expected Output

This sample is the fixed demo target for stage 5. The live app may paraphrase, but the local deterministic demo should preserve the same structure and substance.

## Student Progress

- Alice completed one new curriculum-learning baseline rerun.
- Current result: hard-example macro F1 improved.
- Blockers:
  - the ablation table is incomplete
  - token-level retrieval logging fails on long-context runs
- Risks:
  - calibration regresses after the third curriculum stage
  - retrieval logging still crashes on long-context runs

## Advisor Ideas

- Keep the hard-negative curriculum ablation in next week's plan.
- Test retrieval-assisted logging so every exported task can point back to a transcript slice.

## Action Items

- Prepare the hard-negative curriculum ablation table.
- Instrument retrieval-assisted logging for transcript traceability.
- Share the failing trace logs with Bob.

## Recommended Reading

- Curriculum Learning for Robust Classification
- Calibration Under Distribution Shift
- Grounded Meeting Agents With Retrieval Traces

## Optional Claim

- Claim: curriculum learning consistently improves hard-example macro F1 in small-data settings.
- Expected verdict at demo time: `needs_verification`

## Deliverables

- Weekly report in Markdown
- Next-meeting briefing in Markdown
- Next-week research plan in Markdown
- Presentation outline in Markdown
