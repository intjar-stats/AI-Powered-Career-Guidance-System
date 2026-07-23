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
    - Dashboard layout       : metric cards + charts + tabs (mentor requirement,
                                inspired by a reference dashboard). No login/storage
                                is added — this is a presentation-layer upgrade only,
                                keeping the no-data-stored privacy design intact.

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
import math
import io

import streamlit as st
import pandas as pd
import altair as alt
from fpdf import FPDF
from pypdf import PdfReader


def colorful_bar_chart(df, cat_col, val_col, horizontal=False, color_scheme="category10"):
    """Render a bar chart with a distinct color per bar (Altair) using a
    multi-hue categorical scheme (blue/orange/green/red/purple...) instead of
    Streamlit's native st.bar_chart, which renders every bar in one flat color."""
    if horizontal:
        chart = (
            alt.Chart(df)
            .mark_bar()
            .encode(
                x=alt.X(f"{val_col}:Q", title=val_col),
                y=alt.Y(f"{cat_col}:N", sort="-x", title=None),
                color=alt.Color(f"{cat_col}:N", legend=None,
                                 scale=alt.Scale(scheme=color_scheme)),
                tooltip=[cat_col, val_col],
            )
        )
    else:
        chart = (
            alt.Chart(df)
            .mark_bar()
            .encode(
                x=alt.X(f"{cat_col}:N", sort=None, title=None),
                y=alt.Y(f"{val_col}:Q", title=val_col),
                color=alt.Color(f"{cat_col}:N", legend=None,
                                 scale=alt.Scale(scheme=color_scheme)),
                tooltip=[cat_col, val_col],
            )
        )
    st.altair_chart(chart, use_container_width=True)


def colorful_donut_chart(df, cat_col, val_col, color_scheme="category10"):
    """Render a donut chart (Altair arc mark) with a distinct color per slice."""
    chart = (
        alt.Chart(df)
        .mark_arc(innerRadius=55)
        .encode(
            theta=alt.Theta(f"{val_col}:Q"),
            color=alt.Color(f"{cat_col}:N", legend=alt.Legend(title=None, orient="bottom"),
                             scale=alt.Scale(scheme=color_scheme)),
            tooltip=[cat_col, val_col],
        )
    )
    st.altair_chart(chart, use_container_width=True)


def skill_rating_histogram(self_ratings: dict):
    """Bar-style histogram of how many skills fall at each rating (1-5),
    colored red (low) to green (high) so the color itself carries meaning."""
    counts = {i: 0 for i in range(1, 6)}
    for v in self_ratings.values():
        counts[v] = counts.get(v, 0) + 1
    hist_df = pd.DataFrame(
        {"Rating": list(counts.keys()), "Number of Skills": list(counts.values())}
    )
    chart = (
        alt.Chart(hist_df)
        .mark_bar()
        .encode(
            x=alt.X("Rating:O", title="Self-Rated Level (1=Beginner, 5=Expert)"),
            y=alt.Y("Number of Skills:Q", title="Number of Skills"),
            color=alt.Color(
                "Rating:O", legend=None,
                scale=alt.Scale(
                    domain=[1, 2, 3, 4, 5],
                    range=["#D62728", "#FF7F0E", "#F2C744", "#8FCE00", "#2CA02C"],
                ),
            ),
            tooltip=["Rating", "Number of Skills"],
        )
    )
    st.altair_chart(chart, use_container_width=True)

from predictor import get_predictor, ModelNotLoadedError
from recommender import compute_skill_gap, get_learning_path
from gemini import get_career_recommendation, GenAIUnavailableError
from prompts import SYSTEM_PROMPT

_UNICODE_REPLACEMENTS = {
    "\u2018": "'", "\u2019": "'",     # curly single quotes
    "\u201c": '"', "\u201d": '"',     # curly double quotes
    "\u2013": "-", "\u2014": "-",     # en dash, em dash
    "\u2026": "...",                   # ellipsis
    "\u2022": "-",                     # bullet
}


def _safe(text):
    """fpdf2's built-in font only supports latin-1. Common "smart" punctuation
    from the AI's output (curly quotes, dashes, ellipsis, bullets) is
    converted to a plain-ASCII equivalent first; anything else outside
    latin-1 (emoji, etc.) is then dropped rather than shown as a stray '?',
    which looked messy in the printed report."""
    text = str(text)
    for uni_char, ascii_equiv in _UNICODE_REPLACEMENTS.items():
        text = text.replace(uni_char, ascii_equiv)
    return text.encode("latin-1", "ignore").decode("latin-1")


