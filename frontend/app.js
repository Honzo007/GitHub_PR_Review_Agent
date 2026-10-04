const $ = (id) => document.getElementById(id);
const SUBSTEPS = ["bug_analysis", "security_analysis", "quality_analysis", "final_verdict"];
const STATE_TEXT = { pending: "Pending", running: "Running...", completed: "Completed", failed: "Failed" };
let source = null;

// Safe way to build page elements: textContent never runs HTML, so repository text cannot inject code.
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function setStage(id, status) {
  const card = $(id);
  card.dataset.status = status;
  card.querySelector(".state").textContent = STATE_TEXT[status];
}

function setSub(stage, status) {
  $("sub-" + stage).dataset.status = status;
}

function showError(message) {
  const box = $("error");
  box.textContent = message;
  box.hidden = false;
}

function resetUI() {
  ["stage-github", "stage-pr", "stage-ai"].forEach((id) => setStage(id, "pending"));
  SUBSTEPS.forEach((s) => setSub(s, "pending"));
  $("log").textContent = "";
  $("error").hidden = true;
  $("result").hidden = true;
}

function addLog(ev) {
  const log = $("log");
  log.textContent += ev.message + "\n";
  log.scrollTop = log.scrollHeight;
}

function handleEvent(ev) {
  if (ev.stage === "done") return;
  if (ev.message) addLog(ev);
  if (ev.status === "failed") showError(ev.message);

  if (ev.stage === "github" || ev.stage === "pr") {
    setStage("stage-" + ev.stage, ev.status);
  } else if (SUBSTEPS.includes(ev.stage)) {
    setSub(ev.stage, ev.status);
    const finished = ev.stage === "final_verdict" && ev.status === "completed";
    setStage("stage-ai", ev.status === "failed" ? "failed" : finished ? "completed" : "running");
  } else if (ev.status === "failed") {
    setStage("stage-ai", "failed");        // failure inside the AI review
  }
}

async function startReview() {
  const button = $("start");
  resetUI();
  button.disabled = true;                  // prevents starting two reviews at once
  try {
    const res = await fetch("/api/review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ repo_url: $("url").value.trim() }),
    });
    const data = await res.json();
    if (!res.ok) { showError(data.error || "Could not start the review."); button.disabled = false; return; }

    if (source) source.close();
    source = new EventSource("/api/review/" + data.review_id + "/events");
    source.onmessage = (e) => {
      const ev = JSON.parse(e.data);
      handleEvent(ev);
      if (ev.stage === "done") { source.close(); loadResult(data.review_id); }
    };
    source.onerror = () => {
      source.close();
      showError("Lost the connection to the server.");
      button.disabled = false;
    };
  } catch (err) {
    showError("Could not reach the server. Is it running?");
    button.disabled = false;
  }
}

async function loadResult(id) {
  try {
    const res = await fetch("/api/review/" + id);
    const data = await res.json();
    if (data.verdict) renderResult(data);
  } catch (err) {
    showError("Could not load the result.");
  }
  $("start").disabled = false;
}

function renderResult(r) {
  $("result").hidden = false;
  const verdict = $("verdict");
  verdict.dataset.v = r.verdict;
  verdict.textContent = r.verdict.replace("_", " ") + "  |  " + r.total_issues + " issue(s) found";
  $("summary").textContent = r.summary;

  const counts = $("counts");
  counts.replaceChildren();
  ["critical", "high", "medium", "low"].forEach((sev) => {
    const box = el("div", "count");
    box.append(el("b", "", String(r[sev])), el("span", "", sev.toUpperCase()));
    counts.append(box);
  });

  const meta = $("meta");
  meta.replaceChildren();
  meta.append(document.createTextNode(
    r.repository + "  |  " + r.files_analyzed + " files analyzed  |  +" + r.additions + " / -" + r.deletions + "  |  "));
  if (r.pr_url && r.pr_url.startsWith("https://github.com/")) {
    const link = el("a", "", "Pull Request #" + r.pr_number);
    link.href = r.pr_url;
    link.target = "_blank";
    link.rel = "noopener";
    meta.append(link);
  }

  const warnings = $("warnings");
  warnings.replaceChildren();
  (r.warnings || []).forEach((w) => warnings.append(el("div", "warn", w)));

  const issues = $("issues");
  issues.replaceChildren();
  if (!r.issues.length) issues.append(el("p", "summary", "No meaningful issues found."));
  r.issues.forEach((i) => {
    const card = el("div", "issue");
    card.dataset.sev = i.severity;
    const head = el("div", "issue-head");
    const badge = el("span", "badge", i.severity.toUpperCase());
    badge.dataset.sev = i.severity;
    head.append(badge, el("span", "issue-title", i.title));
    card.append(head);
    card.append(el("div", "issue-loc", i.file + ":" + i.line + "  (" + (i.category || "").replaceAll("+", ", ") + ")"));
    const why = el("p");
    why.append(el("b", "", "Why: "), document.createTextNode(i.explanation));
    const fix = el("p", "fix");
    fix.append(el("b", "", "Fix: "), document.createTextNode(i.fix));
    card.append(why, fix);
    issues.append(card);
  });
  $("result").scrollIntoView({ behavior: "smooth" });
}

$("start").addEventListener("click", startReview);
$("url").addEventListener("keydown", (e) => { if (e.key === "Enter" && !$("start").disabled) startReview(); });
