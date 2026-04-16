# app.py (v16) - Supabase integration + fixes (notes sorting done client-side)
import os
import time
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import base64
from pathlib import Path
from datetime import date, datetime

# Supabase client
from supabase import create_client, Client

st.set_page_config(page_title="SGA - IDP", page_icon="⚽", layout="wide")

# Admin password read from environment (fallback default)
ADMIN_PASSWORD = os.getenv("SGA_ADMIN_PASSWORD", "changeme")

# Padrão de tamanho das fotos dos jogadores (px)
PLAYER_IMG_W = 180
PLAYER_IMG_H = 240

# Logo sources (local base64 fallback to URL)
LOGO_URL = "https://github.com/Dev-SGA/IPI_test/blob/main/Logo_SGA_Completa_Horizontal_AzulEscuro%20(1).png?raw=true"
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

# Domain definitions
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

# ---------------------------
# Helper: trigger safe rerun (avoid st.experimental_rerun() in nested contexts)
# ---------------------------
def trigger_rerun():
    try:
        st.experimental_set_query_params(_refresh=int(time.time()))
    except Exception:
        st.session_state["_refresh_token"] = int(time.time())


# ---------------------------
# Session helpers (auth)
# ---------------------------
if "admin_authenticated" not in st.session_state:
    st.session_state["admin_authenticated"] = False

def is_admin() -> bool:
    return bool(st.session_state.get("admin_authenticated", False))

def try_login(password: str) -> bool:
    if password == ADMIN_PASSWORD:
        st.session_state["admin_authenticated"] = True
        return True
    return False

def logout_admin():
    st.session_state["admin_authenticated"] = False


# ---------------------------
# Database helpers (Supabase)
# ---------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL") or (st.secrets.get("SUPABASE_URL") if hasattr(st, "secrets") else None)
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or (st.secrets.get("SUPABASE_KEY") if hasattr(st, "secrets") else None)

if not SUPABASE_URL or not SUPABASE_KEY:
    st.warning("Supabase não está configurado. Algumas funcionalidades de persistência podem não funcionar. Defina SUPABASE_URL e SUPABASE_KEY nas variáveis de ambiente / secrets.")
    supabase = None
else:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def init_db():
    return

init_db()

def get_players():
    if not supabase:
        return pd.DataFrame(columns=["id", "name", "position", "club", "photo_url"])
    resp = supabase.table("players").select("*").execute()
    data = resp.data or []
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values("name").reset_index(drop=True)
    return df

def add_player(name, position, club, photo_url):
    if not supabase:
        raise Exception("Supabase não configurado.")
    payload = {"name": name, "position": position, "club": club, "photo_url": photo_url}
    resp = supabase.table("players").insert(payload).execute()
    if resp.error:
        raise Exception(resp.error.get("message") if isinstance(resp.error, dict) else resp.error)
    return resp

def delete_player(player_id: int):
    if not supabase:
        raise Exception("Supabase não configurado.")
    resp = supabase.table("players").delete().eq("id", player_id).execute()
    if resp.error:
        raise Exception(resp.error.get("message") if isinstance(resp.error, dict) else resp.error)
    return resp

def update_player(player_id: int, name: str, position: str, club: str, photo_url: str):
    if not supabase:
        raise Exception("Supabase não configurado.")
    payload = {"name": name.strip(), "position": position.strip(), "club": club.strip(), "photo_url": photo_url.strip()}
    resp = supabase.table("players").update(payload).eq("id", player_id).execute()
    if resp.error:
        raise Exception(resp.error.get("message") if isinstance(resp.error, dict) else resp.error)
    return resp