def _wrap_by_width(pdf, text, max_width):
    """Wraps text into lines that actually fit within max_width (mm), using
    fpdf2's own get_string_width() to measure real rendered width for the
    current font — this is far more reliable than guessing a wrap point
    from a fixed character count, which doesn't account for proportional
    font metrics ('W' is much wider than 'i') and was cutting text off when
    used inside the narrower card layout, where the guess no longer matched
    the actually-available width."""
    words = text.split(" ")
    lines = []
    current = ""
    for word in words:
        candidate = (current + " " + word).strip()
        if not current or pdf.get_string_width(candidate) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def _write(pdf, text, width_chars=None):
    """Write text to the PDF, wrapped by actual rendered width (see
    _wrap_by_width) rather than a fixed character-count guess, and rendered
    line-by-line with cell(). This deliberately avoids fpdf2's own internal
    word-wrap (multi_cell), which has a known fragile edge case ('Not
    enough horizontal space to render a single character') that's hard to
    predict from the data alone. width_chars is kept as an accepted
    (now unused) parameter so existing call sites don't need to change."""
    text = _safe(text)
    base_x = pdf.l_margin
    max_width = pdf.w - base_x - pdf.r_margin
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            pdf.ln(3)
            continue
        for line in _wrap_by_width(pdf, paragraph, max_width):
            pdf.set_x(base_x)
            pdf.cell(0, 6, line, ln=True)


def _ensure_space(pdf, needed_height):
    """Add a new page if there isn't enough room left for the next chart.
    fpdf2 only checks for page breaks automatically inside cell()/multi_cell()
    — rect()-based chart drawing doesn't trigger it, so charts near a page
    bottom could otherwise get cut off. Computed from pdf.h/pdf.b_margin
    directly (stable fpdf2 attributes) rather than an internal-only name."""
    bottom_limit = pdf.h - pdf.b_margin
    if pdf.get_y() + needed_height > bottom_limit:
        pdf.add_page()


def _draw_donut_chart_pdf(pdf, slices, cx, cy, outer_r=20, inner_r=10, start_angle_deg=-90):
    """Draws a donut chart as filled polygon 'ring segments' — fpdf2 has no
    built-in pie/donut primitive, so each slice is approximated as a many-
    sided polygon tracing the outer arc then back along the inner arc. This
    only relies on set_fill_color()/polygon(), both simple and stable, so it
    avoids depending on fpdf2's newer/less-common arc-drawing API.
    slices: list of (label, value, (r,g,b)). Returns the total value (for
    computing percentages in the legend)."""
    total = sum(v for _, v, _ in slices) or 1
    angle = start_angle_deg
    steps = 48  # curve smoothness
    for _, value, color in slices:
        sweep = 360 * (value / total)
        a0, a1 = math.radians(angle), math.radians(angle + sweep)
        pts = []
        for i in range(steps + 1):
            a = a0 + (a1 - a0) * i / steps
            pts.append((cx + outer_r * math.cos(a), cy + outer_r * math.sin(a)))
        for i in range(steps + 1):
            a = a1 - (a1 - a0) * i / steps
            pts.append((cx + inner_r * math.cos(a), cy + inner_r * math.sin(a)))
        pdf.set_fill_color(*color)
        pdf.polygon(pts, style="F")
        angle += sweep
    return total


def _draw_donut_legend_pdf(pdf, slices, x, y, total, row_height=5):
    """Color-swatch + percentage legend under a donut chart (fpdf2 can't put
    text directly on curved slices), so this is how the '% per color' is shown."""
    pdf.set_font("Helvetica", "", 8)
    for i, (label, value, color) in enumerate(slices):
        pct = (value / total) * 100
        row_y = y + i * row_height
        pdf.set_fill_color(*color)
        pdf.rect(x, row_y + 1, 3, 3, style="F")
        pdf.set_xy(x + 5, row_y)
        pdf.cell(0, row_height, f"{_safe(label)[:26]}: {pct:.0f}%")
    pdf.set_y(y + len(slices) * row_height + 3)


