# app.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import sqlite3
import base64
from pathlib import Path
from datetime import date

st.set_page_config(page_title="SGA - IDP", page_icon="⚽", layout="wide")

DB_PATH = "sga_evaluations.db"

# Logo sources
LOGO_URL = "https://raw.githubusercontent.com/SEU-USUARIO/SEU-REPO/main/assets/sga_logo.png"
LOGO_PATH = "assets/sga_logo.png"


def get_logo_base64(path: str) -> str:
    file = Path(path)
    if file.exists():
        b64 = base64.b64encode(file.read_bytes()).decode()
        suffix = file.suffix.replace(".", "")
        mime = f"image/{suffix}" if suffix != "svg" else "image/svg+xml"
        return f"data:{mime};base64,{b64}"
    return ""


LOGO_SRC = get_logo_base64(LOGO_PATH) or LOGO_URL

# Fonts
FONT_DISPLAY = "'Orbitron', sans-serif"
FONT_GRAPHIC = "'Source Sans 3', sans-serif"
FONT_DOCUMENT = "'Trebuchet MS', 'Source Sans 3', sans-serif"

# Domain data
TECHNICAL_SKILLS = [
    "General Passing", "1st Touch", "Head. Direction", "1v1 Defending",
    "Crossing", "1v1 Attacking", "Aerials Duels", "Off Ball Def.",
]
MENTAL_SKILLS = ["Awareness", "Effort", "Team Work"]
MOG_CATEGORIES = [
    "Off. Possession", "Off. Transition", "Def. Organization",
    "Def. Transition", "Set Pieces",
]
LEVELS = ["Above Level", "Good", "Average", "Below Level"]