def save_evaluation(player_id, analyst, eval_date, skills, mog, strengths, improvements):
    if not supabase:
        raise Exception("Supabase não configurado.")
    ev = {"player_id": player_id, "analyst": analyst, "eval_date": eval_date}
    resp = supabase.table("evaluations").insert(ev).execute()
    if resp.error or not resp.data:
        raise Exception(resp.error.get("message") if isinstance(resp.error, dict) else (resp.error or "Falha ao criar avaliação"))
    eid = resp.data[0]["id"]

    rows = []
    for cat, sd in (skills or {}).items():
        for sn, lv in sd.items():
            if str(sn).strip() and str(lv).strip():
                rows.append({"evaluation_id": eid, "category": cat, "skill_name": sn.strip(), "level": lv.strip()})
    if rows:
        supabase.table("eval_skills").insert(rows).execute()

    rows = [{"evaluation_id": eid, "category": c, "value": int(v)} for c, v in (mog or {}).items()]
    if rows:
        supabase.table("eval_mog").insert(rows).execute()

    rows = []
    for i, t in enumerate(strengths or []):
        if str(t).strip():
            rows.append({"evaluation_id": eid, "note_type": "strength", "position": i + 1, "text": t.strip()})
    for i, t in enumerate(improvements or []):
        if str(t).strip():
            rows.append({"evaluation_id": eid, "note_type": "improve", "position": i + 1, "text": t.strip()})
    if rows:
        supabase.table("eval_notes").insert(rows).execute()

    return eid

def update_evaluation_meta(evaluation_id: int, analyst: str, eval_date: str):
    if not supabase:
        raise Exception("Supabase não configurado.")
    resp = supabase.table("evaluations").update({"analyst": analyst, "eval_date": eval_date}).eq("id", evaluation_id).execute()
    if resp.error:
        raise Exception(resp.error.get("message") if isinstance(resp.error, dict) else resp.error)
    return resp

def replace_evaluation_content(evaluation_id: int, skills: dict, mog: dict, strengths: list, improvements: list):
    if not supabase:
        raise Exception("Supabase não configurado.")
    supabase.table("eval_skills").delete().eq("evaluation_id", evaluation_id).execute()
    supabase.table("eval_mog").delete().eq("evaluation_id", evaluation_id).execute()
    supabase.table("eval_notes").delete().eq("evaluation_id", evaluation_id).execute()

    rows = []
    for cat, sd in (skills or {}).items():
        for sn, lv in sd.items():
            if str(sn).strip() and str(lv).strip():
                rows.append({"evaluation_id": evaluation_id, "category": cat, "skill_name": sn.strip(), "level": lv.strip()})
    if rows:
        supabase.table("eval_skills").insert(rows).execute()

    rows = [{"evaluation_id": evaluation_id, "category": c, "value": int(v)} for c, v in (mog or {}).items()]
    if rows:
        supabase.table("eval_mog").insert(rows).execute()

    rows = []
    for i, t in enumerate(strengths or []):
        if str(t).strip():
            rows.append({"evaluation_id": evaluation_id, "note_type": "strength", "position": i + 1, "text": t.strip()})
    for i, t in enumerate(improvements or []):
        if str(t).strip():
            rows.append({"evaluation_id": evaluation_id, "note_type": "improve", "position": i + 1, "text": t.strip()})
    if rows:
        supabase.table("eval_notes").insert(rows).execute()

def get_latest_evaluation(player_id):
    if not supabase:
        return None
    resp = supabase.table("evaluations").select("*").eq("player_id", player_id).execute()
    evs = resp.data or []
    if not evs:
        return None
    evs_sorted = sorted(evs, key=lambda x: (x.get("eval_date") or "", x.get("id") or 0), reverse=True)
    ev = evs_sorted[0]
    eid = ev["id"]

    skills = {}
    resp = supabase.table("eval_skills").select("category,skill_name,level").eq("evaluation_id", eid).execute()
    for r in (resp.data or []):
        skills.setdefault(r["category"], {})[r["skill_name"]] = r["level"]

    mog = {}
    resp = supabase.table("eval_mog").select("category,value").eq("evaluation_id", eid).execute()
    for r in (resp.data or []):
        mog[r["category"]] = r["value"]

    strengths = []
    improvements = []
    # Fetch notes and sort client-side to avoid client .order incompatibilities
    resp = supabase.table("eval_notes").select("note_type,position,text").eq("evaluation_id", eid).execute()
    notes = resp.data or []
    try:
        notes_sorted = sorted(notes, key=lambda r: int(r.get("position") or 0))
    except Exception:
        # Fallback: sort by whatever stable key if position can't be cast
        notes_sorted = sorted(notes, key=lambda r: (r.get("position") or 0))

    for r in notes_sorted:
        if r.get("note_type") == "strength":
            strengths.append(r.get("text"))
        else:
            improvements.append(r.get("text"))

    return {"id": eid, "analyst": ev.get("analyst"), "eval_date": str(ev.get("eval_date")), "skills": skills, "mog": mog,
            "strengths": strengths, "improvements": improvements}