def _draw_skills_chart_pdf(pdf, profile, x=15, width=80, chart_height=28, pad=6):
    """Draws a vertical bar chart of self-rated key skills (1-5), using the
    same color-per-skill scheme as the live app for visual consistency."""
    skills = [
        ("Python", profile["python"], (214, 39, 40)),                      # red
        ("Machine Learning", profile["machine_learning"], (44, 160, 44)),  # green
        ("SQL", profile["sql"], (148, 103, 189)),                          # purple
        ("Cloud Computing", profile["cloud_computing"], (31, 119, 180)),   # blue
        ("Data Analysis", profile["data_analysis"], (255, 127, 14)),       # orange
    ]
    y = pdf.get_y() + 5  # room for value labels above bars
    slot_width = width / len(skills)
    bar_width = max(slot_width - pad, 3)
    pdf.set_font("Helvetica", "", 6)
    for i, (label, rating, color) in enumerate(skills):
        bx = x + i * slot_width + pad / 2
        bar_h = (rating / 5) * chart_height
        pdf.set_fill_color(*color)
        pdf.rect(bx, y + (chart_height - bar_h), bar_width, max(bar_h, 1), style="F")
        pdf.set_xy(bx - 2, y + (chart_height - bar_h) - 4)
        pdf.cell(bar_width + 4, 4, str(rating), align="C")
        pdf.set_xy(bx - 4, y + chart_height + 1)
        pdf.cell(bar_width + 8, 4, label[:12], align="C")
    pdf.set_y(y + chart_height + 8)


def _draw_histogram_pdf(pdf, self_ratings, x=15, width=80, chart_height=28):
    """Bar-style histogram of how many skills fall at each rating (1-5),
    colored red (low) to green (high) — mirrors the app's Skill Rating
    Distribution chart."""
    counts = {i: 0 for i in range(1, 6)}
    for v in self_ratings.values():
        counts[v] = counts.get(v, 0) + 1
    colors = {1: (214, 39, 40), 2: (255, 127, 14), 3: (242, 199, 68),
              4: (143, 206, 0), 5: (44, 160, 44)}
    max_count = max(counts.values()) or 1
    y = pdf.get_y()
    slot_width = width / 5
    bar_width = max(slot_width - 6, 3)
    pdf.set_font("Helvetica", "", 6)
    for i, rating in enumerate(range(1, 6)):
        count = counts[rating]
        bx = x + i * slot_width + 3
        bar_h = (count / max_count) * chart_height
        pdf.set_fill_color(*colors[rating])
        pdf.rect(bx, y + (chart_height - bar_h), bar_width, max(bar_h, 1), style="F")
        pdf.set_xy(bx - 2, y + chart_height + 1)
        pdf.cell(bar_width + 4, 4, f"Lvl {rating}", align="C")
    pdf.set_font("Helvetica", "", 7)
    pdf.set_xy(x, y - 5)
    pdf.cell(width, 4, "Self-Rated Level (1=Beginner, 5=Expert)", align="L")
    pdf.set_y(y + chart_height + 6)


