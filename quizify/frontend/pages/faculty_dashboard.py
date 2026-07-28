"""Faculty Analytics Dashboard -- class-wide performance, heatmaps, reports, trends (Agent 4)."""
import sys
from pathlib import Path
import tempfile

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from agents.analytics_agent import AnalyticsAgent
from frontend.components.ui import metric_card, empty_state
from frontend.components.styles import agent_tag

CHART_FONT = dict(family="Inter, sans-serif", color="#F3F1FA")
GRID_COLOR = "rgba(255,255,255,0.08)"


def render(st):
    st.markdown(agent_tag("AGENT 04 \u00b7 ANALYTICS", variant="analytics"), unsafe_allow_html=True)
    st.markdown('<h2 class="gradient-text" style="margin-top:0;">Faculty dashboard</h2>', unsafe_allow_html=True)

    agent = AnalyticsAgent()
    dashboard = agent.get_faculty_dashboard()

    if dashboard["total_students"] == 0:
        empty_state(
            st, "\U0001F465", "No students yet",
            "Once students register and start taking quizzes, class-wide performance "
            "and weak topics will appear here.",
        )
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card(st, "Total students", dashboard["total_students"])
    with c2:
        metric_card(st, "Class avg mastery", dashboard["class_avg_mastery"], "%")
    with c3:
        active = sum(1 for s in dashboard["students"] if s["quizzes_taken"] > 0)
        metric_card(st, "Active students", active)

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown('<h3 class="gradient-text">Student performance</h3>', unsafe_allow_html=True)
        df = pd.DataFrame(dashboard["students"])
        if not df.empty:
            # Sort by roll_no descending so Plotly renders bottom-to-top with lower roll numbers at the top
            df_sorted = df.sort_values("roll_no", ascending=False, na_position="first")
            y_labels = [f"{r['roll_no']} - {r['name']}" if r['roll_no'] else r['name'] for _, r in df_sorted.iterrows()]
            fig = go.Figure(go.Bar(
                x=df_sorted["mastery_score"], y=y_labels, orientation="h",
                marker=dict(
                    color=df_sorted["mastery_score"],
                    colorscale=[[0, "#FF6B81"], [0.5, "#FFB454"], [1, "#26EBC4"]],
                    line=dict(width=0),
                ),
                text=[f"{m}%" for m in df_sorted["mastery_score"]], textposition="outside",
                textfont=dict(family="JetBrains Mono, monospace"),
            ))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=CHART_FONT,
                xaxis=dict(range=[0, 105], gridcolor=GRID_COLOR),
                yaxis=dict(gridcolor=GRID_COLOR),
                margin=dict(l=10, r=40, t=10, b=10),
                height=max(300, len(df) * 42),
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<h3 class="gradient-text">Top weak topics</h3>', unsafe_allow_html=True)
        if dashboard["top_weak_topics"]:
            for topic, count in dashboard["top_weak_topics"]:
                st.markdown(
                    f"""
                    <div class="glass-card-flat" style="margin-bottom:0.6rem;">
                        <b>{topic}</b><br>
                        <span style="color:var(--coral); font-size:0.85rem;">{count} student(s) struggling</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.markdown('<p style="color:var(--text-secondary);">No common weak topics detected yet.</p>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<h3 class="gradient-text">Class mastery heatmap</h3>', unsafe_allow_html=True)

    all_topics = sorted({t for s in dashboard["students"] for t in s["weak_topics"]})
    if all_topics:
        heat_data = []
        active_students = [s for s in dashboard["students"] if s["quizzes_taken"] > 0]
        # Sort active_students by roll_no
        active_students = sorted(active_students, key=lambda s: s.get("roll_no") or "")
        student_labels = [f"{s['roll_no']} - {s['name']}" if s.get('roll_no') else s['name'] for s in active_students]
        for s in active_students:
            row = [1 if t in s["weak_topics"] else 0 for t in all_topics]
            heat_data.append(row)

        if heat_data:
            fig_heat = px.imshow(
                heat_data, x=all_topics, y=student_labels,
                color_continuous_scale=[[0, "#1A1830"], [1, "#FF6B81"]],
                aspect="auto", labels=dict(color="Weak"),
            )
            fig_heat.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=CHART_FONT,
                margin=dict(l=10, r=10, t=10, b=10),
                height=max(300, len(student_labels) * 35),
            )
            st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.markdown(
            '<div class="glass-card-flat" style="color:var(--text-secondary);">No weak-topic data yet -- the heatmap fills in as students take quizzes.</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<h3 class="gradient-text">Leaderboard</h3>', unsafe_allow_html=True)
    for i, s in enumerate(dashboard["leaderboard"][:10]):
        rank = ["1", "2", "3"][i] if i < 3 else f"#{i+1}"
        student_label = f"{s['roll_no']} - {s['name']}" if s.get('roll_no') else s['name']
        st.markdown(
            f"""
            <div class="glass-card-flat" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.6rem;">
                <span><b style="font-family:var(--font-mono); color:var(--violet);">{rank}</b>
                &nbsp;&nbsp;<b>{student_label}</b> &nbsp;
                <span style="color:var(--text-muted); font-size:0.85rem;">{s['quizzes_taken']} quizzes &middot; {s['streak']} day streak</span></span>
                <span class="gradient-text" style="font-family:var(--font-mono); font-weight:700; font-size:1.15rem;">{s['mastery_score']}%</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<h3 class="gradient-text">All students</h3>', unsafe_allow_html=True)
    df_display = pd.DataFrame(dashboard["students"])[["roll_no", "name", "email", "mastery_score", "quizzes_taken", "streak"]]
    df_display.columns = ["Roll No", "Name", "Email", "Mastery %", "Quizzes taken", "Streak"]
    st.dataframe(df_display, use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)
    active_eligible = [s for s in dashboard["students"] if s["quizzes_taken"] > 0]
    if active_eligible:
        student_options = {f"{s['roll_no']} - {s['name']}" if s['roll_no'] else s['name']: s['student_id'] for s in active_eligible}
        selected_option = st.selectbox("Export PDF report for student", list(student_options.keys()))
        if selected_option and st.button("Generate PDF report"):
            selected_student_id = student_options[selected_option]
            selected_student_name = selected_option.split(" - ", 1)[-1]
            with st.spinner("Generating report..."):
                output_path = str(Path(tempfile.gettempdir()) / f"report_{selected_student_id}.pdf")
                agent.export_pdf_report(selected_student_id, output_path)
                with open(output_path, "rb") as f:
                    st.download_button(
                        "Download report", f, file_name=f"{selected_student_name}_progress_report.pdf",
                        mime="application/pdf",
                    )