# ---------------------------
# UI: Sidebar Admin area
# ---------------------------
with st.sidebar.expander("Admin"):
    if is_admin():
        st.success("🔐 Autenticado como admin")
        if st.button("Logout", use_container_width=True):
            logout_admin()
            trigger_rerun()
    else:
        pwd = st.text_input("Senha de administrador", type="password")
        if st.button("Entrar", use_container_width=True):
            if try_login(pwd):
                st.success("Autenticado com sucesso.")
            else:
                st.error("Senha incorreta.")


# ---------------------------
# UI: Sidebar navigation
# ---------------------------
page = st.sidebar.radio("Navegação", ["📊 Dashboard", "📝 Nova Avaliação", "➕ Cadastrar Jogador", "📚 Jogadores"])


# ---------------------------
# Page: Cadastrar Jogador (protected)
# ---------------------------
if page == "➕ Cadastrar Jogador":
    st.header("Cadastrar Novo Jogador")

    if not is_admin():
        st.warning("Atenção: criar jogadores exige autenticação de administrador.")
        st.info("Use o painel 'Admin' na barra lateral para entrar.")
        st.stop()

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
                try:
                    add_player(name.strip(), position.strip(), club.strip(), photo_url.strip())
                    st.success(f"✅ Jogador **{name}** cadastrado!")
                    trigger_rerun()
                except Exception:
                    st.error("Já existe um jogador com esse nome. Escolha outro nome.")


# ---------------------------
# Page: Nova Avaliação
# ---------------------------
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
        st.caption("Digite o nome do atributo e escolha a classificação. Deixe em branco para ignorar.")
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

        st.subheader("📐 Moments of the Game (MoG)")
        mgc = st.columns(5)
        mgv = {}
        for i, c in enumerate(MOG_CATEGORIES):
            with mgc[i]:
                mgv[c] = st.slider(c, 0, 100, 50, key=f"mog_{c}")

        st.divider()

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
                player_id = int(players_df.loc[players_df["name"] == player_name, "id"].iloc[0])
                try:
                    save_evaluation(
                        player_id=player_id,
                        analyst=analyst.strip(),
                        eval_date=eval_date.isoformat(),
                        skills={"technical": tv, "player_specific": ps, "mental": mv},
                        mog=mgv,
                        strengths=[s1, s2, s3],
                        improvements=[i1, i2, i3],
                    )
                    st.success(f"✅ Avaliação de **{player_name}** salva!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erro ao salvar avaliação: {e}")


