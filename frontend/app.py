"""
app.py — AI-Powered Career Guidance System (Streamlit frontend)

Architecture (per Task 8 decisions):
    - Career recommendation : Likhitha's XGBoost model, via predictor.py
    - Skill gap analysis     : CSV lookup (career_skill_gap.csv), via recommender.py
    - Learning roadmap       : CSV lookup (career_learning_path.csv), via recommender.py
                                (Rithik's roadmap_generation module is OUT OF SCOPE
                                 for this submission per team decision)
    - AI explanations        : OpenRouter, via gemini.py
    - AI Career Assistant    : interactive chat (mentor requirement), reuses the
                                same OpenRouter call via gemini.py

Note on structure: results are computed once on button click and stored in
st.session_state, then rendered from session state on every rerun. This keeps
the results (and the PDF button) visible while the user interacts with the
chat assistant — Streamlit reruns the whole script on every interaction, so
anything rendered only inside `if st.button(...)` would vanish on the next
interaction.

Run locally:  streamlit run app.py
Deploy:       Streamlit Community Cloud (see deployment task for steps)
"""

import re
import textwrap

import streamlit as st
from fpdf import FPDF

from predictor import get_predictor, ModelNotLoadedError
from recommender import get_skill_gap, get_learning_path
from gemini import get_career_recommendation, GenAIUnavailableError
from prompts import SYSTEM_PROMPT

def _safe(text):
    """fpdf2's built-in font only supports latin-1 — strip/replace anything
    outside that range (emojis, smart quotes from GenAI output, etc.)."""
    return str(text).encode("latin-1", "replace").decode("latin-1")


def _write(pdf, text, width_chars=85):
    """Write text to the PDF, wrapping it ourselves with Python's textwrap
    and rendering it line-by-line with cell(). This deliberately avoids
    fpdf2's own internal word-wrap (multi_cell), which has a known fragile
    edge case ('Not enough horizontal space to render a single character')
    that's hard to predict from the data alone. Wrapping manually first
    guarantees every line handed to fpdf2 is short and safe."""
    text = _safe(text)
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            pdf.ln(3)
            continue
        wrapped_lines = textwrap.wrap(paragraph, width=width_chars) or [""]
        for line in wrapped_lines:
            pdf.cell(0, 6, line, ln=True)


def generate_pdf_report(name, profile, top3, skill_gap, learning_path, explanation):
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "AI-Powered Career Guidance Report", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    _write(pdf, f"Generated for: {name or 'Student'}")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Profile Summary", ln=True)
    pdf.set_font("Helvetica", "", 10)
    _write(pdf, f"Age: {profile['age']}  |  Gender: {profile['gender']}  |  "
                 f"Degree: {profile['degree_level']} in {profile['field_of_study']}")
    _write(pdf, f"GPA: {profile['gpa']}  |  Years of Experience: {profile['years_experience']}")
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Top 3 Career Recommendations", ln=True)
    pdf.set_font("Helvetica", "", 10)
    for i, item in enumerate(top3, 1):
        _write(pdf, f"{i}. {item['career']}  (confidence: {item['confidence']:.0%})")
    pdf.ln(2)

    if skill_gap:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Skill Gap Analysis", ln=True)
        pdf.set_font("Helvetica", "", 10)
        _write(pdf, f"Current Skills: {skill_gap['current']}")
        _write(pdf, f"Required Skills: {skill_gap['required']}")
        _write(pdf, f"Gap: {skill_gap['gap']}%")
        _write(pdf, f"Estimated Hours: {skill_gap['hours']}")
        _write(pdf, f"Recommended Courses: {skill_gap['courses']}")
        pdf.ln(2)

    if learning_path:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Learning Roadmap", ln=True)
        pdf.set_font("Helvetica", "", 10)
        _write(pdf, f"Learning Stage: {learning_path['stage']}")
        _write(pdf, f"Priority Skills: {learning_path['skills']}")
        _write(pdf, f"Learning Path: {learning_path['path']}")
        _write(pdf, f"Resources: {learning_path['resources']}")
        _write(pdf, f"Estimated Duration: {learning_path['duration']}")
        _write(pdf, f"Milestone: {learning_path['milestone']}")
        pdf.ln(2)

    if explanation:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "AI Career Guidance", ln=True)
        pdf.set_font("Helvetica", "", 10)
        _write(pdf, explanation)

    return bytes(pdf.output())


