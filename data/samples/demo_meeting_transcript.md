# EvidenceFlow Demo Meeting Transcript

[00:00:06] Alice: This week I reran the curriculum-learning baseline on the reviewer-comment benchmark and reached 74 percent macro F1.
[00:00:18] Alice: The improvement comes mostly from hard examples, but calibration still gets worse after the third curriculum stage.
[00:00:31] Alice: I still do not have a clean ablation table, and the long-context runs fail when logging token-level evidence.
[00:00:46] Prof. Chen: Keep the hard-negative curriculum ablation in next week's plan and report macro F1 plus calibration error.
[00:00:59] Prof. Chen: Also test retrieval-assisted logging so we can trace every action item back to a transcript slice.
[00:01:12] Prof. Chen: Before the next meeting, read one paper on curriculum learning, one on calibration under imbalance, and one on retrieval-grounded meeting agents.
[00:01:26] Bob: I can help instrument the logging pipeline if Alice shares the failing traces.
[00:01:39] Prof. Chen: One claim we should verify is whether curriculum learning consistently improves hard-example macro F1 in small-data settings.
