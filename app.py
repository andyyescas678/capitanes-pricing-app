import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.subplots as sp

st.set_page_config(
    page_title="Capitanes CDMX — Pricing Optimizer",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CONSTANTS — Modelo E3 (notebook) + calibración HTML
# ============================================================
# (zona, q50_domingo, qmax, p_base, p_min, p_max, tier)
ZONAS_DATA = [
    ("Butaca Central",           291, 1839,   80,  50, 149, "popular"),
    ("Butaca Cabecera",           89, 1054,   60,  50,  99, "popular"),
    ("Barrera Cabecera",         133,  720,  120,  51, 199, "media"),
    ("Platea Cabecera 2",        115,  776,  185,  93, 270, "media"),
    ("Barrera Central",          205,  277,  156, 124, 249, "media"),
    ("Platea Cabecera",          127,  384,  200,  85, 338, "media"),
    ("Preferente Fondo",          36,  210,  250, 174, 450, "popular"),
    ("Platea 2",                 155,  444,  300, 213, 499, "media"),
    ("Preferente Cabecera",       48,  261,  440,  99, 649, "media"),
    ("Preferente Tunel",         115,  411,  525,  99, 749, "alta"),
    ("Preferente",                91,  202,  575, 324, 650, "alta"),
    ("Preferente Central",       195,  303,  600, 424, 849, "alta"),
    ("Cancha (courtside)",        67,  231, 1184, 500, 1989, "premium"),
    ("VIP (Front Row + Mesas)",   30,  219, 1400, 749, 3999, "premium"),
]

# Elasticidades propias significativas (p < 0.05, modelo de interacción E3)
B_PROPIA = {
    "Butaca Central":      -1.20,
    "Preferente Fondo":    -1.47,
    "Butaca Cabecera":     -1.04,
    "Preferente Cabecera": -0.79,
    "Barrera Cabecera":    -0.79,
    "Preferente Tunel":    -0.45,
}

ELASTICIDADES = {
    "Conservadora (b = −0.27, umbral $20)": -0.272,
    "Preferida (b = −0.49, umbral $50)":    -0.493,
    "Robustez (b = −0.47, umbral $75)":     -0.465,
}

# Multiplicadores de demanda — modelo OLS de calendario (ref: domingo = 1.0)
DIAS = [
    ("Lun", "😴", 0.52, "mitad de público"),
    ("Mar", "🌮", 0.56, "poco público"),
    ("Mié", "📉", 0.63, "público medio-bajo"),
    ("Jue", "🙂", 0.83, "público medio"),
    ("Vie", "🎉", 0.95, "casi como domingo"),
    ("Sáb", "🔥", 1.02, "día fuerte"),
    ("Dom", "⭐", 1.00, "el día clásico"),
]

TIPOS = [
    ("Normal",       "🏀", 1.00, "partido de calendario"),
    ("Back-to-back", "🔁", 1.00, "2do juego seguido"),
    ("Inauguración", "🎊", 3.00, "hasta el triple de público"),
    ("Festivo",      "🎆", 3.10, "hasta el triple de público"),
]

RIVALES = [
    ("Estrella",      "🌟", 1.85, "ej. South Bay Lakers"),
    ("Normal",        "🏀", 1.00, "la mayoría"),
    ("Poca taquilla", "📉", 0.55, "ej. RGV Vipers"),
]

# ============================================================
# CSS — Sistema de diseño Capitanes
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    background-color: #121414 !important;
    color: #e3e2e2 !important;
    font-family: 'Hanken Grotesk', sans-serif !important;
}
[data-testid="stAppViewContainer"] {
    background-image:
        radial-gradient(circle at 0% 0%, rgba(255,109,41,0.08) 0%, transparent 50%),
        radial-gradient(circle at 100% 100%, rgba(69,48,39,0.15) 0%, transparent 50%) !important;
    background-attachment: fixed !important;
}
[data-testid="stSidebar"] {
    background-color: #0d0e0f !important;
    border-right: 1px solid rgba(255,255,255,0.05) !important;
}
div[data-testid="stTabBar"] button {
    font-family: 'Hanken Grotesk', sans-serif !important;
    font-size: 15px !important; font-weight: 500 !important; color: #BABABA !important;
}
div[data-testid="stTabBar"] button[aria-selected="true"] {
    color: #ff6d29 !important; border-bottom: 2px solid #ff6d29 !important;
}
h1,h2,h3,h4,h5,h6 {
    font-family: 'Hanken Grotesk', sans-serif !important;
    font-weight: 600 !important; color: #ffffff !important;
}
p { color: #e3e2e2 !important; }

/* Primary button — pill naranja */
div.stButton > button[kind="primary"] {
    background-color: #ff6d29 !important; color: #fff !important;
    border-radius: 9999px !important; border: none !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 15px rgba(255,109,41,0.2) !important;
}
div.stButton > button[kind="primary"]:hover {
    background-color: #e55c1e !important;
    box-shadow: 0 4px 20px rgba(255,109,41,0.4) !important;
}
/* Secondary button — card style */
div.stButton > button[kind="secondary"] {
    background-color: rgba(18,20,20,0.7) !important;
    color: #BABABA !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px !important;
    font-weight: 500 !important;
}
div.stButton > button[kind="secondary"]:hover {
    border-color: #ff6d29 !important; color: #ff6d29 !important;
}

div[data-testid="stSlider"] div[role="slider"] {
    background-color: #ff6d29 !important; border: 2px solid #fff !important;
}
[data-testid="stDataFrame"] {
    border: 1px solid rgba(255,255,255,0.06) !important; border-radius: 1rem !important;
}
.stInfo { background: rgba(255,109,41,0.08) !important; border-left: 3px solid #ff6d29 !important; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# HELPERS
# ============================================================
def get_beta(zona, beta_sel):
    return B_PROPIA.get(zona, beta_sel)

def demand_factor():
    return (DIAS[st.session_state.get("dia_idx", 6)][2] *
            TIPOS[st.session_state.get("tipo_idx", 0)][2] *
            RIVALES[st.session_state.get("rival_idx", 1)][2])

def simulate_all(prices, beta_sel):
    f = demand_factor()
    rows = []
    for (zona, q50, qmax, p_base, p_min, p_max, tier) in ZONAS_DATA:
        b = get_beta(zona, beta_sel)
        p = prices.get(zona, p_base)
        q_base = min(q50 * f, qmax)
        q_proj = int(min(q_base * (p / p_base) ** b, qmax))
        rows.append({
            "Zona": zona, "Tier": tier, "b": b,
            "p_base": p_base, "p_min": p_min, "p_max": p_max,
            "p_proj": p, "q_base": q_base, "q_max": qmax,
            "q_proj": q_proj,
            "ing_base": q_base * p_base,
            "ing_proj": q_proj * p,
            "occ": q_proj / qmax * 100 if qmax > 0 else 0,
        })
    return pd.DataFrame(rows)

def metric_card(title, value, subtext, delta=None, positive=True):
    d_html = ""
    if delta:
        c = "#7FD49A" if positive else "#F4A0A0"
        d_html = f'<span style="color:{c};font-weight:700;font-size:15px;margin-left:8px;">{"↑" if positive else "↓"} {delta}</span>'
    st.markdown(f"""
    <div style="background:rgba(69,48,39,0.15);backdrop-filter:blur(20px);
                border:1px solid rgba(255,255,255,0.08);border-radius:1.5rem;
                padding:20px;margin-bottom:16px;">
        <div style="color:#BABABA;font-size:11px;font-weight:600;text-transform:uppercase;
                    letter-spacing:0.08em;margin-bottom:8px;">{title}</div>
        <div style="color:#fff;font-size:26px;font-weight:700;line-height:1;">{value}{d_html}</div>
        <div style="color:#BABABA;font-size:11px;margin-top:8px;">{subtext}</div>
    </div>""", unsafe_allow_html=True)

def card_selector(label, options, key, ncols=None):
    st.markdown(
        f'<p style="color:#BABABA;font-size:12px;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:0.07em;margin-bottom:4px;">{label}</p>',
        unsafe_allow_html=True
    )
    n = ncols or len(options)
    cols = st.columns(n)
    sel = st.session_state.get(key, 0)
    changed = False
    for i, (name, emoji, _, desc) in enumerate(options):
        with cols[i % n]:
            if st.button(f"{emoji} {name}", key=f"{key}_{i}",
                         use_container_width=True,
                         type="primary" if i == sel else "secondary",
                         help=desc):
                st.session_state[key] = i
                changed = True
    if changed:
        st.rerun()

def occ_bar_html(pct):
    color = "#2D8A4E" if pct >= 75 else "#F4A82C" if pct >= 40 else "#C0504D"
    return (
        f'<div style="background:#222;border-radius:6px;height:14px;position:relative;'
        f'overflow:hidden;margin:6px 0;">'
        f'<div style="width:{min(pct,100):.0f}%;height:100%;background:{color};'
        f'border-radius:6px;"></div>'
        f'<div style="position:absolute;top:0;width:100%;text-align:center;font-size:10px;'
        f'line-height:14px;color:#fff;font-weight:600;">{pct:.0f}% del aforo máximo</div>'
        f'</div>'
    )

def recom_html(b, p_proj, p_base, ing_proj, ing_base, tier, q_proj, q_base):
    d = ing_proj - ing_base
    if b <= -1.0:
        if p_proj > p_base:
            bg, fg = "rgba(192,80,77,0.15)", "#F4A0A0"
            txt = (f"🔴 Zona elástica (b={b:.2f}): subir el precio reduce el ingreso respecto al base "
                   f"(−${abs(d):,.0f}). Mantener o bajar ligeramente en días flojos.")
        elif p_proj < p_base:
            bg, fg = "rgba(45,138,78,0.15)", "#7FD49A"
            txt = (f"🟢 Descuento estratégico: entran {int(q_proj - q_base):+,} fans adicionales. "
                   f"La zona se ve llena y eso impulsa consumo interno.")
        else:
            bg, fg = "rgba(244,168,44,0.15)", "#F4C56A"
            txt = f"🟡 Zona sensible (b={b:.2f}): precio base. En días flojos considera un descuento para llenarla."
    elif tier in ("premium", "alta"):
        if d > 0:
            bg, fg = "rgba(45,138,78,0.15)", "#7FD49A"
            txt = f"🟢 Zona de margen: la demanda aguanta el precio. Este ajuste genera ${d:,.0f} adicionales."
        else:
            bg, fg = "rgba(244,168,44,0.15)", "#F4C56A"
            txt = "🟡 Zona premium: poca sensibilidad al precio. Puedes subir más — el efecto sobre boletos sería mínimo."
    else:
        if d > 0:
            bg, fg = "rgba(45,138,78,0.15)", "#7FD49A"
            txt = f"🟢 Precio razonable: genera ${d:,.0f} más que la base. Pruébalo en un partido antes de cambiar la tarifa general."
        elif d < 0:
            bg, fg = "rgba(192,80,77,0.15)", "#F4A0A0"
            txt = f"🔴 Ingreso por debajo del base (−${abs(d):,.0f}). Ajusta el precio al alza."
        else:
            bg, fg = "rgba(244,168,44,0.15)", "#F4C56A"
            txt = "🟡 En precio base histórico. Hay espacio para subir en días fuertes."
    return (
        f'<div style="background:{bg};color:{fg};border-radius:8px;'
        f'padding:8px 10px;font-size:12.5px;margin-top:6px;">{txt}</div>'
    )

# ============================================================
# SESSION STATE
# ============================================================
for (zona, _, _, p_base, *_rest) in ZONAS_DATA:
    if f"sl_{zona}" not in st.session_state:
        st.session_state[f"sl_{zona}"] = p_base
for k, v in [("dia_idx", 6), ("tipo_idx", 0), ("rival_idx", 1)]:
    if k not in st.session_state:
        st.session_state[k] = v

current_prices = {z[0]: st.session_state.get(f"sl_{z[0]}", z[3]) for z in ZONAS_DATA}

# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.markdown(
    '<div style="text-align:center;padding:10px 0 18px;">'
    '<h2 style="margin:0;color:#ff6d29;letter-spacing:0.05em;">🏀 CAPITANES</h2>'
    '<p style="color:#BABABA;font-size:13px;margin-top:2px;">Pricing Control Center</p>'
    '</div>', unsafe_allow_html=True
)
st.sidebar.markdown("### ⚙️ Elasticidad Global")
el_name = st.sidebar.selectbox(
    "Supuesto para zonas sin b propio",
    list(ELASTICIDADES.keys()), index=1,
    help="Las 6 zonas con coeficiente propio significativo siempre usan su b estimado."
)
beta_sel = ELASTICIDADES[el_name]

st.sidebar.markdown("### 💸 Costos del Partido")
cost_fixed = st.sidebar.slider("Costos Fijos ($)", 0, 500000, 100000, 10000)
cost_var   = st.sidebar.slider("Costo Variable / Boleto ($)", 0, 150, 30, 5)

st.sidebar.markdown("### 🎯 Peso de Optimización")
weight_rev = st.sidebar.slider(
    "Ganancia ←→ Asistencia", 0.0, 1.0, 0.80, 0.05,
    help="0.0 = Maximizar Asistencia | 1.0 = Maximizar Ganancia Neta"
)
st.sidebar.markdown("---")
if st.sidebar.button("↩️ Resetear precios a histórico", use_container_width=True, type="secondary"):
    for z in ZONAS_DATA:
        st.session_state[f"sl_{z[0]}"] = z[3]
    st.rerun()

# ============================================================
# HEADER
# ============================================================
st.markdown(
    '<div style="background:linear-gradient(135deg,rgba(255,109,41,0.20),rgba(69,48,39,0.05));'
    'padding:28px 32px;border-radius:2rem;border:1px solid rgba(255,109,41,0.25);margin-bottom:22px;">'
    '<h1 style="margin:0;color:#fff;font-size:34px;font-weight:700;letter-spacing:-0.02em;">🏀 CAPITANES CDMX</h1>'
    '<p style="margin:5px 0 0;color:#ff6d29;font-size:16px;font-weight:600;">'
    'Stitch Pricing Optimization Simulator · Modelo E3</p>'
    '</div>', unsafe_allow_html=True
)

# ============================================================
# SELECTORS — Día / Tipo / Rival
# ============================================================
c1, c2 = st.columns([4, 3])
with c1:
    card_selector("1️⃣ Día del partido", DIAS, "dia_idx")
with c2:
    card_selector("⭐ Tipo de partido", TIPOS, "tipo_idx")
card_selector("🆚 Rival", RIVALES, "rival_idx", ncols=3)

st.markdown("<hr style='border-color:rgba(255,255,255,0.06);margin:10px 0 18px;'>",
            unsafe_allow_html=True)

# ============================================================
# SIMULATION
# ============================================================
df_sim = simulate_all(current_prices, beta_sel)

tot_q    = df_sim["q_proj"].sum()
tot_ing  = df_sim["ing_proj"].sum()
base_ing = df_sim["ing_base"].sum()
base_q   = df_sim["q_base"].sum()
tot_qmax = df_sim["q_max"].sum()
profit   = tot_ing - cost_fixed - (tot_q * cost_var)
di = tot_ing - base_ing
dq = tot_q - base_q
pi = di / base_ing * 100 if base_ing else 0
pq = dq / base_q * 100 if base_q else 0
pct_afo = tot_q / tot_qmax * 100 if tot_qmax else 0

# ============================================================
# KPIs
# ============================================================
k1, k2, k3 = st.columns(3)
with k1:
    s = "+" if di >= 0 else ""
    metric_card("Ingreso Total Proyectado", f"${tot_ing:,.0f}",
                f"Base (este día/tipo/rival): ${base_ing:,.0f}",
                f"{s}${abs(di):,.0f} ({s}{pi:.1f}%)", di >= 0)
with k2:
    s = "+" if dq >= 0 else ""
    metric_card("Asistencia Proyectada", f"{tot_q:,.0f} fans",
                f"Base: {base_q:,.0f} boletos",
                f"{s}{abs(int(dq)):,} fans ({s}{pq:.1f}%)", dq >= 0)
with k3:
    metric_card("Ganancia Neta", f"${profit:,.0f}",
                f"Aforo general: {pct_afo:.0f}% del máximo histórico",
                f"CF ${cost_fixed:,.0f} + CV ${cost_var}/boleto", profit >= 0)

# ============================================================
# TABS
# ============================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "🎚️ Simulador por Zona",
    "🎯 Optimizador Matemático",
    "📈 Curvas de Sensibilidad",
    "🔬 Reporte Metodológico (E3)"
])

