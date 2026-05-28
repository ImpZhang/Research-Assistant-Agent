const state = {
  paperId: "",
  jobId: "",
  latestIdeaId: "",
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
    renderResult(
      "workflowResult",
      `Job <code>${job.id}</code> is <strong>${job.status}</strong> at ${Math.round((job.progress || 0) * 100)}%.<br />${renderJobOutput(job.output)}`,
      job.status === "failed" ? "error" : job.status === "completed" ? "ok" : "warn",
    );
    if (job.status === "completed" || job.status === "failed") {
      clearInterval(state.pollTimer);
      state.pollTimer = null;
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

document.addEventListener("DOMContentLoaded", () => {
  $("uploadForm").addEventListener("submit", uploadPaper);
  $("runWorkflowButton").addEventListener("click", runWorkflow);
  $("contextSearchForm").addEventListener("submit", searchContext);
  $("literatureSearchForm").addEventListener("submit", searchLiterature);
  $("refreshJobsButton").addEventListener("click", refreshJobs);
  $("loadDossierButton").addEventListener("click", loadDossier);
  checkHealth();
  refreshJobs();
});
