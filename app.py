import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import sqlite3
from datetime import date

# ──────────────────────────────────────────────
# CONFIGURAÇÃO
# ──────────────────────────────────────────────
st.set_page_config(page_title="SGA - IDP", page_icon="⚽", layout="wide")

DB_PATH = "sga_evaluations.db"

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


# ──────────────────────────────────────────────
# BANCO DE DADOS
# ──────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS players (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL UNIQUE,
            position    TEXT,
            club        TEXT,
            photo_url   TEXT
        );

        CREATE TABLE IF NOT EXISTS evaluations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id   INTEGER NOT NULL,
            analyst     TEXT NOT NULL,
            eval_date   TEXT NOT NULL,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (player_id) REFERENCES players(id)
        );

        CREATE TABLE IF NOT EXISTS eval_skills (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            evaluation_id INTEGER NOT NULL,
            category      TEXT NOT NULL,
            skill_name    TEXT NOT NULL,
            level         TEXT NOT NULL,
            FOREIGN KEY (evaluation_id) REFERENCES evaluations(id)
        );

        CREATE TABLE IF NOT EXISTS eval_mog (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            evaluation_id INTEGER NOT NULL,
            category      TEXT NOT NULL,
            value         INTEGER NOT NULL,
            FOREIGN KEY (evaluation_id) REFERENCES evaluations(id)
        );

        CREATE TABLE IF NOT EXISTS eval_notes (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            evaluation_id INTEGER NOT NULL,
            note_type     TEXT NOT NULL,
            position      INTEGER NOT NULL,
            text          TEXT NOT NULL,
            FOREIGN KEY (evaluation_id) REFERENCES evaluations(id)
        );
    """)
    conn.commit()
    conn.close()


init_db()


# ──────────────────────────────────────────────
# FUNÇÕES DE LEITURA / ESCRITA
# ──────────────────────────────────────────────
def get_players() -> pd.DataFrame:
    conn = get_db()
    df = pd.read_sql("SELECT * FROM players ORDER BY name", conn)
    conn.close()
    return df


def add_player(name, position, club, photo_url):
    conn = get_db()
    conn.execute(
        "INSERT OR IGNORE INTO players (name, position, club, photo_url) VALUES (?, ?, ?, ?)",
        (name, position, club, photo_url),
    )
    conn.commit()
    conn.close()


def save_evaluation(player_id, analyst, eval_date, skills, mog, strengths, improvements):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO evaluations (player_id, analyst, eval_date) VALUES (?, ?, ?)",
        (player_id, analyst, eval_date),
    )
    eval_id = cur.lastrowid

    for category, skill_dict in skills.items():
        for skill_name, level in skill_dict.items():
            if skill_name.strip() and level.strip():
                cur.execute(
                    "INSERT INTO eval_skills (evaluation_id, category, skill_name, level) "
                    "VALUES (?, ?, ?, ?)",
                    (eval_id, category, skill_name, level),
                )

    for cat, val in mog.items():
        cur.execute(
            "INSERT INTO eval_mog (evaluation_id, category, value) VALUES (?, ?, ?)",
            (eval_id, cat, val),
        )

    for i, text in enumerate(strengths):
        if text.strip():
            cur.execute(
                "INSERT INTO eval_notes (evaluation_id, note_type, position, text) "
                "VALUES (?, 'strength', ?, ?)",
                (eval_id, i + 1, text),
            )
    for i, text in enumerate(improvements):
        if text.strip():
            cur.execute(
                "INSERT INTO eval_notes (evaluation_id, note_type, position, text) "
                "VALUES (?, 'improve', ?, ?)",
                (eval_id, i + 1, text),
            )

    conn.commit()
    conn.close()
    return eval_id


def get_latest_evaluation(player_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM evaluations WHERE player_id = ? ORDER BY eval_date DESC, id DESC LIMIT 1",
        (player_id,),
    )
    ev = cur.fetchone()
    if not ev:
        conn.close()
        return None

    eval_id = ev["id"]

    skills = {}
    for row in cur.execute(
        "SELECT category, skill_name, level FROM eval_skills WHERE evaluation_id = ?",
        (eval_id,),
    ):
        skills.setdefault(row["category"], {})[row["skill_name"]] = row["level"]

    mog = {}
    for row in cur.execute(
        "SELECT category, value FROM eval_mog WHERE evaluation_id = ?", (eval_id,),
    ):
        mog[row["category"]] = row["value"]

    strengths, improvements = [], []
    for row in cur.execute(
        "SELECT note_type, position, text FROM eval_notes WHERE evaluation_id = ? ORDER BY position",
        (eval_id,),
    ):
        if row["note_type"] == "strength":
            strengths.append(row["text"])
        else:
            improvements.append(row["text"])

    conn.close()
    return {
        "analyst": ev["analyst"],
        "eval_date": ev["eval_date"],
        "skills": skills,
        "mog": mog,
        "strengths": strengths,
        "improvements": improvements,
    }


# ──────────────────────────────────────────────
# NAVEGAÇÃO
# ──────────────────────────────────────────────
page = st.sidebar.radio(
    "Navegação",
    ["📊 Dashboard", "📝 Nova Avaliação", "➕ Cadastrar Jogador"],
)

# ══════════════════════════════════════════════
# CADASTRAR JOGADOR
# ══════════════════════════════════════════════
if page == "➕ Cadastrar Jogador":
    st.header("Cadastrar Novo Jogador")
    with st.form("form_player"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Nome completo *")
            position = st.text_input("Posição", placeholder="Ex: Left Winger")
        with c2:
            club = st.text_input("Clube", placeholder="Ex: Houston Dynamo")
            photo_url = st.text_input("URL da foto", placeholder="https://...")
        if st.form_submit_button("💾 Cadastrar", use_container_width=True):
            if not name.strip():
                st.error("Nome é obrigatório.")
            else:
                add_player(name.strip(), position.strip(), club.strip(), photo_url.strip())
                st.success(f"✅ Jogador **{name}** cadastrado!")


# ══════════════════════════════════════════════
# NOVA AVALIAÇÃO
# ══════════════════════════════════════════════
elif page == "📝 Nova Avaliação":
    st.header("Nova Avaliação")
    players_df = get_players()
    if players_df.empty:
        st.warning("Nenhum jogador cadastrado. Vá em **➕ Cadastrar Jogador** primeiro.")
        st.stop()

    with st.form("form_evaluation"):
        ca, cb, cc = st.columns(3)
        with ca:
            player_name = st.selectbox("Jogador", players_df["name"].tolist())
        with cb:
            analyst = st.text_input("Nome do Analista *")
        with cc:
            eval_date = st.date_input("Data da Avaliação", value=date.today())

        st.divider()

        # ── Technical ──
        st.subheader("🎯 Technical")
        tech_cols = st.columns(4)
        tech_values = {}
        for i, skill in enumerate(TECHNICAL_SKILLS):
            with tech_cols[i % 4]:
                tech_values[skill] = st.selectbox(skill, LEVELS, key=f"tech_{skill}")

        st.divider()

        # ── Player-Specific (customizável) ──
        st.subheader("⚡ Player-Specific Indicators")
        st.caption("Digite o nome do atributo e escolha a classificação. Deixe em branco para ignorar.")

        ps_values = {}
        num_ps = 4
        ps_cols_name = st.columns(num_ps)
        ps_cols_level = st.columns(num_ps)

        for i in range(num_ps):
            with ps_cols_name[i]:
                attr_name = st.text_input(
                    f"Atributo {i + 1}",
                    key=f"ps_name_{i}",
                    placeholder=f"Ex: Speed, Defense...",
                )
            with ps_cols_level[i]:
                attr_level = st.selectbox(
                    f"Nível {i + 1}",
                    [""] + LEVELS,
                    key=f"ps_level_{i}",
                )
            if attr_name.strip() and attr_level:
                ps_values[attr_name.strip()] = attr_level

        st.divider()

        # ── Mental ──
        st.subheader("🧠 Mental")
        m_cols = st.columns(4)
        m_values = {}
        for i, skill in enumerate(MENTAL_SKILLS):
            with m_cols[i % 4]:
                m_values[skill] = st.selectbox(skill, LEVELS, key=f"m_{skill}")

        st.divider()

        # ── MoG ──
        st.subheader("📐 Moments of the Game (MoG)")
        mog_cols = st.columns(5)
        mog_values = {}
        for i, cat in enumerate(MOG_CATEGORIES):
            with mog_cols[i]:
                mog_values[cat] = st.slider(cat, 0, 100, 50, key=f"mog_{cat}")

        st.divider()

        # ── Strengths & Improve ──
        col_s, col_i = st.columns(2)
        with col_s:
            st.subheader("💪 My Strengths")
            s1 = st.text_input("Strength 1")
            s2 = st.text_input("Strength 2")
            s3 = st.text_input("Strength 3")
        with col_i:
            st.subheader("📈 Need to Improve")
            i1 = st.text_input("Improvement 1")
            i2 = st.text_input("Improvement 2")
            i3 = st.text_input("Improvement 3")

        st.divider()

        if st.form_submit_button("💾 Salvar Avaliação", use_container_width=True):
            if not analyst.strip():
                st.error("Nome do analista é obrigatório.")
            else:
                pid = int(players_df.loc[players_df["name"] == player_name, "id"].iloc[0])
                save_evaluation(
                    player_id=pid,
                    analyst=analyst.strip(),
                    eval_date=eval_date.isoformat(),
                    skills={
                        "technical": tech_values,
                        "player_specific": ps_values,
                        "mental": m_values,
                    },
                    mog=mog_values,
                    strengths=[s1, s2, s3],
                    improvements=[i1, i2, i3],
                )
                st.success(f"✅ Avaliação de **{player_name}** salva!")
                st.balloons()


# ══════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════
else:
    BADGE_STYLES = {
        "Above Level": {"bg": "#1B5E20", "fg": "#FFFFFF"},
        "Good":        {"bg": "#2E7D32", "fg": "#FFFFFF"},
        "Average":     {"bg": "#E6A817", "fg": "#FFFFFF"},
        "Below Level": {"bg": "#C62828", "fg": "#FFFFFF"},
    }

    st.markdown(
        """
        <style>
        .block-container { max-width: 1320px; }
        .header-bar {
            background: linear-gradient(90deg, #0D47A1, #1565C0);
            padding: 20px 36px; border-radius: 12px;
            display: flex; align-items: center; gap: 18px;
            margin-bottom: 24px;
            box-shadow: 0 4px 16px rgba(13,71,161,0.12);
        }
        .header-bar .logo { font-size: 2rem; }
        .header-bar .header-text { display: flex; flex-direction: column; }
        .header-bar .brand {
            color: #90CAF9; font-size: 0.85rem; font-weight: 600;
            letter-spacing: 2px; text-transform: uppercase;
        }
        .header-bar h1 { color: white; margin: 0; font-size: 1.65rem; font-weight: 800; }
        .card {
            background: white; border-radius: 12px; padding: 20px;
            box-shadow: 0 2px 12px rgba(13,71,161,0.12);
        }
        .player-card { text-align: center; }
        .player-card img {
            border-radius: 10px; width: 100%; max-width: 180px;
            border: 3px solid #90CAF9;
        }
        .player-card .divider {
            width: 50px; height: 3px; background: #1E88E5;
            border-radius: 2px; margin: 10px auto;
        }
        .player-card .label {
            font-size: 0.75rem; color: #78909C;
            text-transform: uppercase; letter-spacing: 1.5px; font-weight: 600;
        }
        .player-card .value {
            font-size: 1.05rem; color: #0D47A1; font-weight: 700; margin-bottom: 10px;
        }
        .section {
            border-radius: 12px; overflow: hidden;
            box-shadow: 0 2px 10px rgba(13,71,161,0.12); margin-bottom: 16px;
        }
        .section-header {
            background: #0D47A1; color: white;
            padding: 10px 20px; font-size: 1.05rem; font-weight: 700;
        }
        .section-body { background: #1E88E5; padding: 14px 16px; }

        /* ── Badge Table — larguras fixas ── */
        .badge-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
        .badge-table td { padding: 8px 4px; vertical-align: middle; }
        .badge-table .cell-label {
            color: white; font-size: 0.88rem; font-weight: 500;
            text-align: right; padding-right: 8px;
            overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        }
        .badge-table .cell-tag { text-align: left; width: 110px; }
        .badge-tag {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 5px;
            font-size: 0.76rem;
            font-weight: 700;
            white-space: nowrap;   /* ← NUNCA quebra linha */
            min-width: 90px;
            text-align: center;
        }

        .text-list { list-style: none; padding: 0; margin: 0; }
        .text-list li {
            color: white; font-size: 0.95rem; font-weight: 600; padding: 5px 0;
            border-bottom: 1px solid rgba(255,255,255,0.15);
        }
        .text-list li:last-child { border-bottom: none; }
        .text-list .num {
            display: inline-block; width: 24px; height: 24px; line-height: 24px;
            text-align: center; background: rgba(255,255,255,0.2);
            border-radius: 50%; font-size: 0.8rem; margin-right: 8px;
        }
        .radar-container {
            background: #0C1F3A; border-radius: 12px;
            box-shadow: 0 2px 10px rgba(13,71,161,0.12);
            overflow: hidden; margin-bottom: 16px;
        }
        .radar-container > div { margin: 0 !important; padding: 0 !important; }
        .no-data-msg {
            text-align: center; padding: 40px 20px; color: #78909C; font-size: 1.1rem;
        }
        .eval-meta {
            background: rgba(13,71,161,0.06); border-radius: 8px;
            padding: 8px 16px; margin-top: 8px;
            font-size: 0.85rem; color: #546E7A;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ── Helpers ──
    def badge_tag(level):
        if not level:
            return ""
        s = BADGE_STYLES.get(level, {"bg": "#616161", "fg": "#FFF"})
        return (
            f'<span class="badge-tag" '
            f'style="background:{s["bg"]};color:{s["fg"]};">'
            f"{level}</span>"
        )

    def render_section(title, body_html):
        return (
            f'<div class="section">'
            f'<div class="section-header">{title}</div>'
            f'<div class="section-body">{body_html}</div>'
            f"</div>"
        )

    def render_badges_table(items, cols=4):
        # Cada col-pair: label column (flexible) + tag column (fixed 110px)
        col_defs = ('<col style="width:auto"><col style="width:110px">') * cols
        rows_html = ""
        for rs in range(0, len(items), cols):
            ri = items[rs: rs + cols]
            cells = ""
            for label, level in ri:
                if label:
                    cells += (
                        f'<td class="cell-label">{label}</td>'
                        f'<td class="cell-tag">{badge_tag(level)}</td>'
                    )
                else:
                    cells += "<td></td><td></td>"
            cells += "<td></td><td></td>" * (cols - len(ri))
            rows_html += f"<tr>{cells}</tr>"
        return (
            f'<table class="badge-table">'
            f"<colgroup>{col_defs}</colgroup>"
            f"{rows_html}</table>"
        )

    def render_list(items):
        if not items:
            return '<span style="color:rgba(255,255,255,0.5);">—</span>'
        li = "".join(
            f'<li><span class="num">{i + 1}</span>{t}</li>'
            for i, t in enumerate(items)
        )
        return f'<ul class="text-list">{li}</ul>'

    # ── Header ──
    st.markdown(
        '<div class="header-bar"><div class="logo">⚽</div>'
        '<div class="header-text"><span class="brand">SGA Performance</span>'
        "<h1>Individual Development Plan</h1></div></div>",
        unsafe_allow_html=True,
    )

    # ── Seletor ──
    players_df = get_players()
    if players_df.empty:
        st.info("Nenhum jogador cadastrado. Vá em **➕ Cadastrar Jogador**.")
        st.stop()

    player_name = st.selectbox("Select Player", players_df["name"].tolist())
    player_row = players_df[players_df["name"] == player_name].iloc[0]
    evaluation = get_latest_evaluation(int(player_row["id"]))

    left_col, right_col = st.columns([1, 3], gap="large")

    # ── COLUNA ESQUERDA ──
    with left_col:
        photo = player_row["photo_url"] or "https://via.placeholder.com/180x220/0D47A1/FFFFFF?text=No+Photo"
        st.markdown(
            f'<div class="card player-card">'
            f'<img src="{photo}" alt="{player_name}">'
            f'<div class="divider"></div>'
            f'<div class="label">Position</div>'
            f'<div class="value">{player_row["position"] or "—"}</div>'
            f'<div class="label">Club</div>'
            f'<div class="value">{player_row["club"] or "—"}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )

        if evaluation and evaluation["mog"]:
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            mog = evaluation["mog"]
            cats = list(mog.keys())
            vals = list(mog.values())
            cats_display = []
            for c in cats:
                # Quebra nomes longos em 2 linhas
                if len(c) > 12:
                    parts = c.rsplit(" ", 1)
                    cats_display.append("<br>".join(parts))
                else:
                    cats_display.append(c)
            cats_display.append(cats_display[0])
            vals_c = vals + [vals[0]]

            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=vals_c, theta=cats_display, fill="toself",
                fillcolor="rgba(100,181,246,0.30)",
                line=dict(color="#64B5F6", width=2.5),
                marker=dict(size=6, color="#64B5F6"),
            ))
            fig.update_layout(
                title=dict(
                    text="<b>MoG – Moments of the Game</b>",
                    font=dict(size=15, color="white"), x=0.5, y=0.98,
                ),
                polar=dict(
                    bgcolor="rgba(255,255,255,0.03)",
                    domain=dict(x=[0.15, 0.85], y=[0.0, 0.82]),
                    radialaxis=dict(
                        visible=True, range=[0, 100], showticklabels=False,
                        gridcolor="rgba(255,255,255,0.10)",
                    ),
                    angularaxis=dict(
                        gridcolor="rgba(255,255,255,0.10)",
                        tickfont=dict(size=11, color="#CFD8DC"),
                        rotation=90,
                    ),
                ),
                paper_bgcolor="#0C1F3A", plot_bgcolor="#0C1F3A",
                showlegend=False,
                margin=dict(l=60, r=60, t=55, b=50),
                height=440,
            )
            st.markdown('<div class="radar-container">', unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            st.markdown("</div>", unsafe_allow_html=True)

    # ── COLUNA DIREITA ──
    with right_col:
        if not evaluation:
            st.markdown(
                '<div class="card no-data-msg">'
                "📋 Nenhuma avaliação encontrada.<br>"
                "Vá em <b>📝 Nova Avaliação</b> para criar."
                "</div>",
                unsafe_allow_html=True,
            )
            st.stop()

        sk = evaluation["skills"]

        # Technical (fixo)
        tech_items = [(s, sk.get("technical", {}).get(s, "")) for s in TECHNICAL_SKILLS]
        st.markdown(
            render_section("Technical", render_badges_table(tech_items, 4)),
            unsafe_allow_html=True,
        )

        # Player-Specific (dinâmico — vem do que o analista digitou)
        ps_data = sk.get("player_specific", {})
        ps_items = [(name, level) for name, level in ps_data.items()]
        # Padda até 4 slots para manter alinhamento
        while len(ps_items) < 4:
            ps_items.append(("", ""))
        st.markdown(
            render_section("Player-Specific Indicators", render_badges_table(ps_items, 4)),
            unsafe_allow_html=True,
        )

        # Mental (fixo)
        m_items = [(s, sk.get("mental", {}).get(s, "")) for s in MENTAL_SKILLS]
        while len(m_items) < 4:
            m_items.append(("", ""))
        st.markdown(
            render_section("Mental", render_badges_table(m_items, 4)),
            unsafe_allow_html=True,
        )

        # Strengths & Improve
        sc, ic = st.columns(2, gap="medium")
        with sc:
            st.markdown(
                render_section("My Strengths", render_list(evaluation["strengths"])),
                unsafe_allow_html=True,
            )
        with ic:
            st.markdown(
                render_section("Need to Improve", render_list(evaluation["improvements"])),
                unsafe_allow_html=True,
            )

        # Meta da avaliação
        st.markdown(
            f'<div class="eval-meta">'
            f'📅 <b>Avaliação:</b> {evaluation["eval_date"]} &nbsp;•&nbsp; '
            f'👤 <b>Analista:</b> {evaluation["analyst"]}'
            f"</div>",
            unsafe_allow_html=True,
        )