def _draw_overview_grid_pdf(pdf, top3, profile, skill_gap):
    """Draws a 2x2 visual grid mirroring the app's Overview tab: a career
    match donut, a skill ratings bar chart, a skill-rating histogram, and a
    skill-readiness donut — all natively drawn with fpdf2 (no PNG/image
    conversion needed, so no extra libraries or deployment risk)."""
    left_x, right_x, col_width = 15, 108, 80
    donut_colors = [(31, 119, 180), (255, 127, 14), (44, 160, 44), (214, 39, 40)]

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Visual Summary", ln=True)

    _ensure_space(pdf, 72)
    row1_y = pdf.get_y() + 2

    # --- Row 1, left: Career Match Breakdown (donut) ---
    slices = [(item["career"], item["confidence"], donut_colors[i % len(donut_colors)])
              for i, item in enumerate(top3)]
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_xy(left_x, row1_y)
    pdf.cell(col_width, 5, "Career Match Breakdown")
    donut_cy = row1_y + 6 + 20
    total = _draw_donut_chart_pdf(pdf, slices, left_x + col_width / 2, donut_cy,
                                   outer_r=20, inner_r=10)
    _draw_donut_legend_pdf(pdf, slices, left_x, donut_cy + 23, total)
    row1_left_bottom = pdf.get_y()

    # --- Row 1, right: Your Skill Ratings (bar chart) ---
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_xy(right_x, row1_y)
    pdf.cell(col_width, 5, "Your Skill Ratings")
    pdf.set_xy(right_x, row1_y + 6)
    _draw_skills_chart_pdf(pdf, profile, x=right_x, width=col_width, chart_height=28)
    row1_right_bottom = pdf.get_y()

    row2_y = max(row1_left_bottom, row1_right_bottom) + 6
    pdf.set_y(row2_y)
    _ensure_space(pdf, 60)
    row2_y = pdf.get_y()

    # --- Row 2, left: Skill Rating Distribution (histogram) ---
    self_ratings = {
        "Python": profile["python"], "Machine Learning": profile["machine_learning"],
        "SQL": profile["sql"], "Cloud Computing": profile["cloud_computing"],
        "Data Analysis": profile["data_analysis"],
    }
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_xy(left_x, row2_y)
    pdf.cell(col_width, 5, "Skill Rating Distribution")
    pdf.set_xy(left_x, row2_y + 11)
    _draw_histogram_pdf(pdf, self_ratings, x=left_x, width=col_width, chart_height=26)
    row2_left_bottom = pdf.get_y()

    # --- Row 2, right: Skill Readiness (donut) ---
    row2_right_bottom = row2_y
    if skill_gap:
        ready_pct = max(0, min(100, 100 - skill_gap["gap"]))
        readiness_slices = [
            ("Ready", ready_pct, (44, 160, 44)),
            ("To Learn", skill_gap["gap"], (255, 127, 14)),
        ]
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_xy(right_x, row2_y)
        pdf.cell(col_width, 5, "Skill Readiness")
        donut_cy2 = row2_y + 6 + 17
        total2 = _draw_donut_chart_pdf(pdf, readiness_slices, right_x + col_width / 2,
                                        donut_cy2, outer_r=17, inner_r=8)
        _draw_donut_legend_pdf(pdf, readiness_slices, right_x, donut_cy2 + 20, total2)
        row2_right_bottom = pdf.get_y()

    pdf.set_font("Helvetica", "", 10)
    pdf.set_y(max(row2_left_bottom, row2_right_bottom) + 4)


def _card_start(pdf, indent=6):
    """Begin a bordered 'card' section, mirroring the app's
    st.container(border=True) look. Temporarily indents the page's left/
    right margins so every normal _write()/_write_markdown() call inside
    naturally stays within the card — cell(0, ...) always measures its
    width against the current margins, so this needs no changes to those
    functions. Returns the state needed to close the card afterward."""
    y = pdf.get_y() + 2
    pdf.set_y(y)
    orig_l, orig_r = pdf.l_margin, pdf.r_margin
    start_page = pdf.page
    pdf.set_left_margin(orig_l + indent)
    pdf.set_right_margin(orig_r + indent)
    pdf.set_x(pdf.l_margin)
    return y, orig_l, orig_r, start_page


def _card_end(pdf, card_state, border_color=(210, 210, 218)):
    """Close a card section: restore the original margins, then draw a
    stroke-only rectangle around everything written since _card_start. This
    is done *after* the content on purpose — a hollow (unfilled) rect drawn
    afterward just adds an outline and doesn't cover the text inside it, so
    draw order doesn't matter here, only that we know the final height.
    If the card's content triggered a page break (long AI explanations
    sometimes do), the border is skipped rather than drawn broken/spanning
    two pages — the content itself still renders fine either way."""
    y_start, orig_l, orig_r, start_page = card_state
    y_end = pdf.get_y()
    same_page = (pdf.page == start_page)
    pdf.set_left_margin(orig_l)
    pdf.set_right_margin(orig_r)
    if same_page:
        box_w = pdf.w - orig_l - orig_r
        pdf.set_draw_color(*border_color)
        pdf.set_line_width(0.3)
        pdf.rect(orig_l, y_start - 3, box_w, (y_end - y_start) + 6, style="D")
        pdf.set_draw_color(0, 0, 0)
    pdf.set_x(orig_l)
    pdf.ln(8)


