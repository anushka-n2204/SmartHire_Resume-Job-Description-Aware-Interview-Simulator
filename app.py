import streamlit as st
import PyPDF2
import docx
import pandas as pd
from interview_engine import InterviewEngine

# Wide layout for better scannability
st.set_page_config(
    page_title="AI-Driven Resume-Based Interview Platform",
    layout="wide"
)

# --- UI Styling with Visible Fixed Footer ---
st.markdown("""
<style>
.main { background-color: #fcfcfc; padding-bottom: 80px; }
.stButton>button {
    width: 100%;
    border-radius: 5px;
    height: 3em;
    background-color: #007bff;
    color: white;
    border: none;
    transition: 0.3s;
}
.stButton>button:hover { background-color: #0056b3; }

.footer {
    position: fixed;
    left: 0;
    bottom: 0;
    width: 100%;
    background-color: #ffffff;
    color: #444;
    text-align: center;
    padding: 15px 0;
    font-size: 14px;
    border-top: 1px solid #eaeaea;
    z-index: 1000;
    box-shadow: 0 -2px 10px rgba(0,0,0,0.05);
}
.footer a {
    color: #007bff;
    text-decoration: none;
    margin: 0 10px;
    font-weight: 500;
}
.footer a:hover { text-decoration: underline; }
</style>

<div class="footer">
    <span>🔒 <b>Privacy:</b> All data is processed locally and not stored.</span>
    <a href="mailto:support@smarthire.ai">📧 Contact Support</a>
    <a href="https://www.linkedin.com/in/nayakanushkapriyani/" target="_blank">🔗 LinkedIn</a>
    <a href="https://github.com/anushka-n2204" target="_blank">💻 GitHub</a>
</div>
""", unsafe_allow_html=True)

st.title("🎙️ SmartHire — Resume & Job-Description Aware Interview Simulator")
st.caption(
    "Simulates real technical interviews and evaluates your readiness using your resume and job description"
)

# ---------- Resume extraction ----------
def extract_resume_text(uploaded_file):
    if uploaded_file.type == "application/pdf":
        reader = PyPDF2.PdfReader(uploaded_file)
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = docx.Document(uploaded_file)
        return "\n".join(p.text for p in doc.paragraphs)

    return ""

# ---------- Session State ----------
if "engine" not in st.session_state:
    st.session_state.engine = None
    st.session_state.question = None
    st.session_state.answer = ""
    st.session_state.comment = None
    st.session_state.can_proceed = False
    st.session_state.finished = False

# ---------- Sidebar ----------
with st.sidebar:
    st.header("📋 Interview Setup")
    resume_file = st.file_uploader("Upload Resume", type=["pdf", "docx"])
    jd_input = st.text_area(
        "Job Description / Role Title",
        height=200,
        placeholder="e.g. Backend Developer, SDE, or full job description"
    )

    if st.button("🚀 Start Simulation"):
        if resume_file and jd_input:
            resume_text = extract_resume_text(resume_file)
            engine = InterviewEngine(resume_text, jd_input)

            jd_valid, jd_error = engine.validate_jd()
            if not jd_valid:
                st.error(jd_error)
            else:
                st.session_state.engine = engine
                st.session_state.question = engine.next_question()
                st.session_state.answer = ""
                st.session_state.comment = None
                st.session_state.can_proceed = False
                st.session_state.finished = False
        else:
            st.warning("Resume and Job Description are required.")

# ---------- INTERVIEW MODE ----------
if st.session_state.engine and not st.session_state.finished:
    idx = st.session_state.engine.question_index
    TOTAL_Q = 3

    st.write(f"### Question {idx} of {TOTAL_Q}")
    st.progress(idx / TOTAL_Q)

    st.info(st.session_state.question)

    st.session_state.answer = st.text_area(
        "Your Response",
        value=st.session_state.answer,
        height=200
    )

    if st.button("Submit Answer"):
        result = st.session_state.engine.evaluate_answer(st.session_state.answer)
        st.session_state.comment = result["comment"]
        st.session_state.can_proceed = result["valid"]

    if st.session_state.comment:
        if st.session_state.can_proceed:
            st.success(st.session_state.comment)

            is_last = idx >= TOTAL_Q
            btn_label = "📊 Get Report" if is_last else "Next Question ➡️"

            if st.button(btn_label):
                if is_last:
                    st.session_state.finished = True
                    st.rerun()
                else:
                    st.session_state.answer = ""
                    st.session_state.comment = None
                    st.session_state.can_proceed = False
                    st.session_state.question = st.session_state.engine.next_question()
                    st.rerun()
        else:
            st.error(st.session_state.comment)

# ---------- FINAL REPORT ----------
elif st.session_state.finished:
    score, report, strengths, weaknesses = st.session_state.engine.final_report()

    st.header("📊 Performance Analysis")

    col_met, col_btn = st.columns([3, 1])
    col_met.metric("Interview Readiness Score", f"{score} / 100")

    csv = pd.DataFrame(report.items(), columns=["Metric", "Score"]).to_csv(index=False)
    col_btn.download_button(
        "📥 Export CSV Report",
        csv,
        "interview_report.csv",
        "text/csv"
    )

    st.divider()

    # Skill Match Table
    st.subheader("🔍 Skill Match Overview")
    jd_sk = set(st.session_state.engine.jd_skills)
    res_sk = set(st.session_state.engine.resume_skills)

    skill_rows = [
        {"Skill": s.title(), "Status": "✅ Found" if s in res_sk else "❌ Missing"}
        for s in jd_sk
    ]
    st.table(skill_rows)

    st.divider()

    # Metric Bars
    st.subheader("📈 Competency Breakdown")
    cols = st.columns(2)
    for i, (metric, value) in enumerate(report.items()):
        with cols[i % 2]:
            st.write(metric.replace("_", " ").title())
            st.progress(value)

    st.divider()

    l, r = st.columns(2)
    with l:
        st.subheader("🌟 Strengths")
        for s in strengths:
            st.success(s.replace("_", " ").title())

    with r:
        st.subheader("💡 Improvements")
        for w in weaknesses:
            st.warning(w.replace("_", " ").title())

    if st.button("🔄 Restart"):
        st.session_state.clear()
        st.rerun()

# ---------- LANDING STATE ----------
else:
    st.subheader("Getting Started")
    st.markdown("""
    1. **Upload your resume**  
    2. **Provide a job description or role title**  
    3. **Complete a 3-step interview and receive a readiness report**
    """)
    st.caption("⏱️ Takes less than 5 minutes to complete")
    st.info("👈 Use the sidebar to upload your resume and start the interview.")
