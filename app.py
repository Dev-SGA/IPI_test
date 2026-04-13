import streamlit as st
import plotly.graph_objects as go

# ──────────────────────────────────────────────
# CONFIGURAÇÃO DA PÁGINA
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="SGA - Individual Development Plan",
    page_icon="⚽",
    layout="wide",
)

# ──────────────────────────────────────────────
# DADOS DE EXEMPLO
# ──────────────────────────────────────────────
PLAYERS = {
    "Sebastiao Nzita": {
        "position": "Left Winger",
        "club": "Houston Dynamo",
        "photo_url": "https://via.placeholder.com/180x220/FF6600/FFFFFF?text=S.Nzita",
        "technical": [
            ("General Passing", "Above Level"),
            ("1st Touch", "Average"),
            ("Head. Direction", "Good"),
            ("1v1 Defending", "Average"),
            ("Crossing", "Good"),
            ("1v1 Attacking", "Good"),
            ("Aerials Duels", "Below Level"),
            ("Off Ball Def.", "Good"),
        ],
        "player_specific": [
            ("Finishing", "Good"),
            ("Long Ball", "Good"),
            ("", ""),
            ("", ""),
        ],
        "mental": [
            ("Awareness", "Average"),
            ("Effort", "Good"),
            ("Team Work", "Good"),
            ("", ""),
        ],
        "mog": {
            "Off. Possession": 75,
            "Off. Transition": 60,
            "Def. Organization": 55,
            "Def. Transition": 50,
            "Set Pieces": 65,
        },
        "strengths": [
            "Ability to combine",
            "Decision-Making in Possession",
            "Brave and Competitive Personality",
        ],
        "improve": [
            "Reaction to counter-press",
            "Communication with team",
            "Runs in behind",
        ],
    },
}

# ──────────────────────────────────────────────
# PALETA DE CORES
# ──────────────────────────────────────────────
COLORS = {
    "primary":       "#0D47A1",
    "primary_mid":   "#1565C0",
    "primary_light": "#1E88E5",
    "accent":        "#90CAF9",
    "card_bg":       "#FFFFFF",
    "card_shadow":   "rgba(13,71,161,0.12)",
    "page_bg_start": "#e8eef7",
    "page_bg_end":   "#d0dff0",
    "radar_bg":      "#0C1F3A",
    "radar_fill":    "rgba(100,181,246,0.30)",
    "radar_line":    "#64B5F6",
}

BADGE_STYLES = {
    "Above Level": {"bg": "#1B5E20", "fg": "#FFFFFF"},
    "Good":        {"bg": "#2E7D32", "fg": "#FFFFFF"},
    "Average":     {"bg": "#E6A817", "fg": "#FFFFFF"},
    "Below Level": {"bg": "#C62828", "fg": "#FFFFFF"},
}