def _write_markdown(pdf, text, width_chars=None):
    """A lightweight markdown-to-PDF renderer for the AI-generated
    explanation text, which comes back with GitHub-style markdown
    (#/##/### headings, **bold**, - bullets, --- rules, | tables |). The
    app's st.write() renders this properly via Streamlit's own markdown
    engine; fpdf2 has no such engine, so this hand-rolls the common cases
    rather than dumping the raw # and ** characters as plain text.
    Deliberately cell()-based (not fpdf2's multi_cell/write auto-wrap,
    which has a known fragile edge case) — same manual-wrap approach as
    _write(), wrapped by actual rendered width (see _wrap_by_width) rather
    than a fixed character-count guess. width_chars is kept as an accepted
    (now unused) parameter so existing call sites don't need to change."""
    text = _safe(text)
    base_x = pdf.l_margin
    max_width = pdf.w - base_x - pdf.r_margin

    for raw_line in text.split("\n"):
        line = raw_line.strip()

        if not line:
            pdf.ln(2)
            continue

        # Horizontal rule: ---
        if re.fullmatch(r"-{3,}", line):
            pdf.ln(1)
            y = pdf.get_y()
            pdf.set_draw_color(210, 210, 210)
            pdf.line(base_x, y, pdf.w - pdf.r_margin, y)
            pdf.set_draw_color(0, 0, 0)
            pdf.ln(3)
            continue

        # Headings: #, ##, ### Heading text
        heading_match = re.match(r"^(#{1,4})\s+(.*)$", line)
        if heading_match:
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip("* ")
            size = {1: 13, 2: 12, 3: 11}.get(level, 10)
            pdf.set_font("Helvetica", "B", size)
            pdf.set_x(base_x)
            pdf.cell(0, 7, heading_text, ln=True)
            pdf.set_font("Helvetica", "", 10)
            continue

        # A line that is entirely bold: **Text** (a common LLM pattern for
        # short section labels like "**Match Confidence: 100%**")
        whole_bold = re.fullmatch(r"\*\*(.+?)\*\*:?", line)
        if whole_bold:
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_x(base_x)
            pdf.cell(0, 6, whole_bold.group(1), ln=True)
            pdf.set_font("Helvetica", "", 10)
            continue

        # Bullet lines: "- text" or "* text"
        bullet_match = re.match(r"^[-*]\s+(.*)$", line)
        if bullet_match:
            bullet_text = re.sub(r"\*\*(.+?)\*\*", r"\1", bullet_match.group(1))
            bullet_indent = 4
            for j, wline in enumerate(_wrap_by_width(pdf, bullet_text, max_width - bullet_indent - 3)):
                pdf.set_x(base_x + bullet_indent)
                pdf.cell(0, 6, ("-  " if j == 0 else "   ") + wline, ln=True)
            continue

        # Table rows: strip pipes; skip pure separator rows like |---|---|
        if line.startswith("|"):
            if re.fullmatch(r"\|[\s\-:|]+\|", line):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            row_text = "   ".join(c for c in cells if c)
            for wline in _wrap_by_width(pdf, row_text, max_width):
                pdf.set_x(base_x)
                pdf.cell(0, 6, wline, ln=True)
            continue

        # Regular paragraph line — strip any remaining inline **bold** markers
        # (rendering the enclosed text plain, since mixed bold/normal text
        # on one line needs fpdf2's flowing write() API, which _write() and
        # this function both deliberately avoid for stability)
        clean_line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
        for wline in _wrap_by_width(pdf, clean_line, max_width):
            pdf.set_x(base_x)
            pdf.cell(0, 6, wline, ln=True)


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
    pdf.ln(4)

    _draw_overview_grid_pdf(pdf, top3, profile, skill_gap)
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
        card = _card_start(pdf)
        _write(pdf, f"Learning Stage: {learning_path['stage']}", width_chars=76)
        _write(pdf, f"Priority Skills: {learning_path['skills']}", width_chars=76)
        _write(pdf, f"Learning Path: {learning_path['path']}", width_chars=76)
        _write(pdf, f"Resources: {learning_path['resources']}", width_chars=76)
        _write(pdf, f"Estimated Duration: {learning_path['duration']}", width_chars=76)
        _write(pdf, f"Milestone: {learning_path['milestone']}", width_chars=76)
        _card_end(pdf, card)

    if explanation:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "AI Career Guidance", ln=True)
        pdf.set_font("Helvetica", "", 10)
        card = _card_start(pdf)
        _write_markdown(pdf, explanation, width_chars=76)
        _card_end(pdf, card)

    return bytes(pdf.output())


def extract_resume_text(uploaded_file, max_chars=6000):
    """Extracts text from an uploaded PDF resume using pypdf (pure-Python,
    no system/OS-level dependencies — safe for Streamlit Cloud). Returns
    (text, error_message). Scanned/image-only PDFs have no extractable text
    layer, so that case is detected and reported clearly rather than
    silently returning an empty analysis."""
    try:
        reader = PdfReader(io.BytesIO(uploaded_file.read()))
        pages_text = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(pages_text).strip()
    except Exception as e:  # noqa: BLE001 — any parsing failure should be graceful
        return None, f"Could not read this PDF: {e}"

    if not text:
        return None, (
            "No selectable text found in this PDF — it may be a scanned "
            "image rather than a text-based document. Try exporting your "
            "resume directly from Word/Google Docs as a PDF instead."
        )
    return text[:max_chars], None


