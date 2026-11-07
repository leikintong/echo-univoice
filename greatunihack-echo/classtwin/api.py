"""HTTP endpoint for n8n.  Run:  uvicorn api:app --host 0.0.0.0 --port 8000

POST /analyze  (multipart form, field "file" = PDF)
-> {"mode", "lecturer_email_html", "student_pack_html", "top_fixes", "heatmap"}
"""
from fastapi import FastAPI, File, UploadFile

import core

app = FastAPI(title="ClassTwin API")


@app.get("/")
def health():
    return {"ok": True, "mode": "mock" if core.use_mock() else "live"}


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    report = core.analyze(await file.read())
    title = file.filename or "your lecture"
    return {
        "mode": report["mode"],
        "lecture": title,
        "lecturer_email_html": core.lecturer_email_html(report, title),
        "student_pack_html": core.student_pack_html(report, title),
        "top_fixes": report["advisor"].get("top_fixes", []),
        "heatmap": {p["name"]: [r["confusion"] for r in report["results"][p["id"]]] for p in report["personas"]},
    }