def build_chat_prompt(question, ctx, history):
    """Build a prompt for the AI Career Assistant that carries the student's
    profile, the ML recommendations, and recent chat turns, so answers stay
    personalized and on-topic. Reuses the same OpenRouter call as the main
    explanation (gemini.get_career_recommendation)."""
    top3 = ctx["top3"]
    profile = ctx["profile"]

    history_text = ""
    for role, msg in history[-6:]:  # keep the prompt small: last 6 turns only
        speaker = "Student" if role == "user" else "Assistant"
        history_text += f"{speaker}: {msg}\n"

    return f"""{SYSTEM_PROMPT}

You are now acting as an interactive AI Career Assistant in a chat.
Answer the student's question below. Be helpful, specific and concise
(under 250 words). Stay on career guidance topics; if asked something
unrelated, politely steer back to career guidance.

Student profile:
Name: {ctx['name'] or "Student"}
Degree: {profile['degree_level']} in {profile['field_of_study']}
GPA: {profile['gpa']}  |  Experience: {profile['years_experience']} years
Interests: {ctx['interests'] or "Not specified"}
Preferred Industry: {ctx['preferred_industry'] or "Not specified"}

ML Model's Top 3 Recommendations:
1. {top3[0]['career']} (confidence: {top3[0]['confidence']:.0%})
2. {top3[1]['career']} (confidence: {top3[1]['confidence']:.0%})
3. {top3[2]['career']} (confidence: {top3[2]['confidence']:.0%})

Recent conversation:
{history_text}
Student's question: {question}
"""


st.set_page_config(
    page_title="Career Guidance AI",
    page_icon="🎓",
    layout="centered",
)


# --- Load model once per session (not on every rerun) -----------------------
@st.cache_resource
def load_predictor():
    return get_predictor()


predictor = load_predictor()

st.title("🎓 AI-Powered Career Guidance System")
st.write("Get personalized Top-3 career recommendations, a skill gap analysis, "
         "and a learning roadmap — powered by machine learning and AI.")

if not predictor.is_ready:
    st.error(
        "⚠️ Career prediction model is not available.\n\n"
        f"{predictor.load_error}"
    )
    st.info(
        "This app cannot generate recommendations until the model files are in place. "
        "Contact the ML team (Likhitha) if you're seeing this during development."
    )
    st.stop()  # halt here — no point rendering the form if predictions can't run


# --- Input form ---------------------------------------------------------------
st.header("Your Profile")

col1, col2 = st.columns(2)
with col1:
    name = st.text_input("Your Name")
    age = st.number_input("Age", min_value=16, max_value=45, value=21)
    gender = st.selectbox("Gender", ["Male", "Female"])
    degree_level = st.selectbox("Degree Level", ["Bachelor", "Master", "PhD"])
with col2:
    field_of_study = st.selectbox(
        "Field of Study",
        ["AI", "Computer Science", "Cybersecurity", "Data Science",
         "Software Engineering"],
    )
    gpa = st.slider("GPA (out of 10)", min_value=0.0, max_value=10.0, value=7.5, step=0.1)
    years_experience = st.number_input(
        "Years of Experience", min_value=0.0, max_value=15.0, value=0.0, step=0.5
    )

st.caption(
    "Degree Level is limited to values the model was trained on "
    "(Bachelor / Master / PhD). If your team decides to support Diploma or "
    "High School applicants, the model needs retraining on data that includes them first."
    " Field of Study currently supports technology-related fields only; other "
    "backgrounds (e.g. Economics, Statistics, Mathematics, Operations Research) "
       "would also need model retraining."
)

st.subheader("Technical & Soft Skills")
st.caption("Rate yourself from 1 (beginner) to 5 (expert) for each skill.")

