"""ClassTwin demo UI.  Run:  streamlit run app.py"""
import plotly.graph_objects as go
import streamlit as st

import core4 as core

st.set_page_config(page_title="ClassTwin", page_icon="🎓", layout="wide")
st.title("🎓 ClassTwin")
st.caption("Virtual students read your slides before class, so you hear their questions before your real students do.")

if core.use_mock():
    st.info("Running in **mock mode** (no API key set). Set ANTHROPIC_API_KEY for real AI analysis with Claude.")

else:
    st.success(f"Live AI analysis with **{'Claude' if core.provider() == 'claude' else 'OpenAI'}**.")

up = st.file_uploader("Upload lecture slides (PDF)", type="pdf")
if up and st.button("Run pre-check", type="primary"):
    status = st.status("Virtual students are reading your slides…", expanded=True)
    report = core.analyze(up.getvalue(), progress=lambda n: status.write(f"✅ {n} finished reading"))
    status.update(label="Done", state="complete", expanded=False)
    st.session_state.report, st.session_state.title = report, up.name

report = st.session_state.get("report")
if not report:
    st.stop()

personas, results = report["personas"], report["results"]
n = len(report["pages"])

# --- heatmap
z = [[r["confusion"] for r in results[p["id"]]] for p in personas]
hover = [[f"{p['name']} · slide {r['page']}<br>{r['reason'] or 'Fine'}" for r in results[p["id"]]] for p in personas]
fig = go.Figure(go.Heatmap(
    z=z, x=[f"S{i}" for i in range(1, n + 1)],
    y=[f"{p['name']} ({p['label']})" for p in personas],
    zmin=0, zmax=5, colorscale=[[0, "#e8f5e9"], [0.4, "#fff3c4"], [1, "#d32f2f"]],
    text=hover, hoverinfo="text", colorbar=dict(title="Confusion"),
))
fig.update_layout(height=320, margin=dict(l=10, r=10, t=30, b=10), title="Predicted confusion per slide")
st.plotly_chart(fig, use_container_width=True)

# --- top fixes + pack
c1, c2 = st.columns(2)
with c1:
    st.subheader("🛠️ Top 3 fixes for the lecturer")
    for f in report["advisor"].get("top_fixes", []):
        with st.container(border=True):
            st.markdown(f"**Slide {f.get('page')}** — {f.get('issue')}")
            st.markdown(f"*Fix:* {f.get('fix')}")
            st.caption("Likely to lose: " + ", ".join(f.get("affected", [])))
with c2:
    st.subheader("📘 Student pre-reading pack")
    st.html(core.student_pack_html(report, st.session_state.title))

# --- drill into a slide
st.subheader("🙋 What would the students ask?")
page = st.slider("Slide", 1, n, max(range(1, n + 1), key=lambda i: sum(results[p["id"]][i-1]["confusion"] for p in personas)))
st.caption(report["pages"][page - 1][:400])
for p in personas:
    r = results[p["id"]][page - 1]
    if r["confusion"] >= 2:
        st.markdown(f"**{p['name']}** ({p['label']}, confusion {r['confusion']}/5): “{r['question']}”  \n"
                    f"<small>{r['reason']}</small>", unsafe_allow_html=True)
if all(results[p["id"]][page - 1]["confusion"] < 2 for p in personas):
    st.success("No one is lost on this slide.")

st.download_button("Download lecturer email (HTML)", core.lecturer_email_html(report, st.session_state.title),
                   file_name="classtwin_lecturer.html")
