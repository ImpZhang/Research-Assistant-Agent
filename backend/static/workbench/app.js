const state = {
  apiKey: "",
  projectId: "default",
  projectScope: null,
  paperId: "",
  jobId: "",
  latestJobStatus: "",
  latestIdeaId: "",
  latestRelatedWorkMatrixId: "",
  latestExperimentPlanId: "",
  latestExperimentRunId: "",
  latestExperimentAnalysisId: "",
  latestBenchmarkComparisonBriefId: "",
  latestProposalDraftId: "",
  latestProposalReviewId: "",
  latestProposalRevisionId: "",
  latestNoveltyCheckId: "",
  latestSotaReviewPackageId: "",
  latestSotaExternalSearchEvidenceId: "",
  latestSotaSignoffId: "",
  latestDecisionMemoId: "",
  latestAssumptionAuditId: "",
  latestEvidenceLedgerId: "",
  latestClaimId: "",
  latestTaskIds: [],
  taskBoardItems: [],
  latestTaskSnapshotId: "",
  latestTriageSnapshotId: "",
  latestPilotReportSnapshotId: "",
  latestProjectBundleReadinessSnapshotId: "",
  latestProjectBundleReleaseId: "",
  latestProjectBundleReleaseFeedbackId: "",
  latestProjectBundleReleaseAcceptancePacketSnapshotId: "",
  latestProjectBundleReleaseReviewOutcomeId: "",
  latestProjectBundleReleaseReviewOutcomeSignoffId: "",
  latestResearchPlanId: "",
  latestRealEvalReportId: "",
  researchProfile: null,
  onboardingReadiness: null,
  pollTimer: null,
  requestId: "",
  requestIdHeader: "X-Request-ID",
};

const API_KEY_STORAGE_KEY = "researchAssistantApiKey";
const PROJECT_ID_STORAGE_KEY = "researchAssistantProjectId";
const API_KEY_HEADER = "X-Research-Assistant-Key";
const PROJECT_ID_HEADER = "X-Research-Assistant-Project";
const REQUEST_ID_HEADER = "X-Request-ID";

const $ = (id) => document.getElementById(id);

function setConnection(ok, text) {
  const dot = $("connectionState");
  dot.classList.remove("pending", "ok", "error");
  dot.classList.add(ok ? "ok" : "error");
  $("connectionText").textContent = withRequestId(text);
}

function rememberRequestId(response) {
  const requestId =
    response.headers.get(state.requestIdHeader || REQUEST_ID_HEADER) ||
    response.headers.get(REQUEST_ID_HEADER);
  if (requestId) {
    state.requestId = requestId;
  }
  return requestId;
}

function rememberReadinessConfig(body) {
  const header = body?.checks?.request_id_header?.header;
  if (header) {
    state.requestIdHeader = header;
  }
}

function requestIdLabel(requestId = state.requestId) {
  return requestId ? `req ${requestId.slice(0, 12)}` : "";
}

function withRequestId(text, requestId = state.requestId) {
  const label = requestIdLabel(requestId);
  return label ? `${text} | ${label}` : text;
}

function setPaper(id, label) {
  state.paperId = id;
  $("activePaperLabel").textContent = label || (id ? `Active paper: ${id}` : "No active paper selected.");
  renderLatestWorkflow();
}

function renderLatestWorkflow(message = "") {
  const summary = $("latestWorkflowSummary");
  const facts = $("latestWorkflowFacts");
  if (!summary || !facts) {
    return;
  }

  if (message) {
    summary.textContent = message;
  } else if (state.latestIdeaId) {
    summary.textContent = `Ready on latest idea ${state.latestIdeaId}.`;
  } else if (state.jobId) {
    const status = state.latestJobStatus ? ` is ${state.latestJobStatus}` : " is selected";
    summary.textContent = `Workflow job ${state.jobId}${status}.`;
  } else {
    summary.textContent = "No recent workflow selected.";
  }

  const values = [
    ["Job", state.jobId],
    ["Status", state.latestJobStatus],
    ["Paper", state.paperId],
    ["Idea", state.latestIdeaId],
  ];
  facts.innerHTML = values
    .map(([label, value]) => {
      const displayValue = value || "-";
      const title = value || "Not available";
      return `<span><strong>${escapeHtml(label)}</strong><code title="${escapeHtml(title)}">${escapeHtml(displayValue)}</code></span>`;
    })
    .join("");
}

function setProgress(value) {
  $("jobProgressBar").style.width = `${Math.max(0, Math.min(value, 1)) * 100}%`;
}

function restoreStateFromJob(job) {
  if (!job) {
    return false;
  }
  const output = job.output || {};
  let restored = false;
  if (!state.jobId && job.id) {
    state.jobId = job.id;
    restored = true;
  }
  if (job.status && state.latestJobStatus !== job.status) {
    state.latestJobStatus = job.status;
    restored = true;
  }
  if (!state.paperId && job.input && job.input.paper_id) {
    setPaper(job.input.paper_id, `Active paper from latest job: ${job.input.paper_id}`);
    restored = true;
  }
  if (!state.latestIdeaId && Array.isArray(output.idea_ids) && output.idea_ids.length) {
    state.latestIdeaId = output.idea_ids[0];
    restored = true;
  }
  if (
    !state.latestExperimentPlanId &&
    Array.isArray(output.experiment_plan_ids) &&
    output.experiment_plan_ids.length
  ) {
    state.latestExperimentPlanId = output.experiment_plan_ids[0];
    restored = true;
  }
  if (
    !state.latestNoveltyCheckId &&
    Array.isArray(output.novelty_check_ids) &&
    output.novelty_check_ids.length
  ) {
    state.latestNoveltyCheckId = output.novelty_check_ids[0];
    restored = true;
  }
  if (restored) {
    renderLatestWorkflow("Latest workflow restored from completed jobs.");
  }
  return restored;
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

function workbenchErrorMessage(error) {
  const message = error && error.message
    ? String(error.message)
    : String(error || "Unknown error.");
  const escaped = escapeHtml(message);
  if (message.startsWith("401") || message.toLowerCase().includes("unauthorized")) {
    return `${escaped}<br />Save a valid API key in the top bar, then retry.`;
  }
  if (
    message.includes("Failed to fetch") ||
    message.includes("NetworkError") ||
    message.includes("Load failed")
  ) {
    return `${escaped}<br />Check that the API server is reachable, then retry.`;
  }
  return escaped;
}

function renderWorkbenchError(targetId, error) {
  renderResult(targetId, workbenchErrorMessage(error), "error");
}

function renderWorkbenchEmpty(targetId, message) {
  renderResult(targetId, escapeHtml(message), "warn");
}

function parseCsv(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function formatCsv(items) {
  return (items || []).join(", ");
}

function parseWeights(value) {
  return Object.fromEntries(
    parseCsv(value)
      .map((item) => item.split("=").map((part) => part.trim()))
      .filter(([key, raw]) => key && raw && !Number.isNaN(Number(raw)))
      .map(([key, raw]) => [key, Number(raw)]),
  );
}

function formatWeights(weights) {
  return Object.entries(weights || {})
    .map(([key, value]) => `${key}=${value}`)
    .join(", ");
}

function loadApiKey() {
  state.apiKey = localStorage.getItem(API_KEY_STORAGE_KEY) || "";
  $("apiKeyInput").value = state.apiKey;
  updateApiKeyStatus();
}

function saveApiKey() {
  state.apiKey = $("apiKeyInput").value.trim();
  if (state.apiKey) {
    localStorage.setItem(API_KEY_STORAGE_KEY, state.apiKey);
  } else {
    localStorage.removeItem(API_KEY_STORAGE_KEY);
  }
  updateApiKeyStatus();
  refreshProjectScopeStatus();
}

function clearApiKey() {
  state.apiKey = "";
  localStorage.removeItem(API_KEY_STORAGE_KEY);
  $("apiKeyInput").value = "";
  updateApiKeyStatus();
  refreshProjectScopeStatus();
}

function updateApiKeyStatus() {
  $("apiKeyStatus").textContent = state.apiKey ? "API key saved" : "No API key saved";
}

function loadProjectScope() {
  state.projectId = localStorage.getItem(PROJECT_ID_STORAGE_KEY) || "default";
  $("projectIdInput").value = state.projectId;
  updateProjectScopeStatus();
}

function saveProjectScope() {
  state.projectId = $("projectIdInput").value.trim() || "default";
  localStorage.setItem(PROJECT_ID_STORAGE_KEY, state.projectId);
  $("projectIdInput").value = state.projectId;
  updateProjectScopeStatus();
  refreshProjectScopeStatus();
}

function updateProjectScopeStatus() {
  const requested = state.projectId || "default";
  const scope = state.projectScope;
  if (!scope) {
    $("projectIdStatus").textContent = `Project scope: ${requested}`;
    return;
  }
  const active = scope.active_project_id || requested;
  const mode = scope.compatibility_mode
    ? "compatibility"
    : scope.isolation_status || "scoped";
  $("projectIdStatus").textContent = `Project scope: ${requested} -> ${active} | ${mode}`;
}

async function refreshProjectScopeStatus() {
  if (!state.apiKey) {
    state.projectScope = null;
    updateProjectScopeStatus();
    return;
  }
  try {
    const response = await fetch("/research/project/scope", {
      headers: withAuthHeaders("/research/project/scope"),
    });
    rememberRequestId(response);
    state.projectScope = response.ok ? await response.json() : null;
  } catch (_error) {
    state.projectScope = null;
  }
  updateProjectScopeStatus();
}

function withAuthHeaders(path, headers = {}) {
  const merged = new Headers(headers || {});
  if (path.startsWith("/research")) {
    if (state.apiKey) {
      merged.set(API_KEY_HEADER, state.apiKey);
    }
    if (state.projectId) {
      merged.set(PROJECT_ID_HEADER, state.projectId);
    }
  }
  return merged;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: withAuthHeaders(path, options.headers),
  });
  const requestId = rememberRequestId(response);
  const text = await response.text();
  let body = text;
  try {
    body = JSON.parse(text);
  } catch {
    body = text;
  }
  if (!response.ok) {
    const detail = body && body.detail ? body.detail : text;
    if (response.status === 401 && path.startsWith("/research")) {
      setConnection(false, "API key required");
    }
    throw new Error(withRequestId(`${response.status} ${detail}`, requestId));
  }
  return body;
}

async function downloadWithAuth(path, filename) {
  const response = await fetch(path, { headers: withAuthHeaders(path) });
  const requestId = rememberRequestId(response);
  if (!response.ok) {
    const text = await response.text();
    if (response.status === 401 && path.startsWith("/research")) {
      setConnection(false, "API key required");
    }
    throw new Error(withRequestId(`${response.status} ${text}`, requestId));
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function checkHealth() {
  try {
    const health = await api("/health");
    const readiness = await fetchReadiness();
    renderOperationalReadiness(readiness.body);
    const status = readiness.body.status || (readiness.ok ? "ready" : "not_ready");
    setConnection(readiness.ok, `${health.service} ${status}`);
  } catch (error) {
    setConnection(false, error.message);
    renderOperationalReadiness(null);
  }
}

async function fetchReadiness() {
  const response = await fetch("/health/ready");
  rememberRequestId(response);
  let body = {};
  try {
    body = await response.json();
  } catch (_error) {
    body = { status: "unknown", checks: {} };
  }
  rememberReadinessConfig(body);
  rememberRequestId(response);
  return { ok: response.ok, body };
}

function renderOperationalReadiness(readiness) {
  const checks = readiness?.checks || {};
  const items = [
    ["DB", checks.database],
    ["Storage", checks.database_storage],
    ["Auth", checks.api_key_auth],
    ["Req ID", checks.request_id_header],
    ["Workbench", checks.workbench_assets],
    ["Model", checks.model_provider_configuration],
    ["Literature", checks.external_literature_search],
  ];
  $("readinessStrip").innerHTML = items
    .map(([label, check]) => renderReadinessBadge(label, check))
    .join("");
}

function renderReadinessBadge(label, check) {
  const ok = Boolean(check?.ok);
  const state = ok ? "ok" : "error";
  return `<span class="${state}" title="${escapeHtml(label)} ${ok ? "ok" : "needs attention"}">${escapeHtml(label)}</span>`;
}

async function loadOnboardingReadiness(previewMarkdown = false) {
  renderResult("onboardingResult", "Checking onboarding readiness...", "warn");
  try {
    const body = await api("/research/onboarding/readiness");
    state.onboardingReadiness = body;
    if (previewMarkdown) {
      $("dossierPreview").textContent = body.markdown_export || "";
    }
    const score = Math.round((body.readiness_score || 0) * 100);
    const checklist = renderList(
      "Checklist",
      body.checklist || [],
      (item) => `${String(item.status).toUpperCase()} ${item.label}: ${item.detail}`,
    );
    const actions = renderList(
      "Recommended actions",
      body.recommended_actions || [],
      (action) => action,
    );
    renderResult(
      "onboardingResult",
      `Readiness <code>${escapeHtml(body.readiness_level)}</code> ${score}%. Required ${body.required_done}/${body.required_total}; missing ${body.missing_required.length}.<br />${checklist}${actions}`,
    );
  } catch (error) {
    renderWorkbenchError("onboardingResult", error);
  }
}

async function createOnboardingTasks() {
  renderResult("onboardingResult", "Creating onboarding tasks...", "warn");
  try {
    const body = await api("/research/onboarding/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ limit: 8, include_optional: true, created_by: "workbench" }),
    });
    state.latestTaskIds = [...state.latestTaskIds, ...body.tasks.map((task) => task.id)];
    renderResult(
      "onboardingResult",
      `${escapeHtml(body.message)}<br />${renderList("Onboarding tasks", body.tasks, (task) => `${task.priority}/${task.status}: ${task.title}`)}`,
    );
  } catch (error) {
    renderWorkbenchError("onboardingResult", error);
  }
}

async function loadOnboardingProgress() {
  renderResult("onboardingResult", "Loading onboarding progress...", "warn");
  try {
    const body = await api("/research/onboarding/progress");
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "onboardingResult",
      `Onboarding completion ${Math.round((body.task_summary.completion_ratio || 0) * 100)}%. Open: ${body.task_summary.open_task_count}; blocked: ${body.task_summary.blocked_task_count}.<br />Next: ${escapeHtml(body.next_action)}.`,
    );
  } catch (error) {
    renderWorkbenchError("onboardingResult", error);
  }
}