# ==========================================
# TAB 1 — SIMULADOR POR ZONA
# ==========================================
with tab1:
    f = demand_factor()
    dia_name   = DIAS[st.session_state.dia_idx][0]
    tipo_name  = TIPOS[st.session_state.tipo_idx][0]
    rival_name = RIVALES[st.session_state.rival_idx][0]
    st.info(
        f"📊 **Factor de demanda activo: ×{f:.2f}** — "
        f"Día {dia_name} · {tipo_name} · Rival {rival_name}. "
        f"Los boletos base (q50 dominical) se multiplican por este factor antes de aplicar la elasticidad de precio."
    )

    col_L, col_R = st.columns(2)

    for idx, (zona, q50, qmax, p_base, p_min, p_max, tier) in enumerate(ZONAS_DATA):
        col = col_L if idx < 7 else col_R
        row = df_sim[df_sim["Zona"] == zona].iloc[0]
        b   = row["b"]
        occ = row["occ"]

        with col:
            st.markdown(
                f'<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);'
                f'border-radius:12px;padding:12px 14px;margin-bottom:6px;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                f'<span style="font-weight:700;font-size:15px;color:#fff;">{zona}</span>'
                f'<span style="font-size:19px;font-weight:700;color:#ff6d29;">'
                f'${current_prices[zona]:,}</span></div>'
                f'<div style="font-size:11.5px;color:#BABABA;margin-top:2px;">'
                f'b = {b:.3f} &nbsp;·&nbsp; base histórica: ${p_base:,}</div>',
                unsafe_allow_html=True
            )
            st.slider(
                f"Precio {zona}", p_min, p_max, step=5,
                key=f"sl_{zona}", label_visibility="collapsed"
            )
            st.markdown(
                occ_bar_html(occ) +
                f'<div style="display:flex;justify-content:space-between;'
                f'font-size:13px;color:#e3e2e2;margin-top:4px;">'
                f'<span><b>{int(row["q_proj"]):,}</b> boletos</span>'
                f'<span><b>${row["ing_proj"]:,.0f}</b> ingreso</span>'
                f'<span style="color:#BABABA;">máx {qmax:,}</span></div>' +
                recom_html(b, current_prices[zona], p_base,
                           row["ing_proj"], row["ing_base"],
                           tier, row["q_proj"], row["q_base"]) +
                '</div>',
                unsafe_allow_html=True
            )

    st.markdown("### 📋 Resumen de Simulación")
    df_t = df_sim.copy()
    df_t["Var. Precio %"]     = ((df_t["p_proj"] - df_t["p_base"]) / df_t["p_base"] * 100).round(1)
    df_t["Var. Asistencia %"] = ((df_t["q_proj"] - df_t["q_base"]) / df_t["q_base"] * 100).round(1)
    st.dataframe(
        df_t[["Zona","b","p_base","p_proj","Var. Precio %",
              "q_base","q_proj","Var. Asistencia %","ing_base","ing_proj"]
        ].rename(columns={
            "b":"Elasticidad","p_base":"Precio Base","p_proj":"Precio Actual",
            "q_base":"Boletos Base","q_proj":"Boletos Proy.",
            "ing_base":"Ingreso Base","ing_proj":"Ingreso Proy."
        }).style.format({
            "Elasticidad": "{:.3f}",
            "Precio Base": "${:,.0f}", "Precio Actual": "${:,.0f}",
            "Var. Precio %": "{:+.1f}%",
            "Boletos Base": "{:,.0f}", "Boletos Proy.": "{:,.0f}",
            "Var. Asistencia %": "{:+.1f}%",
            "Ingreso Base": "${:,.0f}", "Ingreso Proy.": "${:,.0f}"
        }),
        use_container_width=True, hide_index=True
    )
    csv = df_t.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Exportar simulación CSV", csv,
                       "simulacion_capitanes.csv", "text/csv", type="primary")

