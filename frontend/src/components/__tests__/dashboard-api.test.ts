import assert from "node:assert/strict";

import {
  fetchDeliverable,
  fetchProjectMemory,
  processMeetingTranscript,
  updateActionItemStatus,
} from "../dashboard-api";

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
          orchestration: {
            controller_agent_name: "主控 Agent",
            llm_provider: "deepseek",
            llm_model: "deepseek-chat",
            stages: [
              {
                stage_key: "controller-intake",
                stage_label: "Controller intake",
                capability: "review_orchestration",
                agent_name: "主控 Agent",
                goal: "Confirm the meeting is ready for execution planning.",
                input_sources: [
                  {
                    kind: "meeting",
                    label: "Live Weekly Meeting",
                    detail: "Transcript import",
                    meeting_id: "meeting-live-001",
                    chunk_ids: [],
                  },
                ],
                output_target: {
                  kind: "review_pipeline",
                  label: "Review pipeline",
                  detail: "Ready to orchestrate the review run.",
                },
                fallback: {
                  summary: "No fallback needed.",
                  used: false,
                  detail: "",
                },
                status: "completed",
                triggered: true,
                trigger_reason: "A meeting transcript was imported.",
                output_summary: "Loaded the transcript and queued the review stages.",
                error_detail: "",
              },
              {
                stage_key: "memory-load",
                stage_label: "Memory load",
                capability: "project_memory_lookup",
                agent_name: "记忆管家 Agent",
                goal: "Load prior memory before planning next week.",
                input_sources: [
                  {
                    kind: "project_id",
                    label: "project-001",
                    detail: "Integration Project",
                    meeting_id: null,
                    chunk_ids: [],
                  },
                ],
                output_target: {
                  kind: "memory_snapshot",
                  label: "Historical project memory snapshot",
                  detail: "Open tasks and prior decisions.",
                },
                fallback: {
                  summary: "Continue in first-meeting mode if memory is empty.",
                  used: false,
                  detail: "",
                },
                status: "completed",
                triggered: true,
                trigger_reason: "Every planning run checks prior memory first.",
                output_summary: "Loaded one prior meeting and one carryover task.",
                error_detail: "",
              },
              {
                stage_key: "plan-generation",
                stage_label: "Plan generation",
                capability: "next_week_plan_generation",
                agent_name: "推进 Agent",
                goal: "Turn ideas and blockers into next-week execution.",
                input_sources: [
                  {
                    kind: "advisor_ideas",
                    label: "Advisor ideas",
                    detail: "1 captured idea",
                    meeting_id: "meeting-live-001",
                    chunk_ids: ["chunk-0001"],
                  },
                ],
                output_target: {
                  kind: "research_plan",
                  label: "Next-week research plan",
                  detail: "Owner, deadline, rationale, and success metric.",
                },
                fallback: {
                  summary: "Fallback to idea-derived next actions if plan generation fails.",
                  used: false,
                  detail: "",
                },
                status: "completed",
                triggered: true,
                trigger_reason: "Ideas and blockers were extracted successfully.",
                output_summary: "Generated one next-week action item.",
                error_detail: "",
              },
            ],
            memory_usage: {
              project_id: "project-001",
              prior_meeting_count: 1,
              open_task_count: 1,
              recent_decision_count: 1,
              relevant_context_count: 2,
              memory_in_use: [
                {
                  item_id: "memory-task-001",
                  title: "Carry forward the ablation checklist",
                  item_type: "action_item",
                  source_meeting_id: "meeting-history-001",
                  status: "open",
                  reason: "Still unresolved and relevant to the current plan.",
                },
              ],
            },
          },
          explanations: {
            action_items: [
              {
                action_item_id: "run the follow-up ablation::alice",
                title: "Run the follow-up ablation",
                rationale: "Advisor requested it.",
                output_summary: "Derived from advisor guidance and a carryover blocker.",
                carryover: true,
                attributions: [
                  {
                    source_type: "advisor_idea",
                    origin_layer: "current_transcript",
                    label: "Run one more ablation before Friday.",
                    detail: "Current advisor idea that triggered the task.",
                    meeting_id: "meeting-live-001",
                    chunk_ids: ["chunk-0001"],
                  },
                  {
                    source_type: "action_item",
                    origin_layer: "history_memory",
                    label: "Carry forward the ablation checklist",
                    detail: "Historical open task that is still unresolved.",
                    meeting_id: "meeting-history-001",
                    chunk_ids: [],
                  },
                ],
              },
            ],
            readings: [
              {
                reading_id: "reading-001",
                title: "Paper One",
                reason: "Supports the ablation design.",
                output_summary: "Chosen because it directly supports next week's experiment.",
                attributions: [
                  {
                    source_type: "advisor_idea",
                    origin_layer: "current_transcript",
                    label: "Run one more ablation before Friday.",
                    detail: "The reading supports this current advisor idea.",
                    meeting_id: "meeting-live-001",
                    chunk_ids: ["chunk-0001"],
                  },
                ],
              },
            ],
            claims: [
              {
                claim_id: "claim-001",
                title: "The baseline is ready for review.",
                trigger_reason: "The claim materially changes next week's plan.",
                verdict: "supported",
                output_summary: "The supporting note aligns with the transcript.",
                attributions: [
                  {
                    source_type: "claim",
                    origin_layer: "current_transcript",
                    label: "Finished the baseline.",
                    detail: "Transcript slice that triggered verification.",
                    meeting_id: "meeting-live-001",
                    chunk_ids: ["chunk-0001"],
                  },
                  {
                    source_type: "key_paper",
                    origin_layer: "evidence_retrieval",
                    label: "Experiment note",
                    detail: "Supporting evidence retrieved during verification.",
                    meeting_id: "meeting-live-001",
                    chunk_ids: [],
                  },
                ],
              },
            ],
            briefing_items: [
              {
                item_id: "briefing-001",
                item_type: "carryover_task",
                title: "Carry forward the ablation checklist",
                reason: "It remains unfinished and still blocks the current plan.",
                origin_layer: "history_memory",
                attributions: [
                  {
                    source_type: "action_item",
                    origin_layer: "history_memory",
                    label: "Carry forward the ablation checklist",
                    detail: "Historical open task reused in the current briefing.",
                    meeting_id: "meeting-history-001",
                    chunk_ids: [],
                  },
                ],
              },
            ],
          },
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
  assert.equal(result.actionItems[0]?.meetingId, "meeting-live-001");
  assert.equal(result.actionItems[0]?.title, "Run the follow-up ablation");
  assert.equal(result.actionItems[0]?.carryover, true);
  assert.equal(result.actionItems[0]?.attributions[1]?.originLayer, "history_memory");
  assert.equal(result.readingList[0]?.attributions[0]?.sourceType, "advisor_idea");
  assert.equal(result.claims[0]?.triggerReason, "The claim materially changes next week's plan.");
  assert.equal(result.claims[0]?.evidenceCards[0]?.stance, "support");
  assert.equal(result.briefing.items[0]?.originLayer, "history_memory");
  assert.equal(result.orchestration.controllerAgentName, "主控 Agent");
  assert.equal(result.orchestration.memoryUsage?.priorMeetingCount, 1);
  assert.equal(result.orchestration.stages[1]?.agentName, "记忆管家 Agent");
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

