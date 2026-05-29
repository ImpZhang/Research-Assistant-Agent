const state = {
  paperId: "",
  jobId: "",
  latestIdeaId: "",
  latestRelatedWorkMatrixId: "",
  latestExperimentPlanId: "",
  latestExperimentRunId: "",
  latestExperimentAnalysisId: "",
  latestProposalDraftId: "",
  latestProposalReviewId: "",
  latestProposalRevisionId: "",
  latestTaskIds: [],
  latestTaskSnapshotId: "",
  pollTimer: null,
};

const $ = (id) => document.getElementById(id);

function setConnection(ok, text) {
  const dot = $("connectionState");
  dot.classList.remove("pending", "ok", "error");
  dot.classList.add(ok ? "ok" : "error");
  $("connectionText").textContent = text;
}

function setPaper(id, label) {
  state.paperId = id;
  $("activePaperLabel").textContent = label || (id ? `Active paper: ${id}` : "No active paper selected.");
}

function setProgress(value) {
  $("jobProgressBar").style.width = `${Math.max(0, Math.min(value, 1)) * 100}%`;
}

function renderResult(targetId, html, kind = "ok") {
  const target = $(targetId);
  target.classList.remove("muted", "message-ok", "message-warn", "message-error");
  target.classList.add(`message-${kind}`);
  target.innerHTML = html;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const text = await response.text();
  let body = text;
  try {
    body = JSON.parse(text);
  } catch {
    body = text;
  }
  if (!response.ok) {
    const detail = body && body.detail ? body.detail : text;
    throw new Error(`${response.status} ${detail}`);
  }
  return body;
}

async function checkHealth() {
  try {
    const body = await api("/health");
    setConnection(true, `${body.service} ready`);
  } catch (error) {
    setConnection(false, error.message);
  }
}

async function uploadPaper(event) {
  event.preventDefault();
  const file = $("paperFile").files[0];
  if (!file) {
    renderResult("uploadResult", "Choose a paper file first.", "warn");
    return;
  }

  const data = new FormData();
  data.append("file", file);
  renderResult("uploadResult", "Uploading and indexing paper...", "warn");

  try {
    const body = await api("/research/papers/upload", {
      method: "POST",
      body: data,
    });
    setPaper(body.paper.id, `Active paper: ${body.paper.title || body.paper.filename}`);
    renderResult(
      "uploadResult",
      `<strong>${escapeHtml(body.message)}</strong><br />Sections: ${body.section_count}, chunks: ${body.chunk_count}, evidence: ${body.evidence_count}`,
    );
  } catch (error) {
    renderResult("uploadResult", escapeHtml(error.message), "error");
  }
}

async function runWorkflow() {
  if (!state.paperId) {
    renderResult("workflowResult", "Upload a paper before running the workflow.", "warn");
    return;
  }

  setProgress(0);
  renderResult("workflowResult", "Queueing workflow job...", "warn");
  try {
    const body = await api("/research/workflows/literature-to-ideas/async", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        paper_id: state.paperId,
        max_gaps: Number($("maxGaps").value || 3),
        max_ideas_per_gap: Number($("maxIdeas").value || 1),
        include_markdown_export: $("includeMarkdown").checked,
      }),
    });
    state.jobId = body.id;
    renderResult("workflowResult", `Queued job <code>${body.id}</code>. Polling status...`);
    startPollingJob(body.id);
    await refreshJobs();
  } catch (error) {
    renderResult("workflowResult", escapeHtml(error.message), "error");
  }
}

function startPollingJob(jobId) {
  if (state.pollTimer) {
    clearInterval(state.pollTimer);
  }
  state.pollTimer = setInterval(() => pollJob(jobId), 1500);
  pollJob(jobId);
}