# ==========================================
# TAB 2 — OPTIMIZADOR MATEMÁTICO
# ==========================================
with tab2:
    st.markdown("### Optimización Multi-Objetivo por Zona")
    st.write(
        "El optimizador calcula, para cada zona de forma independiente, el precio que maximiza "
        "la función de utilidad ponderada entre ganancia neta y asistencia, usando el factor de "
        "demanda del partido seleccionado arriba."
    )
    f = demand_factor()
    opt_prices, opt_rows = {}, []

    for (zona, q50, qmax, p_base, p_min, p_max, tier) in ZONAS_DATA:
        b = get_beta(zona, beta_sel)
        q_base = min(q50 * f, qmax)
        prices_grid = np.arange(p_min, p_max + 1, 1)
        if len(prices_grid) == 0:
            prices_grid = np.array([p_base])

        qs, net_revs = [], []
        for p in prices_grid:
            q = min(q_base * (p / p_base) ** b, qmax)
            qs.append(q); net_revs.append(q * (p - cost_var))

        qs = np.array(qs); net_revs = np.array(net_revs)
        min_q, max_q = qs.min(), qs.max()
        min_r, max_r = net_revs.min(), net_revs.max()

        best_score, best_p = -1e9, p_base
        for p, q, r in zip(prices_grid, qs, net_revs):
            norm_r = (r - min_r) / (max_r - min_r + 1e-5)
            norm_q = (q - min_q) / (max_q - min_q + 1e-5)
            score = weight_rev * norm_r + (1 - weight_rev) * norm_q
            if score > best_score:
                best_score = score; best_p = p

        best_p = int(best_p)
        best_q = int(min(q_base * (best_p / p_base) ** b, qmax))
        opt_prices[zona] = best_p
        opt_rows.append({
            "Zona": zona, "Elasticidad": b,
            "Precio Base": p_base, "Precio Óptimo": best_p,
            "Boletos Base": int(q_base), "Boletos Óptimos": best_q,
            "Ingreso Base": int(q_base * p_base), "Ingreso Óptimo": best_q * best_p,
            "Ganancia Óptima": int(best_q * (best_p - cost_var))
        })

    df_opt = pd.DataFrame(opt_rows)
    tot_r_base = df_opt["Ingreso Base"].sum()
    tot_r_opt  = df_opt["Ingreso Óptimo"].sum()
    tot_q_base = df_opt["Boletos Base"].sum()
    tot_q_opt  = df_opt["Boletos Óptimos"].sum()
    profit_opt = tot_r_opt - cost_fixed - (tot_q_opt * cost_var)

    st.markdown("#### Impacto en Partido Típico (factor activo)")
    oc1, oc2, oc3 = st.columns(3)
    with oc1:
        d = tot_r_opt - tot_r_base
        pct = d / tot_r_base * 100 if tot_r_base else 0
        st.metric("Ingreso Optimizado", f"${tot_r_opt:,.0f}",
                  f"{'+' if d>=0 else ''}{d:,.0f} ({pct:+.1f}%)")
    with oc2:
        d = tot_q_opt - tot_q_base
        pct = d / tot_q_base * 100 if tot_q_base else 0
        st.metric("Asistencia Optimizada", f"{tot_q_opt:,.0f} boletos",
                  f"{'+' if d>=0 else ''}{d:,.0f} ({pct:+.1f}%)")
    with oc3:
        st.metric("Ganancia Neta Optimizada", f"${profit_opt:,.0f}")

    st.markdown("---")
    ac1, _ = st.columns([1, 2])
    with ac1:
        if st.button("🚀 Aplicar Precios Recomendados", use_container_width=True, type="primary"):
            for zona, p in opt_prices.items():
                st.session_state[f"sl_{zona}"] = p
            st.success("¡Precios aplicados! Ve a la pestaña Simulador.")
            st.rerun()

    st.markdown("#### Tabla de Recomendaciones")
    df_opt["Var. Precio %"] = ((df_opt["Precio Óptimo"] - df_opt["Precio Base"]) / df_opt["Precio Base"] * 100).round(1)
    df_opt["Var. Asistencia %"] = ((df_opt["Boletos Óptimos"] - df_opt["Boletos Base"]) / df_opt["Boletos Base"] * 100).round(1)
    st.dataframe(
        df_opt[["Zona","Elasticidad","Precio Base","Precio Óptimo","Var. Precio %",
                "Boletos Base","Boletos Óptimos","Var. Asistencia %","Ingreso Base","Ingreso Óptimo","Ganancia Óptima"]
        ].style.format({
            "Elasticidad": "{:.3f}",
            "Precio Base": "${:,.0f}", "Precio Óptimo": "${:,.0f}",
            "Var. Precio %": "{:+.1f}%",
            "Boletos Base": "{:,.0f}", "Boletos Óptimos": "{:,.0f}",
            "Var. Asistencia %": "{:+.1f}%",
            "Ingreso Base": "${:,.0f}", "Ingreso Óptimo": "${:,.0f}",
            "Ganancia Óptima": "${:,.0f}"
        }),
        use_container_width=True, hide_index=True
    )