async function loadPilotReport() {
  renderResult("onboardingResult", "Loading status report...", "warn");
  try {
    const body = await api("/research/pilot/report");
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "onboardingResult",
      `Status report <code>${escapeHtml(body.report_status)}</code>. Phase <code>${escapeHtml(body.cockpit_phase)}</code>; readiness <code>${escapeHtml(body.readiness_level)}</code>.<br />${escapeHtml(body.executive_summary)}`,
    );
  } catch (error) {
    renderWorkbenchError("onboardingResult", error);
  }
}

async function savePilotReportSnapshot() {
  renderResult("onboardingResult", "Saving status report snapshot...", "warn");
  try {
    const body = await api("/research/pilot/report/snapshots", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: "Workbench Local Status Report",
        created_by: "workbench",
      }),
    });
    state.latestPilotReportSnapshotId = body.id;
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "onboardingResult",
      `Saved status report snapshot <code>${escapeHtml(body.id)}</code> with ${body.markdown_export_chars} Markdown chars.`,
    );
  } catch (error) {
    renderWorkbenchError("onboardingResult", error);
  }
}

async function createPilotReportSnapshotTasks() {
  if (!state.latestPilotReportSnapshotId) {
    renderWorkbenchEmpty("onboardingResult", "Save a status report snapshot first.");
    return;
  }
  renderResult("onboardingResult", "Creating status report snapshot tasks...", "warn");
  try {
    const body = await api(
      `/research/pilot/report/snapshots/${state.latestPilotReportSnapshotId}/tasks`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          limit: 8,
          include_risks: true,
          include_next_actions: true,
          include_quick_actions: true,
          created_by: "workbench",
        }),
      },
    );
    state.latestTaskIds = [...state.latestTaskIds, ...body.tasks.map((task) => task.id)];
    renderResult(
      "onboardingResult",
      `${escapeHtml(body.message)}<br />${renderList("Status report tasks", body.tasks, (task) => `${task.priority}/${task.status}: ${task.title}`)}`,
    );
  } catch (error) {
    renderWorkbenchError("onboardingResult", error);
  }
}

async function comparePilotReportSnapshots() {
  renderResult("onboardingResult", "Comparing latest status report snapshots...", "warn");
  try {
    const snapshots = await api("/research/pilot/report/snapshots?limit=2");
    if (snapshots.length < 2) {
      renderWorkbenchEmpty("onboardingResult", "Save at least two status report snapshots first.");
      return;
    }
    const [candidate, baseline] = snapshots;
    const body = await api("/research/pilot/report/snapshots/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        baseline_snapshot_id: baseline.id,
        candidate_snapshot_id: candidate.id,
      }),
    });
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "onboardingResult",
      `${escapeHtml(body.summary)}<br />Risks +${body.added_risks.length}/-${body.removed_risks.length}; next actions +${body.added_next_actions.length}/-${body.removed_next_actions.length}.`,
    );
  } catch (error) {
    renderWorkbenchError("onboardingResult", error);
  }
}

async function createPilotReportSnapshotComparisonTasks() {
  renderResult("onboardingResult", "Creating status report comparison tasks...", "warn");
  try {
    const snapshots = await api("/research/pilot/report/snapshots?limit=2");
    if (snapshots.length < 2) {
      renderWorkbenchEmpty("onboardingResult", "Save at least two status report snapshots first.");
      return;
    }
    const [candidate, baseline] = snapshots;
    const body = await api("/research/pilot/report/snapshots/compare/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        baseline_snapshot_id: baseline.id,
        candidate_snapshot_id: candidate.id,
        limit: 8,
        include_risks: true,
        include_next_actions: true,
        include_quick_actions: true,
        created_by: "workbench",
      }),
    });
    state.latestTaskIds = [...state.latestTaskIds, ...body.tasks.map((task) => task.id)];
    renderResult(
      "onboardingResult",
      `${escapeHtml(body.message)}<br />${renderList("Status report comparison tasks", body.tasks, (task) => `${task.priority}/${task.status}: ${task.title}`)}`,
    );
  } catch (error) {
    renderWorkbenchError("onboardingResult", error);
  }
}

function fillProfileForm(profile) {
  $("profileName").value = profile.name || "Default Research Profile";
  $("profileDomains").value = formatCsv(profile.primary_domains);
  $("profileQuestions").value = formatCsv(profile.active_questions);
  $("profileVenues").value = formatCsv(profile.target_venues);
  $("profileMethods").value = formatCsv(profile.methodological_preferences);
  $("profileConstraints").value = formatCsv(profile.resource_constraints);
  $("profileRisk").value = profile.risk_tolerance || "medium";
  $("profileTimeline").value = profile.timeline_horizon || "";
  $("profileAvoid").value = formatCsv(profile.negative_preferences);
  $("profileWeights").value = formatWeights(profile.evaluation_weights);
  $("profileNotes").value = profile.notes || "";
}

function fillSetupWizardForm(profile) {
  $("setupName").value = profile.name || "Local Research Agent";
  $("setupDomains").value = formatCsv(profile.primary_domains);
  $("setupQuestions").value = formatCsv(profile.active_questions);
  $("setupVenues").value = formatCsv(profile.target_venues);
  $("setupMethods").value = formatCsv(profile.methodological_preferences);
  $("setupConstraints").value = formatCsv(profile.resource_constraints);
  $("setupRisk").value = profile.risk_tolerance || "medium";
  $("setupTimeline").value = profile.timeline_horizon || "";
}

function profilePayload() {
  return {
    name: $("profileName").value.trim() || "Default Research Profile",
    primary_domains: parseCsv($("profileDomains").value),
    active_questions: parseCsv($("profileQuestions").value),
    target_venues: parseCsv($("profileVenues").value),
    methodological_preferences: parseCsv($("profileMethods").value),
    resource_constraints: parseCsv($("profileConstraints").value),
    risk_tolerance: $("profileRisk").value || "medium",
    timeline_horizon: $("profileTimeline").value.trim(),
    negative_preferences: parseCsv($("profileAvoid").value),
    evaluation_weights: parseWeights($("profileWeights").value),
    notes: $("profileNotes").value.trim(),
    created_by: "workbench",
  };
}

function setupWizardPayload() {
  return {
    name: $("setupName").value.trim() || "Local Research Agent",
    primary_domains: parseCsv($("setupDomains").value),
    active_questions: parseCsv($("setupQuestions").value),
    target_venues: parseCsv($("setupVenues").value),
    methodological_preferences: parseCsv($("setupMethods").value),
    resource_constraints: parseCsv($("setupConstraints").value),
    risk_tolerance: $("setupRisk").value || "medium",
    timeline_horizon: $("setupTimeline").value.trim(),
    negative_preferences: [],
    evaluation_weights: {},
    customer_context: "Workbench local setup",
    success_criteria: parseCsv($("setupCriteria").value),
    first_milestone: $("setupMilestone").value.trim(),
    notes: "",
    created_by: "workbench",
  };
}

async function loadResearchProfile() {
  renderResult("profileResult", "Loading research profile...", "warn");
  try {
    const body = await api("/research/profile");
    state.researchProfile = body;
    fillProfileForm(body);
    fillSetupWizardForm(body);
    $("dossierPreview").textContent = body.markdown_export || "No profile markdown yet.";
    renderResult(
      "profileResult",
      `Loaded profile <code>${escapeHtml(body.name)}</code> with ${body.primary_domains.length} domains and ${body.resource_constraints.length} constraints.`,
    );
  } catch (error) {
    renderWorkbenchError("profileResult", error);
  }
}

async function saveResearchProfile(event) {
  event.preventDefault();
  renderResult("profileResult", "Saving research profile...", "warn");
  try {
    const body = await api("/research/profile", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(profilePayload()),
    });
    state.researchProfile = body;
    fillProfileForm(body);
    fillSetupWizardForm(body);
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "profileResult",
      `Saved profile <code>${escapeHtml(body.name)}</code>. Ranking and briefs will use these constraints.`,
    );
  } catch (error) {
    renderWorkbenchError("profileResult", error);
  }
}

async function runProjectSetupWizard(event) {
  event.preventDefault();
  renderResult("onboardingResult", "Saving project setup...", "warn");
  try {
    const body = await api("/research/onboarding/setup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(setupWizardPayload()),
    });
    state.researchProfile = body.profile;
    state.onboardingReadiness = body.readiness;
    fillProfileForm(body.profile);
    fillSetupWizardForm(body.profile);
    $("dossierPreview").textContent = body.markdown_export;
    const score = Math.round((body.readiness.readiness_score || 0) * 100);
    renderResult(
      "onboardingResult",
      `${escapeHtml(body.message)} Readiness <code>${escapeHtml(body.readiness.readiness_level)}</code> ${score}%.<br />${renderList("Next steps", body.recommended_next_steps, (step) => step)}`,
    );
  } catch (error) {
    renderWorkbenchError("onboardingResult", error);
  }
}

async function previewResearchProfile() {
  renderResult("profileResult", "Loading profile markdown...", "warn");
  try {
    const markdown = await api("/research/profile/export/markdown");
    $("dossierPreview").textContent = markdown;
    renderResult("profileResult", "Loaded profile Markdown preview.");
  } catch (error) {
    renderWorkbenchError("profileResult", error);
  }
}

async function uploadPaper(event) {
  event.preventDefault();
  const file = $("paperFile").files[0];
  if (!file) {
    renderWorkbenchEmpty("uploadResult", "Choose a paper file first.");
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
    renderWorkbenchError("uploadResult", error);
  }
}

async function runWorkflow() {
  if (!state.paperId) {
    renderWorkbenchEmpty("workflowResult", "Upload a paper before running the workflow.");
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
    state.latestJobStatus = body.status || "queued";
    renderLatestWorkflow("Workflow queued. Waiting for artifacts.");
    renderResult("workflowResult", `Queued job <code>${body.id}</code>. Polling status...`);
    startPollingJob(body.id);
    await refreshJobs();
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
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
    state.jobId = job.id || jobId;
    state.latestJobStatus = job.status || state.latestJobStatus;
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
    renderLatestWorkflow(
      job.status === "completed"
        ? "Workflow completed. Dossier can be loaded."
        : `Workflow ${job.status || "running"}.`,
    );
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
    renderWorkbenchError("workflowResult", error);
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
  renderLatestWorkflow("Workflow artifacts loaded.");
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
    renderWorkbenchError("contextResult", error);
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
    renderWorkbenchError("literatureResult", error);
  }
}

async function askAdvisorChat(event) {
  event.preventDefault();
  const question = $("advisorQuestion").value.trim();
  if (!question) return;
  renderResult("advisorChatResult", "Asking project advisor...", "warn");
  try {
    const body = await api("/research/advisor/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        idea_id: state.latestIdeaId || null,
        paper_ids: state.paperId ? [state.paperId] : [],
        include_cockpit: true,
        include_context: true,
        context_limit: 5,
        created_by: "workbench",
      }),
    });
    $("dossierPreview").textContent = body.answer_markdown;
    renderResult(
      "advisorChatResult",
      `<strong>${escapeHtml(body.intent)}</strong> phase <code>${escapeHtml(body.cockpit_phase || "n/a")}</code>, readiness <code>${escapeHtml(body.readiness_level || "n/a")}</code>.<br />${escapeHtml(body.answer)}<br />Actions: ${body.recommended_actions.length}; citations: ${body.cited_evidences.length + body.cited_gaps.length + body.cited_ideas.length}.`,
    );
  } catch (error) {
    renderWorkbenchError("advisorChatResult", error);
  }
}

async function createAdvisorChatTasks() {
  const question = $("advisorQuestion").value.trim();
  if (!question) return;
  renderResult("advisorChatResult", "Creating advisor chat tasks...", "warn");
  try {
    const body = await api("/research/advisor/chat/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        idea_id: state.latestIdeaId || null,
        paper_ids: state.paperId ? [state.paperId] : [],
        include_cockpit: true,
        include_context: true,
        context_limit: 5,
        limit: 8,
        include_recommendations: true,
        include_risks: true,
        created_by: "workbench",
      }),
    });
    state.latestTaskIds = [...state.latestTaskIds, ...body.tasks.map((task) => task.id)];
    renderResult(
      "advisorChatResult",
      `${escapeHtml(body.message)}<br />${renderList("Advisor tasks", body.tasks, (task) => `${task.priority}/${task.status}: ${task.title}`)}`,
    );
  } catch (error) {
    renderWorkbenchError("advisorChatResult", error);
  }
}

async function createAdvisorActionSession() {
  const question = $("advisorQuestion").value.trim();
  if (!question) return;
  renderResult("advisorChatResult", "Creating advisor action session...", "warn");
  try {
    const body = await api("/research/advisor/action-session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        idea_id: state.latestIdeaId || null,
        paper_ids: state.paperId ? [state.paperId] : [],
        include_cockpit: true,
        include_context: true,
        context_limit: 5,
        limit: 8,
        include_recommendations: true,
        include_risks: true,
        include_tool_suggestions: false,
        snapshot_title: "Workbench Advisor Action Session",
        include_snapshot: true,
        created_by: "workbench",
      }),
    });
    state.latestTaskIds = [...state.latestTaskIds, ...body.tasks.map((task) => task.id)];
    state.latestTaskSnapshotId = body.snapshot?.id || state.latestTaskSnapshotId;
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "advisorChatResult",
      `${escapeHtml(body.message)}<br />Intent <code>${escapeHtml(body.chat.intent)}</code>; open tasks: ${body.progress_summary.open_task_count}; snapshot: <code>${escapeHtml(body.progress_summary.snapshot_id || "none")}</code>.`,
    );
  } catch (error) {
    renderWorkbenchError("advisorChatResult", error);
  }
}


function renderPilotMetric(label, value, detail) {
  return `
    <div class="pilot-metric">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
      <small>${escapeHtml(detail)}</small>
    </div>
  `;
}

function renderPilotPathSequence(sequence) {
  const target = $("pilotPathSteps");
  if (!target || !Array.isArray(sequence) || !sequence.length) {
    return;
  }
  target.innerHTML = sequence
    .slice()
    .sort((left, right) => (left.rank || 0) - (right.rank || 0))
    .map((step) => {
      const href = step.workbench_anchor || "#pilot-path";
      const status = step.status || "pending";
      const rank = String(step.rank || "").padStart(2, "0");
      const detail = step.detail || step.action_label || "";
      return `
        <a href="${escapeHtml(href)}" data-stage="${escapeHtml(step.stage || "")}" data-status="${escapeHtml(status)}">
          <span>${escapeHtml(rank)}</span>
          <strong>${escapeHtml(step.label || step.stage || "Stage")}</strong>
          <small>${escapeHtml(status)} - ${escapeHtml(detail)}</small>
        </a>
      `;
    })
    .join("");
}