async function pollJob(jobId) {
  try {
    const job = await api(`/research/jobs/${jobId}`);
    setProgress(job.progress || 0);
    if (job.output && Array.isArray(job.output.idea_ids) && job.output.idea_ids.length) {
      state.latestIdeaId = job.output.idea_ids[0];
    }
    if (
      job.output &&
      Array.isArray(job.output.experiment_plan_ids) &&
      job.output.experiment_plan_ids.length
    ) {
      state.latestExperimentPlanId = job.output.experiment_plan_ids[0];
    }
    renderResult(
      "workflowResult",
      `Job <code>${job.id}</code> is <strong>${job.status}</strong> at ${Math.round((job.progress || 0) * 100)}%.<br />${renderJobOutput(job.output)}`,
      job.status === "failed" ? "error" : job.status === "completed" ? "ok" : "warn",
    );
    if (job.status === "completed" || job.status === "failed") {
      clearInterval(state.pollTimer);
      state.pollTimer = null;
      if (job.status === "completed") {
        await loadJobArtifacts(jobId);
      }
      await refreshJobs();
    }
  } catch (error) {
    renderResult("workflowResult", escapeHtml(error.message), "error");
  }
}

function renderJobOutput(output) {
  if (!output || Object.keys(output).length === 0) {
    return "No outputs yet.";
  }
  const parts = [];
  if (output.card_id) parts.push(`card <code>${output.card_id}</code>`);
  if (output.gap_ids) parts.push(`${output.gap_ids.length} gaps`);
  if (output.idea_ids) parts.push(`${output.idea_ids.length} ideas`);
  if (output.novelty_check_ids) parts.push(`${output.novelty_check_ids.length} novelty checks`);
  if (output.experiment_plan_ids) parts.push(`${output.experiment_plan_ids.length} plans`);
  return parts.length ? parts.join(", ") : escapeHtml(JSON.stringify(output));
}

async function loadJobArtifacts(jobId) {
  const artifacts = await api(`/research/jobs/${jobId}/artifacts`);
  if (artifacts.ideas && artifacts.ideas.length) {
    state.latestIdeaId = artifacts.ideas[0].id;
  }
  if (artifacts.experiment_plans && artifacts.experiment_plans.length) {
    state.latestExperimentPlanId = artifacts.experiment_plans[0].id;
  }
  if (artifacts.markdown_export) {
    $("dossierPreview").textContent = artifacts.markdown_export;
  }
  renderResult(
    "workflowResult",
    `Job <code>${escapeHtml(jobId)}</code> completed.<br />${renderArtifactsSummary(artifacts)}`,
  );
  return artifacts;
}

function renderArtifactsSummary(artifacts) {
  const parts = [
    `${artifacts.gaps.length} gaps`,
    `${artifacts.ideas.length} ideas`,
    `${artifacts.novelty_checks.length} novelty checks`,
    `${artifacts.reviews.length} reviews`,
    `${artifacts.experiment_plans.length} plans`,
  ];
  return `${escapeHtml(artifacts.message)}<br />${parts.join(", ")}`;
}

async function searchContext(event) {
  event.preventDefault();
  const query = $("contextQuery").value.trim();
  if (!query) return;
  renderResult("contextResult", "Searching context...", "warn");
  try {
    const body = await api("/research/search/context", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        paper_ids: state.paperId ? [state.paperId] : [],
        limit: 5,
        include_graph: true,
      }),
    });
    const rows = [
      `<strong>${escapeHtml(body.retrieval_method)}</strong> ${escapeHtml(body.answer_brief)}`,
      renderList("Evidence", body.evidences, (item) => `${item.score} ${item.evidence.evidence_type}: ${item.evidence.summary || item.evidence.text}`),
      renderList("Gaps", body.gaps, (item) => `${item.score} ${item.gap.title}`),
      renderList("Ideas", body.ideas, (item) => `${item.score} ${item.idea.title}`),
    ];
    renderResult("contextResult", rows.join(""));
  } catch (error) {
    renderResult("contextResult", escapeHtml(error.message), "error");
  }
}

async function searchLiterature(event) {
  event.preventDefault();
  const query = $("literatureQuery").value.trim();
  if (!query) return;
  renderResult("literatureResult", "Searching literature...", "warn");
  try {
    const body = await api("/research/literature/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        limit: 5,
        include_external: $("includeExternal").checked,
      }),
    });
    renderResult(
      "literatureResult",
      `<strong>External:</strong> ${escapeHtml(body.external_status)}<br />${renderList("Results", body.items, (item) => `${item.provider}: ${item.title}`)}`,
    );
  } catch (error) {
    renderResult("literatureResult", escapeHtml(error.message), "error");
  }
}

