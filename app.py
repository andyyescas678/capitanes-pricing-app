import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.subplots as sp
import os
import subprocess

# Configure Streamlit page
st.set_page_config(
    page_title="Capitanes CDMX - Pricing Optimizer",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants & Paths
EXCEL_PATH = r"C:\Users\andy_\Downloads\Capitanes_BD\MAESTRO CONSOLIDADO 2022-2026 (1) (1).xlsx"
CONST_CSV_PATH = r"constantes_simulador.csv"
PANEL_CSV_PATH = r"panel_demanda.csv"

# Elasticities mapping
ELASTICIDADES = {
    "Conservadora (b = -0.15)": -0.148,
    "Preferida (b = -0.27)": -0.272,
    "Estricta (b = -0.49)": -0.493
}

ESCENARIOS = {
    "Partido flojo (p25)": "q25",
    "Partido típico (mediana)": "q50",
    "Partido fuerte (p75)": "q75"
}

# 5 zones with statistically significant specific elasticities from OLS
B_PROPIA = {
    "Butaca Central": -1.211,
    "Preferente Fondo": -1.436,
    "Preferente Cabecera": -0.780,
    "Barrera Cabecera": -0.772,
    "Preferente Tunel": -0.434
}

# --- CUSTOM CSS INJECTION ---
def inject_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700&display=swap');
    
    /* Global Fonts & Backgrounds */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #121414 !important;
        color: #e3e2e2 !important;
        font-family: 'Hanken Grotesk', sans-serif !important;
    }
    
    /* Background mesh effect */
    [data-testid="stAppViewContainer"] {
        background-image: radial-gradient(circle at 0% 0%, rgba(255, 109, 41, 0.08) 0%, transparent 50%),
                          radial-gradient(circle at 100% 100%, rgba(69, 48, 39, 0.15) 0%, transparent 50%) !important;
        background-attachment: fixed !important;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #0d0e0f !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
    }
    
    /* Custom tab headers */
    div[data-testid="stTabBar"] button {
        font-family: 'Hanken Grotesk', sans-serif !important;
        font-size: 16px !important;
        font-weight: 500 !important;
        color: #BABABA !important;
        background-color: transparent !important;
        border: none !important;
        padding: 10px 20px !important;
    }
    div[data-testid="stTabBar"] button[aria-selected="true"] {
        color: #ff6d29 !important;
        border-bottom: 2px solid #ff6d29 !important;
    }
    
    /* Headings */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Hanken Grotesk', sans-serif !important;
        font-weight: 600 !important;
        color: #ffffff !important;
    }
    
    /* Primary buttons (Pill) */
    div.stButton > button[kind="primary"] {
        background-color: #ff6d29 !important;
        color: #ffffff !important;
        border-radius: 9999px !important;
        border: none !important;
        padding: 10px 30px !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 15px rgba(255, 109, 41, 0.2) !important;
        transition: all 0.3s ease !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #e55c1e !important;
        box-shadow: 0 4px 20px rgba(255, 109, 41, 0.4) !important;
        transform: translateY(-1px) !important;
    }
    
    /* Secondary buttons */
    div.stButton > button[kind="secondary"] {
        background-color: rgba(69, 48, 39, 0.3) !important;
        color: #ffffff !important;
        border-radius: 9999px !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        padding: 10px 24px !important;
    }
    div.stButton > button[kind="secondary"]:hover {
        border-color: #ff6d29 !important;
        color: #ff6d29 !important;
    }
    
    /* Slider overrides */
    div[data-testid="stSlider"] div[role="slider"] {
        background-color: #ff6d29 !important;
        border: 2px solid #ffffff !important;
    }
    
    /* Glass card container */
    .glass-card {
        background: rgba(69, 48, 39, 0.12) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 2rem !important;
        padding: 24px !important;
        margin-bottom: 24px !important;
    }
    
    /* Style tables nicely */
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 1rem !important;
        overflow: hidden !important;
    }
    
    /* Markdown text */
    p {
        color: #e3e2e2 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Custom metrics generator
def render_metric_card(title, value, subtext, delta=None, is_positive=True):
    delta_html = ""
    if delta is not None:
        color = "#ff6d29" if is_positive else "#FF5555"
        arrow = "↑" if is_positive else "↓"
        delta_html = f'<span style="color: {color}; font-weight: 700; margin-left: 8px; font-size: 18px;">{arrow} {delta}</span>'
    
    html = f"""
    <div style="
        background: rgba(69, 48, 39, 0.15);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 1.5rem;
        padding: 20px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2);
        margin-bottom: 20px;
    ">
        <div style="color: #BABABA; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 8px;">{title}</div>
        <div style="color: #FFFFFF; font-size: 28px; font-weight: 700; display: flex; align-items: baseline; line-height: 1;">{value} {delta_html}</div>
        <div style="color: #BABABA; font-size: 11px; margin-top: 8px; font-weight: 400;">{subtext}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# --- CACHE DATA HANDLING ---
@st.cache_data(show_spinner=False)
def load_cached_data():
    if os.path.exists(CONST_CSV_PATH) and os.path.exists(PANEL_CSV_PATH):
        df_const = pd.read_csv(CONST_CSV_PATH)
        df_panel = pd.read_csv(PANEL_CSV_PATH)
        return df_const, df_panel
    return None, None

def rebuild_cache():
    st.info("Reconstruyendo caché desde el Excel original (MAESTRO CONSOLIDADO 2022-2026). Esto puede tomar hasta 2 minutos...")
    try:
        # Run the generate_cache.py script in a subprocess
        result = subprocess.run(["python", "generate_cache.py"], capture_output=True, text=True, check=True)
        st.success("¡Caché reconstruida exitosamente!")
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error al reconstruir caché: {e}")
        if 'result' in locals() and result.stderr:
            st.error(f"Detalle: {result.stderr}")
        return False

# --- LOAD DATA ---
inject_custom_css()
df_const, df_panel = load_cached_data()

# Auto-rebuild if files are missing
if df_const is None or df_panel is None:
    st.warning("No se encontraron los archivos de caché. Generando caché inicial desde Excel...")
    if rebuild_cache():
        st.rerun()
    else:
        st.stop()

# --- INITIALIZE SESSION STATE FOR PRICES ---
if "prices" not in st.session_state:
    st.session_state.prices = {r["zona"]: int(r["p_base"]) for _, r in df_const.iterrows()}

# --- SIDEBAR CONTROLS ---
st.sidebar.markdown(
    '<div style="text-align: center; padding: 10px 0;"><h2 style="margin: 0; color: #ff6d29; letter-spacing: 0.05em;">🏀 CAPITANES</h2><p style="color: #BABABA; font-size: 13px; font-weight: 500; margin-top: 2px;">Pricing Control Center</p></div>',
    unsafe_allow_html=True
)

st.sidebar.markdown("### ⚙️ Parámetros Generales")

# Scenario Selector
esc_name = st.sidebar.selectbox("Tipo de Partido (Aforo histórico)", list(ESCENARIOS.keys()), index=1)
esc_col = ESCENARIOS[esc_name]

# Elasticity Selector
el_name = st.sidebar.selectbox("Supuesto de Elasticidad", list(ELASTICIDADES.keys()) + ["Personalizada (Slider)"], index=1)
if el_name == "Personalizada (Slider)":
    beta_selected = st.sidebar.slider("Coeficiente de Elasticidad (b)", min_value=-2.00, max_value=-0.05, value=-0.27, step=0.01)
else:
    beta_selected = ELASTICIDADES[el_name]

# Costs Sliders
st.sidebar.markdown("### 💸 Estructura de Costos")
cost_fixed = st.sidebar.slider("Costos Fijos del Partido ($)", min_value=0, max_value=500000, value=100000, step=10000)
cost_var = st.sidebar.slider("Costo Variable por Boleto ($)", min_value=0, max_value=150, value=30, step=5)

# Optimization Weight Slider
st.sidebar.markdown("### 🎯 Enfoque de Optimización")
weight_rev = st.sidebar.slider(
    "Maximizar Ganancia vs Asistencia",
    min_value=0.00,
    max_value=1.00,
    value=0.80,
    step=0.05,
    help="0.0 = Maximizar Asistencia únicamente (precios más bajos) | 1.0 = Maximizar Ganancias netas únicamente (precios óptimos de ganancia)"
)

# Admin Action: Reload Excel
st.sidebar.markdown("---")
st.sidebar.markdown("### 💾 Acciones Administrativas")
if st.sidebar.button("🔄 Recargar Excel Original", use_container_width=True, type="secondary"):
    if rebuild_cache():
        st.rerun()

# --- MATHEMATICAL SIMULATION & CALCULATIONS ---
def get_zone_elasticity(zona):
    return B_PROPIA.get(zona, beta_selected)

def simulate_projection(prices_dict):
    results = []
    total_boletos_base = 0
    total_boletos_proj = 0
    total_ingreso_base = 0
    total_ingreso_proj = 0
    
    for _, r in df_const.iterrows():
        zona = r["zona"]
        p_base = r["p_base"]
        p_min = r["p_min"]
        p_max = r["p_max"]
        q_base = r[esc_col]
        q_max = r["qmax"]
        
        p_proj = prices_dict[zona]
        beta = get_zone_elasticity(zona)
        
        # Calculate projection using notebook formula
        q_proj = int(min(q_base * (p_proj / p_base) ** beta, q_max))
        
        ingreso_base = q_base * p_base
        ingreso_proj = q_proj * p_proj
        
        total_boletos_base += q_base
        total_boletos_proj += q_proj
        total_ingreso_base += ingreso_base
        total_ingreso_proj += ingreso_proj
        
        results.append({
            "Zona": zona,
            "Elasticidad": beta,
            "Precio Base": p_base,
            "Precio Proj": p_proj,
            "Boletos Base": q_base,
            "Boletos Proj": q_proj,
            "Ingreso Base": ingreso_base,
            "Ingreso Proj": ingreso_proj
        })
        
    df_results = pd.DataFrame(results)
    
    # Calculate Profitability
    profit_base = total_ingreso_base - cost_fixed - (total_boletos_base * cost_var)
    profit_proj = total_ingreso_proj - cost_fixed - (total_boletos_proj * cost_var)
    
    margin_base = profit_base / total_ingreso_base if total_ingreso_base > 0 else 0
    margin_proj = profit_proj / total_ingreso_proj if total_ingreso_proj > 0 else 0
    
    metrics = {
        "boletos_base": total_boletos_base,
        "boletos_proj": total_boletos_proj,
        "ingreso_base": total_ingreso_base,
        "ingreso_proj": total_ingreso_proj,
        "profit_base": profit_base,
        "profit_proj": profit_proj,
        "margin_base": margin_base,
        "margin_proj": margin_proj
    }
    
    return df_results, metrics

# Run current simulation
df_sim, sim_metrics = simulate_projection(st.session_state.prices)

# --- MAIN DISPLAY HEADER ---
st.markdown(
    '<div style="background: linear-gradient(135deg, rgba(255, 109, 41, 0.2) 0%, rgba(69, 48, 39, 0.05) 100%); padding: 30px; border-radius: 2rem; border: 1px solid rgba(255,109,41,0.25); margin-bottom: 25px;">'
    '<h1 style="margin: 0; color: #ffffff; font-size: 38px; font-weight: 700; letter-spacing: -0.02em;">🏀 CAPITANES CDMX</h1>'
    '<p style="margin: 6px 0 0 0; color: #ff6d29; font-size: 18px; font-weight: 600; letter-spacing: 0.02em;">Stitch Pricing Optimization Simulator</p>'
    '</div>',
    unsafe_allow_html=True
)

# --- KPI METRICS GRID ---
kpi_cols = st.columns(3)

with kpi_cols[0]:
    delta_rev = sim_metrics["ingreso_proj"] - sim_metrics["ingreso_base"]
    pct_rev = (delta_rev / sim_metrics["ingreso_base"] * 100) if sim_metrics["ingreso_base"] > 0 else 0
    sign = "+" if delta_rev >= 0 else ""
    render_metric_card(
        title="Ingreso Total Proyectado",
        value=f"${sim_metrics['ingreso_proj']:,}",
        subtext=f"Histórico: ${sim_metrics['ingreso_base']:,}",
        delta=f"{sign}${abs(delta_rev):,} ({sign}{pct_rev:.1f}%)",
        is_positive=(delta_rev >= 0)
    )

with kpi_cols[1]:
    delta_boletos = sim_metrics["boletos_proj"] - sim_metrics["boletos_base"]
    pct_boletos = (delta_boletos / sim_metrics["boletos_base"] * 100) if sim_metrics["boletos_base"] > 0 else 0
    sign = "+" if delta_boletos >= 0 else ""
    render_metric_card(
        title="Asistencia Proyectada",
        value=f"{sim_metrics['boletos_proj']:,} fans",
        subtext=f"Histórico: {sim_metrics['boletos_base']:,} boletos",
        delta=f"{sign}{abs(delta_boletos):,} fans ({sign}{pct_boletos:.1f}%)",
        is_positive=(delta_boletos >= 0)
    )

with kpi_cols[2]:
    delta_profit = sim_metrics["profit_proj"] - sim_metrics["profit_base"]
    pct_profit = (delta_profit / abs(sim_metrics["profit_base"]) * 100) if sim_metrics["profit_base"] != 0 else 0
    sign = "+" if delta_profit >= 0 else ""
    render_metric_card(
        title="Ganancia Neta Esperada",
        value=f"${sim_metrics['profit_proj']:,}",
        subtext=f"Margen: {sim_metrics['margin_proj']*100:.1f}% (Base: {sim_metrics['margin_base']*100:.1f}%)",
        delta=f"{sign}${abs(delta_profit):,} ({sign}{pct_profit:.1f}%)",
        is_positive=(delta_profit >= 0)
    )

# --- INTERACTIVE TABS ---
tab1, tab2, tab3, tab4 = st.tabs([
    "🎚️ Simulador por Zona", 
    "🎯 Optimizador Matemático", 
    "📈 Curvas de Sensibilidad", 
    "🔬 Inferencia y Auditoría (E3)"
])

# ==========================================
# TAB 1: SIMULADOR POR ZONA
# ==========================================
with tab1:
    st.markdown("### Ajuste de Precios por Zona")
    st.write("Modifica los deslizadores a continuación para proyectar en tiempo real los boletos e ingresos de cada zona.")
    
    # Categorize zones based on base price
    # Premium: >= 350
    # Preferencial: 150 <= p < 350
    # Cabeceras y Butacas: < 150
    
    col_premium, col_pref, col_butaca = st.columns(3)
    
    with col_premium:
        st.markdown('<div style="border-bottom: 2px solid #ff6d29; margin-bottom:15px; padding-bottom:5px;"><h4 style="margin:0; color:#ff6d29;">⭐ Premium Zones (P >= $350)</h4></div>', unsafe_allow_html=True)
        for _, r in df_const.iterrows():
            if r["p_base"] >= 350:
                zona = r["zona"]
                st.session_state.prices[zona] = st.slider(
                    f"{zona}",
                    min_value=int(r["p_min"]),
                    max_value=int(r["p_max"]),
                    value=st.session_state.prices[zona],
                    step=5,
                    key=f"slider_{zona}_premium"
                )
                
    with col_pref:
        st.markdown('<div style="border-bottom: 2px solid #E0C0B3; margin-bottom:15px; padding-bottom:5px;"><h4 style="margin:0; color:#E0C0B3;">🏢 Preferential Zones ($150 - $349)</h4></div>', unsafe_allow_html=True)
        for _, r in df_const.iterrows():
            if 150 <= r["p_base"] < 350:
                zona = r["zona"]
                st.session_state.prices[zona] = st.slider(
                    f"{zona}",
                    min_value=int(r["p_min"]),
                    max_value=int(r["p_max"]),
                    value=st.session_state.prices[zona],
                    step=5,
                    key=f"slider_{zona}_pref"
                )
                
    with col_butaca:
        st.markdown('<div style="border-bottom: 2px solid #BABABA; margin-bottom:15px; padding-bottom:5px;"><h4 style="margin:0; color:#BABABA;">🎟️ Cabeceras & Butacas (P < $150)</h4></div>', unsafe_allow_html=True)
        for _, r in df_const.iterrows():
            if r["p_base"] < 150:
                zona = r["zona"]
                st.session_state.prices[zona] = st.slider(
                    f"{zona}",
                    min_value=int(r["p_min"]),
                    max_value=int(r["p_max"]),
                    value=st.session_state.prices[zona],
                    step=5,
                    key=f"slider_{zona}_butaca"
                )
                
    # Detailed Projection Table
    st.markdown("### Resumen Detallado de Simulación")
    
    df_table = df_sim.copy()
    # Format columns for display
    df_table["Elasticidad"] = df_table["Elasticidad"].round(3)
    df_table["Var. Precio %"] = (((df_table["Precio Proj"] - df_table["Precio Base"]) / df_table["Precio Base"]) * 100).round(1)
    df_table["Var. Asistencia %"] = (((df_table["Boletos Proj"] - df_table["Boletos Base"]) / df_table["Boletos Base"]) * 100).round(1)
    
    # Calculate Alert Column
    alerts = []
    for _, row in df_table.iterrows():
        # High elasticities are b < -1.0
        if row["Elasticidad"] < -1.0 and row["Precio Proj"] > row["Precio Base"]:
            alerts.append("⚠️ RIESGO: Zona altamente elástica, la subida reduce ingresos.")
        elif row["Elasticidad"] > -0.5 and row["Precio Proj"] > row["Precio Base"]:
            alerts.append("✅ EFICIENTE: Zona inelástica, subir precio captura valor.")
        else:
            alerts.append("Neutral")
            
    df_table["Recomendación / Alerta"] = alerts
    
    # Reorder columns
    display_cols = [
        "Zona", "Elasticidad", "Precio Base", "Precio Proj", "Var. Precio %", 
        "Boletos Base", "Boletos Proj", "Var. Asistencia %", "Ingreso Base", "Ingreso Proj", "Recomendación / Alerta"
    ]
    st.dataframe(
        df_table[display_cols].style.format({
            "Precio Base": "${:,.0f}",
            "Precio Proj": "${:,.0f}",
            "Var. Precio %": "{:+.1f}%",
            "Boletos Base": "{:,.0f}",
            "Boletos Proj": "{:,.0f}",
            "Var. Asistencia %": "{:+.1f}%",
            "Ingreso Base": "${:,.0f}",
            "Ingreso Proj": "${:,.0f}"
        }),
        use_container_width=True,
        hide_index=True
    )
    
    # Export simulation
    st.markdown("#### 📥 Exportar Simulación Actual")
    csv_data = df_table[display_cols].to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Exportar simulación a CSV",
        data=csv_data,
        file_name="simulacion_precios_capitanes.csv",
        mime="text/csv",
        type="primary"
    )

# ==========================================
# TAB 2: OPTIMIZADOR MATEMÁTICO
# ==========================================
with tab2:
    st.markdown("### Optimización Multi-Objetivo por Zona")
    st.write(
        "El optimizador calcula de manera independiente el precio que maximiza la función de utilidad balanceando "
        "la ganancia neta proyectada y la asistencia (aforo), basado en la ponderación elegida en la barra lateral."
    )
    
    # Compute optimal prices
    # For a typical game (q50)
    opt_prices = {}
    opt_results = []
    
    for _, r in df_const.iterrows():
        zona = r["zona"]
        p_base = r["p_base"]
        p_min = r["p_min"]
        p_max = r["p_max"]
        q_base = r["q50"]
        q_max = r["qmax"]
        
        beta = get_zone_elasticity(zona)
        
        # Grid search
        prices = np.arange(p_min, p_max + 1, 1)
        if len(prices) == 0:
            prices = np.array([p_base])
            
        qs = []
        net_revs = []
        for p in prices:
            q = min(q_base * (p / p_base) ** beta, q_max)
            # Net revenue takes variable cost into account
            net_rev = q * (p - cost_var)
            qs.append(q)
            net_revs.append(net_rev)
            
        qs = np.array(qs)
        net_revs = np.array(net_revs)
        
        min_q, max_q = qs.min(), qs.max()
        min_rev, max_rev = net_revs.min(), net_revs.max()
        
        best_score = -999999
        best_price = p_base
        best_q = q_base
        best_rev = q_base * p_base
        
        for p, q, rev in zip(prices, qs, net_revs):
            # Normalize to [0, 1] range to make utility score weight meaningful
            norm_rev = (rev - min_rev) / (max_rev - min_rev + 1e-5)
            norm_q = (q - min_q) / (max_q - min_q + 1e-5)
            
            score = weight_rev * norm_rev + (1.0 - weight_rev) * norm_q
            
            if score > best_score:
                best_score = score
                best_price = p
                best_q = int(q)
                best_rev = int(q * p)
                
        opt_prices[zona] = int(best_price)
        
        opt_results.append({
            "Zona": zona,
            "Elasticidad": beta,
            "Precio Base": p_base,
            "Precio Óptimo": int(best_price),
            "Boletos Base": q_base,
            "Boletos Óptimos": best_q,
            "Ingreso Base": q_base * p_base,
            "Ingreso Óptimo": best_rev,
            "Ganancia Base": int(q_base * (p_base - cost_var)),
            "Ganancia Óptima": int(best_q * (best_price - cost_var))
        })
        
    df_opt = pd.DataFrame(opt_results)
    
    # Calculate Overall Optimized Metrics
    tot_rev_base = df_opt["Ingreso Base"].sum()
    tot_rev_opt = df_opt["Ingreso Óptimo"].sum()
    tot_q_base = df_opt["Boletos Base"].sum()
    tot_q_opt = df_opt["Boletos Óptimos"].sum()
    
    tot_profit_base = tot_rev_base - cost_fixed - (tot_q_base * cost_var)
    tot_profit_opt = tot_rev_opt - cost_fixed - (tot_q_opt * cost_var)
    
    # Display comparison cards for typical game
    st.markdown("#### Impacto de Optimización en Partido Típico")
    opt_cols = st.columns(3)
    
    with opt_cols[0]:
        delta = tot_rev_opt - tot_rev_base
        pct = (delta / tot_rev_base * 100) if tot_rev_base > 0 else 0
        st.metric("Ingreso Total (Optimizado)", f"${tot_rev_opt:,}", f"+${delta:,} (+{pct:.1f}%)" if delta >= 0 else f"-${abs(delta):,} ({pct:.1f}%)")
        
    with opt_cols[1]:
        delta = tot_q_opt - tot_q_base
        pct = (delta / tot_q_base * 100) if tot_q_base > 0 else 0
        st.metric("Asistencia Total (Optimizado)", f"{tot_q_opt:,} boletos", f"+{delta:,} ({pct:.1f}%)" if delta >= 0 else f"{delta:,} ({pct:.1f}%)")
        
    with opt_cols[2]:
        delta = tot_profit_opt - tot_profit_base
        pct = (delta / abs(tot_profit_base) * 100) if tot_profit_base != 0 else 0
        st.metric("Ganancia Neta (Optimizado)", f"${tot_profit_opt:,}", f"+${delta:,} (+{pct:.1f}%)" if delta >= 0 else f"-${abs(delta):,} ({pct:.1f}%)")
        
    # Button to apply recommended prices
    st.markdown("---")
    apply_col1, apply_col2 = st.columns([1, 2])
    with apply_col1:
        if st.button("🚀 Aplicar Precios Recomendados a Sliders", use_container_width=True, type="primary"):
            for zona, p_opt in opt_prices.items():
                st.session_state.prices[zona] = p_opt
            st.success("¡Precios aplicados exitosamente! Regresa a la pestaña del Simulador para ver los resultados.")
            st.rerun()
            
    # Display recommendation table
    st.markdown("#### Tabla Recomendaciones de Precios")
    df_opt_disp = df_opt.copy()
    df_opt_disp["Var. Precio %"] = (((df_opt_disp["Precio Óptimo"] - df_opt_disp["Precio Base"]) / df_opt_disp["Precio Base"]) * 100).round(1)
    df_opt_disp["Var. Asistencia %"] = (((df_opt_disp["Boletos Óptimos"] - df_opt_disp["Boletos Base"]) / df_opt_disp["Boletos Base"]) * 100).round(1)
    
    st.dataframe(
        df_opt_disp[[
            "Zona", "Elasticidad", "Precio Base", "Precio Óptimo", "Var. Precio %", 
            "Boletos Base", "Boletos Óptimos", "Var. Asistencia %", "Ganancia Base", "Ganancia Óptima"
        ]].style.format({
            "Elasticidad": "{:.3f}",
            "Precio Base": "${:,.0f}",
            "Precio Óptimo": "${:,.0f}",
            "Var. Precio %": "{:+.1f}%",
            "Boletos Base": "{:,.0f}",
            "Boletos Óptimos": "{:,.0f}",
            "Var. Asistencia %": "{:+.1f}%",
            "Ganancia Base": "${:,.0f}",
            "Ganancia Óptima": "${:,.0f}"
        }),
        use_container_width=True,
        hide_index=True
    )

# ==========================================
# TAB 3: CURVAS DE SENSIBILIDAD
# ==========================================
with tab3:
    st.markdown("### Análisis Gráfico de Sensibilidad")
    st.write(
        "Selecciona una zona para graficar el comportamiento del ingreso, la ganancia neta y "
        "la asistencia proyectada conforme cambia el precio dentro del rango histórico observado."
    )
    
    selected_zona = st.selectbox("Seleccionar Zona para Graficar", df_const["zona"].unique())
    
    # Calculate curves
    r_z = df_const[df_const["zona"] == selected_zona].iloc[0]
    p_min = int(r_z["p_min"])
    p_max = int(r_z["p_max"])
    p_base = int(r_z["p_base"])
    q_base = int(r_z[esc_col])
    q_max = int(r_z["qmax"])
    beta = get_zone_elasticity(selected_zona)
    
    prices = np.arange(p_min, p_max + 1, 1)
    if len(prices) == 0:
        prices = np.array([p_base])
        
    attendances = []
    revenues = []
    profits = []
    
    for p in prices:
        q = min(q_base * (p / p_base) ** beta, q_max)
        attendances.append(q)
        revenues.append(q * p)
        # Allocate fractional fixed cost for visualization, or just use variable cost
        profits.append(q * (p - cost_var))
        
    # Find optimum for this specific graph (based on current tab2 logic)
    best_idx = 0
    best_score = -999999
    
    min_q, max_q = min(attendances), max(attendances)
    min_pft, max_pft = min(profits), max(profits)
    
    for idx, (p, q, pft) in enumerate(zip(prices, attendances, profits)):
        norm_q = (q - min_q) / (max_q - min_q + 1e-5)
        norm_pft = (pft - min_pft) / (max_pft - min_pft + 1e-5)
        score = weight_rev * norm_pft + (1.0 - weight_rev) * norm_q
        if score > best_score:
            best_score = score
            best_idx = idx
            
    p_opt = prices[best_idx]
    p_curr = st.session_state.prices[selected_zona]
    
    # Build Plotly Subplots
    fig = sp.make_subplots(specs=[[{"secondary_y": True}]])
    
    # Add traces
    fig.add_trace(
        go.Scatter(
            x=prices, 
            y=revenues, 
            name="Ingreso Bruto ($)", 
            line=dict(color="#BABABA", width=1.5, dash="dot"),
            hovertemplate="Precio: $%{x}<br>Ingreso: $%{y:,.0f}"
        ),
        secondary_y=False
    )
    
    fig.add_trace(
        go.Scatter(
            x=prices, 
            y=profits, 
            name="Ganancia Neta (antes de CF) ($)", 
            line=dict(color="#ff6d29", width=3.5),
            hovertemplate="Precio: $%{x}<br>Ganancia: $%{y:,.0f}"
        ),
        secondary_y=False
    )
    
    fig.add_trace(
        go.Scatter(
            x=prices, 
            y=attendances, 
            name="Asistencia (Boletos)", 
            line=dict(color="#E0C0B3", width=2.5, dash="dash"),
            hovertemplate="Precio: $%{x}<br>Boletos: %{y:,.0f}"
        ),
        secondary_y=True
    )
    
    # Draw vertical indicator lines
    fig.add_vline(x=p_base, line_width=1.5, line_dash="solid", line_color="#888888", annotation_text="Base Histórica", annotation_position="top left")
    fig.add_vline(x=p_opt, line_width=2, line_dash="dash", line_color="#ff6d29", annotation_text="Óptimo Calculado", annotation_position="top right")
    fig.add_vline(x=p_curr, line_width=2, line_dash="solid", line_color="#00C0FF", annotation_text="Precio Seleccionado", annotation_position="bottom left")
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Hanken Grotesk", color="#e3e2e2"),
        title=dict(
            text=f"Sensibilidad al Precio: {selected_zona} (Elasticidad: {beta:.3f})", 
            font=dict(size=20, color="#ffffff"),
            x=0.5,
            xanchor='center'
        ),
        xaxis=dict(
            gridcolor='rgba(255,255,255,0.05)', 
            title="Precio ($)",
            tickprefix="$"
        ),
        yaxis=dict(
            gridcolor='rgba(255,255,255,0.05)', 
            title="Métricas Financieras ($)",
            tickprefix="$"
        ),
        yaxis2=dict(
            title="Asistencia (Boletos Vendidos)",
            gridcolor='rgba(255,255,255,0.02)'
        ),
        legend=dict(
            orientation="h", 
            yanchor="bottom", 
            y=-0.25, 
            xanchor="center", 
            x=0.5
        ),
        hovermode="x unified",
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Observations box
    st.markdown("#### 💡 Observaciones de Sensibilidad")
    if beta < -1.0:
        st.markdown(
            f"La zona **{selected_zona}** es **altamente sensible al precio (elástica)** con un coeficiente de {beta:.2f}. "
            "Cualquier incremento en el precio por encima del precio base histórico ($"
            f"{p_base}) provocará una caída de asistencia tan grande que reducirá los ingresos totales. "
            "**Recomendación:** Mantener o reducir levemente el precio para maximizar ingresos."
        )
    elif beta > -0.5:
        st.markdown(
            f"La zona **{selected_zona}** es **inelástica** con un coeficiente de {beta:.2f}. "
            "El porcentaje de caída en asistencia es mucho menor que el porcentaje de incremento del precio. "
            f"Esto significa que subir el precio en el rango histórico permitido (hasta ${p_max}) "
            "incrementará sustancialmente la ganancia neta. "
            "**Recomendación:** Ajustar precios al alza de manera segura."
        )
    else:
        st.markdown(
            f"La zona **{selected_zona}** presenta una sensibilidad moderada ({beta:.2f}). "
            "Se pueden realizar incrementos moderados cuidando el aforo de asistencia."
        )

# ==========================================
# TAB 4: INFERENCIA Y AUDITORÍA E3
# ==========================================
with tab4:
    st.markdown("### Resumen Científico y Metodológico (Notebook E3)")
    st.write(
        "Esta pestaña documenta la metodología formal de depuración e identificación estadística utilizada "
        "en la estimación de la elasticidad de los Capitanes CDMX, garantizando la reproducibilidad del análisis."
    )
    
    col_aud1, col_aud2 = st.columns(2)
    
    with col_aud1:
        st.markdown("#### 🔍 Cascada de Depuración del Universo")
        st.write("Criterios de exclusión económica y matemática aplicados para definir el mercado comercial real:")
        
        excl_data = {
            "Criterio / Paso": [
                "Paso 0 - Archivo completo",
                "Paso 1 - Exclusión de cortesías marcadas",
                "Paso 2 - Exclusión de precio $0 restante",
                "Paso 3 - Exclusión de precios promocionales < $20",
                "Paso 4 - Verificación de zona asignada"
            ],
            "Volumen (Boletos)": [
                "382,625 (100.0%)",
                "343,734 (89.8%)",
                "327,507 (85.6%)",
                "195,138 (51.0%)",
                "195,138 (51.0%)"
            ],
            "Excluidos": [
                "-",
                "38,891 (10.2%) de cortesías",
                "16,227 (4.2%) ceros huérfanos",
                "132,369 (34.6%) promo masiva $10",
                "0 (0.0%) zonas nulas"
            ]
        }
        st.table(pd.DataFrame(excl_data))
        
        st.markdown(
            "> **Nota Contable Crítica (Auditoría):** Se identificaron **~44,000 boletos** con precio positivo pero "
            "**$0 de cobro** registrado en canales de pago (totalizando **$44.5 MDP sin trazabilidad contable**). "
            "Se decidió conservarlos para el análisis de pricing debido a que el precio de mercado era válido, "
            "pero se reportó como un hallazgo severo de gobierno de datos."
        )
        
    with col_aud2:
        st.markdown("#### 🧬 Escalera de Identificación de Regresión")
        st.write("Comparación de las especificaciones OLS para corregir sesgos de variable omitida:")
        
        reg_data = {
            "Modelo": [
                "1. Sin Controles (Sesgo de Calidad)",
                "2. + Efectos Fijos de Zona",
                "3. + Efectos Fijos de Zona y Juego (E3)"
            ],
            "b (Elasticidad)": ["-0.503", "-0.197", "-0.272"],
            "ee": ["0.025", "0.038", "0.033"],
            "R²": ["0.155", "0.482", "0.710"],
            "Interpretación del Sesgo": [
                "Confunde precio con tamaño de zona (zonas premium son chicas y caras).",
                "Corrige la zona, pero sesga b hacia cero por el atractivo del partido.",
                "IDENTIFICACIÓN LIMPIA. Descuenta el atractivo global de cada juego."
            ]
        }
        st.table(pd.DataFrame(reg_data))
        
        st.markdown(
            "#### 📊 Análisis de Sensibilidad al Umbral ($20)\n"
            "El umbral de exclusión de precios promocionales se sometió a análisis de sensibilidad:\n"
            "- Con umbral de **$1**: $b = -0.15$\n"
            "- Con umbral de **$20** (Preferido): $b = -0.27$\n"
            "- Con umbral de **$50**: $b = -0.49$\n"
            "\nEl valor de $|b| < 1$ se mantiene en todos los escenarios, confirmando la **naturaleza inelástica** "
            "de la demanda comercial en los precios históricos."
        )

# --- FOOTER ---
st.markdown("---")
st.markdown(
    '<div style="text-align: center; color: #BABABA; font-size: 13px; padding: 10px 0;">'
    'Proyecto Capitanes CDMX · Desarrollado por Antigravity'
    '</div>',
    unsafe_allow_html=True
)