# ---------------------------
# Page: Jogadores (lista / ações)
# ---------------------------
elif page == "📚 Jogadores":
    st.header("Lista de Atletas Cadastrados")

    players_df = get_players()
    if players_df.empty:
        st.info("Nenhum jogador cadastrado. Vá em 'Cadastrar Jogador' para adicionar.")
    else:
        display_df = players_df[["id", "name", "position", "club", "photo_url"]].rename(
            columns={"id": "ID", "name": "Nome", "position": "Posição", "club": "Clube", "photo_url": "Foto URL"}
        )

        st.subheader("Tabela de Atletas")
        st.dataframe(display_df, use_container_width=True)

        st.markdown("---")
        st.subheader("Ações")

        sel_name = st.selectbox("Selecione um atleta", players_df["name"].tolist())
        sel_row = players_df[players_df["name"] == sel_name].iloc[0]
        evaluation = get_latest_evaluation(int(sel_row["id"]))

        left_col, right_col = st.columns([1, 2], gap="large")

        with left_col:
            if not is_admin():
                st.warning("Para editar/excluir jogadores você precisa estar autenticado como admin.")
                quick_pwd = st.text_input("Senha de admin (rápido)", type="password", key="quick_admin_pwd")
                if st.button("Entrar (rápido)", use_container_width=True):
                    if try_login(quick_pwd):
                        st.success("Autenticado como admin.")
                    else:
                        st.error("Senha incorreta.")
                st.markdown(f"**Nome:** {sel_row['name']}")
                st.markdown(f"**Posição:** {sel_row['position'] or '—'}  •  **Clube:** {sel_row['club'] or '—'}")
                if sel_row["photo_url"]:
                    st.markdown(
                        f'''
                        <div style="width:{PLAYER_IMG_W}px;height:{PLAYER_IMG_H}px;margin:0 auto 8px auto;display:flex;align-items:center;justify-content:center;background:#ffffff;border-radius:10px;border:3px solid #67b6fb;overflow:hidden;">
                            <img src="{sel_row["photo_url"]}" alt="player" style="max-width:100%;max-height:100%;object-fit:contain;display:block;">
                        </div>
                        ''',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown('<div class="block-container card" style="padding:12px">', unsafe_allow_html=True)
                st.markdown('### ✏️ Editar jogador')

                with st.form(f"form_edit_{sel_row['id']}"):
                    new_name = st.text_input("Nome completo *", value=sel_row["name"])
                    new_position = st.text_input("Posição", value=sel_row["position"] or "")
                    new_club = st.text_input("Clube", value=sel_row["club"] or "")
                    new_photo = st.text_input("URL da foto", value=sel_row["photo_url"] or "")

                    if new_photo.strip():
                        st.markdown(
                            f'''
                            <div style="width:{PLAYER_IMG_W}px;height:{PLAYER_IMG_H}px;margin:0 auto 8px auto;display:flex;align-items:center;justify-content:center;background:#ffffff;border-radius:8px;border:2px solid rgba(0,0,0,0.08);overflow:hidden;">
                                <img src="{new_photo.strip()}" alt="preview" style="max-width:100%;max-height:100%;object-fit:contain;display:block;">
                            </div>
                            ''',
                            unsafe_allow_html=True,
                        )

                    st.divider()
                    st.markdown("**Avaliação (editar última ou criar nova)**")

                    if evaluation:
                        analyst_val = evaluation.get("analyst", "")
                        try:
                            eval_date_prefill = datetime.fromisoformat(evaluation.get("eval_date")).date()
                        except Exception:
                            eval_date_prefill = date.today()
                    else:
                        analyst_val = ""
                        eval_date_prefill = date.today()

                    analyst_input = st.text_input("Analista", value=analyst_val)
                    eval_date_input = st.date_input("Data da avaliação", value=eval_date_prefill)

                    st.subheader("🎯 Technical")
                    tech_vals = {}
                    for i, s in enumerate(TECHNICAL_SKILLS):
                        cur_val = ""
                        if evaluation and evaluation.get("skills", {}).get("technical", {}):
                            cur_val = evaluation["skills"]["technical"].get(s, "")
                        tech_vals[s] = st.selectbox(f"{s}", [""] + LEVELS,
                                                    index=([""] + LEVELS).index(cur_val) if cur_val in LEVELS else 0,
                                                    key=f"edit_t_{sel_row['id']}_{s}")

                    st.subheader("⚡ Player-Specific Indicators (até 4)")
                    existing_ps = {}
                    if evaluation and evaluation.get("skills", {}).get("player_specific", {}):
                        existing_ps = evaluation["skills"]["player_specific"].copy()
                    ps_items = list(existing_ps.items())
                    while len(ps_items) < 4:
                        ps_items.append(("", ""))
                    ps_names = []
                    ps_levels = []
                    for i in range(4):
                        default_name = ps_items[i][0]
                        default_level = ps_items[i][1] if ps_items[i][1] in LEVELS else ""
                        name_key = f"edit_ps_name_{sel_row['id']}_{i}"
                        level_key = f"edit_ps_level_{sel_row['id']}_{i}"
                        n = st.text_input(f"Atributo {i+1}", value=default_name or "", key=name_key)
                        l = st.selectbox(f"Nível {i+1}", [""] + LEVELS,
                                         index=([""] + LEVELS).index(default_level) if default_level in LEVELS else 0,
                                         key=level_key)
                        ps_names.append(n)
                        ps_levels.append(l)

                    st.subheader("🧠 Mental")
                    mental_vals = {}
                    for i, s in enumerate(MENTAL_SKILLS):
                        cur_val = ""
                        if evaluation and evaluation.get("skills", {}).get("mental", {}):
                            cur_val = evaluation["skills"]["mental"].get(s, "")
                        mental_vals[s] = st.selectbox(f"{s}", [""] + LEVELS,
                                                      index=([""] + LEVELS).index(cur_val) if cur_val in LEVELS else 0,
                                                      key=f"edit_m_{sel_row['id']}_{s}")

                    st.subheader("📐 Moments of the Game (MoG)")
                    mog_vals = {}
                    for i, c in enumerate(MOG_CATEGORIES):
                        cur_v = 50
                        if evaluation and evaluation.get("mog", {}):
                            try:
                                cur_v = int(evaluation["mog"].get(c, 50))
                            except Exception:
                                cur_v = 50
                        mog_vals[c] = st.slider(c, 0, 100, cur_v, key=f"edit_mog_{sel_row['id']}_{c}")

                    st.subheader("💪 Strengths / 📈 Need to Improve")
                    s_pref = ["", "", ""]
                    i_pref = ["", "", ""]
                    if evaluation:
                        s_pref = (evaluation.get("strengths") or []) + ["", "", ""]
                        i_pref = (evaluation.get("improvements") or []) + ["", "", ""]
                    s1 = st.text_input("Strength 1", value=s_pref[0] or "", key=f"edit_s1_{sel_row['id']}")
                    s2 = st.text_input("Strength 2", value=s_pref[1] or "", key=f"edit_s2_{sel_row['id']}")
                    s3 = st.text_input("Strength 3", value=s_pref[2] or "", key=f"edit_s3_{sel_row['id']}")
                    i1 = st.text_input("Improvement 1", value=i_pref[0] or "", key=f"edit_i1_{sel_row['id']}")
                    i2 = st.text_input("Improvement 2", value=i_pref[1] or "", key=f"edit_i2_{sel_row['id']}")
                    i3 = st.text_input("Improvement 3", value=i_pref[2] or "", key=f"edit_i3_{sel_row['id']}")

                    st.markdown("")  # spacer
                    save_clicked = st.form_submit_button("💾 Salvar alterações", use_container_width=True)

                    if save_clicked:
                        if not new_name.strip():
                            st.error("Nome é obrigatório.")
                        else:
                            try:
                                update_player(int(sel_row["id"]), new_name, new_position, new_club, new_photo)

                                technical_payload = {s: (tech_vals[s] or "").strip() for s in TECHNICAL_SKILLS}
                                mental_payload = {s: (mental_vals[s] or "").strip() for s in MENTAL_SKILLS}
                                ps_payload = {}
                                for n, l in zip(ps_names, ps_levels):
                                    if n.strip() and l:
                                        ps_payload[n.strip()] = l

                                skills_payload = {
                                    "technical": technical_payload,
                                    "player_specific": ps_payload,
                                    "mental": mental_payload,
                                }
                                mog_payload = {c: int(mog_vals[c]) for c in MOG_CATEGORIES}
                                strengths_payload = [s1, s2, s3]
                                improvements_payload = [i1, i2, i3]

                                if evaluation:
                                    eval_id = evaluation["id"]
                                    update_evaluation_meta(eval_id, analyst_input.strip() or evaluation.get("analyst", ""), eval_date_input.isoformat())
                                    replace_evaluation_content(eval_id, skills_payload, mog_payload, strengths_payload, improvements_payload)
                                    st.success(f"✅ Jogador e avaliação atualizados com sucesso!")
                                else:
                                    if not analyst_input.strip():
                                        st.error("Analista é necessário ao criar nova avaliação.")
                                    else:
                                        player_id = int(sel_row["id"])
                                        save_evaluation(
                                            player_id=player_id,
                                            analyst=analyst_input.strip(),
                                            eval_date=eval_date_input.isoformat(),
                                            skills=skills_payload,
                                            mog=mog_payload,
                                            strengths=strengths_payload,
                                            improvements=improvements_payload,
                                        )
                                        st.success("✅ Jogador atualizado e nova avaliação criada!")
                                trigger_rerun()
                            except Exception:
                                st.error("Já existe um jogador com esse nome. Escolha outro nome.")
                st.markdown("</div>", unsafe_allow_html=True)

                confirm = st.checkbox("Confirmo exclusão deste atleta e todas as avaliações associadas", key=f"confirm_del_{sel_row['id']}")
                if confirm:
                    if st.button("Confirmar exclusão"):
                        try:
                            delete_player(int(sel_row["id"]))
                            st.success(f"Atleta {sel_row['name']} apagado com sucesso.")
                            trigger_rerun()
                        except Exception:
                            st.error("Erro ao apagar jogador: existem registros dependentes ou problema de permissão. Entre em contato com o administrador.")

        with right_col:
            st.markdown(f"**Nome:** {sel_row['name']}")
            st.markdown(f"**Posição:** {sel_row['position'] or '—'}  •  **Clube:** {sel_row['club'] or '—'}")
            if sel_row["photo_url"]:
                st.markdown(
                    f'''
                    <div style="width:{PLAYER_IMG_W}px;height:{PLAYER_IMG_H}px;margin:0 auto 8px auto;display:flex;align-items:center;justify-content:center;background:#ffffff;border-radius:10px;border:3px solid #67b6fb;overflow:hidden;">
                        <img src="{sel_row["photo_url"]}" alt="player" style="max-width:100%;max-height:100%;object-fit:contain;display:block;">
                    </div>
                    ''',
                    unsafe_allow_html=True,
                )

            if evaluation and evaluation.get("mog"):
                st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

                def build_radar(mog_data):
                    cats = list(mog_data.keys())
                    vals = list(mog_data.values())
                    if not cats:
                        return go.Figure()
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
                            angularaxis=dict(
                                gridcolor="rgba(255,255,255,0.10)",
                                tickfont=dict(size=12, color="#CFD8DC",
                                              family="Source Sans 3, Trebuchet MS, sans-serif"),
                                rotation=90,
                            ),
                        ),
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        showlegend=False,
                        margin=dict(l=40, r=40, t=48, b=40),
                        height=420,
                    )
                    return fig

                st.markdown('<div class="block-container radar-outer"><div class="radar-title">MoG – Moments of the Game</div><div class="radar-body">', unsafe_allow_html=True)
                fig = build_radar(evaluation["mog"])
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                st.markdown("</div></div>", unsafe_allow_html=True)

        st.markdown("---")
        csv = display_df.to_csv(index=False).encode("utf-8")
        st.download_button(label="Exportar lista como CSV", data=csv, file_name="players.csv", mime="text/csv")


