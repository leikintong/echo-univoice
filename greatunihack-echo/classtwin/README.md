# ClassTwin 🎓

**Virtual students read your slides before class, so you hear their questions before your real students do.**

Lecturers only find out where students got lost after the exam. ClassTwin runs a panel of AI student agents (international student, weak-maths transfer student, missed-the-prerequisite first year, practical learner, top student) over a lecture deck *before* it is taught. Each agent reads slide by slide, remembering earlier slides, and flags where it gets lost and why. An advisor agent then turns this into:

- **For the lecturer:** the 3 most impactful fixes, with ready-to-paste wording
- **For students:** a pre-reading pack (glossary, what to revise first, tricky parts)

Zero extra work for the lecturer: drop the PDF in a folder, n8n does the rest.

## Run it

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...        # without a key it runs in mock mode
python make_sample.py              # creates sample_lecture.pdf
streamlit run app.py               # demo UI
uvicorn api:app --port 8000        # API for n8n
```

## n8n workflow

1. **Trigger:** Google Drive / local folder "new file" (lecture PDF)
2. **HTTP Request:** `POST http://<host>:8000/analyze`, body = multipart form, field `file` = the PDF binary
3. **Send Email** to the lecturer with `{{$json.lecturer_email_html}}`
4. **Send Email / post** to the student channel with `{{$json.student_pack_html}}`

(If n8n runs in the cloud, expose the API with `ngrok http 8000`.)

## Architecture

```
PDF → slide text → 5 student agents (parallel) → per-slide JSON
     {confusion 0-5, trigger, reason, question}
   → advisor agent → top 3 fixes + student pre-reading pack
   → Streamlit heatmap  |  FastAPI → n8n → email
```

## Next steps

- Calibrate personas against real in-class "I'm lost" signals (predict → measure → calibrate)
- Read slide images with a vision model, not only text
- ElevenLabs: each virtual student asks its question out loud
