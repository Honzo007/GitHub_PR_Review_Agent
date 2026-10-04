// Temporary test page. Member A will replace this with the real dashboard.
async function startReview() {
  const log = document.getElementById("log");
  log.textContent = "";
  const res = await fetch("/api/review", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_url: document.getElementById("url").value }),
  });
  const data = await res.json();
  if (!res.ok) { log.textContent = data.error; return; }

  const source = new EventSource("/api/review/" + data.review_id + "/events");
  source.onmessage = (e) => {
    const ev = JSON.parse(e.data);
    log.textContent += ev.stage + " | " + ev.status + " | " + ev.message + "\n";
    if (ev.stage === "done") { source.close(); showResult(data.review_id); }
  };
}

async function showResult(id) {
  const res = await fetch("/api/review/" + id);
  const data = await res.json();
  document.getElementById("log").textContent += "\n" + JSON.stringify(data, null, 2);
}