function renderList(title, items, mapper) {
  if (!items || !items.length) {
    return `<h4>${escapeHtml(title)}</h4><div class="empty-state">No records.</div>`;
  }
  const rows = items
    .slice(0, 5)
    .map((item) => `<li>${escapeHtml(mapper(item))}</li>`)
    .join("");
  return `<h4>${escapeHtml(title)}</h4><ul class="data-list">${rows}</ul>`;
}

async function refreshJobs() {
  try {
    const jobs = await api("/research/jobs?limit=10");
    if (!jobs.length) {
      $("jobsTable").innerHTML = $("emptyTemplate").innerHTML;
      return;
    }
    const rows = jobs
      .map(
        (job) => `<tr>
          <td><code>${escapeHtml(job.id)}</code></td>
          <td>${escapeHtml(job.status)}</td>
          <td>${Math.round((job.progress || 0) * 100)}%</td>
          <td>${escapeHtml(job.input.paper_id || "")}</td>
          <td>${escapeHtml(renderJobOutput(job.output).replace(/<[^>]*>/g, ""))}</td>
        </tr>`,
      )
      .join("");
    $("jobsTable").classList.remove("muted");
    $("jobsTable").innerHTML = `<table>
      <thead><tr><th>Job</th><th>Status</th><th>Progress</th><th>Paper</th><th>Outputs</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
  } catch (error) {
    $("jobsTable").innerHTML = escapeHtml(error.message);
  }
}

async function loadDossier() {
  if (!state.latestIdeaId) {
    if (state.jobId) {
      try {
        await loadJobArtifacts(state.jobId);
        return;
      } catch (error) {
        $("dossierPreview").textContent = error.message;
        return;
      }
    }
    renderResult("workflowResult", "Run a workflow first so an idea id is available.", "warn");
    return;
  }
  try {
    const markdown = await api(`/research/ideas/${state.latestIdeaId}/export/markdown`);
    $("dossierPreview").textContent = markdown;
  } catch (error) {
    $("dossierPreview").textContent = error.message;
  }
}

async function refineLatestIdea() {
  if (!state.latestIdeaId) {
    renderResult("workflowResult", "Run a workflow first so an idea id is available.", "warn");
    return;
  }
  renderResult("workflowResult", "Refining latest idea...", "warn");
  try {
    const body = await api(`/research/ideas/${state.latestIdeaId}/refine`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        focus: $("refineFocus").value.trim(),
        preserve_evidence: true,
      }),
    });
    state.latestIdeaId = body.refined_idea.id;
    state.latestRelatedWorkMatrixId = "";
    state.latestExperimentPlanId = "";
    state.latestExperimentRunId = "";
    state.latestExperimentAnalysisId = "";
    state.latestProposalDraftId = "";
    state.latestProposalReviewId = "";
    state.latestProposalRevisionId = "";
    state.latestTaskIds = [];
    state.latestTaskSnapshotId = "";
    renderResult(
      "workflowResult",
      `Created refined idea <code>${escapeHtml(body.refined_idea.id)}</code> from <code>${escapeHtml(body.source_idea.id)}</code>.<br />${renderList("Applied actions", body.applied_actions, (item) => item)}`,
    );
    await loadDossier();
  } catch (error) {
    renderResult("workflowResult", escapeHtml(error.message), "error");
  }
}

async function createRelatedWorkMatrix() {
  if (!state.latestIdeaId) {
    renderResult("workflowResult", "Run a workflow first so an idea id is available.", "warn");
    return;
  }
  renderResult("workflowResult", "Building related work matrix...", "warn");
  try {
    const body = await api(`/research/ideas/${state.latestIdeaId}/related-work-matrix`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        include_external: true,
        limit: 8,
        created_by: "workbench",
      }),
    });
    state.latestRelatedWorkMatrixId = body.id;
    state.latestProposalReviewId = "";
    state.latestProposalRevisionId = "";
    state.latestTaskIds = [];
    state.latestTaskSnapshotId = "";
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Saved related work matrix <code>${escapeHtml(body.id)}</code> with ${body.items.length} rows.`,
    );
  } catch (error) {
    renderResult("workflowResult", escapeHtml(error.message), "error");
  }
}