# Database helpers
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE, position TEXT, club TEXT, photo_url TEXT
        );
        CREATE TABLE IF NOT EXISTS evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL, analyst TEXT NOT NULL,
            eval_date TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (player_id) REFERENCES players(id)
        );
        CREATE TABLE IF NOT EXISTS eval_skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evaluation_id INTEGER NOT NULL, category TEXT NOT NULL,
            skill_name TEXT NOT NULL, level TEXT NOT NULL,
            FOREIGN KEY (evaluation_id) REFERENCES evaluations(id)
        );
        CREATE TABLE IF NOT EXISTS eval_mog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evaluation_id INTEGER NOT NULL, category TEXT NOT NULL,
            value INTEGER NOT NULL,
            FOREIGN KEY (evaluation_id) REFERENCES evaluations(id)
        );
        CREATE TABLE IF NOT EXISTS eval_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evaluation_id INTEGER NOT NULL, note_type TEXT NOT NULL,
            position INTEGER NOT NULL, text TEXT NOT NULL,
            FOREIGN KEY (evaluation_id) REFERENCES evaluations(id)
        );
    """)
    conn.commit()
    conn.close()


init_db()


def get_players():
    conn = get_db()
    df = pd.read_sql("SELECT * FROM players ORDER BY name", conn)
    conn.close()
    return df


def add_player(name, position, club, photo_url):
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO players (name,position,club,photo_url) VALUES (?,?,?,?)",
                 (name, position, club, photo_url))
    conn.commit()
    conn.close()


def save_evaluation(player_id, analyst, eval_date, skills, mog, strengths, improvements):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO evaluations (player_id,analyst,eval_date) VALUES (?,?,?)",
                (player_id, analyst, eval_date))
    eid = cur.lastrowid
    for cat, sd in skills.items():
        for sn, lv in sd.items():
            if sn.strip() and lv.strip():
                cur.execute("INSERT INTO eval_skills (evaluation_id,category,skill_name,level) VALUES (?,?,?,?)",
                            (eid, cat, sn, lv))
    for c, v in mog.items():
        cur.execute("INSERT INTO eval_mog (evaluation_id,category,value) VALUES (?,?,?)", (eid, c, v))
    for i, t in enumerate(strengths):
        if t.strip():
            cur.execute("INSERT INTO eval_notes (evaluation_id,note_type,position,text) VALUES (?,'strength',?,?)",
                        (eid, i + 1, t))
    for i, t in enumerate(improvements):
        if t.strip():
            cur.execute("INSERT INTO eval_notes (evaluation_id,note_type,position,text) VALUES (?,'improve',?,?)",
                        (eid, i + 1, t))
    conn.commit()
    conn.close()
    return eid


def get_latest_evaluation(player_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM evaluations WHERE player_id=? ORDER BY eval_date DESC, id DESC LIMIT 1",
                (player_id,))
    ev = cur.fetchone()
    if not ev:
        conn.close()
        return None
    eid = ev["id"]
    skills = {}
    for r in cur.execute("SELECT category,skill_name,level FROM eval_skills WHERE evaluation_id=?", (eid,)):
        skills.setdefault(r["category"], {})[r["skill_name"]] = r["level"]
    mog = {}
    for r in cur.execute("SELECT category,value FROM eval_mog WHERE evaluation_id=?", (eid,)):
        mog[r["category"]] = r["value"]
    strengths, improvements = [], []
    for r in cur.execute("SELECT note_type,position,text FROM eval_notes WHERE evaluation_id=? ORDER BY position",
                         (eid,)):
        (strengths if r["note_type"] == "strength" else improvements).append(r["text"])
    conn.close()
    return {"analyst": ev["analyst"], "eval_date": ev["eval_date"], "skills": skills, "mog": mog,
            "strengths": strengths, "improvements": improvements}


# UI navigation
page = st.sidebar.radio("Navegação", ["📊 Dashboard", "📝 Nova Avaliação", "➕ Cadastrar Jogador"])

# Create / List players
if page == "➕ Cadastrar Jogador":
    st.header("Cadastrar Novo Jogador")
    with st.form("form_player"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Nome completo *")
            position = st.text_input("Posição", placeholder="Ex: Left Winger")
        with c2:
            club = st.text_input("Clube", placeholder="Ex: Houston Dynamo")
            photo_url = st.text_input("URL da foto")
        if st.form_submit_button("💾 Cadastrar", use_container_width=True):
            if not name.strip():
                st.error("Nome é obrigatório.")
            else:
                add_player(name.strip(), position.strip(), club.strip(), photo_url.strip())
                st.success(f"✅ Jogador **{name}** cadastrado!")

# New evaluation
elif page == "📝 Nova Avaliação":
    st.header("Nova Avaliação")
    players_df = get_players()
    if players_df.empty:
        st.warning("Nenhum jogador cadastrado. Vá em **➕ Cadastrar Jogador**.")
        st.stop()
    with st.form("form_evaluation"):
        ca, cb, cc = st.columns(3)
        with ca:
            player_name = st.selectbox("Jogador", players_df["name"].tolist())
        with cb:
            analyst = st.text_input("Nome do Analista *")
        with cc:
            eval_date = st.date_input("Data", value=date.today())
        st.divider()
        st.subheader("🎯 Technical")
        tc = st.columns(4)
        tv = {}
        for i, s in enumerate(TECHNICAL_SKILLS):
            with tc[i % 4]:
                tv[s] = st.selectbox(s, LEVELS, key=f"t_{s}")
        st.divider()
        st.subheader("⚡ Player-Specific Indicators")
        st.caption("Digite o nome do atributo e escolha a classificação.")
        ps = {}
        pn = st.columns(4)
        pl = st.columns(4)
        for i in range(4):
            with pn[i]:
                an = st.text_input(f"Atributo {i+1}", key=f"psn_{i}", placeholder="Ex: Speed")
            with pl[i]:
                al = st.selectbox(f"Nível {i+1}", [""] + LEVELS, key=f"psl_{i}")
            if an.strip() and al:
                ps[an.strip()] = al
        st.divider()
        st.subheader("🧠 Mental")
        mc = st.columns(4)
        mv = {}
        for i, s in enumerate(MENTAL_SKILLS):
            with mc[i % 4]:
                mv[s] = st.selectbox(s, LEVELS, key=f"m_{s}")
        st.divider()
        st.subheader("📐 Moments of the Game")
        mgc = st.columns(5)
        mgv = {}
        for i, c in enumerate(MOG_CATEGORIES):
            with mgc[i]:
                mgv[c] = st.slider(c, 0, 100, 50, key=f"mog_{c}")
        st.divider()
        cs, ci = st.columns(2)
        with cs:
            st.subheader("💪 Strengths")
            s1, s2, s3 = st.text_input("1"), st.text_input("2"), st.text_input("3")
        with ci:
            st.subheader("📈 Improve")
            i1, i2, i3 = st.text_input("1 "), st.text_input("2 "), st.text_input("3 ")
        st.divider()
        if st.form_submit_button("💾 Salvar Avaliação", use_container_width=True):
            if not analyst.strip():
                st.error("Nome do analista é obrigatório.")
            else:
                pid = int(players_df.loc[players_df["name"] == player_name, "id"].iloc[0])
                save_evaluation(pid, analyst.strip(), eval_date.isoformat(),
                                {"technical": tv, "player_specific": ps, "mental": mv},
                                mgv, [s1, s2, s3], [i1, i2, i3])
                st.success(f"✅ Avaliação de **{player_name}** salva!")
                st.balloons()

# Dashboard page
else:
    BADGE_STYLES = {
        "Above Level": {"bg": "#1B5E20", "fg": "#FFFFFF"},
        "Good":        {"bg": "#2E7D32", "fg": "#FFFFFF"},
        "Average":     {"bg": "#E6A817", "fg": "#FFFFFF"},
        "Below Level": {"bg": "#C62828", "fg": "#FFFFFF"},
    }

    # Load fonts
    st.markdown(
        '<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;800;900&family=Source+Sans+3:wght@400;600;700;800&display=swap" rel="stylesheet">',
        unsafe_allow_html=True,
    )

    # CSS (use % formatting to avoid f-string braces conflicts)
    _css = """
    <style>
    html, body, .stApp, .stApp * {
        font-family: %(fg)s !important;
    }
    .block-container {
        max-width: 1600px !important;
        padding-left: 2rem;
        padding-right: 2rem;
    }

    .header-bar {
        background: linear-gradient(135deg, #67b6fb 0%%, #5aaaf5 50%%, #4d9eef 100%%);
        padding: 22px 40px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        gap: 28px;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(103,182,251,0.30);
        position: relative;
        overflow: hidden;
    }
    .header-bar::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background: url("data:image/svg+xml,%%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%%3E%%3Cg fill='none' fill-rule='evenodd'%%3E%%3Cg fill='%%23ffffff' fill-opacity='0.06'%%3E%%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'%%2F%%3E%%3C%%2Fg%%3E%%3C%%2Fg%%3E%%3C%%2Fsvg%%3E");
        pointer-events: none;
    }
    .header-bar .header-logo {
        height: 64px;
        width: auto;
        object-fit: contain;
        flex-shrink: 0;
        position: relative;
        z-index: 1;
    }
    .header-bar .header-sep {
        width: 2px;
        height: 48px;
        background: rgba(10,42,74,0.2);
        border-radius: 1px;
        flex-shrink: 0;
        position: relative;
        z-index: 1;
    }
    .header-bar h1 {
        font-family: %(fd)s !important;
        color: #0a2a4a;
        margin: 0;
        font-size: 2rem;
        font-weight: 900;
        letter-spacing: 2.5px;
        text-transform: uppercase;
        position: relative;
        z-index: 1;
        line-height: 1.2;
    }

    .card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 12px rgba(13,71,161,0.12);
    }
    .player-card { text-align: center; }
    .player-card img {
        border-radius: 10px;
        width: 100%%;
        max-width: 180px;
        border: 3px solid #67b6fb;
    }
    .player-card .divider {
        width: 50px; height: 3px;
        background: #67b6fb;
        border-radius: 2px;
        margin: 10px auto;
    }
    .player-card .label {
        font-family: %(fg)s !important;
        font-size: 0.72rem;
        color: #78909C;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-weight: 700;
    }
    .player-card .value {
        font-family: %(fg)s !important;
        font-size: 1.05rem;
        color: #0D47A1;
        font-weight: 700;
        margin-bottom: 10px;
    }

    .section {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 2px 10px rgba(13,71,161,0.12);
        margin-bottom: 16px;
    }
    .section-header {
        background: #0D47A1;
        color: white;
        padding: 10px 20px;
        font-family: %(fd)s !important;
        font-size: 0.9rem;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
    }
    .section-body {
        background: #1E88E5;
        padding: 14px 20px;
    }

    /* ── Badge Table — aligned columns, no truncation ── */
    .badge-table {
        width: 100%%;
        border-collapse: collapse;
        table-layout: fixed;  /* fixed so colgroup widths are respected */
    }
    .badge-table td {
        padding: 8px 8px;
        vertical-align: middle;
    }
    .badge-table .cell-label {
        color: white;
        font-family: %(fg)s !important;
        font-size: 0.92rem;
        font-weight: 600;
        text-align: right;
        padding-right: 14px;
        white-space: normal;     /* allow wrapping instead of ellipsis */
        word-break: break-word;
    }
    .badge-table .cell-tag {
        text-align: left;
        white-space: nowrap;     /* badge must stay single-line */
    }
    .badge-tag {
        display: inline-block;
        padding: 6px 12px;
        border-radius: 6px;
        font-family: %(fg)s !important;
        font-size: 0.82rem;
        font-weight: 700;
        white-space: nowrap;
        min-width: 90px;
        text-align: center;
    }

    .text-list {
        list-style: none;
        padding: 0;
        margin: 0;
    }
    .text-list li {
        color: white;
        font-family: %(fdo)s !important;
        font-size: 0.95rem;
        font-weight: 600;
        padding: 5px 0;
        border-bottom: 1px solid rgba(255,255,255,0.15);
    }
    .text-list li:last-child { border-bottom: none; }
    .text-list .num {
        display: inline-block;
        width: 24px; height: 24px;
        line-height: 24px;
        text-align: center;
        background: rgba(255,255,255,0.2);
        border-radius: 50%%;
        font-size: 0.8rem;
        margin-right: 8px;
    }

    .radar-outer {
        background: #0C1F3A;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(13,71,161,0.12);
        overflow: hidden;
        margin-bottom: 16px;
    }
    .radar-title {
        background: #0C1F3A;
        color: white;
        text-align: center;
        font-family: %(fd)s !important;
        font-size: 0.85rem;
        font-weight: 700;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        padding: 14px 12px 0 12px;
    }
    .radar-body { background: #0C1F3A; }
    .radar-body > div { margin: 0 !important; padding: 0 !important; }

    .no-data-msg {
        text-align: center;
        padding: 40px 20px;
        color: #78909C;
        font-size: 1.1rem;
    }
    .eval-meta {
        background: rgba(13,71,161,0.06);
        border-radius: 8px;
        padding: 8px 16px;
        margin-top: 8px;
        font-family: %(fdo)s !important;
        font-size: 0.85rem;
        color: #546E7A;
    }
    div[data-testid="stSelectbox"] label {
        font-weight: 600;
        color: #0D47A1;
        font-family: %(fg)s !important;
    }
    </style>
    """ % {"fd": FONT_DISPLAY, "fg": FONT_GRAPHIC, "fdo": FONT_DOCUMENT}

    st.markdown(_css, unsafe_allow_html=True)

    # Helpers
    def badge_tag(level):
        if not level:
            return ""
        s = BADGE_STYLES.get(level, {"bg": "#616161", "fg": "#FFF"})
        return '<span class="badge-tag" style="background:' + s["bg"] + ";color:" + s["fg"] + ';">' + level + "</span>"

    def render_section(title, body):
        return '<div class="section"><div class="section-header">' + title + '</div><div class="section-body">' + body + "</div></div>"

    # UPDATED function: builds table with colgroup (label-cols + tag-cols)
    def render_badges_table(items: list, cols: int = 4, tag_px: int = 110) -> str:
        """
        items: list of (label, level) pairs in the order you want columns to appear.
        cols: number of columns per row (each column = label + tag).
        tag_px: fixed px width for each tag column.
        """
        # pad to multiple of cols
        if len(items) % cols != 0:
            remaining = cols - (len(items) % cols)
            items = items + [("", "")] * remaining

        total_tag_px = tag_px * cols
        # label column width: remaining space divided by cols
        label_col_calc = f"calc((100% - {total_tag_px}px) / {cols})"

        # colgroup HTML
        colgroup_html = "<colgroup>"
        for _ in range(cols):
            colgroup_html += f'<col class="label-col" style="width:{label_col_calc}">'
            colgroup_html += f'<col class="tag-col" style="width:{tag_px}px">'
        colgroup_html += "</colgroup>"

        # rows
        rows_html = ""
        for row_start in range(0, len(items), cols):
            row_items = items[row_start: row_start + cols]
            cells = ""
            for label, level in row_items:
                if label:
                    cells += f'<td class="cell-label">{label}</td>'
                    if level:
                        cells += f'<td class="cell-tag">{badge_tag(level)}</td>'
                    else:
                        cells += '<td class="cell-tag"></td>'
                else:
                    cells += "<td></td><td></td>"
            rows_html += f"<tr>{cells}</tr>"

        table_html = f'<table class="badge-table">{colgroup_html}{rows_html}</table>'
        return table_html

    def render_list(items):
        if not items:
            return '<span style="color:rgba(255,255,255,0.5);">—</span>'
        li = ""
        for i, t in enumerate(items):
            li += '<li><span class="num">' + str(i + 1) + "</span>" + t + "</li>"
        return '<ul class="text-list">' + li + "</ul>"

    def build_radar(mog_data):
        cats = list(mog_data.keys())
        vals = list(mog_data.values())
        cats_c = cats + [cats[0]]
        vals_c = vals + [vals[0]]
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=vals_c, theta=cats_c, fill="toself",
            fillcolor="rgba(100,181,246,0.30)",
            line=dict(color="#64B5F6", width=2.5),
            marker=dict(size=6, color="#64B5F6"),
        ))
        fig.update_layout(
            polar=dict(
                bgcolor="rgba(255,255,255,0.03)",
                domain=dict(x=[0.0, 1.0], y=[0.0, 1.0]),
                radialaxis=dict(visible=True, range=[0, 100], showticklabels=False,
                                gridcolor="rgba(255,255,255,0.10)"),
                angularaxis=dict(gridcolor="rgba(255,255,255,0.10)",
                                 tickfont=dict(size=12, color="#CFD8DC",
                                               family="Source Sans 3, Trebuchet MS, sans-serif"),
                                 rotation=90),
            ),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False, margin=dict(l=70, r=70, t=40, b=50), height=500,
        )
        return fig

    # Header: logo + separator + title
    st.markdown(
        '<div class="header-bar">'
        '<img src="' + LOGO_SRC + '" alt="SGA Logo" class="header-logo">'
        '<div class="header-sep"></div>'
        '<h1>Individual Development Plan</h1>'
        '</div>',
        unsafe_allow_html=True,
    )

    players_df = get_players()
    if players_df.empty:
        st.info("Nenhum jogador cadastrado. Vá em **➕ Cadastrar Jogador**.")
        st.stop()

    player_name = st.selectbox("Select Player", players_df["name"].tolist())
    pr = players_df[players_df["name"] == player_name].iloc[0]
    evaluation = get_latest_evaluation(int(pr["id"]))

    left_col, right_col = st.columns([1, 3], gap="large")

    with left_col:
        photo = pr["photo_url"] or "https://via.placeholder.com/180x220/0D47A1/FFFFFF?text=No+Photo"
        st.markdown(
            '<div class="card player-card">'
            '<img src="' + str(photo) + '" alt="' + str(player_name) + '">'
            '<div class="divider"></div>'
            '<div class="label">Position</div><div class="value">' + str(pr["position"] or "—") + "</div>"
            '<div class="label">Club</div><div class="value">' + str(pr["club"] or "—") + "</div></div>",
            unsafe_allow_html=True,
        )
        if evaluation and evaluation["mog"]:
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            st.markdown(
                '<div class="radar-outer">'
                '<div class="radar-title">MoG – Moments of the Game</div>'
                '<div class="radar-body">',
                unsafe_allow_html=True,
            )
            fig = build_radar(evaluation["mog"])
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            st.markdown("</div></div>", unsafe_allow_html=True)

    with right_col:
        if not evaluation:
            st.markdown(
                '<div class="card no-data-msg">📋 Nenhuma avaliação encontrada.<br>'
                'Vá em <b>📝 Nova Avaliação</b> para criar.</div>',
                unsafe_allow_html=True,
            )
            st.stop()
        sk = evaluation["skills"]

        # Technical (keeps original order - indexes determine columns)
        tech_items = [(s, sk.get("technical", {}).get(s, "")) for s in TECHNICAL_SKILLS]
        st.markdown(render_section("Technical", render_badges_table(tech_items, 4)), unsafe_allow_html=True)

        # Player-specific: we must preserve the slots order the analyst filled. We stored them by insertion order.
        ps_data = sk.get("player_specific", {})
        # Build list in order: attempt to preserve insertion order (dict) — pad to 4 slots
        ps_items = [(n, l) for n, l in ps_data.items()]
        while len(ps_items) < 4:
            ps_items.append(("", ""))
        st.markdown(render_section("Player-Specific Indicators", render_badges_table(ps_items, 4)), unsafe_allow_html=True)

        # Mental: fixed order, pad to 4
        m_items = [(s, sk.get("mental", {}).get(s, "")) for s in MENTAL_SKILLS]
        while len(m_items) < 4:
            m_items.append(("", ""))
        st.markdown(render_section("Mental", render_badges_table(m_items, 4)), unsafe_allow_html=True)

        sc, ic = st.columns(2, gap="medium")
        with sc:
            st.markdown(render_section("My Strengths", render_list(evaluation["strengths"])), unsafe_allow_html=True)
        with ic:
            st.markdown(render_section("Need to Improve", render_list(evaluation["improvements"])), unsafe_allow_html=True)

        st.markdown(
            '<div class="eval-meta">📅 <b>Avaliação:</b> ' + evaluation["eval_date"]
            + " &nbsp;•&nbsp; 👤 <b>Analista:</b> " + evaluation["analyst"] + "</div>",
            unsafe_allow_html=True,
        )