function renderPilotActionList(actions) {
  if (!actions.length) {
    return "";
  }
  return `<ol class="pilot-action-list">${actions
    .map((action) => `<li>${escapeHtml(action)}</li>`)
    .join("")}</ol>`;
}

async function loadPilotLaunch() {
  renderResult("pilotLaunchResult", "Refreshing launch status...", "warn");
  try {
    const [readiness, progress, cockpit] = await Promise.all([
      api("/research/onboarding/readiness"),
      api("/research/onboarding/progress?limit=100"),
      api("/research/cockpit"),
    ]);
    const taskSummary = progress.task_summary || {};
    const metrics = [
      renderPilotMetric(
        "Readiness",
        readiness.readiness_level,
        `${Math.round((readiness.readiness_score || 0) * 100)}% setup score`,
      ),
      renderPilotMetric(
        "Onboarding",
        `${readiness.required_done}/${readiness.required_total}`,
        `${readiness.missing_required.length} required gaps`,
      ),
      renderPilotMetric("Cockpit", cockpit.phase, cockpit.readiness_level),
      renderPilotMetric(
        "Tasks",
        `${taskSummary.open_task_count || 0} open`,
        `${taskSummary.blocked_task_count || 0} blocked`,
      ),
    ];
    $("pilotLaunchMetrics").innerHTML = metrics.join("");
    renderPilotPathSequence(cockpit.pilot_task_sequence);
    const primaryAction =
      (cockpit.primary_next_action && cockpit.primary_next_action.label) || progress.next_action;
    const actions = [
      primaryAction,
      ...(readiness.recommended_actions || []).slice(0, 3),
      ...(cockpit.risk_alerts || []).slice(0, 2),
    ].filter(Boolean);
    renderResult(
      "pilotLaunchResult",
      `Local readiness <code>${escapeHtml(readiness.readiness_level)}</code>; cockpit phase <code>${escapeHtml(cockpit.phase)}</code>.${renderPilotActionList(actions)}`,
    );
  } catch (error) {
    $("pilotLaunchMetrics").innerHTML = [
      renderPilotMetric("Readiness", "Unavailable", "Check API connection."),
      renderPilotMetric("Onboarding", "Unavailable", "Refresh after setup."),
      renderPilotMetric("Cockpit", "Unavailable", "Refresh after workflow."),
      renderPilotMetric("Tasks", "Unavailable", "Refresh after tasks."),
    ].join("");
    renderWorkbenchError("pilotLaunchResult", error);
  }
}

async function listRealPaperEvaluationReports() {
  renderResult("realEvalResult", "Loading real-paper evaluation reports...", "warn");
  try {
    const reports = await api("/research/evaluations/real-paper/reports?limit=8");
    if (!reports.length) {
      renderWorkbenchEmpty("realEvalResult", "No real-paper evaluation reports found.");
      return;
    }
    state.latestRealEvalReportId = reports[0].report_id;
    renderResult(
      "realEvalResult",
      renderList(
        "Reports",
        reports,
        (report) =>
          `${report.report_id}: ${report.completed_paper_count}/${report.paper_count} papers, ${report.total_ideas} ideas, readiness ${report.average_readiness}, quality ${report.average_quality_gate}`,
      ),
    );
  } catch (error) {
    renderWorkbenchError("realEvalResult", error);
  }
}

async function loadLatestRealPaperEvaluationReport() {
  renderResult("realEvalResult", "Loading latest real-paper evaluation report...", "warn");
  try {
    const report = await api("/research/evaluations/real-paper/reports/latest");
    state.latestRealEvalReportId = report.report_id;
    $("dossierPreview").textContent =
      report.markdown_export || JSON.stringify(report.summary, null, 2);
    renderResult("realEvalResult", renderRealPaperEvaluationReport(report));
  } catch (error) {
    renderWorkbenchError("realEvalResult", error);
  }
}

function renderRealPaperEvaluationReport(report) {
  const blockers = [];
  for (const paper of report.papers || []) {
    const readinessLevel = paper.metrics?.readiness_level || "";
    const qualityDecision = paper.metrics?.quality_decision || "";
    if (readinessLevel && readinessLevel !== "ready") {
      blockers.push(`${paper.filename}: readiness ${readinessLevel}`);
    }
    if (qualityDecision && !["advance", "ready"].includes(qualityDecision)) {
      blockers.push(`${paper.filename}: quality ${qualityDecision}`);
    }
  }
  const papers = renderList("Papers", report.papers || [], (paper) => {
    const metrics = paper.metrics || {};
    return `${paper.filename}: ${paper.status}, ${metrics.gaps || 0} gaps, ${metrics.ideas || 0} ideas, readiness ${metrics.readiness_score || 0}, quality ${metrics.quality_score || 0}`;
  });
  const blockerText = blockers.length
    ? renderList("Blockers", blockers, (blocker) => blocker)
    : '<h4>Blockers</h4><div class="empty-state">No report-level blockers detected.</div>';
  return `
    <strong>${escapeHtml(report.report_id)}</strong><br />
    Completed ${report.completed_paper_count}/${report.paper_count} papers; gaps ${report.total_gaps}; ideas ${report.total_ideas}; embeddings ${report.total_embedding_indexed}.<br />
    Avg readiness ${report.average_readiness}; avg quality ${report.average_quality_gate}; models ${escapeHtml((report.embedding_models || []).join(", ") || "n/a")}.
    ${papers}${blockerText}
  `;
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

function renderJobActions(job) {
  const cancelDisabled = !["pending", "running"].includes(job.status) ? "disabled" : "";
  const retryDisabled = !["failed", "canceled"].includes(job.status) ? "disabled" : "";
  return `
    <div class="job-actions">
      <button class="compact-button" data-job-action="cancel" data-job-id="${escapeHtml(job.id)}" ${cancelDisabled}>Cancel</button>
      <button class="compact-button" data-job-action="retry" data-job-id="${escapeHtml(job.id)}" ${retryDisabled}>Retry</button>
    </div>
  `;
}

async function refreshJobs() {
  try {
    const jobs = await api("/research/jobs?limit=10");
    if (!jobs.length) {
      $("jobsTable").innerHTML = $("emptyTemplate").innerHTML;
      renderLatestWorkflow("No recent jobs found.");
      return;
    }
    const latestCompletedJob = jobs.find(
      (job) =>
        job.status === "completed" &&
        job.output &&
        Array.isArray(job.output.idea_ids) &&
        job.output.idea_ids.length,
    );
    if (latestCompletedJob) {
      restoreStateFromJob(latestCompletedJob);
    } else {
      renderLatestWorkflow("No completed workflow with ideas found yet.");
    }
    const rows = jobs
      .map(
        (job) => `<tr>
          <td><code>${escapeHtml(job.id)}</code></td>
          <td>${escapeHtml(job.status)}</td>
          <td>${Math.round((job.progress || 0) * 100)}%</td>
          <td>${escapeHtml(job.input.paper_id || "")}</td>
          <td>${escapeHtml(renderJobOutput(job.output).replace(/<[^>]*>/g, ""))}</td>
          <td>${renderJobActions(job)}</td>
        </tr>`,
      )
      .join("");
    $("jobsTable").classList.remove("muted");
    $("jobsTable").innerHTML = `<table>
      <thead><tr><th>Job</th><th>Status</th><th>Progress</th><th>Paper</th><th>Outputs</th><th>Actions</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
  } catch (error) {
    $("jobsTable").innerHTML = escapeHtml(error.message);
  }
}

async function handleJobAction(event) {
  const button = event.target.closest("button[data-job-action]");
  if (!button) {
    return;
  }
  const jobId = button.dataset.jobId;
  const action = button.dataset.jobAction;
  if (!jobId || !action || button.disabled) {
    return;
  }
  renderResult("workflowResult", `${action === "cancel" ? "Canceling" : "Retrying"} job...`, "warn");
  try {
    const body = await api(`/research/jobs/${jobId}/${action}`, { method: "POST" });
    if (action === "retry") {
      state.jobId = body.id;
      if (["pending", "running"].includes(body.status)) {
        pollJob(body.id);
      }
    }
    renderResult(
      "workflowResult",
      `Job <code>${escapeHtml(body.id)}</code> is now <strong>${escapeHtml(body.status)}</strong>.`,
    );
    await refreshJobs();
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
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
    try {
      const jobs = await api("/research/jobs?limit=10");
      const latestCompletedJob = jobs.find(
        (job) =>
          job.status === "completed" &&
          job.output &&
          Array.isArray(job.output.idea_ids) &&
          job.output.idea_ids.length,
      );
      if (restoreStateFromJob(latestCompletedJob) && state.jobId) {
        await loadJobArtifacts(state.jobId);
        return;
      }
    } catch (error) {
      $("dossierPreview").textContent = error.message;
      return;
    }
    renderWorkbenchEmpty("workflowResult", "Run a workflow first so an idea id is available.");
    return;
  }
  try {
    const markdown = await api(`/research/ideas/${state.latestIdeaId}/export/markdown`);
    $("dossierPreview").textContent = markdown;
    renderLatestWorkflow("Dossier loaded for latest idea.");
    renderResult(
      "workflowResult",
      `Loaded dossier for idea <code>${escapeHtml(state.latestIdeaId)}</code>.`,
    );
  } catch (error) {
    $("dossierPreview").textContent = error.message;
  }
}

async function refineLatestIdea() {
  if (!state.latestIdeaId) {
    renderWorkbenchEmpty("workflowResult", "Run a workflow first so an idea id is available.");
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
    state.latestNoveltyCheckId = "";
    state.latestEvidenceLedgerId = "";
    state.latestTaskIds = [];
    state.latestTaskSnapshotId = "";
    renderResult(
      "workflowResult",
      `Created refined idea <code>${escapeHtml(body.refined_idea.id)}</code> from <code>${escapeHtml(body.source_idea.id)}</code>.<br />${renderList("Applied actions", body.applied_actions, (item) => item)}`,
    );
    await loadDossier();
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function refreshNoveltySearch() {
  if (!state.latestIdeaId) {
    renderWorkbenchEmpty("workflowResult", "Run a workflow first so an idea id is available.");
    return;
  }
  renderResult("workflowResult", "Refreshing novelty search...", "warn");
  try {
    const body = await api(`/research/ideas/${state.latestIdeaId}/novelty-refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        include_external: true,
        limit: 8,
        query_override: $("refineFocus").value.trim(),
      }),
    });
    state.latestNoveltyCheckId = body.id;
    renderResult(
      "workflowResult",
      `Novelty refresh <code>${escapeHtml(body.id)}</code>: ${escapeHtml(body.risk_level)} risk with ${body.collision_signals.length} signals.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function createSotaReviewPackage() {
  if (!state.latestIdeaId) {
    renderWorkbenchEmpty("workflowResult", "Run a workflow first so an idea id is available.");
    return;
  }
  renderResult("workflowResult", "Creating SOTA review package...", "warn");
  try {
    const includeExternal = Boolean($("includeExternal")?.checked);
    const body = await api(`/research/ideas/${state.latestIdeaId}/sota-review-package`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        include_external: includeExternal,
        limit: 8,
        created_by: "workbench",
      }),
    });
    state.latestSotaReviewPackageId = body.id;
    $("dossierPreview").textContent = body.markdown_export;
    const summary = body.summary || {};
    renderResult(
      "workflowResult",
      `Created SOTA package <code>${escapeHtml(body.id)}</code> with status <code>${escapeHtml(summary.review_status || "manual_sota_review_required")}</code>. Missing searches: ${(summary.missing_searches || []).length}.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function createSotaExternalSearchEvidence() {
  if (!state.latestIdeaId) {
    renderWorkbenchEmpty("workflowResult", "Run a workflow first so an idea id is available.");
    return;
  }
  renderResult("workflowResult", "Creating SOTA external search evidence...", "warn");
  try {
    const includeExternal = Boolean($("includeExternal")?.checked);
    const body = await api(`/research/ideas/${state.latestIdeaId}/sota-external-search-evidence`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        review_package_id: state.latestSotaReviewPackageId,
        queries: [],
        include_external: includeExternal,
        limit: 8,
        created_by: "workbench",
      }),
    });
    state.latestSotaExternalSearchEvidenceId = body.id;
    $("dossierPreview").textContent = body.markdown_export;
    const summary = body.summary || {};
    renderResult(
      "workflowResult",
      `Created SOTA search evidence <code>${escapeHtml(body.id)}</code> with status <code>${escapeHtml(summary.search_status || "unknown")}</code>. Results: ${summary.result_count || 0}.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function createSotaSignoff() {
  if (!state.latestIdeaId) {
    renderWorkbenchEmpty("workflowResult", "Run a workflow first so an idea id is available.");
    return;
  }
  renderResult("workflowResult", "Recording SOTA signoff...", "warn");
  try {
    const benchmarkRunIds = state.latestExperimentRunId ? [state.latestExperimentRunId] : [];
    const body = await api(`/research/ideas/${state.latestIdeaId}/sota-signoffs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        review_package_id: state.latestSotaReviewPackageId,
        external_search_evidence_id: state.latestSotaExternalSearchEvidenceId,
        decision: "needs_more_search",
        reviewer: "workbench",
        external_searches_completed: false,
        nearest_work: [],
        evidence_links: [],
        benchmark_run_ids: benchmarkRunIds,
        final_novelty_claim: $("refineFocus").value.trim(),
        limitations: ["Workbench signoff is provisional until external search and nearest-work review are complete."],
        notes: "Workbench-created signoff record for manual SOTA closure.",
        created_by: "workbench",
      }),
    });
    state.latestSotaSignoffId = body.id;
    $("dossierPreview").textContent = body.markdown_export;
    const summary = body.summary || {};
    renderResult(
      "workflowResult",
      `Recorded SOTA signoff <code>${escapeHtml(body.id)}</code> with status <code>${escapeHtml(summary.signoff_status || "needs_more_search")}</code>.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function createNoveltyTasks() {
  if (!state.latestIdeaId || !state.latestNoveltyCheckId) {
    renderWorkbenchEmpty("workflowResult", "Refresh novelty before creating novelty tasks.");
    return;
  }
  renderResult("workflowResult", "Creating novelty follow-up tasks...", "warn");
  try {
    const body = await api(
      `/research/ideas/${state.latestIdeaId}/novelty-checks/${state.latestNoveltyCheckId}/tasks`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ created_by: "workbench" }),
      },
    );
    state.latestTaskIds = [...state.latestTaskIds, ...body.tasks.map((task) => task.id)];
    renderResult(
      "workflowResult",
      `${escapeHtml(body.message)}<br />${renderList("Novelty tasks", body.tasks, (task) => `${task.priority}/${task.status}: ${task.title}`)}`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function createRelatedWorkMatrix() {
  if (!state.latestIdeaId) {
    renderWorkbenchEmpty("workflowResult", "Run a workflow first so an idea id is available.");
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
    renderWorkbenchError("workflowResult", error);
  }
}

async function createProposalDraft() {
  if (!state.latestIdeaId) {
    renderWorkbenchEmpty("workflowResult", "Run a workflow first so an idea id is available.");
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
    renderWorkbenchError("workflowResult", error);
  }
}

async function reviewProposalDraft() {
  if (!state.latestIdeaId || !state.latestProposalDraftId) {
    renderWorkbenchEmpty("workflowResult", "Create a proposal draft first.");
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
    renderWorkbenchError("workflowResult", error);
  }
}

async function reviseProposalDraft() {
  if (!state.latestIdeaId || !state.latestProposalDraftId) {
    renderWorkbenchEmpty("workflowResult", "Create a proposal draft first.");
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
    renderWorkbenchError("workflowResult", error);
  }
}

async function createTaskBacklog() {
  if (!state.latestIdeaId || !state.latestProposalDraftId || !state.latestProposalRevisionId) {
    renderWorkbenchEmpty("workflowResult", "Create a proposal revision first.");
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
    renderWorkbenchError("workflowResult", error);
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
    renderWorkbenchError("workflowResult", error);
  }
}

function fillTaskSelect(tasks) {
  const select = $("taskSelect");
  select.innerHTML = "";
  for (const task of tasks) {
    const option = document.createElement("option");
    option.value = task.id;
    option.textContent = `${task.priority}/${task.status} ${task.title}`.slice(0, 96);
    select.appendChild(option);
  }
}

function renderTaskBoardMarkdown(tasks) {
  const lines = ["# Workbench Task Board", ""];
  if (!tasks.length) {
    lines.push("- No tasks found.");
    return lines.join("\n");
  }
  for (const task of tasks) {
    lines.push(
      `- \`${task.id}\` \`${task.priority}\` \`${task.status}\` owner=\`${task.owner_type}\` ${task.title}`,
    );
    if (task.due_phase) {
      lines.push(`  - due_phase: ${task.due_phase}`);
    }
  }
  return `${lines.join("\n")}\n`;
}