with st.expander("Technical Skills", expanded=True):
    tcol1, tcol2 = st.columns(2)
    with tcol1:
        python = st.slider("Python", 1, 5, 1)
        java = st.slider("Java", 1, 5, 1)
        c_cpp = st.slider("C / C++", 1, 5, 1)
        sql = st.slider("SQL", 1, 5, 1)
        machine_learning = st.slider("Machine Learning", 1, 5, 1)
        data_analysis = st.slider("Data Analysis", 1, 5, 1)
    with tcol2:
        cloud_computing = st.slider("Cloud Computing", 1, 5, 1)
        cybersecurity = st.slider("Cybersecurity", 1, 5, 1)
        web_development = st.slider("Web Development", 1, 5, 1)
        devops = st.slider("DevOps", 1, 5, 1)
        networking = st.slider("Networking", 1, 5, 1)

with st.expander("Soft Skills", expanded=False):
    scol1, scol2 = st.columns(2)
    with scol1:
        communication = st.slider("Communication", 1, 5, 1)
        leadership = st.slider("Leadership", 1, 5, 1)
        problem_solving = st.slider("Problem Solving", 1, 5, 1)
    with scol2:
        teamwork = st.slider("Teamwork", 1, 5, 1)
        adaptability = st.slider("Adaptability", 1, 5, 1)

# Free-text context — NOT fed to the ML model (it wasn't trained on free text),
# but genuinely useful as extra context for the GenAI explanation step.
st.subheader("Additional Context (optional)")
interests = st.text_area(
    "Interests", placeholder="e.g. AI research, product design, cloud infrastructure..."
)
preferred_industry = st.text_input(
    "Preferred Industry", placeholder="e.g. Technology, Healthcare, Finance..."
)


# --- Prediction ----------------------------------------------------------------
# Results are computed ONCE here and stored in session state; they are rendered
# further below (outside this block) so they survive Streamlit reruns caused by
# chat input / PDF download clicks.
if st.button("Get Career Recommendation", type="primary"):

    profile = {
        "age": age,
        "gender": gender,
        "degree_level": degree_level,
        "field_of_study": field_of_study,
        "gpa": gpa,
        "years_experience": years_experience,
        "python": python,
        "java": java,
        "c_cpp": c_cpp,
        "sql": sql,
        "machine_learning": machine_learning,
        "data_analysis": data_analysis,
        "cloud_computing": cloud_computing,
        "cybersecurity": cybersecurity,
        "web_development": web_development,
        "devops": devops,
        "networking": networking,
        "communication": communication,
        "leadership": leadership,
        "problem_solving": problem_solving,
        "teamwork": teamwork,
        "adaptability": adaptability,
    }

    # --- Step 1: ML-based Top-3 recommendation ---
    try:
        with st.spinner("Analyzing your profile..."):
            top3 = predictor.predict_top3(profile)
    except ModelNotLoadedError as e:
        st.error(f"Model unavailable: {e}")
        st.stop()
    except ValueError as e:
        st.error(f"Could not process your profile: {e}")
        st.stop()

    top_career = top3[0]["career"]

    # --- Step 2: Skill gap + roadmap (CSV lookup, keyed on top predicted career) ---
    skill_gap = get_skill_gap(top_career)
    learning_path = get_learning_path(top_career)

    # --- Step 3: GenAI explanation (called once, stored; not re-called on reruns) ---
    prompt = f"""{SYSTEM_PROMPT}

Name: {name or "Student"}
Age: {age}
Gender: {gender}
Degree: {degree_level} in {field_of_study}
GPA: {gpa}
Years of Experience: {years_experience}
Interests: {interests or "Not specified"}
Preferred Industry: {preferred_industry or "Not specified"}

ML Model's Top 3 Recommendations:
1. {top3[0]['career']} (confidence: {top3[0]['confidence']:.0%})
2. {top3[1]['career']} (confidence: {top3[1]['confidence']:.0%})
3. {top3[2]['career']} (confidence: {top3[2]['confidence']:.0%})
"""

    explanation_text = None
    explanation_error = None
    try:
        with st.spinner("Generating personalized explanation..."):
            explanation_text = get_career_recommendation(prompt)
    except GenAIUnavailableError as e:
        explanation_error = str(e)

    # --- Store everything for rendering + chat context ---
    st.session_state["ctx"] = {
        "name": name,
        "profile": profile,
        "top3": top3,
        "top_career": top_career,
        "skill_gap": skill_gap,
        "learning_path": learning_path,
        "explanation_text": explanation_text,
        "explanation_error": explanation_error,
        "interests": interests,
        "preferred_industry": preferred_industry,
    }
    # New recommendation = fresh chat (old answers may not match the new profile)
    st.session_state["chat_history"] = []


