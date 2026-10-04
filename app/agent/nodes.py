import os
import re
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

from app.agent.config import (ALLOWED_VERDICTS, DEFAULT_VERDICT, MAX_DIFF_CHARS, MODEL,
                              SEVERITY_ORDER, VERDICT_RULES)
from app.agent.prompts import SYSTEM_PROMPT, build_prompt
from app.agent.schemas import AnalysisResult


def _ask_gemini(kind, diff):
    """Sends the diff to Gemini and validates the JSON answer.
    Tries up to 3 times (waiting 3 and 8 seconds) when Google's servers are busy or the answer has the wrong shape."""
    load_dotenv()
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is missing from the .env file")
    client = genai.Client(api_key=key)
    last_error = None
    for delay in (0, 3, 8):
        if delay:
            time.sleep(delay)
        try:
            reply = client.models.generate_content(
                model=MODEL,
                contents=build_prompt(kind, diff[:MAX_DIFF_CHARS]),
                config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT,
                                                   response_mime_type="application/json", temperature=0.2))
        except errors.ServerError as e:           # Google's side is busy (500/503): wait and retry
            last_error = e
            continue
        except errors.ClientError as e:
            if getattr(e, "code", None) == 429:   # free-tier rate limit: wait and retry
                last_error = e
                continue
            raise
        text = (reply.text or "").strip().replace("```json", "").replace("```", "").strip()
        try:
            return [f.model_dump() for f in AnalysisResult.model_validate_json(text).findings]
        except ValueError as e:                   # wrong shape: try again
            last_error = e
    raise last_error


# ---------------- graph steps (nodes) ----------------
def load_pr(state):
    if not state.get("diff", "").strip():
        return {"status": "failed", "errors": state.get("errors", []) + ["The pull request has no changes to review."]}
    return {"status": "loaded", "bugs": [], "security_issues": [], "quality_issues": []}


def analyze_diff(state):
    return {"status": "diff_ready"}


def _make_analyzer(kind, state_key):
    def node(state):
        if not state.get("diff", "").strip():
            return {}
        try:
            return {state_key: _ask_gemini(kind, state["diff"])}
        except Exception as e:            # never show the secret or crash the whole review
            msg = f"{kind} analysis failed ({type(e).__name__}). The review can be retried."
            return {state_key: [], "errors": state.get("errors", []) + [msg]}
    return node


bug_analysis = _make_analyzer("bugs", "bugs")
security_analysis = _make_analyzer("security", "security_issues")
quality_analysis = _make_analyzer("quality", "quality_issues")


def _tokens(title):
    return {w for w in re.findall(r"[a-z0-9]+", title.lower()) if len(w) > 2}


def _similar(a, b):
    """Two findings are the same problem if they are in the same file, a few lines apart, with similar titles."""
    if a["file"] != b["file"] or abs(a["line"] - b["line"]) > 3:
        return False
    ta, tb = _tokens(a["title"]), _tokens(b["title"])
    return bool(ta and tb) and len(ta & tb) / len(ta | tb) >= 0.5


def aggregate(state):
    """Merges the three lists, merges duplicates (keeping the most severe version) and sorts by severity."""
    tagged = ([("bug", f) for f in state.get("bugs", [])]
              + [("security", f) for f in state.get("security_issues", [])]
              + [("quality", f) for f in state.get("quality_issues", [])])
    merged = []
    for category, f in tagged:
        for m in merged:
            if _similar(m, f):
                if SEVERITY_ORDER.index(f["severity"]) < SEVERITY_ORDER.index(m["severity"]):
                    m.update({k: f[k] for k in ("severity", "title", "explanation", "fix", "line")})
                if category not in m["category"].split("+"):
                    m["category"] += "+" + category
                break
        else:
            merged.append({**f, "category": category})
    merged.sort(key=lambda f: SEVERITY_ORDER.index(f["severity"]))
    counts = {s: sum(1 for f in merged if f["severity"] == s) for s in SEVERITY_ORDER}
    parts = [f"{counts[s]} {s}" for s in SEVERITY_ORDER if counts[s]]
    summary = (f"Found {len(merged)} issue(s): " + ", ".join(parts) + ".") if merged else "No meaningful issues found."
    return {"all_findings": merged, "counts": counts, "review_summary": summary}


def decide_verdict(state):
    """The verdict comes from the rules in config.py. The AI never chooses it."""
    counts = state.get("counts", {})
    verdict = DEFAULT_VERDICT
    for severity, result in VERDICT_RULES:
        if counts.get(severity, 0) > 0:
            verdict = result
            break
    if state.get("errors") and verdict == DEFAULT_VERDICT:
        verdict = "REVIEW_REQUIRED"       # an AI step failed, so never auto-approve
    assert verdict in ALLOWED_VERDICTS
    return {"final_verdict": verdict, "status": "completed"}