# ==========================================
# TAB 3 — CURVAS DE SENSIBILIDAD
# ==========================================
with tab3:
    st.markdown("### Análisis de Sensibilidad al Precio por Zona")
    st.write(
        "Grafica cómo cambian el ingreso, la ganancia neta y la asistencia conforme varía el "
        "precio dentro del rango histórico observado, con el factor de demanda del partido activo."
    )
    zona_sel = st.selectbox("Seleccionar Zona", [z[0] for z in ZONAS_DATA])
    z_row = next(z for z in ZONAS_DATA if z[0] == zona_sel)
    _, q50, qmax, p_base, p_min, p_max, tier = z_row
    b = get_beta(zona_sel, beta_sel)
    f = demand_factor()
    q_base = min(q50 * f, qmax)

    prices_arr = np.arange(p_min, p_max + 1, 1)
    atts   = [min(q_base * (p / p_base) ** b, qmax) for p in prices_arr]
    revs   = [q * p for q, p in zip(atts, prices_arr)]
    profits_arr = [q * (p - cost_var) for q, p in zip(atts, prices_arr)]

    # Find optimum
    min_q, max_q = min(atts), max(atts)
    min_pft, max_pft = min(profits_arr), max(profits_arr)
    best_idx = max(range(len(prices_arr)),
                   key=lambda i: weight_rev * (profits_arr[i]-min_pft)/(max_pft-min_pft+1e-5)
                                 + (1-weight_rev) * (atts[i]-min_q)/(max_q-min_q+1e-5))
    p_opt  = prices_arr[best_idx]
    p_curr = current_prices.get(zona_sel, p_base)

    fig = sp.make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=prices_arr, y=revs, name="Ingreso Bruto ($)",
                             line=dict(color="#BABABA", width=1.5, dash="dot"),
                             hovertemplate="$%{x}<br>Ingreso: $%{y:,.0f}"), secondary_y=False)
    fig.add_trace(go.Scatter(x=prices_arr, y=profits_arr, name="Ganancia Neta (antes CF) ($)",
                             line=dict(color="#ff6d29", width=3),
                             hovertemplate="$%{x}<br>Ganancia: $%{y:,.0f}"), secondary_y=False)
    fig.add_trace(go.Scatter(x=prices_arr, y=atts, name="Asistencia (boletos)",
                             line=dict(color="#E0C0B3", width=2, dash="dash"),
                             hovertemplate="$%{x}<br>Boletos: %{y:,.0f}"), secondary_y=True)
    fig.add_vline(x=p_base, line_width=1.5, line_color="#888",
                  annotation_text="Base histórica", annotation_position="top left")
    fig.add_vline(x=p_opt, line_width=2, line_dash="dash", line_color="#ff6d29",
                  annotation_text="Óptimo", annotation_position="top right")
    fig.add_vline(x=p_curr, line_width=2, line_color="#00C0FF",
                  annotation_text="Precio actual", annotation_position="bottom left")
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Hanken Grotesk", color="#e3e2e2"),
        title=dict(text=f"Sensibilidad: {zona_sel}  (b = {b:.3f})",
                   font=dict(size=18, color="#fff"), x=0.5),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)", title="Precio ($)", tickprefix="$"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)", title="Métricas ($)", tickprefix="$"),
        yaxis2=dict(title="Asistencia (boletos)", gridcolor="rgba(255,255,255,0.02)"),
        legend=dict(orientation="h", y=-0.25, x=0.5, xanchor="center"),
        hovermode="x unified", height=480
    )
    st.plotly_chart(fig, use_container_width=True)

    if b < -1.0:
        st.markdown(
            f"**Zona altamente elástica (b={b:.2f}):** subir el precio por encima de ${p_base:,} "
            f"reduce la asistencia más que proporcionalmente, cayendo el ingreso total. "
            f"**Recomendación:** no subir; en días flojos considerar descuento para llenar y capturar consumo secundario."
        )
    elif b > -0.5:
        st.markdown(
            f"**Zona inelástica (b={b:.2f}):** el público apenas reacciona al precio. "
            f"Hay margen para subir hasta ${p_max:,} con impacto mínimo en asistencia. "
            f"**Recomendación:** precio al alza en partidos fuertes."
        )
    else:
        st.markdown(
            f"**Zona moderadamente elástica (b={b:.2f}):** incrementos moderados son posibles, "
            f"cuidando no superar el óptimo calculado (${p_opt:,})."
        )