async function loadTaskBoard() {
  renderResult("workflowResult", "Loading task board...", "warn");
  try {
    const params = new URLSearchParams({ limit: "50" });
    if (state.latestIdeaId) {
      params.set("idea_id", state.latestIdeaId);
    }
    if ($("taskStatusFilter").value) {
      params.set("status", $("taskStatusFilter").value);
    }
    const tasks = await api(`/research/tasks?${params.toString()}`);
    state.taskBoardItems = tasks;
    state.latestTaskIds = tasks.map((task) => task.id);
    fillTaskSelect(tasks);
    $("dossierPreview").textContent = renderTaskBoardMarkdown(tasks);
    renderResult("workflowResult", `Loaded ${tasks.length} tasks into the workbench task board.`);
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function updateSelectedTask(status) {
  const taskId = $("taskSelect").value || state.latestTaskIds[0];
  if (!taskId) {
    renderWorkbenchEmpty("workflowResult", "Load a task board before updating a task.");
    return;
  }
  renderResult("workflowResult", `Updating task <code>${escapeHtml(taskId)}</code>...`, "warn");
  try {
    const task = await api(`/research/tasks/${taskId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        status,
        note: `Marked ${status} from the workbench task board.`,
        created_by: "workbench",
      }),
    });
    renderResult(
      "workflowResult",
      `Updated task <code>${escapeHtml(task.id)}</code> to <strong>${escapeHtml(task.status)}</strong>.`,
    );
    await loadTaskBoard();
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function recordClaimValidationResult() {
  const taskId = $("taskSelect").value || state.latestTaskIds[0];
  if (!taskId) {
    renderWorkbenchEmpty("workflowResult", "Load a claim validation task first.");
    return;
  }
  renderResult("workflowResult", `Recording claim result for <code>${escapeHtml(taskId)}</code>...`, "warn");
  try {
    const event = await api(`/research/tasks/${taskId}/claim-validation-result`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        validation_status: "needs_more_evidence",
        evidence_ids: [],
        notes: $("refineFocus").value.trim() || "Workbench claim validation result.",
        next_action: "Collect one independent support source or counterexample.",
        created_by: "workbench",
      }),
    });
    renderResult(
      "workflowResult",
      `Recorded claim result <code>${escapeHtml(event.id)}</code>: ${escapeHtml(event.metadata.validation_status)}.`,
    );
    await loadTaskBoard();
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function createExperimentRun() {
  if (!state.latestIdeaId) {
    renderWorkbenchEmpty("workflowResult", "Run a workflow first so an idea id is available.");
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
    renderWorkbenchError("workflowResult", error);
  }
}

async function createBenchmarkRun() {
  if (!state.latestIdeaId) {
    renderWorkbenchEmpty("workflowResult", "Run a workflow first so an idea id is available.");
    return;
  }
  renderResult("workflowResult", "Recording benchmark run packet...", "warn");
  try {
    if (!state.latestExperimentPlanId) {
      const plan = await api(`/research/ideas/${state.latestIdeaId}/experiment-plan`, {
        method: "POST",
      });
      state.latestExperimentPlanId = plan.id;
    }
    const body = await api(`/research/experiment-plans/${state.latestExperimentPlanId}/benchmark-run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: "Workbench benchmark packet",
        task_id: state.latestTaskIds.length ? state.latestTaskIds[0] : null,
        benchmark_name: "First validation benchmark",
        dataset: "Dataset to be confirmed",
        split: "validation",
        baseline_name: "nearest recorded baseline",
        primary_metric: "primary_metric",
        metric_direction: "higher_is_better",
        candidate_result: null,
        baseline_result: null,
        metric_results: {},
        command: "",
        config: { source: "workbench" },
        artifact_links: [],
        dry_run: true,
        reproducibility_notes: $("refineFocus").value.trim(),
        created_by: "workbench",
      }),
    });
    state.latestExperimentRunId = body.id;
    state.latestExperimentAnalysisId = "";
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Recorded benchmark packet <code>${escapeHtml(body.id)}</code> with status ${escapeHtml(body.status)}.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function executeBenchmarkRun() {
  if (!state.latestIdeaId) {
    renderWorkbenchEmpty("workflowResult", "Run a workflow first so an idea id is available.");
    return;
  }
  renderResult("workflowResult", "Loading benchmark profiles...", "warn");
  try {
    if (!state.latestExperimentPlanId) {
      const plan = await api(`/research/ideas/${state.latestIdeaId}/experiment-plan`, {
        method: "POST",
      });
      state.latestExperimentPlanId = plan.id;
    }
    const profileResponse = await api("/research/benchmark-profiles");
    const profiles = profileResponse.profiles || [];
    const selectedProfile =
      profiles.find((profile) => profile.id === "geoloc-country-accuracy-jsonl" && profile.runnable) ||
      profiles.find((profile) => profile.id === "json-metrics-smoke" && profile.runnable) ||
      profiles.find((profile) => profile.runnable);
    if (!selectedProfile) {
      const profileDetails = profiles.length
        ? renderList(
            "Profiles",
            profiles,
            (profile) =>
              `${profile.id}: ${profile.runnable ? "runnable" : profile.disabled_reason || "not runnable"}`,
          )
        : "No benchmark profiles are configured.";
      renderResult(
        "workflowResult",
        `No runnable benchmark profile is available.<br />${profileDetails}`,
        "warn",
      );
      return;
    }
    renderResult(
      "workflowResult",
      `Executing benchmark profile <code>${escapeHtml(selectedProfile.id)}</code>...`,
      "warn",
    );
    const body = await api(
      `/research/experiment-plans/${state.latestExperimentPlanId}/benchmark-run/execute`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: "Workbench benchmark execution",
          task_id: state.latestTaskIds.length ? state.latestTaskIds[0] : null,
          profile_id: selectedProfile.id,
          config: { source: "workbench", selected_profile_label: selectedProfile.label },
          created_by: "workbench",
        }),
      },
    );
    state.latestExperimentRunId = body.id;
    state.latestExperimentAnalysisId = "";
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Executed benchmark profile <code>${escapeHtml(selectedProfile.id)}</code> as run <code>${escapeHtml(body.id)}</code> with status ${escapeHtml(body.status)}.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function compareBenchmarkRuns() {
  if (!state.latestExperimentPlanId) {
    renderWorkbenchEmpty("workflowResult", "Create or load an experiment plan first.");
    return;
  }
  renderResult("workflowResult", "Comparing recent benchmark runs...", "warn");
  try {
    const runs = await api(`/research/experiment-plans/${state.latestExperimentPlanId}/runs?limit=20`);
    const benchmarkRuns = (runs || []).filter((run) =>
      ["benchmark", "benchmark_command"].includes(run.parameters?.execution_kind),
    );
    if (benchmarkRuns.length < 2) {
      renderResult(
        "workflowResult",
        "At least two benchmark runs are required before a comparison can be created.",
        "warn",
      );
      return;
    }
    const [candidateRun, baselineRun] = benchmarkRuns;
    const body = await api("/research/experiment-runs/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        baseline_run_id: baselineRun.id,
        candidate_run_id: candidateRun.id,
        primary_metric: candidateRun.parameters?.primary_metric || baselineRun.parameters?.primary_metric || "",
        created_by: "workbench",
      }),
    });
    state.latestBenchmarkComparisonBriefId = body.brief_id;
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Compared benchmark runs into brief <code>${escapeHtml(body.brief_id)}</code> with status <code>${escapeHtml(body.status)}</code>.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function loadBenchmarkEvidenceReadiness() {
  if (!state.latestIdeaId) {
    renderWorkbenchEmpty("workflowResult", "Run or load an idea first.");
    return;
  }
  renderResult("workflowResult", "Checking benchmark evidence readiness...", "warn");
  try {
    const body = await api(
      `/research/ideas/${state.latestIdeaId}/benchmark-evidence/readiness`,
    );
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Benchmark evidence is <code>${escapeHtml(body.readiness_status)}</code>. Runs: ${body.completed_benchmark_run_count}/${body.benchmark_run_count}; comparisons: ${body.benchmark_comparison_count}.`,
      body.ready_for_sota_review ? "ok" : "warn",
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function createBenchmarkEvidenceTasks() {
  if (!state.latestIdeaId) {
    renderWorkbenchEmpty("workflowResult", "Run or load an idea first.");
    return;
  }
  renderResult("workflowResult", "Creating benchmark evidence tasks...", "warn");
  try {
    const body = await api(
      `/research/ideas/${state.latestIdeaId}/benchmark-evidence/readiness/tasks`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ created_by: "workbench" }),
      },
    );
    state.latestTaskIds = body.tasks.map((task) => task.id);
    renderResult(
      "workflowResult",
      `${escapeHtml(body.message)}<br />${renderList("Benchmark tasks", body.tasks, (task) => `${task.priority}/${task.status}: ${task.title}`)}`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function analyzeExperimentRun() {
  if (!state.latestExperimentRunId) {
    renderWorkbenchEmpty("workflowResult", "Record an experiment run first.");
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
    renderWorkbenchError("workflowResult", error);
  }
}

async function createAnalysisTasks() {
  if (!state.latestExperimentAnalysisId) {
    renderWorkbenchEmpty("workflowResult", "Analyze an experiment run first.");
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
    renderWorkbenchError("workflowResult", error);
  }
}

async function createDecisionMemo() {
  if (!state.latestIdeaId) {
    renderWorkbenchEmpty("workflowResult", "Run a workflow first so an idea id is available.");
    return;
  }
  renderResult("workflowResult", "Creating idea decision memo...", "warn");
  try {
    const body = await api(`/research/ideas/${state.latestIdeaId}/decision-memo`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        decision: "pursue",
        created_by: "workbench",
      }),
    });
    state.latestDecisionMemoId = body.id;
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Created decision memo <code>${escapeHtml(body.id)}</code> with ${body.next_commitments.length} commitments.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function createDecisionMemoTasks() {
  if (!state.latestIdeaId || !state.latestDecisionMemoId) {
    renderWorkbenchEmpty("workflowResult", "Create a decision memo first.");
    return;
  }
  renderResult("workflowResult", "Creating decision follow-up tasks...", "warn");
  try {
    const body = await api(
      `/research/ideas/${state.latestIdeaId}/decision-memos/${state.latestDecisionMemoId}/tasks`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ created_by: "workbench" }),
      },
    );
    state.latestTaskIds = [...state.latestTaskIds, ...body.tasks.map((task) => task.id)];
    renderResult(
      "workflowResult",
      `${escapeHtml(body.message)}<br />${renderList("Decision tasks", body.tasks, (task) => `${task.priority} ${task.status}: ${task.title}`)}`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function createAssumptionAudit() {
  if (!state.latestIdeaId) {
    renderWorkbenchEmpty("workflowResult", "Run a workflow first so an idea id is available.");
    return;
  }
  renderResult("workflowResult", "Auditing idea assumptions...", "warn");
  try {
    const body = await api(`/research/ideas/${state.latestIdeaId}/assumption-audit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ created_by: "workbench" }),
    });
    state.latestAssumptionAuditId = body.id;
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Created assumption audit <code>${escapeHtml(body.id)}</code> with ${body.assumptions.length} assumptions.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function createEvidenceLedger() {
  if (!state.latestIdeaId) {
    renderWorkbenchEmpty("workflowResult", "Run a workflow first so an idea id is available.");
    return;
  }
  renderResult("workflowResult", "Building claim-level evidence ledger...", "warn");
  try {
    const body = await api(`/research/ideas/${state.latestIdeaId}/evidence-ledger`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ created_by: "workbench" }),
    });
    state.latestEvidenceLedgerId = body.id;
    state.latestClaimId = body.claims.length ? body.claims[0].claim_id : "C1";
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Created evidence ledger <code>${escapeHtml(body.id)}</code> with ${body.claims.length} claims, coverage ${body.coverage_score}.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function createEvidenceLedgerTasks() {
  if (!state.latestIdeaId || !state.latestEvidenceLedgerId) {
    renderWorkbenchEmpty("workflowResult", "Create an evidence ledger first.");
    return;
  }
  renderResult("workflowResult", "Creating evidence follow-up tasks...", "warn");
  try {
    const body = await api(
      `/research/ideas/${state.latestIdeaId}/evidence-ledgers/${state.latestEvidenceLedgerId}/tasks`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ created_by: "workbench" }),
      },
    );
    state.latestTaskIds = [...state.latestTaskIds, ...body.tasks.map((task) => task.id)];
    renderResult(
      "workflowResult",
      `${escapeHtml(body.message)}<br />${renderList("Ledger tasks", body.tasks.slice(0, 8), (task) => `${task.priority} ${task.status}: ${task.title}`)}`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function loadClaimValidationPacket() {
  if (!state.latestIdeaId || !state.latestEvidenceLedgerId) {
    renderWorkbenchEmpty("workflowResult", "Create an evidence ledger first.");
    return;
  }
  const claimId = state.latestClaimId || "C1";
  renderResult("workflowResult", `Loading claim packet <code>${escapeHtml(claimId)}</code>...`, "warn");
  try {
    const body = await api(
      `/research/ideas/${state.latestIdeaId}/evidence-ledgers/${state.latestEvidenceLedgerId}/claims/${claimId}/validation-packet`,
    );
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Loaded claim packet <code>${escapeHtml(claimId)}</code> with ${body.supporting_evidence.length} supporting evidence records and ${body.related_tasks.length} related tasks.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function loadClaimValidationQueue() {
  renderResult("workflowResult", "Loading claim validation queue...", "warn");
  try {
    const params = new URLSearchParams({ limit: "20" });
    if (state.latestIdeaId) {
      params.set("idea_id", state.latestIdeaId);
    }
    const body = await api(`/research/claims/validation-queue?${params.toString()}`);
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Loaded ${body.items.length} claim validation queue items across ${body.summary.idea_count || 0} ideas.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function createClaimValidationQueueTasks() {
  renderResult("workflowResult", "Creating claim validation queue tasks...", "warn");
  try {
    const body = await api("/research/claims/validation-queue/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        idea_id: state.latestIdeaId || null,
        limit: 5,
        priority_filter: ["critical", "high"],
        created_by: "workbench",
      }),
    });
    state.latestTaskIds = body.tasks.map((task) => task.id);
    renderResult(
      "workflowResult",
      `${escapeHtml(body.message)}<br />${renderList("Claim validation tasks", body.tasks.slice(0, 8), (task) => `${task.priority} ${task.status}: ${task.title}`)}`,
    );
    await loadTaskBoard();
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function loadIdeaLineage() {
  if (!state.latestIdeaId) {
    renderWorkbenchEmpty("workflowResult", "Run a workflow first so an idea id is available.");
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
    renderWorkbenchError("workflowResult", error);
  }
}

async function loadIdeaTimeline() {
  if (!state.latestIdeaId) {
    renderWorkbenchEmpty("workflowResult", "Run a workflow first so an idea id is available.");
    return;
  }
  renderResult("workflowResult", "Loading idea timeline...", "warn");
  try {
    const body = await api(`/research/ideas/${state.latestIdeaId}/timeline`);
    $("dossierPreview").textContent = body.markdown_export;
    renderResult("workflowResult", `${escapeHtml(body.message)} Latest events: ${body.events.length}.`);
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function loadIdeaProgress() {
  if (!state.latestIdeaId) {
    renderWorkbenchEmpty("workflowResult", "Run a workflow first so an idea id is available.");
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
    renderWorkbenchError("workflowResult", error);
  }
}

async function loadResearchPacket() {
  if (!state.latestIdeaId) {
    renderWorkbenchEmpty("workflowResult", "Run a workflow first so an idea id is available.");
    return;
  }
  renderResult("workflowResult", "Loading idea research packet...", "warn");
  try {
    const body = await api(`/research/ideas/${state.latestIdeaId}/research-packet`);
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `${escapeHtml(body.message)} Open tasks: ${body.open_tasks.length}.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function downloadIdeaBundle() {
  if (!state.latestIdeaId) {
    renderWorkbenchEmpty("workflowResult", "Run a workflow first so an idea id is available.");
    return;
  }
  const url = `/research/ideas/${encodeURIComponent(state.latestIdeaId)}/export/bundle`;
  renderResult("workflowResult", "Preparing idea bundle export...", "warn");
  try {
    await downloadWithAuth(url, `idea-${state.latestIdeaId}-research-bundle.zip`);
    renderResult(
      "workflowResult",
      `Downloaded bundle export for idea <code>${escapeHtml(state.latestIdeaId)}</code>.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function downloadProjectBundle() {
  renderResult("workflowResult", "Preparing project bundle export...", "warn");
  try {
    await downloadWithAuth("/research/export/project-bundle", "research-project-bundle.zip");
    renderResult("workflowResult", "Downloaded project bundle export.");
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function saveProjectBundleReleaseNote() {
  renderResult("workflowResult", "Saving project bundle release note...", "warn");
  try {
    const body = await api("/research/export/project-bundle/releases", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: "Workbench Project Bundle Release Note",
        recipient: "advisor_or_reviewer",
        release_notes: "Workbench release note generated before project bundle handoff.",
        created_by: "workbench",
      }),
    });
    state.latestProjectBundleReleaseId = body.id;
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Saved project bundle release note <code>${escapeHtml(body.id)}</code> for ${escapeHtml(body.summary.recipient)}.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function listProjectBundleReleaseNotes() {
  renderResult("workflowResult", "Loading project bundle release notes...", "warn");
  try {
    const releases = await api("/research/export/project-bundle/releases?limit=6");
    if (releases.length) {
      state.latestProjectBundleReleaseId = releases[0].id;
    }
    const lines = ["# Project Bundle Release Notes", ""];
    if (!releases.length) {
      lines.push("- No project bundle release notes saved.");
    }
    for (const release of releases) {
      lines.push(
        `- \`${release.id}\` ${release.title}: ${release.summary.recipient || "recipient"} (${release.summary.readiness_level || "unknown"})`,
      );
    }
    $("dossierPreview").textContent = lines.join("\n");
    renderResult("workflowResult", `Loaded ${releases.length} project bundle release notes.`);
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function createProjectBundleReleaseTasks() {
  renderResult("workflowResult", "Creating project bundle release tasks...", "warn");
  try {
    let releaseId = state.latestProjectBundleReleaseId;
    if (!releaseId) {
      const releases = await api("/research/export/project-bundle/releases?limit=1");
      if (!releases.length) {
        renderWorkbenchEmpty(
          "workflowResult",
          "Save a project bundle release note before creating release tasks.",
        );
        return;
      }
      releaseId = releases[0].id;
      state.latestProjectBundleReleaseId = releaseId;
    }
    const body = await api(`/research/export/project-bundle/releases/${releaseId}/tasks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        limit: 6,
        include_missing_required: true,
        include_handoff_checks: true,
        created_by: "workbench",
      }),
    });
    state.latestTaskIds = [...state.latestTaskIds, ...body.tasks.map((task) => task.id)];
    renderResult(
      "workflowResult",
      `${escapeHtml(body.message)}<br />${renderList("Project bundle release tasks", body.tasks, (task) => `${task.priority}/${task.status}: ${task.title}`)}`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function loadProjectBundleReleaseProgress() {
  renderResult("workflowResult", "Loading project bundle release progress...", "warn");
  try {
    let releaseId = state.latestProjectBundleReleaseId;
    if (!releaseId) {
      const releases = await api("/research/export/project-bundle/releases?limit=1");
      if (!releases.length) {
        renderWorkbenchEmpty(
          "workflowResult",
          "Save a project bundle release note before checking release progress.",
        );
        return;
      }
      releaseId = releases[0].id;
      state.latestProjectBundleReleaseId = releaseId;
    }
    const body = await api(`/research/export/project-bundle/releases/${releaseId}/progress`);
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Release follow-up is ${(body.completion_ratio * 100).toFixed(1)}% complete. Open tasks: ${body.task_summary.open_task_count || 0}; blockers: ${body.task_summary.blocked_task_count || 0}.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function ensureProjectBundleReleaseId() {
  let releaseId = state.latestProjectBundleReleaseId;
  if (releaseId) {
    return releaseId;
  }
  const releases = await api("/research/export/project-bundle/releases?limit=1");
  if (!releases.length) {
    return "";
  }
  releaseId = releases[0].id;
  state.latestProjectBundleReleaseId = releaseId;
  return releaseId;
}

async function recordProjectBundleReleaseFeedback() {
  renderResult("workflowResult", "Recording project bundle release feedback...", "warn");
  try {
    const releaseId = await ensureProjectBundleReleaseId();
    if (!releaseId) {
      renderWorkbenchEmpty(
        "workflowResult",
        "Save a project bundle release note before recording feedback.",
      );
      return;
    }
    const body = await api(`/research/export/project-bundle/releases/${releaseId}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: "Workbench Project Bundle Release Feedback",
        recipient: "advisor_or_reviewer",
        feedback_status: "changes_requested",
        signoff_confirmed: false,
        feedback_notes: "Workbench feedback captured after project bundle handoff.",
        requested_changes: [
          "Clarify the next owner for open release tasks.",
          "Summarize unresolved claim validation risks before signoff.",
        ],
        blockers: ["Recipient signoff is pending until requested changes are addressed."],
        accepted_artifacts: ["README.md", "metadata/manifest.json"],
        created_by: "workbench",
      }),
    });
    state.latestProjectBundleReleaseFeedbackId = body.id;
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Recorded release feedback <code>${escapeHtml(body.id)}</code> with status <code>${escapeHtml(body.summary.feedback_status)}</code>.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function listProjectBundleReleaseFeedback() {
  renderResult("workflowResult", "Loading project bundle release feedback...", "warn");
  try {
    const releaseId = await ensureProjectBundleReleaseId();
    if (!releaseId) {
      renderWorkbenchEmpty(
        "workflowResult",
        "Save a project bundle release note before loading feedback.",
      );
      return;
    }
    const feedbackRecords = await api(
      `/research/export/project-bundle/releases/${releaseId}/feedback?limit=6`,
    );
    if (feedbackRecords.length) {
      state.latestProjectBundleReleaseFeedbackId = feedbackRecords[0].id;
    }
    const lines = ["# Project Bundle Release Feedback", ""];
    if (!feedbackRecords.length) {
      lines.push("- No release feedback saved.");
    }
    for (const feedback of feedbackRecords) {
      lines.push(
        `- \`${feedback.id}\` ${feedback.title}: ${feedback.summary.feedback_status || "received"} signoff=${feedback.summary.signoff_confirmed || false}`,
      );
    }
    $("dossierPreview").textContent = lines.join("\n");
    renderResult("workflowResult", `Loaded ${feedbackRecords.length} release feedback records.`);
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function createProjectBundleReleaseFeedbackTasks() {
  renderResult("workflowResult", "Creating project bundle release feedback tasks...", "warn");
  try {
    const releaseId = await ensureProjectBundleReleaseId();
    if (!releaseId) {
      renderWorkbenchEmpty(
        "workflowResult",
        "Save a project bundle release note before creating feedback tasks.",
      );
      return;
    }
    let feedbackId = state.latestProjectBundleReleaseFeedbackId;
    if (!feedbackId) {
      const feedbackRecords = await api(
        `/research/export/project-bundle/releases/${releaseId}/feedback?limit=1`,
      );
      if (!feedbackRecords.length) {
        renderWorkbenchEmpty(
          "workflowResult",
          "Record project bundle release feedback before creating feedback tasks.",
        );
        return;
      }
      feedbackId = feedbackRecords[0].id;
      state.latestProjectBundleReleaseFeedbackId = feedbackId;
    }
    const body = await api(
      `/research/export/project-bundle/releases/${releaseId}/feedback/${feedbackId}/tasks`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          limit: 6,
          include_requested_changes: true,
          include_blockers: true,
          include_signoff_check: true,
          created_by: "workbench",
        }),
      },
    );
    state.latestTaskIds = [...state.latestTaskIds, ...body.tasks.map((task) => task.id)];
    renderResult(
      "workflowResult",
      `${escapeHtml(body.message)}<br />${renderList("Release feedback tasks", body.tasks, (task) => `${task.priority}/${task.status}: ${task.title}`)}`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function loadProjectBundleReleaseCloseout() {
  renderResult("workflowResult", "Loading project bundle release closeout...", "warn");
  try {
    const releaseId = await ensureProjectBundleReleaseId();
    if (!releaseId) {
      renderWorkbenchEmpty(
        "workflowResult",
        "Save a project bundle release note before loading closeout.",
      );
      return;
    }
    const body = await api(`/research/export/project-bundle/releases/${releaseId}/closeout`);
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Release closeout is <code>${escapeHtml(body.closeout_status)}</code>. Ready: ${body.ready_to_close}. Next actions: ${body.next_actions.length}.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function createProjectBundleReleaseCloseoutTasks() {
  renderResult("workflowResult", "Creating project bundle release closeout tasks...", "warn");
  try {
    const releaseId = await ensureProjectBundleReleaseId();
    if (!releaseId) {
      renderWorkbenchEmpty(
        "workflowResult",
        "Save a project bundle release note before creating closeout tasks.",
      );
      return;
    }
    const body = await api(
      `/research/export/project-bundle/releases/${releaseId}/closeout/tasks`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          limit: 6,
          include_blockers: true,
          include_next_actions: true,
          include_signoff_check: true,
          created_by: "workbench",
        }),
      },
    );
    state.latestTaskIds = [...state.latestTaskIds, ...body.tasks.map((task) => task.id)];
    renderResult(
      "workflowResult",
      `${escapeHtml(body.message)}<br />${renderList("Release closeout tasks", body.tasks, (task) => `${task.priority}/${task.status}: ${task.title}`)}`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function loadProjectBundleReleaseAcceptancePacket() {
  renderResult("workflowResult", "Loading project bundle release acceptance packet...", "warn");
  try {
    const releaseId = await ensureProjectBundleReleaseId();
    if (!releaseId) {
      renderWorkbenchEmpty(
        "workflowResult",
        "Save a project bundle release note before loading the acceptance packet.",
      );
      return;
    }
    const body = await api(
      `/research/export/project-bundle/releases/${releaseId}/acceptance-packet`,
    );
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Release acceptance is <code>${escapeHtml(body.acceptance_status)}</code>. Ready for signoff: ${body.ready_for_signoff}. Remaining actions: ${body.remaining_actions.length}.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function saveProjectBundleReleaseAcceptancePacketSnapshot() {
  renderResult(
    "workflowResult",
    "Saving project bundle release acceptance packet snapshot...",
    "warn",
  );
  try {
    const releaseId = await ensureProjectBundleReleaseId();
    if (!releaseId) {
      renderWorkbenchEmpty(
        "workflowResult",
        "Save a project bundle release note before saving an acceptance snapshot.",
      );
      return;
    }
    const body = await api(
      `/research/export/project-bundle/releases/${releaseId}/acceptance-packet/snapshots`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: "Workbench Project Bundle Release Acceptance Packet Snapshot",
          created_by: "workbench",
        }),
      },
    );
    state.latestProjectBundleReleaseAcceptancePacketSnapshotId = body.id;
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Saved release acceptance snapshot <code>${escapeHtml(body.id)}</code> with status <code>${escapeHtml(body.summary.acceptance_status)}</code>.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function listProjectBundleReleaseAcceptancePacketSnapshots() {
  renderResult("workflowResult", "Loading release acceptance packet snapshots...", "warn");
  try {
    const releaseId = await ensureProjectBundleReleaseId();
    if (!releaseId) {
      renderWorkbenchEmpty(
        "workflowResult",
        "Save a project bundle release note before loading acceptance snapshots.",
      );
      return;
    }
    const snapshots = await api(
      `/research/export/project-bundle/releases/${releaseId}/acceptance-packet/snapshots?limit=6`,
    );
    if (snapshots.length) {
      state.latestProjectBundleReleaseAcceptancePacketSnapshotId = snapshots[0].id;
    }
    const lines = ["# Release Acceptance Packet Snapshots", ""];
    if (!snapshots.length) {
      lines.push("- No release acceptance packet snapshots saved.");
    }
    for (const snapshot of snapshots) {
      const status = snapshot.summary.acceptance_status || "unknown";
      const ready = snapshot.summary.ready_for_signoff ? "ready" : "not ready";
      lines.push(`- \`${snapshot.id}\` ${snapshot.title}: ${status}, ${ready}`);
    }
    $("dossierPreview").textContent = lines.join("\n");
    renderResult("workflowResult", `Loaded ${snapshots.length} acceptance snapshots.`);
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function compareProjectBundleReleaseAcceptancePacketSnapshots() {
  renderResult("workflowResult", "Comparing latest acceptance snapshots...", "warn");
  try {
    const releaseId = await ensureProjectBundleReleaseId();
    if (!releaseId) {
      renderWorkbenchEmpty(
        "workflowResult",
        "Save a project bundle release note before comparing acceptance snapshots.",
      );
      return;
    }
    const snapshots = await api(
      `/research/export/project-bundle/releases/${releaseId}/acceptance-packet/snapshots?limit=2`,
    );
    if (snapshots.length < 2) {
      renderWorkbenchEmpty(
        "workflowResult",
        "Save at least two acceptance snapshots before comparing them.",
      );
      return;
    }
    const body = await api(
      `/research/export/project-bundle/releases/${releaseId}/acceptance-packet/snapshots/compare`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          baseline_snapshot_id: snapshots[1].id,
          candidate_snapshot_id: snapshots[0].id,
        }),
      },
    );
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `${escapeHtml(body.summary)}<br />New actions: ${body.added_remaining_actions.length}. New checklist gaps: ${body.newly_blocked_checklist_items.length}.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function createProjectBundleReleaseAcceptancePacketSnapshotComparisonTasks() {
  renderResult("workflowResult", "Creating acceptance comparison tasks...", "warn");
  try {
    const releaseId = await ensureProjectBundleReleaseId();
    if (!releaseId) {
      renderWorkbenchEmpty(
        "workflowResult",
        "Save a project bundle release note before creating acceptance comparison tasks.",
      );
      return;
    }
    const snapshots = await api(
      `/research/export/project-bundle/releases/${releaseId}/acceptance-packet/snapshots?limit=2`,
    );
    if (snapshots.length < 2) {
      renderWorkbenchEmpty(
        "workflowResult",
        "Save at least two acceptance snapshots before creating comparison tasks.",
      );
      return;
    }
    const body = await api(
      `/research/export/project-bundle/releases/${releaseId}/acceptance-packet/snapshots/compare/tasks`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          baseline_snapshot_id: snapshots[1].id,
          candidate_snapshot_id: snapshots[0].id,
          limit: 6,
          include_remaining_actions: true,
          include_checklist_regressions: true,
          include_status_regression: true,
          created_by: "workbench",
        }),
      },
    );
    state.latestTaskIds = [...state.latestTaskIds, ...body.tasks.map((task) => task.id)];
    renderResult(
      "workflowResult",
      `${escapeHtml(body.message)}<br />${renderList("Acceptance comparison tasks", body.tasks, (task) => `${task.priority}/${task.status}: ${task.title}`)}`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function loadProjectBundleReleaseReviewSession() {
  renderResult("workflowResult", "Loading project bundle release review session...", "warn");
  try {
    const releaseId = await ensureProjectBundleReleaseId();
    if (!releaseId) {
      renderWorkbenchEmpty(
        "workflowResult",
        "Save a project bundle release note before loading the review session.",
      );
      return;
    }
    const body = await api(
      `/research/export/project-bundle/releases/${releaseId}/review-session`,
    );
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Release review is <code>${escapeHtml(body.review_status)}</code>. Decisions: ${body.decisions_needed.length}. Follow-up actions: ${body.follow_up_actions.length}.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function createProjectBundleReleaseReviewSessionTasks() {
  renderResult("workflowResult", "Creating release review tasks...", "warn");
  try {
    const releaseId = await ensureProjectBundleReleaseId();
    if (!releaseId) {
      renderWorkbenchEmpty(
        "workflowResult",
        "Save a project bundle release note before creating review tasks.",
      );
      return;
    }
    const body = await api(
      `/research/export/project-bundle/releases/${releaseId}/review-session/tasks`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          limit: 8,
          include_decisions: true,
          include_risks: true,
          include_follow_up_actions: true,
          created_by: "workbench",
        }),
      },
    );
    state.latestTaskIds = [...state.latestTaskIds, ...body.tasks.map((task) => task.id)];
    renderResult(
      "workflowResult",
      `${escapeHtml(body.message)}<br />${renderList("Release review tasks", body.tasks, (task) => `${task.priority}/${task.status}: ${task.title}`)}`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function recordProjectBundleReleaseReviewOutcome() {
  renderResult("workflowResult", "Recording release review outcome...", "warn");
  try {
    const releaseId = await ensureProjectBundleReleaseId();
    if (!releaseId) {
      renderWorkbenchEmpty(
        "workflowResult",
        "Save a project bundle release note before recording a review outcome.",
      );
      return;
    }
    const body = await api(
      `/research/export/project-bundle/releases/${releaseId}/review-session/outcomes`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: "Workbench Project Bundle Release Review Outcome",
          review_decision: "follow_up_needed",
          participants: ["workbench user", "advisor_or_reviewer"],
          outcome_notes:
            "Workbench review outcome captured from the release review session.",
          decisions: ["Confirm owners for unresolved acceptance follow-up."],
          accepted_artifacts: ["Project bundle", "Release review session"],
          follow_up_actions: ["Work unresolved release review follow-up tasks."],
          risks: ["Acceptance remains blocked until follow-up is complete."],
          signoff_confirmed: false,
          created_by: "workbench",
        }),
      },
    );
    state.latestProjectBundleReleaseReviewOutcomeId = body.id;
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Recorded release review outcome <code>${escapeHtml(body.id)}</code> with decision <code>${escapeHtml(body.summary.review_decision)}</code>.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function listProjectBundleReleaseReviewOutcomes() {
  renderResult("workflowResult", "Loading release review outcomes...", "warn");
  try {
    const releaseId = await ensureProjectBundleReleaseId();
    if (!releaseId) {
      renderWorkbenchEmpty(
        "workflowResult",
        "Save a project bundle release note before loading review outcomes.",
      );
      return;
    }
    const outcomes = await api(
      `/research/export/project-bundle/releases/${releaseId}/review-session/outcomes?limit=6`,
    );
    if (outcomes.length) {
      state.latestProjectBundleReleaseReviewOutcomeId = outcomes[0].id;
    }
    const lines = ["# Release Review Outcomes", ""];
    if (!outcomes.length) {
      lines.push("- No release review outcomes saved.");
    }
    for (const outcome of outcomes) {
      const decision = outcome.summary.review_decision || "pending";
      const signoff = outcome.summary.signoff_confirmed ? "signed" : "not signed";
      lines.push(`- \`${outcome.id}\` ${outcome.title}: ${decision}, ${signoff}`);
    }
    $("dossierPreview").textContent = lines.join("\n");
    renderResult("workflowResult", `Loaded ${outcomes.length} release review outcomes.`);
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function createProjectBundleReleaseReviewOutcomeTasks() {
  renderResult("workflowResult", "Creating release review outcome tasks...", "warn");
  try {
    const releaseId = await ensureProjectBundleReleaseId();
    if (!releaseId) {
      renderWorkbenchEmpty(
        "workflowResult",
        "Save a project bundle release note before creating review outcome tasks.",
      );
      return;
    }
    let outcomeId = state.latestProjectBundleReleaseReviewOutcomeId;
    if (!outcomeId) {
      const outcomes = await api(
        `/research/export/project-bundle/releases/${releaseId}/review-session/outcomes?limit=1`,
      );
      if (!outcomes.length) {
        renderWorkbenchEmpty(
          "workflowResult",
          "Record a release review outcome before creating outcome tasks.",
        );
        return;
      }
      outcomeId = outcomes[0].id;
      state.latestProjectBundleReleaseReviewOutcomeId = outcomeId;
    }
    const body = await api(
      `/research/export/project-bundle/releases/${releaseId}/review-session/outcomes/${outcomeId}/tasks`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          limit: 8,
          include_decisions: true,
          include_risks: true,
          include_follow_up_actions: true,
          include_signoff_check: true,
          created_by: "workbench",
        }),
      },
    );
    state.latestTaskIds = [...state.latestTaskIds, ...body.tasks.map((task) => task.id)];
    renderResult(
      "workflowResult",
      `${escapeHtml(body.message)}<br />${renderList("Review outcome tasks", body.tasks, (task) => `${task.priority}/${task.status}: ${task.title}`)}`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function loadProjectBundleReleaseReviewOutcomeProgress() {
  renderResult("workflowResult", "Loading release review outcome progress...", "warn");
  try {
    const releaseId = await ensureProjectBundleReleaseId();
    if (!releaseId) {
      renderWorkbenchEmpty(
        "workflowResult",
        "Save a project bundle release note before loading review outcome progress.",
      );
      return;
    }
    let outcomeId = state.latestProjectBundleReleaseReviewOutcomeId;
    if (!outcomeId) {
      const outcomes = await api(
        `/research/export/project-bundle/releases/${releaseId}/review-session/outcomes?limit=1`,
      );
      if (!outcomes.length) {
        renderWorkbenchEmpty(
          "workflowResult",
          "Record a release review outcome before loading outcome progress.",
        );
        return;
      }
      outcomeId = outcomes[0].id;
      state.latestProjectBundleReleaseReviewOutcomeId = outcomeId;
    }
    const body = await api(
      `/research/export/project-bundle/releases/${releaseId}/review-session/outcomes/${outcomeId}/progress`,
    );
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Review outcome follow-up is ${(body.completion_ratio * 100).toFixed(1)}% complete. Open tasks: ${body.task_summary.open_task_count || 0}; blockers: ${body.task_summary.blocked_task_count || 0}.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}



async function ensureProjectBundleReleaseReviewOutcomeId(releaseId) {
  let outcomeId = state.latestProjectBundleReleaseReviewOutcomeId;
  if (outcomeId) {
    return outcomeId;
  }
  const outcomes = await api(
    `/research/export/project-bundle/releases/${releaseId}/review-session/outcomes?limit=1`,
  );
  if (!outcomes.length) {
    return "";
  }
  outcomeId = outcomes[0].id;
  state.latestProjectBundleReleaseReviewOutcomeId = outcomeId;
  return outcomeId;
}

async function recordProjectBundleReleaseReviewOutcomeSignoff() {
  renderResult("workflowResult", "Recording release review outcome signoff...", "warn");
  try {
    const releaseId = await ensureProjectBundleReleaseId();
    if (!releaseId) {
      renderWorkbenchEmpty(
        "workflowResult",
        "Save a project bundle release note before recording outcome signoff.",
      );
      return;
    }
    const outcomeId = await ensureProjectBundleReleaseReviewOutcomeId(releaseId);
    if (!outcomeId) {
      renderWorkbenchEmpty(
        "workflowResult",
        "Record a release review outcome before recording signoff evidence.",
      );
      return;
    }
    const body = await api(
      `/research/export/project-bundle/releases/${releaseId}/review-session/outcomes/${outcomeId}/signoffs`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: "Workbench Project Bundle Release Review Outcome Signoff",
          signoff_decision: "deferred",
          approver: "advisor_or_reviewer",
          signoff_notes:
            "Workbench signoff evidence captured with the current review outcome progress snapshot.",
          accepted_artifacts: [
            "Project bundle",
            "Release review outcome",
            "Review outcome progress report",
          ],
          conditions: ["Complete open release review outcome follow-up tasks."],
          evidence_links: [
            "artifacts/releases/latest-project-bundle-release-review-outcome-progress.md",
          ],
          created_by: "workbench",
        }),
      },
    );
    state.latestProjectBundleReleaseReviewOutcomeSignoffId = body.id;
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Recorded release review outcome signoff <code>${escapeHtml(body.id)}</code> with decision <code>${escapeHtml(body.summary.signoff_decision)}</code>.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function listProjectBundleReleaseReviewOutcomeSignoffs() {
  renderResult("workflowResult", "Loading release review outcome signoffs...", "warn");
  try {
    const releaseId = await ensureProjectBundleReleaseId();
    if (!releaseId) {
      renderWorkbenchEmpty(
        "workflowResult",
        "Save a project bundle release note before loading outcome signoffs.",
      );
      return;
    }
    const outcomeId = await ensureProjectBundleReleaseReviewOutcomeId(releaseId);
    if (!outcomeId) {
      renderWorkbenchEmpty(
        "workflowResult",
        "Record a release review outcome before loading signoff evidence.",
      );
      return;
    }
    const signoffs = await api(
      `/research/export/project-bundle/releases/${releaseId}/review-session/outcomes/${outcomeId}/signoffs?limit=6`,
    );
    if (signoffs.length) {
      state.latestProjectBundleReleaseReviewOutcomeSignoffId = signoffs[0].id;
    }
    const lines = ["# Release Review Outcome Signoffs", ""];
    if (!signoffs.length) {
      lines.push("- No release review outcome signoffs saved.");
    }
    for (const signoff of signoffs) {
      const decision = signoff.summary.signoff_decision || "pending";
      const approver = signoff.summary.approver || "unknown";
      const confirmed = signoff.summary.signoff_confirmed ? "confirmed" : "not confirmed";
      lines.push(`- \`${signoff.id}\` ${signoff.title}: ${decision}, ${confirmed}, ${approver}`);
    }
    $("dossierPreview").textContent = lines.join("\n");
    renderResult("workflowResult", `Loaded ${signoffs.length} release review outcome signoffs.`);
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function loadProjectBundleReadiness() {
  renderResult("workflowResult", "Checking project bundle readiness...", "warn");
  try {
    const body = await api("/research/export/project-bundle/readiness");
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Bundle readiness <code>${escapeHtml(body.readiness_level)}</code> (${body.readiness_score}). Missing required checks: ${body.missing_required.length}.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function createProjectBundleReadinessTasks() {
  renderResult("workflowResult", "Creating project bundle readiness tasks...", "warn");
  try {
    const body = await api("/research/export/project-bundle/readiness/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ limit: 8, include_optional: true, created_by: "workbench" }),
    });
    state.latestTaskIds = [...state.latestTaskIds, ...body.tasks.map((task) => task.id)];
    renderResult(
      "workflowResult",
      `${escapeHtml(body.message)}<br />${renderList("Bundle readiness tasks", body.tasks, (task) => `${task.priority}/${task.status}: ${task.title}`)}`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function saveProjectBundleReadinessSnapshot() {
  renderResult("workflowResult", "Saving project bundle readiness snapshot...", "warn");
  try {
    const body = await api("/research/export/project-bundle/readiness/snapshots", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: "Workbench Project Bundle Readiness Snapshot",
        created_by: "workbench",
      }),
    });
    state.latestProjectBundleReadinessSnapshotId = body.id;
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Saved bundle readiness snapshot <code>${escapeHtml(body.id)}</code> with score ${body.summary.readiness_score}.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function listProjectBundleReadinessSnapshots() {
  renderResult("workflowResult", "Loading project bundle readiness snapshots...", "warn");
  try {
    const snapshots = await api("/research/export/project-bundle/readiness/snapshots?limit=6");
    if (snapshots.length) {
      state.latestProjectBundleReadinessSnapshotId = snapshots[0].id;
    }
    const lines = ["# Project Bundle Readiness Snapshots", ""];
    if (!snapshots.length) {
      lines.push("- No bundle readiness snapshots saved.");
    }
    for (const snapshot of snapshots) {
      lines.push(
        `- \`${snapshot.id}\` ${snapshot.title}: ${snapshot.summary.readiness_level || "unknown"} (${snapshot.summary.readiness_score ?? 0})`,
      );
    }
    $("dossierPreview").textContent = lines.join("\n");
    renderResult("workflowResult", `Loaded ${snapshots.length} bundle readiness snapshots.`);
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function compareProjectBundleReadinessSnapshots() {
  renderResult("workflowResult", "Comparing latest bundle readiness snapshots...", "warn");
  try {
    const snapshots = await api("/research/export/project-bundle/readiness/snapshots?limit=2");
    if (snapshots.length < 2) {
      renderWorkbenchEmpty(
        "workflowResult",
        "Save at least two bundle readiness snapshots before comparing them.",
      );
      return;
    }
    const body = await api("/research/export/project-bundle/readiness/snapshots/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        baseline_snapshot_id: snapshots[1].id,
        candidate_snapshot_id: snapshots[0].id,
      }),
    });
    $("dossierPreview").textContent = body.markdown_export;
    const scoreDelta = body.readiness_delta?.readiness_score?.delta ?? 0;
    renderResult(
      "workflowResult",
      `${escapeHtml(body.summary)}<br />Score delta: <code>${escapeHtml(scoreDelta)}</code>.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function createProjectBundleReadinessComparisonTasks() {
  renderResult("workflowResult", "Creating bundle readiness comparison tasks...", "warn");
  try {
    const snapshots = await api("/research/export/project-bundle/readiness/snapshots?limit=2");
    if (snapshots.length < 2) {
      renderWorkbenchEmpty(
        "workflowResult",
        "Save at least two bundle readiness snapshots before creating comparison tasks.",
      );
      return;
    }
    const body = await api("/research/export/project-bundle/readiness/snapshots/compare/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        baseline_snapshot_id: snapshots[1].id,
        candidate_snapshot_id: snapshots[0].id,
        limit: 8,
        include_missing_required: true,
        include_recommended_actions: true,
        include_quick_actions: true,
        created_by: "workbench",
      }),
    });
    state.latestTaskIds = [...state.latestTaskIds, ...body.tasks.map((task) => task.id)];
    renderResult(
      "workflowResult",
      `${escapeHtml(body.message)}<br />${renderList("Bundle readiness comparison tasks", body.tasks, (task) => `${task.priority}/${task.status}: ${task.title}`)}`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function loadIdeaReadiness() {
  if (!state.latestIdeaId) {
    renderWorkbenchEmpty("workflowResult", "Run a workflow first so an idea id is available.");
    return;
  }
  renderResult("workflowResult", "Scoring idea readiness...", "warn");
  try {
    const body = await api(`/research/ideas/${state.latestIdeaId}/readiness`);
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Readiness ${body.readiness_score}: <strong>${escapeHtml(body.decision)}</strong>. Blockers: ${body.blockers.length}.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function loadIdeaQualityGate() {
  if (!state.latestIdeaId) {
    renderWorkbenchEmpty("workflowResult", "Run a workflow first so an idea id is available.");
    return;
  }
  renderResult("workflowResult", "Running idea quality gate...", "warn");
  try {
    const body = await api(`/research/ideas/${state.latestIdeaId}/quality-gate`);
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Quality gate ${body.gate_score}: <strong>${escapeHtml(body.decision)}</strong>. Actions: ${body.recommended_actions.length}.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function createQualityGateTasks() {
  if (!state.latestIdeaId) {
    renderWorkbenchEmpty("workflowResult", "Run a workflow first so an idea id is available.");
    return;
  }
  renderResult("workflowResult", "Creating quality-gate follow-up tasks...", "warn");
  try {
    const body = await api(`/research/ideas/${state.latestIdeaId}/quality-gate/tasks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ created_by: "workbench" }),
    });
    state.latestTaskIds = [...state.latestTaskIds, ...body.tasks.map((task) => task.id)];
    renderResult(
      "workflowResult",
      `${escapeHtml(body.message)}<br />${renderList("Quality-gate tasks", body.tasks, (task) => `${task.priority}/${task.status}: ${task.title}`)}`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function createReadinessTasks() {
  if (!state.latestIdeaId) {
    renderWorkbenchEmpty("workflowResult", "Run a workflow first so an idea id is available.");
    return;
  }
  renderResult("workflowResult", "Creating readiness follow-up tasks...", "warn");
  try {
    const body = await api(`/research/ideas/${state.latestIdeaId}/readiness/tasks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ created_by: "workbench" }),
    });
    state.latestTaskIds = [...state.latestTaskIds, ...body.tasks.map((task) => task.id)];
    renderResult(
      "workflowResult",
      `${escapeHtml(body.message)}<br />${renderList("Readiness tasks", body.tasks, (task) => `${task.priority}/${task.status}: ${task.title}`)}`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function loadProjectCockpit() {
  renderResult("workflowResult", "Loading project cockpit...", "warn");
  try {
    const body = await api("/research/cockpit");
    const primaryAction = body.primary_next_action?.label || "No primary action";
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Cockpit phase <code>${escapeHtml(body.phase)}</code>, readiness <code>${escapeHtml(body.readiness_level)}</code>.<br />Primary: ${escapeHtml(primaryAction)}.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function createProjectCockpitTasks() {
  renderResult("workflowResult", "Creating project cockpit tasks...", "warn");
  try {
    const body = await api("/research/cockpit/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ limit: 8, include_risks: true, created_by: "workbench" }),
    });
    state.latestTaskIds = [...state.latestTaskIds, ...body.tasks.map((task) => task.id)];
    renderResult(
      "workflowResult",
      `${escapeHtml(body.message)}<br />${renderList("Cockpit tasks", body.tasks, (task) => `${task.priority}/${task.status}: ${task.title}`)}`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
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
    renderWorkbenchError("workflowResult", error);
  }
}

async function loadProjectTriageBrief() {
  renderResult("workflowResult", "Loading project triage brief...", "warn");
  try {
    const body = await api("/research/triage/brief");
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `${escapeHtml(body.message)} Next actions: ${body.next_actions.length}.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function loadProjectTriageMarkdown() {
  renderResult("workflowResult", "Exporting project triage Markdown...", "warn");
  try {
    const markdown = await api("/research/triage/brief/export/markdown");
    $("dossierPreview").textContent = markdown;
    renderResult("workflowResult", "Loaded project triage Markdown export.");
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function saveProjectTriageSnapshot() {
  renderResult("workflowResult", "Saving project triage snapshot...", "warn");
  try {
    const body = await api("/research/triage/snapshots", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: "Workbench Project Triage Snapshot",
        idea_limit: 50,
        opportunity_limit: 8,
        created_by: "workbench",
      }),
    });
    state.latestTriageSnapshotId = body.id;
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Saved project triage snapshot <code>${escapeHtml(body.id)}</code> with ${body.next_actions.length} next actions.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function compareProjectTriageSnapshots() {
  renderResult("workflowResult", "Comparing recent project triage snapshots...", "warn");
  try {
    const snapshots = await api("/research/triage/snapshots?limit=2");
    if (snapshots.length < 2) {
      renderWorkbenchEmpty(
        "workflowResult",
        "Save at least two triage snapshots before comparing.",
      );
      return;
    }
    const body = await api("/research/triage/snapshots/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        baseline_snapshot_id: snapshots[1].id,
        candidate_snapshot_id: snapshots[0].id,
      }),
    });
    $("dossierPreview").textContent = body.markdown_export;
    renderResult("workflowResult", escapeHtml(body.summary));
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function createProjectTriageComparisonTasks() {
  renderResult("workflowResult", "Creating project triage comparison tasks...", "warn");
  try {
    const snapshots = await api("/research/triage/snapshots?limit=2");
    if (snapshots.length < 2) {
      renderWorkbenchEmpty(
        "workflowResult",
        "Save at least two triage snapshots before creating comparison tasks.",
      );
      return;
    }
    const body = await api("/research/triage/snapshots/compare/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        baseline_snapshot_id: snapshots[1].id,
        candidate_snapshot_id: snapshots[0].id,
        limit: 8,
        include_focus: true,
        include_risks: true,
        created_by: "workbench",
      }),
    });
    state.latestTaskIds = [...state.latestTaskIds, ...body.tasks.map((task) => task.id)];
    renderResult(
      "workflowResult",
      `${escapeHtml(body.message)}<br />${renderList("Comparison tasks", body.tasks, (task) => `${task.priority}/${task.status}: ${task.title}`)}`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function createProjectTriageTasks() {
  renderResult("workflowResult", "Creating project triage tasks...", "warn");
  try {
    const body = await api("/research/triage/brief/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        limit: 8,
        include_risks: true,
        created_by: "workbench",
      }),
    });
    state.latestTaskIds = [...state.latestTaskIds, ...body.tasks.map((task) => task.id)];
    renderResult(
      "workflowResult",
      `${escapeHtml(body.message)}<br />${renderList("Triage tasks", body.tasks, (task) => `${task.priority}/${task.status}: ${task.title}`)}`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function loadProjectReadinessOverview() {
  renderResult("workflowResult", "Loading project readiness overview...", "warn");
  try {
    const body = await api("/research/readiness/overview");
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `${escapeHtml(body.message)} Average readiness: ${body.average_readiness}.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function loadProjectQualityOverview() {
  renderResult("workflowResult", "Loading project quality gate overview...", "warn");
  try {
    const body = await api("/research/quality/overview");
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `${escapeHtml(body.message)} Average gate score: ${body.average_gate_score}.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function createProjectQualityTasks() {
  renderResult("workflowResult", "Creating project quality-gate tasks...", "warn");
  try {
    const body = await api("/research/quality/overview/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        limit: 5,
        actions_per_idea: 1,
        created_by: "workbench",
      }),
    });
    state.latestTaskIds = [...state.latestTaskIds, ...body.tasks.map((task) => task.id)];
    renderResult(
      "workflowResult",
      `${escapeHtml(body.message)}<br />${renderList("Project gate tasks", body.tasks, (task) => `${task.priority}/${task.status}: ${task.title}`)}`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function loadOpportunityRadar() {
  renderResult("workflowResult", "Loading research opportunity radar...", "warn");
  try {
    const body = await api("/research/opportunities/radar?limit=8");
    if (body.top_opportunities.length) {
      state.latestIdeaId = body.top_opportunities[0].idea_id;
    }
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `${escapeHtml(body.message)} Top opportunities: ${body.top_opportunities.length}.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function createOpportunityRadarTasks() {
  renderResult("workflowResult", "Creating opportunity radar tasks...", "warn");
  try {
    const body = await api("/research/opportunities/radar/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        limit: 5,
        actions_per_opportunity: 1,
        created_by: "workbench",
      }),
    });
    state.latestTaskIds = [...state.latestTaskIds, ...body.tasks.map((task) => task.id)];
    if (body.tasks.length) {
      state.latestIdeaId = body.tasks[0].idea_id || state.latestIdeaId;
    }
    renderResult(
      "workflowResult",
      `${escapeHtml(body.message)}<br />${renderList("Radar tasks", body.tasks, (task) => `${task.priority}/${task.status}: ${task.title}`)}`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function createAdvisorBrief() {
  renderResult("workflowResult", "Creating advisor brief...", "warn");
  try {
    const body = await api("/research/briefs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: "Workbench Advisor Research Brief",
        scope: state.latestIdeaId ? "idea_set" : "project",
        idea_ids: state.latestIdeaId ? [state.latestIdeaId] : [],
        created_by: "workbench",
      }),
    });
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Saved advisor brief <code>${escapeHtml(body.id)}</code> for ${body.idea_ids.length} ideas.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function createResearchPlan() {
  renderResult("workflowResult", "Creating research execution plan...", "warn");
  try {
    const body = await api("/research/plans", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: "Workbench Research Execution Plan",
        horizon_days: 14,
        idea_ids: state.latestIdeaId ? [state.latestIdeaId] : [],
        created_by: "workbench",
      }),
    });
    state.latestResearchPlanId = body.id;
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `Created plan <code>${escapeHtml(body.id)}</code> with ${body.plan_items.length} plan items.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function createResearchPlanTasks() {
  if (!state.latestResearchPlanId) {
    renderWorkbenchEmpty("workflowResult", "Create a research plan before generating plan tasks.");
    return;
  }
  renderResult("workflowResult", "Creating tasks from research plan...", "warn");
  try {
    const body = await api(`/research/plans/${state.latestResearchPlanId}/tasks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ created_by: "workbench" }),
    });
    state.latestTaskIds = body.tasks.map((task) => task.id);
    renderResult(
      "workflowResult",
      `${escapeHtml(body.message)}<br />${renderList("Plan tasks", body.tasks, (task) => `${task.priority}/${task.status}: ${task.title}`)}`,
    );
    await refreshJobs();
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
  }
}

async function loadResearchPlanProgress() {
  if (!state.latestResearchPlanId) {
    renderWorkbenchEmpty("workflowResult", "Create a research plan before loading plan progress.");
    return;
  }
  renderResult("workflowResult", "Loading research plan progress...", "warn");
  try {
    const body = await api(`/research/plans/${state.latestResearchPlanId}/progress`);
    state.latestTaskIds = body.tasks.map((task) => task.id);
    $("dossierPreview").textContent = body.markdown_export;
    renderResult(
      "workflowResult",
      `${escapeHtml(body.message)} Completion: ${body.task_summary.completion_ratio}. Open: ${body.task_summary.open_task_count}.`,
    );
  } catch (error) {
    renderWorkbenchError("workflowResult", error);
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
    renderWorkbenchError("workflowResult", error);
  }
}

async function shortlistLatestIdea() {
  if (!state.latestIdeaId) {
    renderWorkbenchEmpty("workflowResult", "Run a workflow first so an idea id is available.");
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
    renderWorkbenchError("workflowResult", error);
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
    renderWorkbenchError("workflowResult", error);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  $("uploadForm").addEventListener("submit", uploadPaper);
  $("runWorkflowButton").addEventListener("click", runWorkflow);
  $("setupWizardForm").addEventListener("submit", runProjectSetupWizard);
  $("profileForm").addEventListener("submit", saveResearchProfile);
  $("saveApiKeyButton").addEventListener("click", saveApiKey);
  $("clearApiKeyButton").addEventListener("click", clearApiKey);
  $("saveProjectIdButton").addEventListener("click", saveProjectScope);
  $("onboardingButton").addEventListener("click", () => loadOnboardingReadiness(false));
  $("onboardingMarkdownButton").addEventListener("click", () => loadOnboardingReadiness(true));
  $("onboardingTasksButton").addEventListener("click", createOnboardingTasks);
  $("onboardingProgressButton").addEventListener("click", loadOnboardingProgress);
  $("pilotReportButton").addEventListener("click", loadPilotReport);
  $("pilotReportSnapshotButton").addEventListener("click", savePilotReportSnapshot);
  $("pilotReportSnapshotTasksButton").addEventListener(
    "click",
    createPilotReportSnapshotTasks,
  );
  $("pilotReportSnapshotCompareButton").addEventListener(
    "click",
    comparePilotReportSnapshots,
  );
  $("pilotReportSnapshotComparisonTasksButton").addEventListener(
    "click",
    createPilotReportSnapshotComparisonTasks,
  );
  $("apiKeyInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      saveApiKey();
    }
  });
  $("projectIdInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      saveProjectScope();
    }
  });
  $("pilotLaunchRefreshButton").addEventListener("click", loadPilotLaunch);
  $("realEvalLatestButton").addEventListener("click", loadLatestRealPaperEvaluationReport);
  $("realEvalListButton").addEventListener("click", listRealPaperEvaluationReports);
  $("loadProfileButton").addEventListener("click", loadResearchProfile);
  $("previewProfileButton").addEventListener("click", previewResearchProfile);
  $("contextSearchForm").addEventListener("submit", searchContext);
  $("literatureSearchForm").addEventListener("submit", searchLiterature);
  $("advisorChatForm").addEventListener("submit", askAdvisorChat);
  $("advisorChatTasksButton").addEventListener("click", createAdvisorChatTasks);
  $("advisorActionSessionButton").addEventListener("click", createAdvisorActionSession);
  $("refreshJobsButton").addEventListener("click", refreshJobs);
  $("latestWorkflowRefreshJobsButton").addEventListener("click", refreshJobs);
  $("latestWorkflowLoadDossierButton").addEventListener("click", loadDossier);
  $("quickLoadDossierButton").addEventListener("click", loadDossier);
  $("quickRelatedWorkButton").addEventListener("click", createRelatedWorkMatrix);
  $("quickProposalDraftButton").addEventListener("click", createProposalDraft);
  $("quickExperimentRunButton").addEventListener("click", createExperimentRun);
  $("quickResearchPacketButton").addEventListener("click", loadResearchPacket);
  $("quickProjectBundleButton").addEventListener("click", downloadProjectBundle);
  $("jobsTable").addEventListener("click", handleJobAction);
  $("loadDossierButton").addEventListener("click", loadDossier);
  $("refineIdeaButton").addEventListener("click", refineLatestIdea);
  $("noveltyRefreshButton").addEventListener("click", refreshNoveltySearch);
  $("sotaReviewPackageButton").addEventListener("click", createSotaReviewPackage);
  $("sotaExternalSearchButton").addEventListener("click", createSotaExternalSearchEvidence);
  $("sotaSignoffButton").addEventListener("click", createSotaSignoff);
  $("noveltyTasksButton").addEventListener("click", createNoveltyTasks);
  $("relatedWorkButton").addEventListener("click", createRelatedWorkMatrix);
  $("proposalDraftButton").addEventListener("click", createProposalDraft);
  $("proposalReviewButton").addEventListener("click", reviewProposalDraft);
  $("proposalRevisionButton").addEventListener("click", reviseProposalDraft);
  $("taskBacklogButton").addEventListener("click", createTaskBacklog);
  $("taskSnapshotButton").addEventListener("click", saveTaskSnapshot);
  $("taskBoardButton").addEventListener("click", loadTaskBoard);
  $("startTaskButton").addEventListener("click", () => updateSelectedTask("doing"));
  $("completeTaskButton").addEventListener("click", () => updateSelectedTask("done"));
  $("blockTaskButton").addEventListener("click", () => updateSelectedTask("blocked"));
  $("claimResultButton").addEventListener("click", recordClaimValidationResult);
  $("experimentRunButton").addEventListener("click", createExperimentRun);
  $("benchmarkRunButton").addEventListener("click", createBenchmarkRun);
  $("benchmarkExecuteButton").addEventListener("click", executeBenchmarkRun);
  $("benchmarkCompareButton").addEventListener("click", compareBenchmarkRuns);
  $("benchmarkGateButton").addEventListener("click", loadBenchmarkEvidenceReadiness);
  $("benchmarkTasksButton").addEventListener("click", createBenchmarkEvidenceTasks);
  $("experimentAnalysisButton").addEventListener("click", analyzeExperimentRun);
  $("analysisTasksButton").addEventListener("click", createAnalysisTasks);
  $("decisionMemoButton").addEventListener("click", createDecisionMemo);
  $("decisionMemoTasksButton").addEventListener("click", createDecisionMemoTasks);
  $("assumptionAuditButton").addEventListener("click", createAssumptionAudit);
  $("evidenceLedgerButton").addEventListener("click", createEvidenceLedger);
  $("evidenceLedgerTasksButton").addEventListener("click", createEvidenceLedgerTasks);
  $("claimPacketButton").addEventListener("click", loadClaimValidationPacket);
  $("claimQueueButton").addEventListener("click", loadClaimValidationQueue);
  $("claimQueueTasksButton").addEventListener("click", createClaimValidationQueueTasks);
  $("lineageButton").addEventListener("click", loadIdeaLineage);
  $("timelineButton").addEventListener("click", loadIdeaTimeline);
  $("progressButton").addEventListener("click", loadIdeaProgress);
  $("researchPacketButton").addEventListener("click", loadResearchPacket);
  $("ideaBundleButton").addEventListener("click", downloadIdeaBundle);
  $("projectBundleButton").addEventListener("click", downloadProjectBundle);
  $("projectBundleReleaseButton").addEventListener("click", saveProjectBundleReleaseNote);
  $("projectBundleReleasesButton").addEventListener("click", listProjectBundleReleaseNotes);
  $("projectBundleReleaseTasksButton").addEventListener(
    "click",
    createProjectBundleReleaseTasks,
  );
  $("projectBundleReleaseProgressButton").addEventListener(
    "click",
    loadProjectBundleReleaseProgress,
  );
  $("projectBundleReleaseFeedbackButton").addEventListener(
    "click",
    recordProjectBundleReleaseFeedback,
  );
  $("projectBundleReleaseFeedbackListButton").addEventListener(
    "click",
    listProjectBundleReleaseFeedback,
  );
  $("projectBundleReleaseFeedbackTasksButton").addEventListener(
    "click",
    createProjectBundleReleaseFeedbackTasks,
  );
  $("projectBundleReleaseCloseoutButton").addEventListener(
    "click",
    loadProjectBundleReleaseCloseout,
  );
  $("projectBundleReleaseCloseoutTasksButton").addEventListener(
    "click",
    createProjectBundleReleaseCloseoutTasks,
  );
  $("projectBundleReleaseAcceptancePacketButton").addEventListener(
    "click",
    loadProjectBundleReleaseAcceptancePacket,
  );
  $("projectBundleReleaseAcceptancePacketSnapshotButton").addEventListener(
    "click",
    saveProjectBundleReleaseAcceptancePacketSnapshot,
  );
  $("projectBundleReleaseAcceptancePacketSnapshotsButton").addEventListener(
    "click",
    listProjectBundleReleaseAcceptancePacketSnapshots,
  );
  $("projectBundleReleaseAcceptancePacketSnapshotCompareButton").addEventListener(
    "click",
    compareProjectBundleReleaseAcceptancePacketSnapshots,
  );
  $("projectBundleReleaseAcceptancePacketSnapshotTasksButton").addEventListener(
    "click",
    createProjectBundleReleaseAcceptancePacketSnapshotComparisonTasks,
  );
  $("projectBundleReleaseReviewSessionButton").addEventListener(
    "click",
    loadProjectBundleReleaseReviewSession,
  );
  $("projectBundleReleaseReviewSessionTasksButton").addEventListener(
    "click",
    createProjectBundleReleaseReviewSessionTasks,
  );
  $("projectBundleReleaseReviewOutcomeButton").addEventListener(
    "click",
    recordProjectBundleReleaseReviewOutcome,
  );
  $("projectBundleReleaseReviewOutcomesButton").addEventListener(
    "click",
    listProjectBundleReleaseReviewOutcomes,
  );
  $("projectBundleReleaseReviewOutcomeTasksButton").addEventListener(
    "click",
    createProjectBundleReleaseReviewOutcomeTasks,
  );
  $("projectBundleReleaseReviewOutcomeProgressButton").addEventListener(
    "click",
    loadProjectBundleReleaseReviewOutcomeProgress,
  );
  $("projectBundleReleaseReviewOutcomeSignoffButton").addEventListener(
    "click",
    recordProjectBundleReleaseReviewOutcomeSignoff,
  );
  $("projectBundleReleaseReviewOutcomeSignoffsButton").addEventListener(
    "click",
    listProjectBundleReleaseReviewOutcomeSignoffs,
  );
  $("projectBundleReadinessButton").addEventListener("click", loadProjectBundleReadiness);
  $("projectBundleReadinessTasksButton").addEventListener(
    "click",
    createProjectBundleReadinessTasks,
  );
  $("projectBundleReadinessSnapshotButton").addEventListener(
    "click",
    saveProjectBundleReadinessSnapshot,
  );
  $("projectBundleReadinessSnapshotsButton").addEventListener(
    "click",
    listProjectBundleReadinessSnapshots,
  );
  $("projectBundleReadinessSnapshotCompareButton").addEventListener(
    "click",
    compareProjectBundleReadinessSnapshots,
  );
  $("projectBundleReadinessComparisonTasksButton").addEventListener(
    "click",
    createProjectBundleReadinessComparisonTasks,
  );
  $("readinessButton").addEventListener("click", loadIdeaReadiness);
  $("qualityGateButton").addEventListener("click", loadIdeaQualityGate);
  $("qualityGateTasksButton").addEventListener("click", createQualityGateTasks);
  $("readinessTasksButton").addEventListener("click", createReadinessTasks);
  $("cockpitButton").addEventListener("click", loadProjectCockpit);
  $("cockpitTasksButton").addEventListener("click", createProjectCockpitTasks);
  $("overviewButton").addEventListener("click", loadProjectOverview);
  $("triageBriefButton").addEventListener("click", loadProjectTriageBrief);
  $("triageMarkdownButton").addEventListener("click", loadProjectTriageMarkdown);
  $("triageSnapshotButton").addEventListener("click", saveProjectTriageSnapshot);
  $("triageCompareButton").addEventListener("click", compareProjectTriageSnapshots);
  $("triageComparisonTasksButton").addEventListener(
    "click",
    createProjectTriageComparisonTasks,
  );
  $("triageTasksButton").addEventListener("click", createProjectTriageTasks);
  $("readinessOverviewButton").addEventListener("click", loadProjectReadinessOverview);
  $("qualityOverviewButton").addEventListener("click", loadProjectQualityOverview);
  $("projectQualityTasksButton").addEventListener("click", createProjectQualityTasks);
  $("opportunityRadarButton").addEventListener("click", loadOpportunityRadar);
  $("opportunityRadarTasksButton").addEventListener("click", createOpportunityRadarTasks);
  $("advisorBriefButton").addEventListener("click", createAdvisorBrief);
  $("researchPlanButton").addEventListener("click", createResearchPlan);
  $("researchPlanProgressButton").addEventListener("click", loadResearchPlanProgress);
  $("researchPlanTasksButton").addEventListener("click", createResearchPlanTasks);
  $("shortlistIdeaButton").addEventListener("click", shortlistLatestIdea);
  $("rankIdeasButton").addEventListener("click", rankIdeas);
  $("savePortfolioButton").addEventListener("click", savePortfolio);
  loadApiKey();
  loadProjectScope();
  refreshProjectScopeStatus();
  renderLatestWorkflow();
  checkHealth();
  loadPilotLaunch();
  loadResearchProfile();
  refreshJobs();
});
