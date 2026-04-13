import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# ──────────────────────────────────────────────
# CONFIGURAÇÃO DA PÁGINA
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="SGA - Individual Development Plan",
    page_icon="⚽",
    layout="wide",
)

# ──────────────────────────────────────────────
# DADOS DE EXEMPLO (substitua pela sua fonte real)
# ──────────────────────────────────────────────
PLAYERS = {
    "Sebastiao Nzita": {
        "position": "Left Winger",
        "club": "Houston Dynamo",
        "photo_url": "https://via.placeholder.com/180x220/FF6600/FFFFFF?text=S.Nzita",
        "technical": {
            "General Passing": "Above Level",
            "1st Touch": "Average",
            "Head. Direction": "Good",
            "1v1 Defending": "Average",
            "Crossing": "Good",
            "1v1 Attacking": "Good",
            "Aerials Duels": "Below Level",
            "Off Ball Def.": "Good",
        },
        "player_specific": {
            "Finishing": "Good",
            "Long Ball": "Good",
        },
        "mental": {
            "Awareness": "Average",
            "Effort": "Good",
            "Team Work": "Good",
        },
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
    # Adicione mais jogadores aqui seguindo a mesma estrutura
}

# ──────────────────────────────────────────────
# FUNÇÕES AUXILIARES
# ──────────────────────────────────────────────
BADGE_COLORS = {
    "Above Level": ("#1B5E20", "#FFFFFF"),   # verde escuro
    "Good":        ("#2E7D32", "#FFFFFF"),    # verde
    "Average":     ("#F9A825", "#FFFFFF"),    # amarelo/dourado
    "Below Level": ("#C62828", "#FFFFFF"),    # vermelho
}


def badge(label: str, level: str) -> str:
    """Retorna HTML de um indicador com badge colorida."""
    bg, fg = BADGE_COLORS.get(level, ("#616161", "#FFFFFF"))
    return (
        f'<span style="font-size:0.95rem;font-weight:500;margin-right:6px;">{label}</span>'
        f'<span style="background:{bg};color:{fg};padding:4px 14px;border-radius:4px;'
        f'font-size:0.85rem;font-weight:700;">{level}</span>'
    )


def section_title(text: str) -> str:
    return (
        f'<div style="background:#1565C0;color:white;padding:8px 16px;'
        f'border-radius:6px 6px 0 0;font-size:1.15rem;font-weight:700;'
        f'margin-bottom:0;">{text}</div>'
    )


def section_body(inner_html: str) -> str:
    return (
        f'<div style="background:#1E88E5;padding:14px 16px;border-radius:0 0 6px 6px;'
        f'color:white;margin-bottom:16px;">{inner_html}</div>'
    )


def render_badges_grid(items: dict, cols: int = 4) -> str:
    """Monta uma grid HTML de badges."""
    cells = "".join(
        f'<div style="padding:6px 4px;text-align:center;">{badge(k, v)}</div>'
        for k, v in items.items()
    )
    return (
        f'<div style="display:grid;grid-template-columns:repeat({cols}, 1fr);'
        f'gap:4px 12px;">{cells}</div>'
    )


# ──────────────────────────────────────────────
# CSS GLOBAL
# ──────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* Fundo geral */
    .stApp {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
    }
    /* Remove padding extra */
    .block-container { padding-top: 1rem; }
    /* Header */
    .header-bar {
        background: linear-gradient(90deg, #0D47A1, #1565C0);
        padding: 18px 32px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        gap: 16px;
        margin-bottom: 20px;
    }
    .header-bar h1 {
        color: white;
        margin: 0;
        font-size: 1.8rem;
        letter-spacing: 1px;
    }
    .header-bar .logo-text {
        color: #90CAF9;
        font-size: 1rem;
        font-weight: 600;
    }
    /* Card do jogador */
    .player-card {
        background: white;
        border-radius: 10px;
        padding: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.12);
        text-align: center;
    }
    .player-card img {
        border-radius: 8px;
        width: 160px;
        height: auto;
        object-fit: cover;
    }
    .player-card .info { margin-top: 10px; }
    .player-card .info h3 { margin: 2px 0; color: #0D47A1; }
    .player-card .info p  { margin: 0; color: #333; font-size: 0.95rem; }
    /* Listas de strengths / improve */
    .text-list { list-style: none; padding-left: 0; }
    .text-list li {
        font-size: 1rem;
        font-weight: 600;
        color: white;
        padding: 4px 0;
    }
    .text-list li::before {
        content: counter(li) ". ";
        counter-increment: li;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────
# HEADER
# ──────────────────────────────────────────────
st.markdown(
    """
    <div class="header-bar">
        <div>
            <span class="logo-text">⚽ SGA Performance</span>
            <h1>INDIVIDUAL DEVELOPMENT PLAN</h1>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────
# SELETOR DE JOGADOR
# ──────────────────────────────────────────────
player_name = st.selectbox("Select Player", list(PLAYERS.keys()))
p = PLAYERS[player_name]

# ──────────────────────────────────────────────
# LAYOUT PRINCIPAL
# ──────────────────────────────────────────────
left_col, right_col = st.columns([1, 3], gap="medium")

# ---- COLUNA ESQUERDA: Card + Radar ----
with left_col:
    # Card do jogador
    st.markdown(
        f"""
        <div class="player-card">
            <img src="{p['photo_url']}" alt="{player_name}">
            <div class="info">
                <p><strong>Position</strong></p>
                <h3>{p['position']}</h3>
                <p><strong>Club</strong></p>
                <h3>{p['club']}</h3>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Radar Chart – MoG (Moments of the Game)
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    st.markdown(section_title("MoG"), unsafe_allow_html=True)

    categories = list(p["mog"].keys())
    values = list(p["mog"].values())
    # Fechar o polígono
    categories_closed = categories + [categories[0]]
    values_closed = values + [values[0]]

    fig = go.Figure(
        go.Scatterpolar(
            r=values_closed,
            theta=categories_closed,
            fill="toself",
            fillcolor="rgba(21,101,192,0.35)",
            line=dict(color="#0D47A1", width=2),
            marker=dict(size=5),
        )
    )
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(255,255,255,0.05)",
            radialaxis=dict(visible=True, range=[0, 100], showticklabels=False),
            angularaxis=dict(color="white"),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        margin=dict(l=40, r=40, t=20, b=40),
        height=320,
        font=dict(color="white"),
    )
    st.plotly_chart(fig, use_container_width=True)

# ---- COLUNA DIREITA: Indicadores ----
with right_col:
    # TECHNICAL
    st.markdown(section_title("Technical"), unsafe_allow_html=True)
    st.markdown(
        section_body(render_badges_grid(p["technical"], cols=4)),
        unsafe_allow_html=True,
    )

    # PLAYER-SPECIFIC INDICATORS
    st.markdown(section_title("Player-Specific Indicators"), unsafe_allow_html=True)
    st.markdown(
        section_body(render_badges_grid(p["player_specific"], cols=4)),
        unsafe_allow_html=True,
    )

    # MENTAL
    st.markdown(section_title("Mental"), unsafe_allow_html=True)
    st.markdown(
        section_body(render_badges_grid(p["mental"], cols=3)),
        unsafe_allow_html=True,
    )

    # STRENGTHS & IMPROVE – lado a lado
    s_col, i_col = st.columns(2)
    with s_col:
        st.markdown(section_title("My Strengths"), unsafe_allow_html=True)
        items_html = "".join(
            f"<li><strong>{i+1}.</strong> {s}</li>"
            for i, s in enumerate(p["strengths"])
        )
        st.markdown(
            section_body(f'<ul style="list-style:none;padding:0;margin:0;">{items_html}</ul>'),
            unsafe_allow_html=True,
        )
    with i_col:
        st.markdown(section_title("Need to Improve"), unsafe_allow_html=True)
        items_html = "".join(
            f"<li><strong>{i+1}.</strong> {s}</li>"
            for i, s in enumerate(p["improve"])
        )
        st.markdown(
            section_body(f'<ul style="list-style:none;padding:0;margin:0;">{items_html}</ul>'),
            unsafe_allow_html=True,
        )
