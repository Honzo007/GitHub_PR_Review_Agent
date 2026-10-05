const $ = (id) => document.getElementById(id);
const SUBSTEPS = ["bug_analysis", "security_analysis", "quality_analysis", "final_verdict"];
const STATE_TEXT = { pending: "Pending", running: "Running...", completed: "Completed", failed: "Failed" };
const VERDICTS = { APPROVE: "Approved", CHANGES_REQUESTED: "Changes requested", REVIEW_REQUIRED: "Review required" };
const SEVS = ["critical", "high", "medium", "low"];
const KEY = "pr-review-history";
let source = null, timerId = null, startedAt = 0, current = null, filter = "all";

// textContent never runs HTML, so repository text cannot inject code into the page.
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);

/* ---------- Progress UI ---------- */
function setStage(id, status) {
  const card = $(id);
  card.dataset.status = status;
  card.querySelector(".state").textContent = STATE_TEXT[status];
}
function setSub(stage, status) { $("sub-" + stage).dataset.status = status; }

function friendly(msg) {
  const m = (msg || "").toLowerCase();
  if (m.includes("token") || m.includes("credential") || m.includes("401")) return msg + " Check the GitHub token in your .env file.";
  if (m.includes("not found") || m.includes("404")) return msg + " Check that the link is correct and you have access to it.";
  return msg;
}
function showError(message) {
  const box = $("error");
  box.textContent = friendly(message);
  box.hidden = false;
}

function fmt(s) { return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0"); }
function startTimer() {
  stopTimer();
  startedAt = Date.now();
  $("timer").textContent = "0:00";
  timerId = setInterval(() => { $("timer").textContent = fmt(Math.floor((Date.now() - startedAt) / 1000)); }, 500);
}
function stopTimer() { clearInterval(timerId); timerId = null; }

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
    setStage("stage-ai", "failed");
  }
}

/* ---------- Mode ---------- */
function currentMode() { return document.querySelector('input[name="mode"]:checked').value; }

function applyMode() {
  const pr = currentMode() === "pr";
  $("url").placeholder = pr ? "https://github.com/owner/repo/pull/12" : "https://github.com/user/repository";
  $("t-github").textContent = pr ? "Connect repo" : "Push code";
  $("t-pr").textContent = pr ? "Load PR" : "Open PR";
  $("demo-note").hidden = pr;
}
function requestBody() {
  const link = $("url").value.trim();
  return currentMode() === "pr" ? { pr_url: link } : { repo_url: link };
}

/* ---------- Start a review ---------- */
async function startReview() {
  const button = $("start");
  resetUI();
  if (!$("url").value.trim()) { showError("Paste a GitHub link first."); return; }
  button.disabled = true;                  // prevents starting two reviews at once
  startTimer();
  try {
    const res = await fetch("/api/review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestBody()),
    });
    const data = await res.json();
    if (!res.ok) { stopTimer(); showError(data.error || "Could not start the review."); button.disabled = false; return; }

    if (source) source.close();
    source = new EventSource("/api/review/" + data.review_id + "/events");
    source.onmessage = (e) => {
      const ev = JSON.parse(e.data);
      handleEvent(ev);
      if (ev.stage === "done") { source.close(); stopTimer(); loadResult(data.review_id); }
    };
    source.onerror = () => {
      source.close();
      stopTimer();
      showError("Lost the connection to the server.");
      button.disabled = false;
    };
  } catch (err) {
    stopTimer();
    showError("Could not reach the server. Is it running?");
    button.disabled = false;
  }
}

async function loadResult(id) {
  try {
    const res = await fetch("/api/review/" + id);
    const data = await res.json();
    if (data.verdict) { saveHistory(data); renderResult(data); }
  } catch (err) {
    showError("Could not load the result.");
  }
  $("start").disabled = false;
}

/* ---------- Result ---------- */
function renderResult(r) {
  current = r;
  filter = "all";
  $("result").hidden = false;
  const verdict = $("verdict");
  verdict.dataset.v = r.verdict;
  verdict.textContent = (VERDICTS[r.verdict] || r.verdict) + " \u00B7 " + r.total_issues + " issue(s) found";
  $("summary").textContent = r.summary;

  const meta = $("meta");
  meta.replaceChildren();
  meta.append(document.createTextNode(
    (r.pr_title ? r.pr_title + " \u00B7 " : "") + r.repository + " \u00B7 " + r.files_analyzed + " files \u00B7 +" + r.additions + " / -" + r.deletions + " \u00B7 "));
  if (r.pr_url && r.pr_url.startsWith("https://github.com/")) {
    const link = el("a", "", "Pull request #" + r.pr_number);
    link.href = r.pr_url;
    link.target = "_blank";
    link.rel = "noopener";
    meta.append(link);
  }

  const warnings = $("warnings");
  warnings.replaceChildren();
  (r.warnings || []).forEach((w) => warnings.append(el("div", "warn", w)));

  renderCounts();
  renderIssues();
  $("result").scrollIntoView({ behavior: "smooth" });
}

