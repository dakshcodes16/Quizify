"""Learning Gap Dashboard -- weak topics, mastery visualization, recommendations (Agent 3)."""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
import plotly.graph_objects as go
from agents.analytics_agent import AnalyticsAgent
from frontend.components.ui import pill, metric_card, empty_state, card_container
from frontend.components.styles import agent_tag

CHART_FONT = dict(family="Inter, sans-serif", color="#F3F1FA")
GRID_COLOR = "rgba(255,255,255,0.08)"


def render(st):
    st.markdown(agent_tag("AGENT 03 \u00b7 ADAPTIVE", variant="adapt"), unsafe_allow_html=True)
    st.markdown('<h2 class="gradient-text" style="margin-top:0;">Learning gaps</h2>', unsafe_allow_html=True)

    agent = AnalyticsAgent()
    dashboard = agent.get_student_dashboard(st.session_state["user_id"])

    if dashboard["quizzes_taken"] == 0:
        empty_state(
            st, "\U0001F3AF", "Nothing to show yet",
            "Take a quiz and your weak topics, mastery breakdown, and progress curve will appear here.",
        )
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card(st, "Overall mastery", dashboard["mastery_score"], "%")
    with c2:
        metric_card(st, "Quizzes taken", dashboard["quizzes_taken"])
    with c3:
        metric_card(st, "Current streak", dashboard["current_streak"], " days")

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        with card_container(st):
            st.markdown('<h4 style="margin-top:0;">Weak topics</h4>', unsafe_allow_html=True)
            if dashboard["weak_topics"]:
                for t in dashboard["weak_topics"]:
                    mastery = dashboard["topic_mastery"].get(t, 0)
                    st.markdown(
                        f'<p style="color:var(--text-secondary); margin:0.4rem 0;">{t} &mdash; {mastery}% {pill("Needs review", "danger")}</p>',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown('<p style="color:var(--text-secondary);">No weak topics detected -- nice work.</p>', unsafe_allow_html=True)

    with col2:
        with card_container(st):
            st.markdown('<h4 style="margin-top:0;">Strong topics</h4>', unsafe_allow_html=True)
            if dashboard["strong_topics"]:
                for t in dashboard["strong_topics"]:
                    mastery = dashboard["topic_mastery"].get(t, 0)
                    st.markdown(
                        f'<p style="color:var(--text-secondary); margin:0.4rem 0;">{t} &mdash; {mastery}% {pill("Mastered", "success")}</p>',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown('<p style="color:var(--text-secondary);">Keep practicing to build mastery here.</p>', unsafe_allow_html=True)

    if dashboard["topic_mastery"]:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<h3 class="gradient-text">Topic mastery</h3>', unsafe_allow_html=True)

        topics = list(dashboard["topic_mastery"].keys())
        scores = list(dashboard["topic_mastery"].values())
        colors = ["#FF6B81" if s < 70 else "#FFB454" if s < 85 else "#26EBC4" for s in scores]

        fig = go.Figure(go.Bar(
            x=scores, y=topics, orientation="h",
            marker=dict(color=colors, line=dict(width=0)),
            text=[f"{s}%" for s in scores], textposition="outside",
            textfont=dict(family="JetBrains Mono, monospace", color="#F3F1FA"),
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=CHART_FONT,
            xaxis=dict(range=[0, 105], gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR),
            yaxis=dict(gridcolor=GRID_COLOR),
            margin=dict(l=10, r=40, t=10, b=10),
            height=max(250, len(topics) * 52),
        )
        st.plotly_chart(fig, use_container_width=True)

    if dashboard["history"]:
        st.markdown('<h3 class="gradient-text">Progress over time</h3>', unsafe_allow_html=True)
        history = dashboard["history"]
        dates = [h["date"][:10] for h in history]
        accuracies = [h["accuracy"] for h in history]

        fig2 = go.Figure(go.Scatter(
            x=dates, y=accuracies, mode="lines+markers",
            line=dict(color="#7C5CFF", width=3),
            marker=dict(size=8, color="#4F7CFF", line=dict(width=2, color="#0B0A1A")),
            fill="tozeroy", fillcolor="rgba(124,92,255,0.12)",
        ))
        fig2.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=CHART_FONT,
            yaxis=dict(range=[0, 100], gridcolor=GRID_COLOR, title="Accuracy %"),
            xaxis=dict(gridcolor=GRID_COLOR),
            margin=dict(l=10, r=10, t=10, b=10),
            height=320,
        )
        st.plotly_chart(fig2, use_container_width=True)

    if dashboard["badges"]:
        st.markdown('<h3 class="gradient-text">Badges earned</h3>', unsafe_allow_html=True)
        badge_cols = st.columns(len(dashboard["badges"]))
        for col, badge in zip(badge_cols, dashboard["badges"]):
            with col:
                st.markdown(
                    f"""
                    <div class="metric-card" style="text-align:center;">
                        <div style="font-size:1.8rem;">{badge['icon']}</div>
                        <div style="font-family:var(--font-display); font-weight:600; margin-top:0.4rem;">{badge['name']}</div>
                        <div style="font-size:0.78rem; color:var(--text-muted); margin-top:0.2rem;">{badge['description']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
