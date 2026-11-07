"""ClassTwin core: virtual students pre-read lecture slides and flag confusion.

Uses the OpenAI API when OPENAI_API_KEY is set; otherwise (or with MOCK=1)
falls back to a deterministic mock so the demo always runs.
"""
import hashlib
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import pymupdf as fitz

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
MAX_CHARS_PER_PAGE = 1500

PERSONAS = [
    {
        "id": "mei",
        "name": "Mei",
        "label": "International student",
        "profile": (
            "First-year international student. English is your second language. "
            "Strong at maths. You do not know British idioms, slang, cultural or "
            "sports references, and you struggle with long, dense sentences."
        ),
    },
    {
        "id": "tom",
        "name": "Tom",
        "label": "Weak maths background",
        "profile": (
            "Transferred from History. Fluent English, good at essays. Your maths "
            "stopped at GCSE. Formulas, Greek letters and unexplained symbols lose you "
            "quickly, especially when steps are skipped."
        ),
    },
    {
        "id": "aisha",
        "name": "Aisha",
        "label": "Missed the prerequisite",
        "profile": (
            "First-year student who has NOT taken the prerequisite module. You get lost "
            "whenever a slide assumes a concept that was never defined in these slides."
        ),
    },
    {
        "id": "jamal",
        "name": "Jamal",
        "label": "Practical learner",
        "profile": (
            "Average student who learns through examples. Abstract definitions without "
            "a concrete example or a reason why it matters confuse and disengage you."
        ),
    },
    {
        "id": "leo",
        "name": "Leo",
        "label": "Top student",
        "profile": (
            "Top of the class. You rarely get confused, but you notice errors, "
            "ambiguity, contradictions and big logical jumps between slides."
        ),
    },
]


# ---------------------------------------------------------------- slides
def extract_pages(pdf_bytes: bytes) -> list[str]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    for p in doc:
        text = re.sub(r"\s+", " ", p.get_text()).strip()
        pages.append(text[:MAX_CHARS_PER_PAGE] or "(slide with no text, mostly visual)")
    return pages


def _slides_block(pages: list[str]) -> str:
    return "\n".join(f"[Slide {i}] {t}" for i, t in enumerate(pages, 1))


# ---------------------------------------------------------------- LLM mode
def provider() -> str:
    """claude if ANTHROPIC_API_KEY is set, else openai if OPENAI_API_KEY is set, else mock."""
    if os.getenv("MOCK") == "1":
        return "mock"
    if os.getenv("ANTHROPIC_API_KEY"):
        return "claude"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    return "mock"


def _client():
    if provider() == "claude":
        import anthropic

        return anthropic.Anthropic()
    from openai import OpenAI

    return OpenAI()


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1])