async function createProposalDraft() {
  if (!state.latestIdeaId) {
    renderResult("workflowResult", "Run a workflow first so an idea id is available.", "warn");
    return;
  }
  renderResult("workflowResult", "Drafting proposal...", "warn");
  try {
    const body = await api(`/research/ideas/${state.latestIdeaId}/proposal-draft`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        include_latest_related_work: true,
        include_latest_experiment_plan: true,
        created_by: "workbench",
      }),
    });
    state.latestProposalDraftId = body.id;
    state.latestExperimentPlanId = body.experiment_plan_id || state.latestExperimentPlanId;
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Saved proposal draft <code>${escapeHtml(body.id)}</code> for idea <code>${escapeHtml(body.idea_id)}</code>.`,
    );
  } catch (error) {
    renderResult("workflowResult", escapeHtml(error.message), "error");
  }
}

async function reviewProposalDraft() {
  if (!state.latestIdeaId || !state.latestProposalDraftId) {
    renderResult("workflowResult", "Create a proposal draft first.", "warn");
    return;
  }
  renderResult("workflowResult", "Reviewing proposal readiness...", "warn");
  try {
    const body = await api(
      `/research/ideas/${state.latestIdeaId}/proposal-drafts/${state.latestProposalDraftId}/review`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          reviewer_type: "advisor",
          created_by: "workbench",
        }),
      },
    );
    state.latestProposalReviewId = body.id;
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Reviewed proposal <code>${escapeHtml(body.proposal_draft_id)}</code>: ${escapeHtml(body.decision)} (${body.readiness_score}).`,
    );
  } catch (error) {
    renderResult("workflowResult", escapeHtml(error.message), "error");
  }
}

async function reviseProposalDraft() {
  if (!state.latestIdeaId || !state.latestProposalDraftId) {
    renderResult("workflowResult", "Create a proposal draft first.", "warn");
    return;
  }
  renderResult("workflowResult", "Revising proposal from review actions...", "warn");
  try {
    const body = await api(
      `/research/ideas/${state.latestIdeaId}/proposal-drafts/${state.latestProposalDraftId}/revise`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          proposal_review_id: state.latestProposalReviewId || null,
          include_latest_review: true,
          created_by: "workbench",
        }),
      },
    );
    state.latestProposalRevisionId = body.id;
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Saved proposal revision <code>${escapeHtml(body.id)}</code> with ${body.applied_revisions.length} applied actions.`,
    );
  } catch (error) {
    renderResult("workflowResult", escapeHtml(error.message), "error");
  }
}

async function createTaskBacklog() {
  if (!state.latestIdeaId || !state.latestProposalDraftId || !state.latestProposalRevisionId) {
    renderResult("workflowResult", "Create a proposal revision first.", "warn");
    return;
  }
  renderResult("workflowResult", "Creating task backlog...", "warn");
  try {
    const body = await api(
      `/research/ideas/${state.latestIdeaId}/proposal-drafts/${state.latestProposalDraftId}/revisions/${state.latestProposalRevisionId}/tasks`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ created_by: "workbench" }),
      },
    );
    state.latestTaskIds = body.tasks.map((task) => task.id);
    renderResult(
      "workflowResult",
      `${escapeHtml(body.message)}<br />${renderList("Tasks", body.tasks.slice(0, 8), (task) => `${task.priority} ${task.status}: ${task.title}`)}`,
    );
  } catch (error) {
    renderResult("workflowResult", escapeHtml(error.message), "error");
  }
}

async function saveTaskSnapshot() {
  renderResult("workflowResult", "Saving task board snapshot...", "warn");
  try {
    const body = await api("/research/tasks/snapshots", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: "Workbench Research Task Board",
        idea_id: state.latestIdeaId || null,
        owner_type: "proposal_revision",
        statuses: [],
        created_by: "workbench",
      }),
    });
    state.latestTaskSnapshotId = body.id;
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Saved task snapshot <code>${escapeHtml(body.id)}</code> with ${body.task_ids.length} tasks.`,
    );
  } catch (error) {
    renderResult("workflowResult", escapeHtml(error.message), "error");
  }
}