function renderCounts() {
  const counts = $("counts");
  counts.replaceChildren();
  [["all", current.total_issues], ...SEVS.map((s) => [s, current[s]])].forEach(([key, n]) => {
    const btn = el("button", "count");
    btn.type = "button";
    btn.setAttribute("aria-pressed", String(filter === key));
    btn.append(el("b", "", String(n)), el("span", "", cap(key)));
    btn.addEventListener("click", () => { filter = key; renderCounts(); renderIssues(); });
    counts.append(btn);
  });
}

function renderIssues() {
  const box = $("issues");
  box.replaceChildren();
  const list = current.issues.filter((i) => filter === "all" || i.severity === filter);
  if (!list.length) { box.append(el("p", "empty", filter === "all" ? "No meaningful issues found." : "No " + filter + " issues.")); return; }
  list.forEach((i) => {
    const card = el("details", "issue");
    card.dataset.sev = i.severity;
    card.open = i.severity === "critical" || i.severity === "high";
    const head = el("summary");
    const badge = el("span", "badge", i.severity);
    badge.dataset.sev = i.severity;
    head.append(badge, el("span", "issue-title", i.title),
      el("span", "issue-loc", i.file + ":" + i.line + (i.category ? " (" + i.category.replaceAll("+", ", ") + ")" : "")));
    const body = el("div", "issue-body");
    const why = el("p");
    why.append(el("b", "", "Why: "), document.createTextNode(i.explanation));
    const fix = el("p", "fix");
    fix.append(el("b", "", "Fix: "), document.createTextNode(i.fix));
    body.append(why, fix);
    card.append(head, body);
    box.append(card);
  });
}

/* ---------- Copy report ---------- */
function toMarkdown(r) {
  const out = ["# PR review: " + (VERDICTS[r.verdict] || r.verdict), "", r.summary, "",
    "- Repository: " + r.repository,
    "- Files analyzed: " + r.files_analyzed + " (+" + r.additions + " / -" + r.deletions + ")",
    "- Issues: " + r.critical + " critical, " + r.high + " high, " + r.medium + " medium, " + r.low + " low", ""];
  r.issues.forEach((i) => {
    out.push("### [" + cap(i.severity) + "] " + i.title, "`" + i.file + ":" + i.line + "`", "",
      "**Why:** " + i.explanation, "", "**Fix:** " + i.fix, "");
  });
  return out.join("\n");
}

async function copyReport() {
  if (!current) return;
  const text = toMarkdown(current);
  try { await navigator.clipboard.writeText(text); }
  catch (e) {
    const area = document.createElement("textarea");
    area.value = text;
    document.body.append(area);
    area.select();
    document.execCommand("copy");
    area.remove();
  }
  const btn = $("copy");
  btn.textContent = "Copied";
  setTimeout(() => { btn.textContent = "Copy report"; }, 1500);
}

/* ---------- Recent reviews (saved in this browser only) ---------- */
function loadHistory() {
  try { return JSON.parse(localStorage.getItem(KEY)) || []; } catch (e) { return []; }
}
function saveHistory(r) {
  try {
    const list = [{ at: Date.now(), result: r }, ...loadHistory()].slice(0, 8);
    localStorage.setItem(KEY, JSON.stringify(list));
  } catch (e) { /* storage unavailable: skip */ }
  renderHistory();
}
function renderHistory() {
  const list = loadHistory();
  const box = $("history");
  box.replaceChildren();
  $("history-wrap").hidden = !list.length;
  list.forEach((item) => {
    const r = item.result;
    const btn = el("button", "hist-item");
    btn.type = "button";
    const badge = el("span", "badge", VERDICTS[r.verdict] || r.verdict);
    badge.dataset.sev = r.verdict === "APPROVE" ? "low" : r.verdict === "CHANGES_REQUESTED" ? "critical" : "medium";
    btn.append(badge, el("span", "hist-name", r.pr_title || r.repository), el("span", "hist-time", new Date(item.at).toLocaleString()));
    btn.addEventListener("click", () => { resetUI(); renderResult(r); });
    box.append(btn);
  });
}

/* ---------- Wiring ---------- */
$("start").addEventListener("click", startReview);
$("url").addEventListener("keydown", (e) => { if (e.key === "Enter" && !$("start").disabled) startReview(); });
$("copy").addEventListener("click", copyReport);
$("clear").addEventListener("click", () => { try { localStorage.removeItem(KEY); } catch (e) {} renderHistory(); });
document.querySelectorAll('input[name="mode"]').forEach((radio) => radio.addEventListener("change", applyMode));
applyMode();
renderHistory();