def build_resume_analysis_prompt(resume_text, ctx):
    """Builds a prompt asking the AI to evaluate the uploaded resume against
    the ML model's top recommended career, reusing the same OpenRouter call
    (gemini.get_career_recommendation) as the rest of the app."""
    top_career = ctx["top3"][0]["career"]
    return f"""{SYSTEM_PROMPT}

You are now analyzing a student's resume against their top ML-recommended
career match. Be specific and reference actual content from the resume,
not generic advice.

Top Recommended Career: {top_career} (confidence: {ctx['top3'][0]['confidence']:.0%})

Resume Text:
---
{resume_text}
---

Provide, with clear section headers:
1. **Match Score** — a percentage (0-100%) estimating how well this resume
   aligns with the "{top_career}" role, with one sentence explaining why.
2. **Key Strengths** — 2-4 bullet points on relevant strengths actually
   found in the resume.
3. **Gaps** — 2-4 bullet points on missing skills/experience typically
   expected for this role.
4. **Suggestions** — 3-4 concrete, actionable improvements to the resume.

Keep the entire response under 350 words.
"""


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

st.info(
    "**Welcome — let's map out your next career move.** 🎯 Fill in your "
    "profile and skills below, and get AI-matched career recommendations, "
    "a skill gap breakdown, a personalized learning roadmap, and a resume "
    "review 📄 in seconds — with an assistant 💬 on standby for anything "
    "else. 🔒 No login, no data stored: this session is yours alone."
)

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
    "Note: This system currently supports Bachelor / Master / PhD degree levels "
    "and technology-related fields of study only. Support for other degree levels "
    "(e.g. Diploma) and other backgrounds (e.g. Economics, Statistics, Mathematics, "
    "Operations Research) is planned as future work and would require model retraining. "
    "The Gender field is currently limited to the categories present in the training "
    "dataset (Male/Female); expanding this to be more inclusive is also planned as "
    "future work and would likewise require retraining on a more representative dataset."
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

    # --- Step 2: Skill gap (personalized, computed from the student's own
    # ratings) + roadmap (CSV lookup, keyed on top predicted career) ---
    skill_gap = compute_skill_gap(profile, top_career)
    learning_path = get_learning_path(top_career)

    # --- Step 3: GenAI explanation (called once, stored; not re-called on reruns) ---
    prompt = f"""{SYSTEM_PROMPT}

IMPORTANT: Do not restate or summarize the student's profile (name, age,
degree, GPA, experience) at the start of your response — it is already
shown separately in the report, right above where your response appears.
Start directly with the career recommendations.

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
    st.session_state["resume_result"] = None
    st.session_state["resume_error"] = None


# --- Results (rendered from session state so they survive reruns) --------------
if "ctx" in st.session_state:
    ctx = st.session_state["ctx"]
    top3 = ctx["top3"]
    top_career = ctx["top_career"]
    skill_gap = ctx["skill_gap"]
    learning_path = ctx["learning_path"]
    profile = ctx["profile"]

    st.success("Recommendation Ready!")

    # === Dashboard metric cards (mentor requirement — quick-glance summary) ===
    # Uses st.container(border=True) — a native Streamlit feature — for the
    # card look, rather than custom HTML/CSS, so it stays robust across
    # Streamlit versions. The top career's name is shown as wrapped caption
    # text below the number (not as a metric value), since long career names
    # get cut off inside st.metric's narrow value slot — that was today's bug.
    m1, m2, m3, m4 = st.columns(4)

    with m1:
        with st.container(border=True):
            st.markdown("🏆 **Top Match**")
            st.markdown(f"### {top3[0]['confidence']:.0%}")
            st.caption(top3[0]["career"])

    with m2:
        with st.container(border=True):
            st.markdown("📊 **Skill Gap**")
            st.markdown(f"### {skill_gap['gap']}%" if skill_gap else "### N/A")
            st.caption("Gap to close for your top match")

    with m3:
        with st.container(border=True):
            st.markdown("⏱️ **Est. Learning Time**")
            st.markdown(f"### {skill_gap['hours']} hrs" if skill_gap else "### N/A")
            st.caption("To close the skill gap")

    with m4:
        with st.container(border=True):
            st.markdown("🎯 **Matches Shown**")
            st.markdown(f"### {len(top3)}")
            st.caption("Careers recommended for you")

    st.divider()

    # Precompute both charts once — used in the Overview tab (side-by-side,
    # at-a-glance) and again in their respective detail tabs. Kept as plain
    # (non-indexed) DataFrames since Altair colors bars by column, not index.
    confidence_df = pd.DataFrame(
        {"Career": [item["career"] for item in top3],
         "Confidence (%)": [item["confidence"] * 100 for item in top3]}
    )

    self_ratings = {
        "Python": profile["python"], "Machine Learning": profile["machine_learning"],
        "SQL": profile["sql"], "Cloud Computing": profile["cloud_computing"],
        "Data Analysis": profile["data_analysis"],
    }
    skills_df = pd.DataFrame(
        {"Skill": list(self_ratings.keys()),
         "Your Rating (1-5)": list(self_ratings.values())}
    )

    # === Section switcher (mentor requirement — dashboard-style organization) ===
    # Uses st.radio instead of st.tabs deliberately: st.tabs() doesn't
    # remember which tab was active across a script rerun (any widget
    # interaction, like the Resume Analysis button, triggers a rerun), so
    # it kept jumping back to the first tab after every button click.
    # A small CSS override forces the pills to stay on one line (with
    # horizontal scroll as a fallback on narrow screens) instead of
    # wrapping to two rows. This targets Streamlit's data-testid attribute,
    # which is far more stable across Streamlit versions than its internal
    # class names — if a future Streamlit version ever changes it, this
    # simply stops applying and the layout falls back to wrapping (not a
    # crash), so it degrades safely either way.
    st.markdown(
        """
        <style>
        div[data-testid="stRadio"] > div[role="radiogroup"] {
            flex-wrap: nowrap;
            overflow-x: auto;
            padding-bottom: 4px;
        }
        div[data-testid="stRadio"] label {
            white-space: nowrap;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    section_options = ["🏠 Overview", "📌 Recommendations", "📊 Skill Gap",
                        "📚 Roadmap", "🤖 AI Guidance", "📄 Resume Analysis",
                        "💬 Assistant"]
    if "active_section" not in st.session_state:
        st.session_state["active_section"] = section_options[0]
    selected_section = st.radio(
        "View", section_options, horizontal=True,
        key="active_section", label_visibility="collapsed",
    )
    st.divider()

    if selected_section == "🏠 Overview":
        st.caption(
            "A quick-glance summary — see the detail tabs above for the full "
            "breakdown of each section."
        )

        # Row 1: Career match donut + colorful skill ratings bar chart
        ocol1, ocol2 = st.columns(2)
        with ocol1:
            st.markdown("**Career Match Breakdown**")
            colorful_donut_chart(confidence_df, "Career", "Confidence (%)")
        with ocol2:
            st.markdown("**Your Skill Ratings**")
            colorful_bar_chart(skills_df, "Skill", "Your Rating (1-5)")

        # Row 2: Skill rating histogram + skill readiness donut
        ocol3, ocol4 = st.columns(2)
        with ocol3:
            st.markdown("**Skill Rating Distribution**")
            skill_rating_histogram(self_ratings)
        with ocol4:
            st.markdown("**Skill Readiness**")
            if skill_gap:
                readiness_df = pd.DataFrame({
                    "Status": ["Ready", "To Learn"],
                    "Percent": [100 - skill_gap["gap"], skill_gap["gap"]],
                })
                readiness_chart = (
                    alt.Chart(readiness_df)
                    .mark_arc(innerRadius=55)
                    .encode(
                        theta="Percent:Q",
                        color=alt.Color(
                            "Status:N", legend=alt.Legend(title=None, orient="bottom"),
                            scale=alt.Scale(domain=["Ready", "To Learn"],
                                             range=["#2CA02C", "#FF7F0E"]),
                        ),
                        tooltip=["Status", "Percent"],
                    )
                )
                st.altair_chart(readiness_chart, use_container_width=True)
            else:
                st.info("No skill gap data available for this career.")

        if learning_path:
            st.info(
                f"📚 **Estimated duration to close the gap:** "
                f"{learning_path['duration']} — Milestone: {learning_path['milestone']}"
            )

    if selected_section == "📌 Recommendations":
        st.subheader("Top 3 Career Recommendations")
        medals = ["🥇", "🥈", "🥉"]
        for medal, item in zip(medals, top3):
            st.write(f"{medal} **{item['career']}** — confidence: {item['confidence']:.0%}")

        # Confidence comparison chart (Likhitha's suggestion: bar chart for
        # comparing scores instead of plain text)
        colorful_bar_chart(confidence_df, "Career", "Confidence (%)", horizontal=True)

    if selected_section == "📊 Skill Gap":
        st.subheader("Skill Gap Analysis")
        if skill_gap:
            st.write("**Current Skills:**", skill_gap["current"])
            st.write("**Required Skills:**", skill_gap["required"])
            st.write("**Gap Percentage:**", f'{skill_gap["gap"]}%')
            st.write("**Estimated Hours:**", skill_gap["hours"])
            st.write("**Recommended Courses:**", skill_gap["courses"])

            # Current self-rated skill levels chart (Likhitha's suggestion)
            st.caption("Your self-rated proficiency (from the form above) for key skills:")
            colorful_bar_chart(skills_df, "Skill", "Your Rating (1-5)")

            st.caption("Distribution of your ratings across these key skills:")
            skill_rating_histogram(self_ratings)
        else:
            st.info(
                f"No skill gap data found for '{top_career}'. This can happen if the "
                f"career label from the ML model doesn't exactly match a label in "
                f"career_skill_gap.csv — worth checking during testing."
            )

    if selected_section == "📚 Roadmap":
        st.subheader("Learning Roadmap")
        if learning_path:
            with st.container(border=True):
                st.write("**📈 Learning Stage:**", learning_path["stage"])
                st.write("**🎯 Priority Skills:**", learning_path["skills"])
                st.write("**🛤️ Learning Path:**", learning_path["path"])
                st.write("**📖 Resources:**", learning_path["resources"])
                st.write("**⏳ Estimated Duration:**", learning_path["duration"])
                st.write("**🏁 Milestone:**", learning_path["milestone"])
        else:
            st.info(
                f"No roadmap data found for '{top_career}'. Same likely cause as above — "
                f"label mismatch between datasets."
            )

    if selected_section == "🤖 AI Guidance":
        st.subheader("AI Career Guidance")
        if ctx["explanation_text"]:
            with st.container(border=True):
                st.write(ctx["explanation_text"])
        else:
            st.warning(
                "The AI explanation service is temporarily unavailable, but your "
                "ML-based recommendations above are still valid."
            )
            if ctx["explanation_error"]:
                st.caption(f"Technical detail: {ctx['explanation_error']}")

    if selected_section == "📄 Resume Analysis":
        st.subheader("Resume Analysis")
        st.caption(
            f"Upload your resume (PDF) to see how well it matches your top "
            f"recommended career — {top3[0]['career']}."
        )

        resume_file = st.file_uploader("Upload resume (PDF)", type=["pdf"])

        if resume_file is not None:
            if st.button("Analyze Resume", key="analyze_resume_btn"):
                resume_text, extract_error = extract_resume_text(resume_file)
                if extract_error:
                    st.session_state["resume_result"] = None
                    st.session_state["resume_error"] = extract_error
                else:
                    try:
                        with st.spinner("Analyzing your resume..."):
                            result = get_career_recommendation(
                                build_resume_analysis_prompt(resume_text, ctx)
                            )
                        st.session_state["resume_result"] = result
                        st.session_state["resume_error"] = None
                    except GenAIUnavailableError as e:
                        st.session_state["resume_result"] = None
                        st.session_state["resume_error"] = (
                            "The AI analysis service is temporarily unavailable. "
                            "Please try again in a moment."
                        )

        if st.session_state.get("resume_result"):
            with st.container(border=True):
                st.write(st.session_state["resume_result"])
        elif st.session_state.get("resume_error"):
            st.warning(st.session_state["resume_error"])
        elif resume_file is None:
            st.caption("No resume uploaded yet.")

    if selected_section == "💬 Assistant":
        st.subheader("AI Career Assistant")
        st.caption(
            "Ask follow-up questions about your recommended careers, skills, "
            "courses, certifications, or how to get started."
        )

        if "chat_history" not in st.session_state:
            st.session_state["chat_history"] = []

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

    # --- PDF report download (outside tabs — always visible) ---
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