async function runProjectMemoryFetchTest() {
  globalThis.fetch = (async (input: RequestInfo | URL) => {
    const url = String(input);
    if (!url.endsWith("/api/projects/project-001/memory")) {
      throw new Error(`Unexpected fetch URL: ${url}`);
    }

    return new Response(
      JSON.stringify({
        project_memory: {
          project: {
            project_id: "project-001",
            name: "Integration Project",
          },
          meetings: [
            {
              meeting_id: "meeting-history-001",
              title: "History Meeting",
              summary: "Original ablation request.",
              created_at: "2026-04-11T10:00:00+00:00",
            },
            {
              meeting_id: "meeting-live-001",
              title: "Live Weekly Meeting",
              summary: "Status review.",
              created_at: "2026-04-18T10:00:00+00:00",
            },
          ],
          decisions: [
            {
              id: "decision-001",
              meeting_id: "meeting-history-001",
              title: "Keep the ablation in scope",
              rationale: "It remains the fastest validation path.",
              decided_by: "Prof. Chen",
              created_at: "2026-04-11T10:00:00+00:00",
            },
          ],
          action_items: [
            {
              meeting_id: "meeting-history-001",
              title: "Carry forward the ablation checklist",
              owner: "Alice",
              deadline: "Friday",
              priority: "high",
              status: "open",
            },
            {
              meeting_id: "meeting-live-001",
              title: "Run the follow-up ablation",
              owner: "Alice",
              deadline: "Tuesday",
              priority: "high",
              status: "in_progress",
            },
          ],
          relevant_context: [{ entry_id: "memory-hit-001" }],
        },
        briefing: {
          summary: "Briefing summary from project memory.",
          focus_questions: ["What still blocks execution?"],
          recommended_agenda: [
            {
              title: "Close the carryover ablation",
              reason: "It still blocks the next result review.",
              priority: "high",
            },
          ],
        },
        briefing_items: [
          {
            item_id: "briefing-001",
            item_type: "carryover_task",
            title: "Carry forward the ablation checklist",
            reason: "Still unfinished and relevant this week.",
            origin_layer: "history_memory",
            attributions: [],
          },
        ],
      }),
      { status: 200, headers: { "Content-Type": "application/json" } }
    );
  }) as typeof fetch;

  const memory = await fetchProjectMemory("project-001", "meeting-live-001");

  assert.equal(memory.projectId, "project-001");
  assert.equal(memory.memoryUsage.priorMeetingCount, 1);
  assert.equal(memory.openActionItems.length, 2);
  assert.equal(memory.openActionItems[0]?.originLayer, "history_memory");
  assert.equal(memory.briefing.items[0]?.originLayer, "history_memory");
  assert.equal(memory.recentDecisions[0]?.meetingTitle, "History Meeting");
}