async function createExperimentRun() {
  if (!state.latestIdeaId) {
    renderResult("workflowResult", "Run a workflow first so an idea id is available.", "warn");
    return;
  }
  renderResult("workflowResult", "Recording experiment run...", "warn");
  try {
    if (!state.latestExperimentPlanId) {
      const plan = await api(`/research/ideas/${state.latestIdeaId}/experiment-plan`, {
        method: "POST",
      });
      state.latestExperimentPlanId = plan.id;
    }
    const body = await api(`/research/experiment-plans/${state.latestExperimentPlanId}/runs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: "Workbench experiment run",
        task_id: state.latestTaskIds.length ? state.latestTaskIds[0] : null,
        status: "running",
        dataset_snapshot: "Workbench run dataset snapshot pending.",
        parameters: { source: "workbench" },
        metric_results: {},
        artifact_links: [],
        notes: $("refineFocus").value.trim(),
        created_by: "workbench",
      }),
    });
    state.latestExperimentRunId = body.id;
    state.latestExperimentAnalysisId = "";
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Recorded experiment run <code>${escapeHtml(body.id)}</code> with status ${escapeHtml(body.status)}.`,
    );
  } catch (error) {
    renderResult("workflowResult", escapeHtml(error.message), "error");
  }
}

async function analyzeExperimentRun() {
  if (!state.latestExperimentRunId) {
    renderResult("workflowResult", "Record an experiment run first.", "warn");
    return;
  }
  renderResult("workflowResult", "Analyzing experiment run...", "warn");
  try {
    const body = await api(`/research/experiment-runs/${state.latestExperimentRunId}/analysis`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ created_by: "workbench" }),
    });
    state.latestExperimentAnalysisId = body.id;
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Analyzed run <code>${escapeHtml(body.experiment_run_id)}</code>: ${escapeHtml(body.decision)} (${body.confidence}).`,
    );
  } catch (error) {
    renderResult("workflowResult", escapeHtml(error.message), "error");
  }
}

async function createAnalysisTasks() {
  if (!state.latestExperimentAnalysisId) {
    renderResult("workflowResult", "Analyze an experiment run first.", "warn");
    return;
  }
  renderResult("workflowResult", "Creating analysis follow-up tasks...", "warn");
  try {
    const body = await api(`/research/experiment-analyses/${state.latestExperimentAnalysisId}/tasks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ created_by: "workbench" }),
    });
    state.latestTaskIds = [...state.latestTaskIds, ...body.tasks.map((task) => task.id)];
    renderResult(
      "workflowResult",
      `${escapeHtml(body.message)}<br />${renderList("Analysis tasks", body.tasks, (task) => `${task.priority} ${task.status}: ${task.title}`)}`,
    );
  } catch (error) {
    renderResult("workflowResult", escapeHtml(error.message), "error");
  }
}

async function loadIdeaLineage() {
  if (!state.latestIdeaId) {
    renderResult("workflowResult", "Run a workflow first so an idea id is available.", "warn");
    return;
  }
  renderResult("workflowResult", "Loading idea lineage...", "warn");
  try {
    const body = await api(`/research/ideas/${state.latestIdeaId}/lineage`);
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `${escapeHtml(body.message)} Graph edge types: ${Object.keys(body.graph_edge_summary).length}.`,
    );
  } catch (error) {
    renderResult("workflowResult", escapeHtml(error.message), "error");
  }
}

async function loadIdeaProgress() {
  if (!state.latestIdeaId) {
    renderResult("workflowResult", "Run a workflow first so an idea id is available.", "warn");
    return;
  }
  renderResult("workflowResult", "Loading idea progress...", "warn");
  try {
    const body = await api(`/research/ideas/${state.latestIdeaId}/progress`);
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `${escapeHtml(body.message)} Next: ${escapeHtml(body.recommended_next_step)}`,
    );
  } catch (error) {
    renderResult("workflowResult", escapeHtml(error.message), "error");
  }
}

async function loadProjectOverview() {
  renderResult("workflowResult", "Loading project overview...", "warn");
  try {
    const body = await api("/research/progress/overview");
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `${escapeHtml(body.message)} Recommended actions: ${body.recommended_actions.length}.`,
    );
  } catch (error) {
    renderResult("workflowResult", escapeHtml(error.message), "error");
  }
}