# ──────────────────────────────────────────────
# CSS GLOBAL
# ──────────────────────────────────────────────
st.markdown(
    f"""
    <style>
    .stApp {{
        background: linear-gradient(160deg, {COLORS['page_bg_start']} 0%, {COLORS['page_bg_end']} 100%);
    }}
    .block-container {{
        padding-top: 1.2rem;
        padding-bottom: 1rem;
        max-width: 1320px;
    }}

    /* ── Header ── */
    .header-bar {{
        background: linear-gradient(90deg, {COLORS['primary']}, {COLORS['primary_mid']});
        padding: 20px 36px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        gap: 18px;
        margin-bottom: 24px;
        box-shadow: 0 4px 16px {COLORS['card_shadow']};
    }}
    .header-bar .logo {{ font-size: 2rem; line-height: 1; }}
    .header-bar .header-text {{ display: flex; flex-direction: column; }}
    .header-bar .brand {{
        color: {COLORS['accent']};
        font-size: 0.85rem; font-weight: 600;
        letter-spacing: 2px; text-transform: uppercase;
    }}
    .header-bar h1 {{
        color: white; margin: 0;
        font-size: 1.65rem; font-weight: 800;
    }}

    /* ── Player Card ── */
    .card {{
        background: {COLORS['card_bg']};
        border-radius: 12px; padding: 20px;
        box-shadow: 0 2px 12px {COLORS['card_shadow']};
    }}
    .player-card {{ text-align: center; }}
    .player-card img {{
        border-radius: 10px; width: 100%; max-width: 180px;
        height: auto; object-fit: cover;
        border: 3px solid {COLORS['accent']};
    }}
    .player-card .divider {{
        width: 50px; height: 3px;
        background: {COLORS['primary_light']};
        border-radius: 2px; margin: 10px auto;
    }}
    .player-card .label {{
        font-size: 0.75rem; color: #78909C;
        text-transform: uppercase; letter-spacing: 1.5px;
        margin-bottom: 2px; font-weight: 600;
    }}
    .player-card .value {{
        font-size: 1.05rem; color: {COLORS['primary']};
        font-weight: 700; margin-bottom: 10px;
    }}

    /* ── Section (blue panels) ── */
    .section {{
        border-radius: 12px; overflow: hidden;
        box-shadow: 0 2px 10px {COLORS['card_shadow']};
        margin-bottom: 16px;
    }}
    .section-header {{
        background: {COLORS['primary']};
        color: white; padding: 10px 20px;
        font-size: 1.05rem; font-weight: 700;
    }}
    .section-body {{
        background: {COLORS['primary_light']};
        padding: 14px 10px;
    }}

    /* ── Badge Table ── */
    .badge-table {{
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
    }}
    .badge-table td {{
        padding: 8px 6px;
        vertical-align: middle;
    }}
    .badge-table .cell-label {{
        color: white;
        font-size: 0.88rem;
        font-weight: 500;
        text-align: right;
        padding-right: 8px;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .badge-table .cell-tag {{
        text-align: left;
        width: 100px;
    }}
    .badge-tag {{
        display: inline-block;
        padding: 4px 12px;
        border-radius: 5px;
        font-size: 0.78rem;
        font-weight: 700;
        white-space: nowrap;
        letter-spacing: 0.3px;
        min-width: 80px;
        text-align: center;
    }}

    /* ── Text lists ── */
    .text-list {{ list-style: none; padding: 0; margin: 0; }}
    .text-list li {{
        color: white; font-size: 0.95rem; font-weight: 600;
        padding: 5px 0;
        border-bottom: 1px solid rgba(255,255,255,0.15);
    }}
    .text-list li:last-child {{ border-bottom: none; }}
    .text-list .num {{
        display: inline-block; width: 24px; height: 24px;
        line-height: 24px; text-align: center;
        background: rgba(255,255,255,0.2);
        border-radius: 50%; font-size: 0.8rem; margin-right: 8px;
    }}

    /* ── Radar: remove gaps do Streamlit ── */
    .radar-container {{
        background: {COLORS['radar_bg']};
        border-radius: 12px;
        box-shadow: 0 2px 10px {COLORS['card_shadow']};
        overflow: hidden;
        margin-bottom: 16px;
    }}
    .radar-container .stPlotlyChart {{
        margin: 0 !important;
        padding: 0 !important;
    }}

    div[data-testid="stSelectbox"] label {{
        font-weight: 600; color: {COLORS['primary']};
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ──────────────────────────────────────────────
# FUNÇÕES AUXILIARES
# ──────────────────────────────────────────────
def badge_tag(level: str) -> str:
    if not level:
        return ""
    s = BADGE_STYLES.get(level, {"bg": "#616161", "fg": "#FFF"})
    return f'<span class="badge-tag" style="background:{s["bg"]};color:{s["fg"]};">{level}</span>'


def render_section(title: str, body_html: str) -> str:
    return (
        f'<div class="section">'
        f'  <div class="section-header">{title}</div>'
        f'  <div class="section-body">{body_html}</div>'
        f'</div>'
    )


def render_badges_table(items: list, cols: int = 4) -> str:
    col_defs = ""
    for _ in range(cols):
        col_defs += '<col style="width:auto"><col style="width:100px">'

    rows_html = ""
    for row_start in range(0, len(items), cols):
        row_items = items[row_start : row_start + cols]
        cells = ""
        for label, level in row_items:
            if label:
                cells += f'<td class="cell-label">{label}</td>'
                cells += f'<td class="cell-tag">{badge_tag(level)}</td>'
            else:
                cells += "<td></td><td></td>"
        remaining = cols - len(row_items)
        cells += "<td></td><td></td>" * remaining
        rows_html += f"<tr>{cells}</tr>"

    return f'<table class="badge-table"><colgroup>{col_defs}</colgroup>{rows_html}</table>'


def render_list(items: list) -> str:
    li = "".join(
        f'<li><span class="num">{i+1}</span>{text}</li>'
        for i, text in enumerate(items)
    )
    return f'<ul class="text-list">{li}</ul>'


def build_radar_chart(mog_data: dict) -> go.Figure:
    """Cria o radar com título embutido no Plotly — zero HTML externo."""
    categories = list(mog_data.keys())
    values = list(mog_data.values())
    categories_closed = categories + [categories[0]]
    values_closed = values + [values[0]]

    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=values_closed,
            theta=categories_closed,
            fill="toself",
            fillcolor=COLORS["radar_fill"],
            line=dict(color=COLORS["radar_line"], width=2.5),
            marker=dict(size=6, color=COLORS["radar_line"]),
            hovertemplate="%{theta}: %{r}<extra></extra>",
        )
    )

    fig.update_layout(
        # Título embutido no próprio gráfico
        title=dict(
            text="<b>MoG – Moments of the Game</b>",
            font=dict(size=16, color="white", family="Arial, sans-serif"),
            x=0.5,
            xanchor="center",
            y=0.97,
            yanchor="top",
            pad=dict(t=0, b=0),
        ),
        polar=dict(
            bgcolor="rgba(255,255,255,0.03)",
            domain=dict(x=[0.05, 0.95], y=[0, 0.88]),
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                showticklabels=False,
                gridcolor="rgba(255,255,255,0.10)",
                linecolor="rgba(255,255,255,0.05)",
            ),
            angularaxis=dict(
                gridcolor="rgba(255,255,255,0.10)",
                linecolor="rgba(255,255,255,0.12)",
                tickfont=dict(size=12, color="#B0BEC5", family="Arial, sans-serif"),
                rotation=90,
            ),
        ),
        paper_bgcolor=COLORS["radar_bg"],
        plot_bgcolor=COLORS["radar_bg"],
        showlegend=False,
        margin=dict(l=12, r=12, t=50, b=12),
        height=380,
    )

    return fig


# ──────────────────────────────────────────────
# HEADER
# ──────────────────────────────────────────────
st.markdown(
    """
    <div class="header-bar">
        <div class="logo">⚽</div>
        <div class="header-text">
            <span class="brand">SGA Performance</span>
            <h1>Individual Development Plan</h1>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────
# SELETOR
# ──────────────────────────────────────────────
player_name = st.selectbox("Select Player", list(PLAYERS.keys()))
p = PLAYERS[player_name]

# ──────────────────────────────────────────────
# LAYOUT
# ──────────────────────────────────────────────
left_col, right_col = st.columns([1, 3], gap="large")

with left_col:
    # Player Card
    st.markdown(
        f"""
        <div class="card player-card">
            <img src="{p['photo_url']}" alt="{player_name}">
            <div class="divider"></div>
            <div class="label">Position</div>
            <div class="value">{p['position']}</div>
            <div class="label">Club</div>
            <div class="value">{p['club']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # Radar — componente único, sem HTML wrapper separado
    radar_fig = build_radar_chart(p["mog"])
    st.markdown('<div class="radar-container">', unsafe_allow_html=True)
    st.plotly_chart(
        radar_fig,
        use_container_width=True,
        config={"displayModeBar": False},
    )
    st.markdown("</div>", unsafe_allow_html=True)


with right_col:
    st.markdown(
        render_section("Technical", render_badges_table(p["technical"], cols=4)),
        unsafe_allow_html=True,
    )

    st.markdown(
        render_section(
            "Player-Specific Indicators",
            render_badges_table(p["player_specific"], cols=4),
        ),
        unsafe_allow_html=True,
    )

    st.markdown(
        render_section("Mental", render_badges_table(p["mental"], cols=4)),
        unsafe_allow_html=True,
    )

    s_col, i_col = st.columns(2, gap="medium")
    with s_col:
        st.markdown(
            render_section("My Strengths", render_list(p["strengths"])),
            unsafe_allow_html=True,
        )
    with i_col:
        st.markdown(
            render_section("Need to Improve", render_list(p["improve"])),
            unsafe_allow_html=True,
        )