async function runActionItemStatusUpdateTest() {
  globalThis.fetch = (async (input: RequestInfo | URL) => {
    const url = String(input);
    if (!url.endsWith("/api/projects/project-001/action-items/status")) {
      throw new Error(`Unexpected fetch URL: ${url}`);
    }

    return new Response(
      JSON.stringify({
        updated_action_item: {
          meeting_id: "meeting-live-001",
          title: "Run the follow-up ablation",
          owner: "Alice",
          deadline: "Tuesday",
          priority: "high",
          status: "done",
        },
        project_memory: {
          project: {
            project_id: "project-001",
            name: "Integration Project",
          },
          meetings: [
            {
              meeting_id: "meeting-history-001",
              title: "History Meeting",
              summary: "Original ablation request.",
              created_at: "2026-04-11T10:00:00+00:00",
            },
            {
              meeting_id: "meeting-live-001",
              title: "Live Weekly Meeting",
              summary: "Status review.",
              created_at: "2026-04-18T10:00:00+00:00",
            },
          ],
          decisions: [],
          action_items: [
            {
              meeting_id: "meeting-history-001",
              title: "Carry forward the ablation checklist",
              owner: "Alice",
              deadline: "Friday",
              priority: "high",
              status: "open",
            },
            {
              meeting_id: "meeting-live-001",
              title: "Run the follow-up ablation",
              owner: "Alice",
              deadline: "Tuesday",
              priority: "high",
              status: "done",
            },
          ],
          relevant_context: [],
        },
        briefing: {
          summary: "Updated briefing summary.",
          focus_questions: ["Which carryover task is still open?"],
          recommended_agenda: [],
        },
        briefing_items: [
          {
            item_id: "briefing-002",
            item_type: "carryover_task",
            title: "Carry forward the ablation checklist",
            reason: "The older task is still open.",
            origin_layer: "history_memory",
            attributions: [],
          },
        ],
      }),
      { status: 200, headers: { "Content-Type": "application/json" } }
    );
  }) as typeof fetch;

  const update = await updateActionItemStatus("project-001", {
    meetingId: "meeting-live-001",
    title: "Run the follow-up ablation",
    owner: "Alice",
    status: "done",
    currentMeetingId: "meeting-live-001",
  });

  assert.equal(update.updatedActionItem.id, "meeting-live-001::run the follow-up ablation::alice");
  assert.equal(update.updatedActionItem.status, "done");
  assert.equal(update.projectMemory.openActionItems.length, 1);
  assert.equal(update.projectMemory.openActionItems[0]?.title, "Carry forward the ablation checklist");
  assert.equal(update.projectMemory.briefing.summary, "Updated briefing summary.");
}

async function main() {
  try {
    await runProcessTranscriptMappingTest();
    await runDeliverableRefreshTest();
    await runProjectMemoryFetchTest();
    await runActionItemStatusUpdateTest();
    console.log("frontend dashboard api tests passed");
  } finally {
    globalThis.fetch = originalFetch;
  }
}

void main();
