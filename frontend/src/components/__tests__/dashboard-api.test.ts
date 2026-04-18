import assert from "node:assert/strict";

import { fetchDeliverable, processMeetingTranscript } from "../dashboard-api";

const originalFetch = globalThis.fetch;

async function runProcessTranscriptMappingTest() {
  let callCount = 0;
  globalThis.fetch = (async (input: RequestInfo | URL) => {
    const url = String(input);
    callCount += 1;

    if (url.endsWith("/api/meetings/import")) {
      return new Response(
        JSON.stringify({
          meeting: {
            meeting_id: "meeting-live-001",
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      );
    }

    if (url.endsWith("/api/meetings/meeting-live-001/review")) {
      return new Response(
        JSON.stringify({
          project: {
            project_id: "project-001",
            name: "Integration Project",
          },
          meeting: {
            meeting_id: "meeting-live-001",
            meeting_title: "Live Weekly Meeting",
            created_at: "2026-04-18T10:00:00+00:00",
            status: "processed",
          },
          transcript: {
            chunks: [
              {
                chunk_id: "chunk-0001",
                timestamp_start: "00:01",
                speaker: "Alice",
                text: "Finished the baseline.",
              },
            ],
          },
          progress: {
            summary: "Progress summary.",
            student_progress: [
              {
                student_name: "Alice",
                completed_work: ["Finished the baseline."],
                current_result: "Baseline is ready.",
                blockers: ["Need one more ablation."],
                risks: [
                  {
                    title: "Ablation missing",
                    level: "medium",
                    description: "Still one gap left.",
                  },
                ],
                next_step_suggestion: "Run the follow-up ablation.",
                unresolved_questions: ["Will the metric hold?"],
              },
            ],
          },
          ideas: {
            ideas: [
              {
                id: "idea-001",
                idea_text: "Run one more ablation before Friday.",
                expected_validation: "Validate the baseline change.",
                validation_metrics: ["macro F1"],
                recommended_reading: [{ title: "Paper One" }],
              },
            ],
          },
          research_plan: {
            tasks: [
              {
                idea_id: "idea-001",
                title: "Run the follow-up ablation",
                owner: "Alice",
                due_date: "Friday",
                priority: "high",
                success_metrics: ["macro F1"],
                rationale: "Advisor requested it.",
              },
            ],
          },
          reading_recommendations: {
            recommendations: [
              {
                id: "reading-001",
                title: "Paper One",
                reason: "Supports the ablation design.",
                priority: "high",
                source_url: "https://example.org/paper-one",
                student_name: "Alice",
              },
            ],
          },
          claims: [
            {
              claim: {
                id: "claim-001",
                text: "The baseline is ready for review.",
                speaker: "Alice",
                verification_status: "supported",
                transcript_snippet: "Finished the baseline.",
                source_chunk_ids: ["chunk-0001"],
              },
              verdict: "supported",
              confidence: "high",
              evidence_cards: [
                {
                  id: "evidence-001",
                  source_title: "Experiment note",
                  source_url: "https://example.org/note",
                  source_type: "project_note",
                  stance: "support",
                  confidence: "high",
                  snippet: "Finished the baseline.",
                },
              ],
            },
          ],
          briefing: {
            summary: "Briefing summary.",
            focus_questions: ["What changed since last week?"],
            recommended_agenda: [
              {
                title: "Review the follow-up ablation",
                reason: "It is the highest-value next step.",
                priority: "high",
              },
            ],
          },
          deliverables: [
            {
              deliverable_type: "weekly_report",
              title: "Weekly Report - Integration Project",
              content_markdown: "# Weekly Report",
            },
          ],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      );
    }

    throw new Error(`Unexpected fetch URL: ${url}`);
  }) as typeof fetch;

  const result = await processMeetingTranscript("demo transcript");

  assert.equal(callCount, 2);
  assert.equal(result.projectId, "project-001");
  assert.equal(result.meetingId, "meeting-live-001");
  assert.equal(result.projectName, "Integration Project");
  assert.equal(result.actionItems[0]?.title, "Run the follow-up ablation");
  assert.equal(result.claims[0]?.evidenceCards[0]?.stance, "support");
  assert.equal(result.deliverables[0]?.key, "weekly-report");
}

async function runDeliverableRefreshTest() {
  globalThis.fetch = (async () =>
    new Response(
      JSON.stringify({
        document: {
          deliverable_type: "presentation_outline",
          title: "Presentation Outline - Integration Project",
          content_markdown: "# Presentation Outline",
        },
      }),
      { status: 200, headers: { "Content-Type": "application/json" } }
    )) as typeof fetch;

  const document = await fetchDeliverable("project-001", "presentation-outline");

  assert.equal(document.key, "presentation-outline");
  assert.equal(document.title, "Presentation Outline - Integration Project");
  assert.equal(document.content, "# Presentation Outline");
}

async function main() {
  try {
    await runProcessTranscriptMappingTest();
    await runDeliverableRefreshTest();
    console.log("frontend dashboard api tests passed");
  } finally {
    globalThis.fetch = originalFetch;
  }
}

void main();