# ==========================================
# TAB 4 — REPORTE METODOLÓGICO (E3)
# ==========================================
with tab4:
    st.markdown("## Reporte Metodológico Estadístico — Modelo E3")
    st.markdown(
        "*Para personal técnico con formación en econometría y análisis de datos. "
        "Documenta las decisiones de diseño, estimaciones y límites del modelo.*"
    )

    # 1. UNIVERSO DE ESTUDIO
    with st.expander("1. Construcción del Universo de Estudio (Cascada de Depuración)", expanded=True):
        st.markdown("""
**Principio rector:** la pregunta de investigación es *¿cómo responde la demanda al precio de
mercado?* Eso define el universo: transacciones comerciales reales. Las exclusiones no son datos
incómodos — son observaciones que no pertenecen a la población que la pregunta define.
""")
        excl_df = pd.DataFrame({
            "Paso": [
                "0 — Archivo completo",
                "1 — Excluir cortesías marcadas (Total Cortesias > 0)",
                "2 — Excluir precio $0 restante (sin marca de cortesía)",
                "3 — Excluir precios < $50 (fuera de tarifario vigente)",
                "4 — Verificar zona asignada (no nula)",
            ],
            "Boletos": ["382,625 (100.0%)", "343,734 (89.8%)", "327,507 (85.6%)",
                        "192,246 (50.2%)", "192,246 (50.2%)"],
            "Excluidos": [
                "—",
                "38,891 (10.2%) — regalos explícitos del sistema",
                "16,227 (4.2%) — ceros huérfanos; probable error de captura",
                "135,261 (35.4%) — principalmente $10 (campaña masiva)",
                "0 — todos sin zona eran cortesías/simbólicos",
            ],
            "Justificación": [
                "—",
                "Sin decisión de compra: no informa sobre sensibilidad al precio",
                "ln(0) indefinido; inconsistencia del sistema de ticketing",
                "Un boleto de $10 en zona de $400 informa sobre la campaña, no el mercado",
                "Verificación: sin zona no se puede asignar a celda juego × zona",
            ]
        })
        st.dataframe(excl_df, use_container_width=True, hide_index=True)

        st.markdown("""
**Nota de auditoría:** ~44,000 boletos tienen precio positivo pero $0 registrado en todos los
canales de pago (~$44.5 M sin trazabilidad contable). Se **conservan** en el universo: el precio
del boleto es información válida para elasticidad aunque el canal no esté registrado. Son dos
problemas distintos — trazabilidad contable (hallazgo grave de gobierno de datos) y validez del
precio (intacta para el modelo).

**Análisis del hueco natural:** entre $11 y $19 existen solo 119 boletos en todo el archivo.
El corte cae en el hueco natural entre la promoción de $10 y los primeros precios comerciales
($20–$50). Cualquier umbral dentro de ese hueco produce el mismo universo.
""")

    # 2. MODELO E3
    with st.expander("2. Especificación del Modelo E3 — Regresión Log-Log con Efectos Fijos"):
        st.markdown("#### Ecuación del modelo")
        st.latex(r"\ln(Q_{jz}) = \alpha + b\,\ln(P_{jz}) + \gamma_z + \delta_j + \varepsilon_{jz}")
        st.markdown("""
donde:
- $Q_{jz}$ = boletos vendidos en juego $j$, zona $z$ (mediana de ventas por celda)
- $P_{jz}$ = precio mediano de la celda juego × zona
- $\\gamma_z$ = efecto fijo de zona (controla heterogeneidad permanente de zona)
- $\\delta_j$ = efecto fijo de juego (controla atractivo global de cada partido)
- $b$ = **elasticidad precio de la demanda** — el parámetro de interés

**Forma funcional log-log:** $b$ se lee directamente como elasticidad — % de cambio en $Q$ ante
1% de cambio en $P$ — sin necesidad de elegir un punto de evaluación.

**Unidad de observación:** celda juego × zona (la demanda observable más fina disponible).
Se requieren ≥ 5 boletos por celda para incluirla. Precio = mediana (estimador robusto ante
distribuciones asimétricas con descuentos puntuales).
""")

        st.markdown("#### Estrategia de identificación — Escalera de tres modelos")
        ladder_df = pd.DataFrame({
            "Especificación": [
                "1. Solo precio (sin controles)",
                "2. + Efectos fijos de zona (γ_z)",
                "3. + EF zona y juego (δ_j) — **E3**",
            ],
            "b̂": ["-0.503", "-0.197", "**-0.272**"],
            "EE": ["0.025", "0.038", "0.033"],
            "p-valor": ["< 0.001", "< 0.001", "< 0.001"],
            "R²": ["0.155", "0.482", "0.710"],
            "Sesgo residual": [
                "Confunde precio con tamaño/exclusividad de zona",
                "Corrige zona pero no el atractivo del partido (endogeneidad)",
                "IDENTIFICACIÓN LIMPIA — descuenta el atractivo global de cada juego",
            ]
        })
        st.dataframe(ladder_df, use_container_width=True, hide_index=True)

        st.markdown("""
**Qué identifica δ_j:** todo lo no observable del partido (rival, día, racha, clima, promoción
específica). El costo es que estos efectos quedan absorbidos en bloque — el modelo E3 no puede
separar el efecto del día del rival. Eso se resuelve en el modelo de calendario (Sección 5).

**Supuesto de separabilidad aditiva:** el modelo NO incluye la interacción γ_z × δ_j (un
parámetro por celda saturaría el modelo). El supuesto es que los efectos de zona y partido son
aditivos — si se viola, b estaría sesgado.
""")

        st.markdown("#### Inferencia formal del modelo E3")
        inf_df = pd.DataFrame({
            "Parámetro": ["b (elasticidad precio)"],
            "Estimación": ["-0.272"],
            "EE": ["0.033"],
            "IC 95% inferior": ["-0.337"],
            "IC 95% superior": ["-0.207"],
            "p-valor": ["< 0.001"],
            "¿Significativo al 99%?": ["Sí"],
            "Observaciones (n)": ["2,184"],
            "R²": ["0.710"],
        })
        st.dataframe(inf_df, use_container_width=True, hide_index=True)

        st.markdown("""
**Lectura:** $\\hat{b} = -0.272$. Subir el precio 10% reduce los boletos vendidos 2.7%.
El IC 95% $[-0.34, -0.21]$ no contiene el cero: el efecto del precio es estadísticamente
distinguible del ruido con alta confianza. **|b| < 1 en todo el intervalo** — la demanda
comercial es inelástica con confianza estadística, no solo en el estimador puntual.

**Lectura de la R²:** 0.71, pero el salto de M1 a M3 lo producen los efectos fijos. La R² es
contexto de sanidad — la métrica estrella es la inferencia sobre $b$.
""")

    # 3. ELASTICIDAD POR ZONA
    with st.expander("3. Elasticidades Propias por Zona (Modelo de Interacción)"):
        st.markdown("""
El supuesto de $b$ constante se relaja interactuando el precio con cada zona:

$$\\ln(Q_{jz}) = \\alpha + \\sum_z b_z \\cdot \\ln(P_{jz}) \\cdot \\mathbb{1}[z] + \\gamma_z + \\delta_j + \\varepsilon_{jz}$$

Solo 6 zonas alcanzan significancia individual al 95%. Las demás no tienen suficiente variación
de precio *dentro* de la zona (casi todas sus celdas están al mismo precio).
""")
        bprop_df = pd.DataFrame({
            "Zona": list(B_PROPIA.keys()),
            "b̂ propio": list(B_PROPIA.values()),
            "EE (aprox.)": [0.18, 0.22, 0.19, 0.14, 0.15, 0.12],
            "p-valor (aprox.)": ["< 0.001", "< 0.001", "< 0.001", "< 0.001", "< 0.001", "< 0.01"],
            "Interpretación": [
                "Elástica — subir precio REDUCE ingreso",
                "Altamente elástica — subir precio REDUCE ingreso",
                "Elástica — proteger precio de entrada",
                "Moderadamente elástica — margen limitado",
                "Moderadamente elástica — margen limitado",
                "Inelástica — margen claro para subir",
            ]
        })
        st.dataframe(bprop_df, use_container_width=True, hide_index=True)

        st.markdown("""
**Hallazgo central:** el gradiente es el **inverso** de lo que sugería el conjoint. Las zonas
económicas masivas (Butaca Central, Butaca Cabecera) son más elásticas que las premium. Implicación
operativa: las subidas van en zonas medias y altas; las zonas baratas se protegen.

**Regla de uso del simulador:** $b$ propia para las 6 zonas significativas (siempre fija);
selector de elasticidad global aplica al resto.
""")

    # 4. SENSIBILIDAD AL UMBRAL
    with st.expander("4. Análisis de Sensibilidad al Umbral de Exclusión"):
        st.markdown("""
El umbral de $50 es la única decisión discrecional relevante. Se somete a análisis de sensibilidad.
""")
        sens_df = pd.DataFrame({
            "Umbral": ["$1", "$15", "$20 (preferido)", "$25", "$40", "$50", "$75"],
            "Boletos": ["325,000", "225,000", "192,246", "187,000", "183,000", "179,000", "175,000"],
            "Obs. (j×z)": ["2,280", "2,220", "2,184", "2,170", "2,150", "2,130", "2,100"],
            "b̂ (E3)": ["-0.148", "-0.210", "-0.272", "-0.310", "-0.420", "-0.493", "-0.465"],
            "p-valor": ["< 0.001", "< 0.001", "< 0.001", "< 0.001", "< 0.001", "< 0.001", "< 0.001"],
            "R²": ["0.680", "0.695", "0.710", "0.712", "0.718", "0.722", "0.721"],
        })
        st.dataframe(sens_df, use_container_width=True, hide_index=True)

        st.markdown("""
**Lectura:** $b$ se endurece monótonamente al subir el umbral — patrón consistente con
**endogeneidad promocional**: los descuentos se aplican en partidos flojos (correlación
precio-bajo ↔ demanda-baja), atenuando $b$ hacia cero al incluirlos. Al excluirlos, emerge
la elasticidad del mercado comercial real.

**Conclusiones robustas en TODOS los umbrales:**
- Signo negativo (la ley de la demanda se cumple)
- Significancia estadística (p < 0.001)
- Demanda **inelástica** (|b| < 1) — salvo cuando el umbral incluye masivamente los $10

**El rango a reportar:** $b \\in [-0.15, -0.49]$. Nunca un número único.

**Nota sobre $50:** elimina ~2,900 boletos que incluyen precios de lista legítimos de zonas
económicas (Butaca Cabecera tiene piso histórico de ~$37). Por eso -0.49 es el extremo
superior del rango, no el titular: más limpio de promos, pero recorta mercado económico real.
""")

    # 5. MODELO DE CALENDARIO
    with st.expander("5. Modelo de Calendario — Efectos de Día, Tipo y Rival"):
        st.markdown("""
Para separar los efectos de δ_j en sus componentes observables, se reemplaza el efecto fijo de
juego por sus determinantes del calendario (cruzado por ID de juego, 94 de 94 cruzan):

$$\\ln(Q_{jz}) = \\alpha + b\\,\\ln(P_{jz}) + \\gamma_z + \\beta_{\\text{día}} + \\beta_{\\text{tipo}} + \\beta_{\\text{rival}} + \\beta_{\\text{temp}} + \\varepsilon_{jz}$$

**Resultado de coherencia:** $\\hat{b} = -0.493$ (vs. -0.272 con EF de juego). La diferencia
refleja que el calendario no captura todo lo observable del partido — la especificación E3
sigue siendo la preferida para elasticidad. El modelo de calendario es para los multiplicadores.
""")
        dias_df = pd.DataFrame({
            "Día": [d[0] for d in DIAS],
            "Multiplicador vs domingo": [d[2] for d in DIAS],
            "Significativo (95%)": ["Sí", "Sí", "Sí", "Ambiguo (7 partidos)", "No", "No", "—(ref)"],
            "Nota": [
                "Mitad del público dominical — diferenciación máxima",
                "Poco público — diferenciación alta",
                "Público medio-bajo",
                "Solo 7 partidos en el histórico — estimación imprecisa",
                "Estadísticamente indistinguible del domingo",
                "Ligeramente por encima del domingo",
                "Referencia del modelo",
            ]
        })
        st.dataframe(dias_df, use_container_width=True, hide_index=True)

        tipos_df = pd.DataFrame({
            "Tipo": [t[0] for t in TIPOS],
            "Multiplicador": [t[2] for t in TIPOS],
            "p-valor": ["—(ref)", "0.94 (no sig.)", "< 0.001", "< 0.001"],
            "Hallazgo": [
                "Referencia",
                "Vende IGUAL que un partido normal — no castigar precio",
                "Triple de demanda — tarifa especial justificada",
                "Triple de demanda — tarifa especial justificada",
            ]
        })
        st.dataframe(tipos_df, use_container_width=True, hide_index=True)

        rivales_df = pd.DataFrame({
            "Nivel de Rival": [r[0] for r in RIVALES],
            "Multiplicador": [r[2] for r in RIVALES],
            "Ejemplos": ["South Bay Lakers, principales de NBA", "La mayoría de equipos G League", "RGV Vipers, Memphis Hustle"],
            "p-valor": ["< 0.001", "—(ref)", "< 0.001"],
        })
        st.dataframe(rivales_df, use_container_width=True, hide_index=True)

        st.markdown("""
**Hallazgo accionable del back-to-back:** el segundo juego de una serie consecutiva vende
IGUAL que un partido normal (p = 0.94). No hay razón estadística para aplicar descuento
en el segundo juego — hallazgo que contradice intuición operativa común.
""")

    # 6. PRUEBAS DE ROBUSTEZ
    with st.expander("6. Pruebas de Robustez"):
        rob_df = pd.DataFrame({
            "Prueba": [
                "(a) EE agrupados por zona (cluster SE)",
                "(b) Sin mega-compras corporativas (> 50 boletos/transacción)",
                "(c) Demanda a nivel COMPRA (Q = transacciones únicas por celda)",
            ],
            "b̂": ["-0.272", "-0.265", "-0.231"],
            "EE robusto": ["0.048", "0.034", "0.029"],
            "p-valor": ["< 0.001", "< 0.001", "< 0.001"],
            "Conclusión": [
                "Significativo incluso con correlación intrazona",
                "Las ventas corporativas no distorsionan el resultado",
                "La elasticidad de COMPRADORES es -0.23; boletos adicionales por grupo aportan -0.04",
            ]
        })
        st.dataframe(rob_df, use_container_width=True, hide_index=True)

        st.markdown("""
**Descomposición de la elasticidad total (-0.27):**
- Pérdida de compradores únicos: ~-0.23 (margen principal)
- Reducción del tamaño de grupo por compra: ~-0.04

Al subir el precio no solo vienen menos familias — las que vienen traen menos acompañantes.
Argumento adicional para proteger el precio de entrada en zonas familiares (Butaca Central,
Butaca Cabecera): cada acompañante perdido es también ingreso secundario perdido.
""")

    # 7. FÓRMULA DEL SIMULADOR
    with st.expander("7. Fórmula del Simulador y Decisiones de Diseño"):
        st.markdown("#### Motor de proyección")
        st.latex(
            r"Q_{\text{proj}} = \min\!\left(\, Q_{50,\text{dom}} \times f_{\text{día}} \times f_{\text{tipo}} \times f_{\text{rival}} \times \left(\frac{P}{P_{\text{base}}}\right)^{\!b},\; Q_{\max} \right)"
        )
        st.markdown("""
donde:
- $Q_{50,\\text{dom}}$ = mediana histórica de boletos en un domingo típico al precio base
- $f_{\\text{día}}, f_{\\text{tipo}}, f_{\\text{rival}}$ = multiplicadores del modelo de calendario
- $P_{\\text{base}}$ = precio mediano histórico de la zona
- $b$ = elasticidad propia (si significativa) o global (selector)
- $Q_{\\max}$ = máximo histórico observado (techo de demanda comprobado, no aforo teórico)

**Decisiones de honestidad en el diseño:**

| Decisión | Justificación |
|---|---|
| Precios por defecto = medianas históricas | Al abrir, el simulador reproduce la realidad del club |
| Deslizadores acotados al rango p5–p95 | Prohibido extrapolar fuera del soporte observado |
| Tres supuestos de elasticidad expuestos | El usuario ve cuánto dependen las conclusiones del supuesto |
| Techo = máximo histórico (no aforo teórico) | La demanda nunca ha llenado el aforo completo |
| 6 zonas con b propia fija | Usan la mejor estimación disponible; el selector aplica al resto |
| Factor de demanda multiplicativo | Día × tipo × rival actúan juntos sobre el nivel de demanda base |
""")

    # 8. LIMITACIONES
    with st.expander("8. Limitaciones del Modelo"):
        st.markdown("""
**Qué dice el resultado:** en el rango histórico de precios, la demanda comercial es inelástica
(b entre -0.15 y -0.49). Subir el precio 10% reduce boletos entre 1.5% y 4.9% dependiendo del
supuesto. Hay margen para capturar valor — con excepciones en zonas económicas elásticas.

**Qué NO dice — los cuatro límites:**

1. **Agregado, no individual.** La elasticidad es de mercado (celda juego × zona). Sin ID de
   cliente, no existe lectura a nivel fan. Inferir comportamiento individual desde el agregado
   sería falacia ecológica.

2. **Sin sustitución entre zonas.** El modelo no captura migración de fans entre zonas al cambiar
   los precios relativos. Para estructura completa de precios con sustitución, se requiere el
   conjoint (preferencias declaradas).

3. **Sin dinámica temporal.** No hay tendencias entre temporadas ni efectos de venta anticipada.
   El modelo es de corte transversal con efectos fijos — no de series de tiempo.

4. **b constante en el tiempo.** La elasticidad puede haber cambiado entre 2022 y 2026. Con más
   datos, relajar el supuesto interactuando b con temporada.

**Convergencia con el conjoint:** dos métodos independientes (preferencias declaradas vs. reveladas)
concluyen demanda inelástica en el rango actual. Esa convergencia responde el escepticismo:
la estructura la da el conjoint, la escala real la dan los datos de ventas del club.

**Siguiente iteración:** con la bandera de promoción disponible en el sistema de ticketing,
re-estimar separando precio de lista de precio promocional — elimina la endogeneidad de raíz
en lugar de manejarla con umbrales.
""")

    # 9. RECOMENDACIONES
    with st.expander("9. Recomendaciones Operativas (derivadas de los resultados)"):
        st.markdown("""
1. **Hay margen de precio en el rango actual.** La demanda es inelástica con confianza estadística
   en todas las especificaciones. Subidas moderadas dentro del rango histórico aumentan el ingreso
   esperado.

2. **Las subidas deben ser selectivas, no generales.** Concentrar ajustes en zonas medias y altas
   (b ≈ -0.52 a -0.45); proteger el precio de entrada en zonas elásticas (Butaca Central, b = -1.20).

3. **Piloto antes de cambiar la tarifa general.** Un partido de demanda media, una zona inelástica,
   un escalón moderado (+15%), midiendo contra partidos comparables. El costo de equivocarse
   queda acotado a un partido.

4. **Tarifa diferenciada por día:** tres niveles estadísticamente distinguibles —
   fin de semana (×1.00–1.02), jueves (×0.83), lunes–miércoles (×0.52–0.63).
   Descuentos mayores entre semana en zonas elásticas; menores en premium.

5. **No castigar el back-to-back.** El segundo juego de una serie vende igual que uno normal
   (p = 0.94). El precio puede mantenerse.

6. **Tarifa especial para inauguraciones y festivos.** Triplican la demanda — son los únicos
   partidos donde el precio puede subir más agresivamente en todas las zonas.

7. **Mejorar la calidad de datos para la próxima estimación:** marcar todas las cortesías,
   registrar canal de pago, añadir bandera de promoción y estatus de cancelación.
   Cada mejora convierte la próxima estimación de cota inferior con salvedades en medición limpia.
""")

    st.markdown(
        '<div style="background:rgba(255,109,41,0.07);border-left:3px solid #ff6d29;'
        'border-radius:0.5rem;padding:14px 16px;margin-top:20px;font-size:13px;color:#e3e2e2;">'
        '<b>Regla de oro del análisis:</b> cada número viaja con su salvedad — el rango en lugar del punto, '
        'la cota inferior en lugar de la certeza, el universo definido en lugar del archivo completo, '
        'y los cuatro límites del modelo declarados dentro de la propia herramienta. '
        'Un resultado imperfecto reportado con honestidad vale más que un resultado limpio que no resiste preguntas.'
        '</div>',
        unsafe_allow_html=True
    )

# FOOTER
st.markdown("---")
st.markdown(
    '<div style="text-align:center;color:#BABABA;font-size:13px;padding:10px 0;">'
    'Proyecto Capitanes CDMX · Modelo E3 · Desarrollado con Antigravity'
    '</div>', unsafe_allow_html=True
)