def _chat_json(client, system: str, user: str) -> dict:
    if provider() == "claude":
        resp = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4000,
            system=system + "\n\nReturn only the JSON object, with no other text.",
            messages=[{"role": "user", "content": user}],
        )
        return _parse_json("".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", "") == "text"))
    resp = client.chat.completions.create(
        model=MODEL,
        temperature=0.4,
        response_format={"type": "json_object"},
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    return json.loads(resp.choices[0].message.content)


STUDENT_SYSTEM = """You are {name}, a university student attending a lecture.
{profile}

You read the lecture slides in order, as if hearing them in class, remembering what
earlier slides said. Stay strictly in character: only get confused where THIS
student genuinely would. Most slides should score 0-1; be honest, not dramatic.

Return JSON: {{"pages": [{{"page": <int>, "confusion": <0-5>,
"trigger": "<exact word/phrase that loses you, or empty>",
"reason": "<one short sentence why, or empty>",
"question": "<the question you would ask the lecturer, or empty>"}}]}}
Include every slide exactly once."""

ADVISOR_SYSTEM = """You are an experienced university teaching advisor.
Several virtual students pre-read a lecture and reported confusion per slide.
Lecturers are busy: give ONLY the 3 most impactful fixes, each concrete and
ready to paste into the slide. Also write a short pre-reading pack for students.

Return JSON: {"top_fixes": [{"page": <int>, "issue": "<short>",
"fix": "<concrete wording or change>", "affected": ["<student names>"]}],
"prep_pack": {"glossary": [{"term": "", "definition": ""}],
"prerequisites": ["<concept to revise first>"],
"hard_parts": [{"page": <int>, "tip": "<how to prepare>"}]}}
Max 3 fixes, max 8 glossary terms, max 4 prerequisites, max 3 hard parts."""


def _student_llm(client, persona, pages):
    data = _chat_json(
        client,
        STUDENT_SYSTEM.format(**persona),
        "Lecture slides:\n" + _slides_block(pages),
    )
    by_page = {int(r.get("page", 0)): r for r in data.get("pages", [])}
    return [_clean_row(by_page.get(i, {}), i) for i in range(1, len(pages) + 1)]


def _advisor_llm(client, pages, results):
    lines = []
    for p in PERSONAS:
        for r in results[p["id"]]:
            if r["confusion"] >= 2:
                lines.append(
                    f"Slide {r['page']} | {p['name']} ({p['label']}) | score {r['confusion']} | "
                    f"trigger: {r['trigger']} | reason: {r['reason']} | asks: {r['question']}"
                )
    report = "\n".join(lines) or "No significant confusion reported."
    return _chat_json(
        client,
        ADVISOR_SYSTEM,
        f"Slides:\n{_slides_block(pages)}\n\nStudent reports:\n{report}",
    )


def _clean_row(r: dict, page: int) -> dict:
    try:
        score = max(0, min(5, int(r.get("confusion", 0))))
    except (TypeError, ValueError):
        score = 0
    return {
        "page": page,
        "confusion": score,
        "trigger": str(r.get("trigger", "") or ""),
        "reason": str(r.get("reason", "") or ""),
        "question": str(r.get("question", "") or ""),
    }


# ---------------------------------------------------------------- mock mode
_IDIOMS = ["ballpark", "rule of thumb", "piece of cake", "on the same page", "back of the envelope",
           "cricket", "a level", "quid", "touch base", "bottom line"]
_MATHS = re.compile(r"[=∑σμβαλ√^]|\bvariance\b|\bderivative\b|\bintegral\b|\bmatrix\b|\bn-1\b|\bn − 1\b", re.I)
_JARGON = re.compile(r"\b[A-Z]{3,}\b")


def _h(*parts) -> int:
    return int(hashlib.md5("|".join(map(str, parts)).encode()).hexdigest(), 16)


def _student_mock(persona, pages):
    rows = []
    for i, text in enumerate(pages, 1):
        low = text.lower()
        score, trigger, reason, q = _h(persona["id"], i) % 2, "", "", ""
        pid = persona["id"]
        idiom = next((w for w in _IDIOMS if w in low), None)
        maths = _MATHS.search(text)
        jargon = _JARGON.search(text)
        if pid == "mei" and idiom:
            score, trigger = 4, idiom
            reason = f"I don't know what '{idiom}' means here."
            q = f"Sorry, what does '{idiom}' mean?"
        elif pid == "tom" and maths:
            score, trigger = 4, maths.group(0)
            reason = "Formula appears without the steps or the intuition."
            q = "Could you walk through that formula step by step?"
        elif pid == "aisha" and jargon:
            score, trigger = 3, jargon.group(0)
            reason = f"'{jargon.group(0)}' was never defined in the slides."
            q = f"What does {jargon.group(0)} stand for?"
        elif pid == "jamal" and len(text) > 400 and "example" not in low:
            score, trigger = 3, "abstract definition"
            reason = "Dense slide with no concrete example."
            q = "Can you show an example of this?"
        elif pid == "leo" and _h("leo", i) % 7 == 0 and i > 1:
            score, trigger = 2, f"link from slide {i-1}"
            reason = "The jump from the previous slide is not explained."
            q = f"How does this follow from slide {i-1}?"
        rows.append({"page": i, "confusion": score, "trigger": trigger, "reason": reason, "question": q})
    return rows


def _advisor_mock(pages, results):
    by_page = {}
    for p in PERSONAS:
        for r in results[p["id"]]:
            if r["confusion"] >= 2:
                by_page.setdefault(r["page"], []).append((p, r))
    ranked = sorted(by_page.items(), key=lambda kv: -sum(r["confusion"] for _, r in kv[1]))[:3]
    fixes, glossary, hard = [], [], []
    for page, hits in ranked:
        p, r = max(hits, key=lambda h: h[1]["confusion"])
        fixes.append({
            "page": page,
            "issue": r["reason"],
            "fix": (f"Add one sentence of intuition and a worked step before the formula ('{r['trigger']}')."
                    if p["id"] == "tom" else
                    f"Briefly define or explain '{r['trigger']}' on this slide and add one worked example."),
            "affected": [h[0]["name"] for h in hits],
        })
        hard.append({"page": page, "tip": f"Before class, look up '{r['trigger']}'."})
        if r["trigger"] and len(r["trigger"]) > 2 and not r["trigger"].startswith(("link", "abstract")):
            glossary.append({"term": r["trigger"], "definition": "(definition generated in live mode)"})
    return {
        "top_fixes": fixes,
        "prep_pack": {"glossary": glossary, "prerequisites": ["Review the previous lecture's key terms"],
                      "hard_parts": hard},
    }


# ---------------------------------------------------------------- pipeline
def use_mock() -> bool:
    return provider() == "mock"


def analyze(pdf_bytes: bytes, progress=None) -> dict:
    pages = extract_pages(pdf_bytes)
    mock = use_mock()
    client = None if mock else _client()

    def run(persona):
        rows = _student_mock(persona, pages) if mock else _student_llm(client, persona, pages)
        return persona, rows

    # Workers only call the model; progress is reported from the main thread,
    # because Streamlit UI calls are not allowed from background threads.
    results = {}
    with ThreadPoolExecutor(max_workers=len(PERSONAS)) as ex:
        futures = [ex.submit(run, p) for p in PERSONAS]
        for fut in as_completed(futures):
            persona, rows = fut.result()
            results[persona["id"]] = rows
            if progress:
                progress(persona["name"])

    advisor = _advisor_mock(pages, results) if mock else _advisor_llm(client, pages, results)
    return {"mode": provider(), "pages": pages, "personas": PERSONAS,
            "results": results, "advisor": advisor}


# ---------------------------------------------------------------- outputs
def _esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def lecturer_email_html(report: dict, title: str = "your lecture") -> str:
    fixes = report["advisor"].get("top_fixes", [])
    items = "".join(
        f"<li><b>Slide {f.get('page')}:</b> {_esc(f.get('issue',''))}<br>"
        f"<i>Suggested fix:</i> {_esc(f.get('fix',''))}<br>"
        f"<small>Likely to lose: {_esc(', '.join(f.get('affected', [])))}</small></li>"
        for f in fixes
    ) or "<li>No major issues predicted. Nice slides!</li>"
    return (
        f"<h2>ClassTwin pre-check: {_esc(title)}</h2>"
        f"<p>Our virtual students read your slides before class. Top {len(fixes)} things to fix:</p>"
        f"<ol>{items}</ol>"
        "<p>A pre-reading pack has been prepared for your students.</p>"
    )


def student_pack_html(report: dict, title: str = "this lecture") -> str:
    pack = report["advisor"].get("prep_pack", {})
    gl = "".join(f"<li><b>{_esc(g.get('term'))}</b>: {_esc(g.get('definition'))}</li>"
                 for g in pack.get("glossary", []))
    pre = "".join(f"<li>{_esc(x)}</li>" for x in pack.get("prerequisites", []))
    hard = "".join(f"<li>Slide {h.get('page')}: {_esc(h.get('tip'))}</li>" for h in pack.get("hard_parts", []))
    return (
        f"<h2>Pre-reading pack: {_esc(title)}</h2>"
        f"<h3>Key terms</h3><ul>{gl or '<li>None</li>'}</ul>"
        f"<h3>Revise first</h3><ul>{pre or '<li>None</li>'}</ul>"
        f"<h3>Heads-up: tricky parts</h3><ul>{hard or '<li>None</li>'}</ul>"
    )