async function rankIdeas() {
  renderResult("workflowResult", "Ranking idea portfolio...", "warn");
  try {
    const body = await api("/research/ideas/rank", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        paper_ids: state.paperId ? [state.paperId] : [],
        limit: 5,
        deduplicate_lineage: true,
      }),
    });
    if (body.ranked_ideas.length) {
      state.latestIdeaId = body.ranked_ideas[0].idea.id;
    }
    renderResult(
      "workflowResult",
      `${escapeHtml(body.message)}<br />${renderList("Ranked ideas", body.ranked_ideas, (item) => `#${item.rank} ${item.weighted_score}: ${item.idea.title}`)}`,
    );
    const markdown = await api("/research/ideas/rank/export/markdown", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        paper_ids: state.paperId ? [state.paperId] : [],
        limit: 5,
        deduplicate_lineage: true,
        title: "Research Idea Portfolio",
      }),
    });
    $("dossierPreview").textContent = markdown;
  } catch (error) {
    renderResult("workflowResult", escapeHtml(error.message), "error");
  }
}

async function shortlistLatestIdea() {
  if (!state.latestIdeaId) {
    renderResult("workflowResult", "Run a workflow first so an idea id is available.", "warn");
    return;
  }
  try {
    const body = await api(`/research/ideas/${state.latestIdeaId}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        decision: "shortlist",
        rating: 4.5,
        comment: $("refineFocus").value.trim(),
        tags: ["shortlist", "workbench"],
      }),
    });
    renderResult(
      "workflowResult",
      `Shortlisted idea <code>${escapeHtml(body.idea_id)}</code> with rating ${escapeHtml(body.rating)}.`,
    );
    await rankIdeas();
  } catch (error) {
    renderResult("workflowResult", escapeHtml(error.message), "error");
  }
}

async function savePortfolio() {
  renderResult("workflowResult", "Saving ranked portfolio snapshot...", "warn");
  try {
    const body = await api("/research/ideas/portfolios", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        paper_ids: state.paperId ? [state.paperId] : [],
        limit: 5,
        deduplicate_lineage: true,
        title: "Workbench Research Idea Portfolio",
        description: $("refineFocus").value.trim(),
        created_by: "workbench",
      }),
    });
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Saved portfolio <code>${escapeHtml(body.id)}</code> with ${body.idea_ids.length} ideas.`,
    );
  } catch (error) {
    renderResult("workflowResult", escapeHtml(error.message), "error");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  $("uploadForm").addEventListener("submit", uploadPaper);
  $("runWorkflowButton").addEventListener("click", runWorkflow);
  $("contextSearchForm").addEventListener("submit", searchContext);
  $("literatureSearchForm").addEventListener("submit", searchLiterature);
  $("refreshJobsButton").addEventListener("click", refreshJobs);
  $("loadDossierButton").addEventListener("click", loadDossier);
  $("refineIdeaButton").addEventListener("click", refineLatestIdea);
  $("relatedWorkButton").addEventListener("click", createRelatedWorkMatrix);
  $("proposalDraftButton").addEventListener("click", createProposalDraft);
  $("proposalReviewButton").addEventListener("click", reviewProposalDraft);
  $("proposalRevisionButton").addEventListener("click", reviseProposalDraft);
  $("taskBacklogButton").addEventListener("click", createTaskBacklog);
  $("taskSnapshotButton").addEventListener("click", saveTaskSnapshot);
  $("experimentRunButton").addEventListener("click", createExperimentRun);
  $("experimentAnalysisButton").addEventListener("click", analyzeExperimentRun);
  $("analysisTasksButton").addEventListener("click", createAnalysisTasks);
  $("lineageButton").addEventListener("click", loadIdeaLineage);
  $("progressButton").addEventListener("click", loadIdeaProgress);
  $("overviewButton").addEventListener("click", loadProjectOverview);
  $("shortlistIdeaButton").addEventListener("click", shortlistLatestIdea);
  $("rankIdeasButton").addEventListener("click", rankIdeas);
  $("savePortfolioButton").addEventListener("click", savePortfolio);
  checkHealth();
  refreshJobs();
});