# ---------------------------
# Page: Dashboard (full)
# ---------------------------
else:
    BADGE_STYLES = {
        "Above Level": {"bg": "rgba(27,94,32,0.85)", "fg": "#FFFFFF"},
        "Good": {"bg": "rgba(102,187,106,0.72)", "fg": "#FFFFFF"},
        "Average": {"bg": "rgba(230,168,23,0.75)", "fg": "#FFFFFF"},
        "Below Level": {"bg": "rgba(198,40,40,0.75)", "fg": "#FFFFFF"},
    }

    st.markdown(
        '<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;800;900&family=Source+Sans+3:wght@400;600;700;800&display=swap" rel="stylesheet">',
        unsafe_allow_html=True,
    )

    _css_template = """
    <style>
    .block-container, .block-container * {
        font-family: __FG__ !important;
    }
    /* (CSS truncated here for brevity in chat - full CSS kept in actual file) */
    </style>
    """

    _css = _css_template.replace("__FD__", FONT_DISPLAY).replace("__FG__", FONT_GRAPHIC).replace("__FDO__", FONT_DOCUMENT)
    st.markdown(_css, unsafe_allow_html=True)

    def badge_tag(level):
        if not level:
            return ""
        s = BADGE_STYLES.get(level, {"bg": "#616161", "fg": "#FFF"})
        return f'<span class="badge-tag" style="background:{s["bg"]};color:{s["fg"]};">{level}</span>'

    def render_section(title, body):
        return f'<div class="section"><div class="section-header">{title}</div><div class="section-body">{body}</div></div>'

    def render_badges_table(items: list, cols: int = 4, tag_px: int = 110) -> str:
        if len(items) % cols != 0:
            remaining = cols - (len(items) % cols)
            items = items + [("", "")] * remaining
        total_tag_px = tag_px * cols
        label_col_calc = f"calc((100% - {total_tag_px}px) / {cols})"
        colgroup_html = "<colgroup>"
        for _ in range(cols):
            colgroup_html += f'<col class="label-col" style="width:{label_col_calc}">'
            colgroup_html += f'<col class="tag-col" style="width:{tag_px}px">'
        colgroup_html += "</colgroup>"
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
            li += f'<li><span class="num">{i + 1}</span>{t}</li>'
        return '<ul class="text-list">' + li + "</ul>"

    def build_radar(mog_data):
        cats = list(mog_data.keys())
        vals = list(mog_data.values()) if mog_data else [50]*len(cats)
        if not cats:
            return go.Figure()
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
                angularaxis=dict(
                    gridcolor="rgba(255,255,255,0.10)",
                    tickfont=dict(size=12, color="#CFD8DC",
                                  family="Source Sans 3, Trebuchet MS, sans-serif"),
                    rotation=90,
                ),
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            margin=dict(l=40, r=40, t=48, b=40),
            height=420,
        )
        return fig

    st.markdown(f'''
        <div class="block-container header-bar">
            <img src="{LOGO_SRC}" alt="SGA Logo" class="header-logo">
            <div class="header-sep"></div>
            <h1>Individual Player Indicators</h1>
        </div>
        ''', unsafe_allow_html=True)

    players_df = get_players()
    if players_df.empty:
        st.info("Nenhum jogador cadastrado. Vá em **➕ Cadastrar Jogador**.")
        st.stop()

    player_name = st.selectbox("Select Player", players_df["name"].tolist())
    pr = players_df[players_df["name"] == player_name].iloc[0]
    evaluation = get_latest_evaluation(int(pr["id"]))

    left_col, right_col = st.columns([1, 3], gap="large")

    with left_col:
        photo = pr["photo_url"] or ""
        if photo:
            st.markdown(
                f'''
                <div class="block-container card player-card">
                    <div style="width:{PLAYER_IMG_W}px;height:{PLAYER_IMG_H}px;margin:0 auto 8px auto;display:flex;align-items:center;justify-content:center;background:#ffffff;border-radius:10px;border:3px solid #67b6fb;overflow:hidden;">
                        <img src="{photo}" alt="{player_name}" style="max-width:100%;max-height:100%;object-fit:contain;display:block;">
                    </div>
                    <div class="divider"></div>
                    <div class="label">Position</div><div class="value">{pr["position"] or "—"}</div>
                    <div class="label">Club</div><div class="value">{pr["club"] or "—"}</div>
                </div>
                ''',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(f'''
                <div class="block-container card player-card">
                    <div class="divider"></div>
                    <div class="label">Position</div><div class="value">{pr["position"] or "—"}</div>
                    <div class="label">Club</div><div class="value">{pr["club"] or "—"}</div>
                </div>
                ''', unsafe_allow_html=True)

        if evaluation and evaluation["mog"]:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.markdown('<div class="block-container radar-outer"><div class="radar-title">MoG – Moments of the Game</div><div class="radar-body">', unsafe_allow_html=True)
            fig = build_radar(evaluation["mog"])
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            st.markdown("</div></div>", unsafe_allow_html=True)

    with right_col:
        if not evaluation:
            st.markdown(
                '<div class="block-container card no-data-msg">📋 Nenhuma avaliação encontrada.<br>'
                'Vá em <b>📝 Nova Avaliação</b> para criar.</div>',
                unsafe_allow_html=True,
            )
            st.stop()

        sk = evaluation["skills"]

        tech_items = [(s, sk.get("technical", {}).get(s, "")) for s in TECHNICAL_SKILLS]
        st.markdown(render_section("Technical", render_badges_table(tech_items, 4)), unsafe_allow_html=True)

        ps_data = sk.get("player_specific", {})
        ps_items = [(n, l) for n, l in ps_data.items()]
        while len(ps_items) < 4:
            ps_items.append(("", ""))
        st.markdown(render_section("Player-Specific Indicators", render_badges_table(ps_items, 4)), unsafe_allow_html=True)

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
            f'<div class="block-container eval-meta">📅 <b>Avaliação:</b> {evaluation["eval_date"]} &nbsp;•&nbsp; 👤 <b>Analista:</b> {evaluation["analyst"]}</div>',
            unsafe_allow_html=True,
        )