# --- Results (rendered from session state so they survive reruns) --------------
if "ctx" in st.session_state:
    ctx = st.session_state["ctx"]
    top3 = ctx["top3"]
    top_career = ctx["top_career"]
    skill_gap = ctx["skill_gap"]
    learning_path = ctx["learning_path"]

    st.success("Recommendation Ready!")
    st.subheader("📌 Top 3 Career Recommendations")
    medals = ["🥇", "🥈", "🥉"]
    for medal, item in zip(medals, top3):
        st.write(f"{medal} **{item['career']}** — confidence: {item['confidence']:.0%}")

    if skill_gap:
        st.subheader("📊 Skill Gap Analysis")
        st.write("**Current Skills:**", skill_gap["current"])
        st.write("**Required Skills:**", skill_gap["required"])
        st.write("**Gap Percentage:**", f'{skill_gap["gap"]}%')
        st.write("**Estimated Hours:**", skill_gap["hours"])
        st.write("**Recommended Courses:**", skill_gap["courses"])
    else:
        st.info(
            f"No skill gap data found for '{top_career}'. This can happen if the "
            f"career label from the ML model doesn't exactly match a label in "
            f"career_skill_gap.csv — worth checking during testing."
        )

    if learning_path:
        st.subheader("📚 Learning Roadmap")
        st.write("**Learning Stage:**", learning_path["stage"])
        st.write("**Priority Skills:**", learning_path["skills"])
        st.write("**Learning Path:**", learning_path["path"])
        st.write("**Resources:**", learning_path["resources"])
        st.write("**Estimated Duration:**", learning_path["duration"])
        st.write("**Milestone:**", learning_path["milestone"])
    else:
        st.info(
            f"No roadmap data found for '{top_career}'. Same likely cause as above — "
            f"label mismatch between datasets."
        )

    st.subheader("🤖 AI Career Guidance")
    if ctx["explanation_text"]:
        st.write(ctx["explanation_text"])
    else:
        st.warning(
            "The AI explanation service is temporarily unavailable, but your "
            "ML-based recommendations above are still valid."
        )
        if ctx["explanation_error"]:
            st.caption(f"Technical detail: {ctx['explanation_error']}")

    # --- PDF report download ---
    st.divider()
    try:
        pdf_bytes = generate_pdf_report(
            ctx["name"], ctx["profile"], top3, skill_gap,
            learning_path, ctx["explanation_text"],
        )
        st.download_button(
            label="📄 Download PDF Report",
            data=pdf_bytes,
            file_name=f"career_report_{(ctx['name'] or 'student').replace(' ', '_')}.pdf",
            mime="application/pdf",
        )
    except Exception as e:
        st.caption(f"PDF generation failed: {e}")

    # --- AI Career Assistant (interactive chat — mentor requirement) -----------
    st.divider()
    st.subheader("💬 AI Career Assistant")
    st.caption(
        "Ask follow-up questions about your recommended careers, skills, "
        "courses, certifications, or how to get started."
    )

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    # Render existing conversation
    for role, msg in st.session_state["chat_history"]:
        with st.chat_message(role):
            st.write(msg)

    question = st.chat_input("e.g. What certifications should I do first?")
    if question:
        st.session_state["chat_history"].append(("user", question))
        with st.chat_message("user"):
            st.write(question)

        try:
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    answer = get_career_recommendation(
                        build_chat_prompt(
                            question, ctx, st.session_state["chat_history"]
                        )
                    )
                st.write(answer)
            st.session_state["chat_history"].append(("assistant", answer))
        except GenAIUnavailableError:
            with st.chat_message("assistant"):
                st.warning(
                    "The AI assistant is temporarily unavailable. Please try "
                    "again in a moment — your recommendations above are unaffected."
                )
