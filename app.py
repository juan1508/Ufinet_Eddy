import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import json
import os
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# PAGE CONFIG & UFINET BRAND STYLES
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Ufinet | Monitor de Incidencias",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Ufinet brand colors: Blue #0057A8, Dark Navy #003087, Light #E8F1FB
UFINET_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow:wght@400;600;700;800&family=Barlow+Condensed:wght@700;900&display=swap');

html, body, [class*="css"] {
    font-family: 'Barlow', sans-serif;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #003087 !important;
    border-right: 3px solid #0057A8;
}
[data-testid="stSidebar"] * {
    color: #FFFFFF !important;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stMultiSelect label,
[data-testid="stSidebar"] h1, h2, h3 {
    color: #FFFFFF !important;
}

/* Top header */
.ufinet-header {
    background: linear-gradient(135deg, #003087 0%, #0057A8 100%);
    padding: 18px 28px;
    border-radius: 10px;
    border-left: 6px solid #00AEEF;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 20px;
}
.ufinet-header h1 {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 2.2rem;
    font-weight: 900;
    color: #FFFFFF;
    margin: 0;
    letter-spacing: 1px;
    text-transform: uppercase;
}
.ufinet-header span {
    color: #00AEEF;
}

/* KPI Cards */
.kpi-card {
    background: #003087;
    border-radius: 10px;
    padding: 20px;
    border-top: 4px solid #0057A8;
    text-align: center;
}
.kpi-value {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 2.8rem;
    font-weight: 900;
    color: #0057A8;
}
.kpi-label {
    font-size: 0.85rem;
    color: #aaaaaa;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* Alert pills */
.badge-critical { background:#E30613; color:#fff; padding:3px 10px; border-radius:20px; font-size:0.78rem; font-weight:700; }
.badge-risk     { background:#FF6B00; color:#fff; padding:3px 10px; border-radius:20px; font-size:0.78rem; font-weight:700; }
.badge-warning  { background:#FFC107; color:#000; padding:3px 10px; border-radius:20px; font-size:0.78rem; font-weight:700; }
.badge-ok       { background:#28a745; color:#fff; padding:3px 10px; border-radius:20px; font-size:0.78rem; font-weight:700; }

/* Section title */
.section-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.4rem;
    font-weight: 800;
    text-transform: uppercase;
    color: #0057A8;
    letter-spacing: 1px;
    border-bottom: 2px solid #0057A8;
    padding-bottom: 6px;
    margin-bottom: 16px;
}

/* Dataframe fix */
.dataframe th {
    background: #003087 !important;
    color: #00AEEF !important;
}

div[data-testid="stMetricValue"] {
    color: #0057A8 !important;
    font-family: 'Barlow Condensed', sans-serif !important;
    font-size: 2rem !important;
    font-weight: 900 !important;
}

/* ── Multiselect tags: quitar rojo, poner azul ── */
span[data-baseweb="tag"] {
    background-color: #0057A8 !important;
    border-color: #003087 !important;
}
span[data-baseweb="tag"] span {
    color: #FFFFFF !important;
}
/* X button dentro del tag */
span[data-baseweb="tag"] svg {
    fill: #FFFFFF !important;
}
/* Botón "clear all" (X grande circular) */
div[data-baseweb="select"] svg {
    color: #0057A8 !important;
    fill: #0057A8 !important;
}

/* ── Tab activo: línea azul en vez de roja ── */
button[data-baseweb="tab"][aria-selected="true"] {
    color: #0057A8 !important;
    border-bottom-color: #0057A8 !important;
}
div[data-testid="stTabs"] button[aria-selected="true"] {
    border-bottom: 3px solid #0057A8 !important;
    color: #0057A8 !important;
}

/* Hover en tabs */
div[data-testid="stTabs"] button:hover {
    color: #00AEEF !important;
    border-bottom: 3px solid #00AEEF !important;
}
</style>
"""
st.markdown(UFINET_CSS, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown("""
<div class="ufinet-header">
    <div>
        <h1>🔵 Ufinet <span>|</span> Monitor de Incidencias</h1>
        <p style="color:#cce4ff; margin:0; font-size:0.9rem;">Dashboard de Reincidencias · MTBF · Disponibilidad · Cono Sur</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_from_gsheet(sheet_url: str, sheet_name: str = None):
    """Load data from Google Sheets using service account credentials stored in st.secrets."""
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly",
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sh = client.open_by_url(sheet_url)
        ws = sh.worksheet(sheet_name) if sheet_name else sh.get_worksheet(0)
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        return df, None
    except Exception as e:
        return None, str(e)


@st.cache_data(ttl=300)
def load_from_upload(uploaded_file):
    """Load data from uploaded Excel file."""
    try:
        df = pd.read_excel(uploaded_file, engine="openpyxl")
        return df, None
    except Exception as e:
        return None, str(e)


def standardize_df(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns to standard internal names."""
    col_map = {
        "Id de Ticket": "ticket_id",
        "Fecha y Hora de creación": "fecha_creacion",
        "Fecha de restablecimiento del servicio": "fecha_restablecimiento",
        "Fecha estado resuelto": "fecha_resuelto",
        "Cliente Customer": "cliente",
        "Servicio afectado": "servicio",
        "País Origen": "pais",
        "Prioridad": "prioridad",
        "Tiempo imputable a Ufinet": "tiempo_ufinet_min",
        "Capacidad (Mpbs)": "capacidad",
        "Título de la Incidencia": "titulo",
        "Tipo de Incidencia": "tipo_incidencia",
        "Imputable a": "imputable",
        "Código administrativo": "codigo_admin",
        "Cliente Final (Servicio afectado) (Servicios contratados)": "cliente_final",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    # Parse dates
    for col in ["fecha_creacion", "fecha_restablecimiento", "fecha_resuelto"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Numeric
    if "tiempo_ufinet_min" in df.columns:
        df["tiempo_ufinet_min"] = pd.to_numeric(df["tiempo_ufinet_min"], errors="coerce").fillna(0)

    return df


# ─────────────────────────────────────────────
# SIDEBAR – DATA SOURCE
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuración")
    st.markdown("---")

    data_source = st.radio(
        "Fuente de datos",
        ["📂 Subir Excel", "🌐 Google Sheets"],
        index=0,
    )

    df_raw = None
    load_error = None

    if data_source == "🌐 Google Sheets":
        sheet_url = st.text_input(
            "URL de Google Sheets",
            placeholder="https://docs.google.com/spreadsheets/d/...",
        )
        sheet_tab = st.text_input("Nombre de pestaña (opcional)", "")
        if st.button("🔄 Cargar datos", type="primary") and sheet_url:
            with st.spinner("Conectando con Google Sheets..."):
                df_raw, load_error = load_from_gsheet(
                    sheet_url, sheet_tab if sheet_tab else None
                )
        st.markdown("---")
        st.markdown(
            "**Nota:** Configura tus credenciales de servicio en `.streamlit/secrets.toml` "
            "bajo la clave `[gcp_service_account]`."
        )
    else:
        uploaded = st.file_uploader("Sube tu archivo Excel (.xlsx)", type=["xlsx", "xls"])
        if uploaded:
            df_raw, load_error = load_from_upload(uploaded)

    st.markdown("---")
    st.markdown("### 🗓️ Filtros globales")

    # Placeholder filters (populated after data loads)
    filter_pais = []
    filter_cliente = []
    filter_fecha_start = None
    filter_fecha_end = None


# ─────────────────────────────────────────────
# LOAD SAMPLE DATA IF NOTHING LOADED
# ─────────────────────────────────────────────
if df_raw is None and load_error is None:
    st.info("👆 Sube un archivo Excel o conecta Google Sheets en el panel lateral para comenzar.", icon="ℹ️")
    st.stop()

if load_error:
    st.error(f"❌ Error al cargar datos: {load_error}")
    st.stop()

df = standardize_df(df_raw.copy())

# ─────────────────────────────────────────────
# SIDEBAR FILTERS (after data is loaded)
# ─────────────────────────────────────────────
with st.sidebar:
    if "pais" in df.columns:
        paises = sorted(df["pais"].dropna().unique().tolist())
        filter_pais = st.multiselect("🌍 País", paises, default=paises)

    if "cliente" in df.columns:
        clientes = sorted(df["cliente"].dropna().unique().tolist())
        filter_cliente = st.multiselect("🏢 Cliente", clientes, default=clientes)

    if "fecha_creacion" in df.columns:
        min_d = df["fecha_creacion"].min().date()
        max_d = df["fecha_creacion"].max().date()
        filter_fecha_start = st.date_input("Desde", value=min_d)
        filter_fecha_end = st.date_input("Hasta", value=max_d)

# Apply filters
mask = pd.Series([True] * len(df), index=df.index)
if filter_pais and "pais" in df.columns:
    mask &= df["pais"].isin(filter_pais)
if filter_cliente and "cliente" in df.columns:
    mask &= df["cliente"].isin(filter_cliente)
if filter_fecha_start and "fecha_creacion" in df.columns:
    mask &= df["fecha_creacion"].dt.date >= filter_fecha_start
if filter_fecha_end and "fecha_creacion" in df.columns:
    mask &= df["fecha_creacion"].dt.date <= filter_fecha_end

df_f = df[mask].copy()

# ─────────────────────────────────────────────
# DATE HELPERS
# ─────────────────────────────────────────────
now = datetime.now()
inicio_mes_actual = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
inicio_trimestre = now - timedelta(days=90)
inicio_30d = now - timedelta(days=30)

date_col = "fecha_creacion" if "fecha_creacion" in df_f.columns else None

# ─────────────────────────────────────────────
# KPI ROW
# ─────────────────────────────────────────────
total_tickets = len(df_f)
if date_col:
    tickets_mes = df_f[df_f[date_col] >= inicio_mes_actual]
    total_mes = len(tickets_mes)
else:
    total_mes = 0

servicios_uniq = df_f["servicio"].nunique() if "servicio" in df_f.columns else 0
clientes_uniq = df_f["cliente"].nunique() if "cliente" in df_f.columns else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("🎫 Total Tickets", f"{total_tickets:,}")
col2.metric("📅 Tickets Este Mes", f"{total_mes:,}")
col3.metric("🔗 Servicios Únicos", f"{servicios_uniq:,}")
col4.metric("🏢 Clientes", f"{clientes_uniq:,}")

st.markdown("---")

# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🔁 Reincidencias (Punto 2)",
    "⏱️ MTBF (Punto 3)",
    "📶 Disponibilidad (Puntos 4-5)",
    "📊 Alertas Diarias (Punto 1)",
])


# ═══════════════════════════════════════════
# TAB 1 – REINCIDENCIAS ⭐ URGENTE
# ═══════════════════════════════════════════
with tab1:
    st.markdown('<div class="section-title">🔁 Reporte de Reincidencias / Recurrencias</div>', unsafe_allow_html=True)
    st.markdown("""
    > **Criterios de alerta:**  
    > • Más de **2 incidentes en el último mes**  
    > • **Más de 2 incidentes en el último trimestre** AND al menos **1 incidente en el último mes**
    """)

    if date_col is None or "servicio" not in df_f.columns:
        st.warning("Se requieren columnas de fecha y servicio para calcular reincidencias.")
    else:
        # Build per-service counts
        df_mes = df_f[df_f[date_col] >= inicio_mes_actual]
        df_30d = df_f[df_f[date_col] >= inicio_30d]
        df_trim = df_f[df_f[date_col] >= inicio_trimestre]

        cnt_mes = df_mes.groupby("servicio").size().rename("incidentes_mes")
        cnt_30d = df_30d.groupby("servicio").size().rename("incidentes_30d")
        cnt_trim = df_trim.groupby("servicio").size().rename("incidentes_trimestre")

        stats = pd.concat([cnt_mes, cnt_30d, cnt_trim], axis=1).fillna(0).astype(int)
        stats = stats.reset_index()

        # Criterio 1: >2 en último mes
        crit1 = stats["incidentes_mes"] > 2
        # Criterio 2: >2 en último trimestre Y al menos 1 en último mes
        crit2 = (stats["incidentes_trimestre"] > 2) & (stats["incidentes_mes"] >= 1)

        stats["reincidente"] = crit1 | crit2
        stats["motivo"] = ""
        stats.loc[crit1 & ~crit2, "motivo"] = "🔴 >2 incidentes en el mes"
        stats.loc[~crit1 & crit2, "motivo"] = "🟠 >2 en trimestre + activo en mes"
        stats.loc[crit1 & crit2, "motivo"] = "🔴 Ambos criterios"

        # Merge with cliente info
        if "cliente" in df_f.columns:
            cliente_map = df_f.groupby("servicio")["cliente"].first().rename("cliente")
            stats = stats.merge(cliente_map, on="servicio", how="left")

        reincidentes = stats[stats["reincidente"]].sort_values("incidentes_mes", ascending=False)
        no_reincidentes = stats[~stats["reincidente"]]

        # KPIs row
        k1, k2, k3 = st.columns(3)
        k1.metric("🔴 Servicios Reincidentes", len(reincidentes))
        k2.metric("✅ Servicios Estables", len(no_reincidentes))
        pct = round(len(reincidentes) / max(len(stats), 1) * 100, 1)
        k3.metric("⚠️ % Reincidencia", f"{pct}%")

        st.markdown("---")

        if len(reincidentes) == 0:
            st.success("✅ No se detectaron reincidencias en el período analizado.")
        else:
            st.markdown(f"### 🚨 {len(reincidentes)} servicio(s) con reincidencia detectada")

            # Filter controls
            fc1, fc2 = st.columns([2, 2])
            with fc1:
                search_srv = st.text_input("🔍 Buscar servicio o cliente", "", key="search_reinc")
            with fc2:
                motivo_filter = st.multiselect(
                    "Filtrar por motivo",
                    reincidentes["motivo"].unique().tolist(),
                    default=reincidentes["motivo"].unique().tolist(),
                    key="motivo_filter"
                )

            df_show = reincidentes.copy()
            if search_srv:
                mask_s = df_show["servicio"].str.contains(search_srv, case=False, na=False)
                if "cliente" in df_show.columns:
                    mask_s |= df_show["cliente"].str.contains(search_srv, case=False, na=False)
                df_show = df_show[mask_s]
            if motivo_filter:
                df_show = df_show[df_show["motivo"].isin(motivo_filter)]

            # Display columns
            display_cols = ["servicio", "motivo", "incidentes_mes", "incidentes_30d", "incidentes_trimestre"]
            if "cliente" in df_show.columns:
                display_cols = ["cliente"] + display_cols

            st.dataframe(
                df_show[display_cols].rename(columns={
                    "servicio": "Servicio",
                    "cliente": "Cliente",
                    "motivo": "Criterio Reincidencia",
                    "incidentes_mes": "Incidentes Mes Actual",
                    "incidentes_30d": "Incidentes Últimos 30d",
                    "incidentes_trimestre": "Incidentes Últimos 90d",
                }),
                use_container_width=True,
                height=500,
            )

            # Download button
            csv = df_show[display_cols].to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Exportar Reincidentes CSV",
                csv,
                "reincidencias_ufinet.csv",
                "text/csv",
                key="download_reinc",
            )

            st.markdown("---")
            st.markdown("### 📋 Detalle de tickets por servicio reincidente")
            if len(reincidentes) > 0:
                srv_sel = st.selectbox(
                    "Selecciona un servicio para ver sus tickets",
                    reincidentes["servicio"].tolist(),
                    key="srv_detail"
                )
                tickets_srv = df_f[df_f["servicio"] == srv_sel].copy()
                detail_cols = [c for c in ["ticket_id", "fecha_creacion", "fecha_resuelto", "titulo", "cliente", "pais", "prioridad"] if c in tickets_srv.columns]
                st.dataframe(
                    tickets_srv[detail_cols].sort_values("fecha_creacion", ascending=False),
                    use_container_width=True,
                )


# ═══════════════════════════════════════════
# TAB 2 – MTBF
# ═══════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-title">⏱️ MTBF – Mean Time Between Failures</div>', unsafe_allow_html=True)
    st.markdown("""
    > Promedio de días entre fallas. Evalúa la estabilidad de cada servicio.
    
    | MTBF | Nivel |
    |------|-------|
    | > 30 días | 🟢 Estable |
    | 15–30 días | 🟡 Moderado |
    | 7–15 días | 🟠 Inestable |
    | < 7 días | 🔴 Crítico |
    """)

    MTBF_COLORS = {
        "🟢 Estable (>30d)": "#28a745",
        "🟡 Moderado (15-30d)": "#FFC107",
        "🟠 Inestable (7-15d)": "#FF6B00",
        "🔴 Crítico (<7d)": "#E30613",
    }

    if date_col is None or "servicio" not in df_f.columns:
        st.warning("Se requieren columnas de fecha y servicio para calcular MTBF.")
    else:
        df_30d_mtbf = df_f[df_f[date_col] >= inicio_30d].copy()

        mtbf_records = []
        for srv, grp in df_30d_mtbf.groupby("servicio"):
            fechas = grp[date_col].dropna().sort_values().tolist()
            if len(fechas) < 2:
                continue
            diffs = [(fechas[i+1] - fechas[i]).days for i in range(len(fechas)-1)]
            mtbf_val = round(np.mean(diffs), 1)
            n_fallas = len(fechas)

            if mtbf_val > 30:
                nivel = "🟢 Estable (>30d)"
            elif mtbf_val >= 15:
                nivel = "🟡 Moderado (15-30d)"
            elif mtbf_val >= 7:
                nivel = "🟠 Inestable (7-15d)"
            else:
                nivel = "🔴 Crítico (<7d)"

            cliente_val = grp["cliente"].iloc[0] if "cliente" in grp.columns else "-"
            mtbf_records.append({
                "Servicio": srv,
                "Cliente": cliente_val,
                "MTBF (días)": mtbf_val,
                "# Fallas (30d)": n_fallas,
                "Nivel": nivel,
            })

        if not mtbf_records:
            st.info("No hay servicios con más de 1 incidente en los últimos 30 días.")
        else:
            df_mtbf = pd.DataFrame(mtbf_records).sort_values("MTBF (días)")

            # KPI
            km1, km2, km3, km4 = st.columns(4)
            km1.metric("🔴 Críticos (<7d)", len(df_mtbf[df_mtbf["Nivel"].str.startswith("🔴")]))
            km2.metric("🟠 Inestables (7-15d)", len(df_mtbf[df_mtbf["Nivel"].str.startswith("🟠")]))
            km3.metric("🟡 Moderados (15-30d)", len(df_mtbf[df_mtbf["Nivel"].str.startswith("🟡")]))
            km4.metric("🟢 Estables (>30d)", len(df_mtbf[df_mtbf["Nivel"].str.startswith("🟢")]))

            nivel_filter = st.multiselect(
                "Filtrar por nivel MTBF",
                df_mtbf["Nivel"].unique().tolist(),
                default=df_mtbf["Nivel"].unique().tolist(),
            )
            df_mtbf_show = df_mtbf[df_mtbf["Nivel"].isin(nivel_filter)]

            st.dataframe(df_mtbf_show, use_container_width=True, height=450)

            csv_mtbf = df_mtbf_show.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Exportar MTBF CSV", csv_mtbf, "mtbf_ufinet.csv", "text/csv")


# ═══════════════════════════════════════════
# TAB 3 – DISPONIBILIDAD
# ═══════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-title">📶 Disponibilidad – SLA 99.8%</div>', unsafe_allow_html=True)
    st.markdown("""
    > **Fórmula:** Consumo SLA = Downtime acumulado / Downtime permitido  
    > **Downtime permitido** al 99.8% de disponibilidad mensual ≈ **87.6 minutos/mes** (en un mes de 30d)
    
    | Consumo SLA | Nivel |
    |-------------|-------|
    | < 60% | 🟢 Seguro |
    | 60–80% | 🟡 Atención |
    | 80–95% | 🟠 Riesgo |
    | > 95% | 🔴 Crítico |
    """)

    DOWNTIME_PERMITTED_MIN = 87.6  # minutos/mes (99.8% disponibilidad, mes de 30 días)

    if "tiempo_ufinet_min" not in df_f.columns or date_col is None or "servicio" not in df_f.columns:
        st.warning("Se requieren columnas 'Tiempo imputable a Ufinet', fecha y servicio.")
    else:
        df_mes_disp = df_f[df_f[date_col] >= inicio_mes_actual].copy()
        df_mes_disp["tiempo_ufinet_min"] = pd.to_numeric(df_mes_disp["tiempo_ufinet_min"], errors="coerce").fillna(0)
        # Convert seconds to minutes if values look too large
        if df_mes_disp["tiempo_ufinet_min"].median() > 10000:
            df_mes_disp["tiempo_ufinet_min"] = df_mes_disp["tiempo_ufinet_min"] / 60

        disp_stats = df_mes_disp.groupby("servicio").agg(
            downtime_acum=("tiempo_ufinet_min", "sum"),
            n_tickets=("ticket_id", "count") if "ticket_id" in df_mes_disp.columns else ("servicio", "count"),
        ).reset_index()

        if "cliente" in df_f.columns:
            cm = df_f.groupby("servicio")["cliente"].first().reset_index()
            disp_stats = disp_stats.merge(cm, on="servicio", how="left")

        disp_stats["consumo_sla"] = (disp_stats["downtime_acum"] / DOWNTIME_PERMITTED_MIN * 100).round(1)
        disp_stats["consumo_sla"] = disp_stats["consumo_sla"].clip(0, 100)

        def sla_nivel(c):
            if c < 60: return "🟢 Seguro"
            elif c < 80: return "🟡 Atención"
            elif c < 95: return "🟠 Riesgo"
            else: return "🔴 Crítico"

        disp_stats["nivel_sla"] = disp_stats["consumo_sla"].apply(sla_nivel)
        disp_stats = disp_stats.sort_values("consumo_sla", ascending=False)

        # KPIs
        kd1, kd2, kd3, kd4 = st.columns(4)
        kd1.metric("🔴 Críticos (>95%)", len(disp_stats[disp_stats["nivel_sla"] == "🔴 Crítico"]))
        kd2.metric("🟠 Riesgo (80-95%)", len(disp_stats[disp_stats["nivel_sla"] == "🟠 Riesgo"]))
        kd3.metric("🟡 Atención (60-80%)", len(disp_stats[disp_stats["nivel_sla"] == "🟡 Atención"]))
        kd4.metric("🟢 Seguros (<60%)", len(disp_stats[disp_stats["nivel_sla"] == "🟢 Seguro"]))

        st.markdown("---")
        st.markdown("### 🔝 Top 20 servicios con menor disponibilidad")
        top20 = disp_stats.head(20)
        display_cols_d = ["servicio", "nivel_sla", "consumo_sla", "downtime_acum", "n_tickets"]
        if "cliente" in top20.columns:
            display_cols_d = ["cliente"] + display_cols_d

        st.dataframe(
            top20[display_cols_d].rename(columns={
                "servicio": "Servicio",
                "cliente": "Cliente",
                "nivel_sla": "Nivel SLA",
                "consumo_sla": "Consumo SLA (%)",
                "downtime_acum": "Downtime Acum. (min)",
                "n_tickets": "# Tickets",
            }),
            use_container_width=True,
        )

        csv_disp = disp_stats.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Exportar Disponibilidad CSV", csv_disp, "disponibilidad_ufinet.csv", "text/csv")


# ═══════════════════════════════════════════
# TAB 4 – ALERTAS DIARIAS (Punto 1)
# ═══════════════════════════════════════════
with tab4:
    st.markdown('<div class="section-title">🔔 Alertas Diarias – Servicios con >2 eventos en el mes</div>', unsafe_allow_html=True)
    st.markdown("> Servicios que ya superaron **2 incidentes** en el mes en curso. Reportar a Operación & Mantenimiento.")

    if date_col is None or "servicio" not in df_f.columns:
        st.warning("Se requieren columnas de fecha y servicio.")
    else:
        df_mes_alert = df_f[df_f[date_col] >= inicio_mes_actual]
        cnt_alert = df_mes_alert.groupby("servicio").size().reset_index(name="incidentes_mes")
        if "cliente" in df_f.columns:
            cm2 = df_f.groupby("servicio")["cliente"].first().reset_index()
            cnt_alert = cnt_alert.merge(cm2, on="servicio", how="left")

        alertas = cnt_alert[cnt_alert["incidentes_mes"] > 2].sort_values("incidentes_mes", ascending=False)

        if len(alertas) == 0:
            st.success("✅ Ningún servicio supera los 2 incidentes este mes.")
        else:
            st.error(f"🚨 **{len(alertas)} servicio(s)** superan 2 incidentes este mes — Requieren atención de O&M")
            cols_a = ["servicio", "incidentes_mes"]
            if "cliente" in alertas.columns:
                cols_a = ["cliente"] + cols_a
            st.dataframe(
                alertas[cols_a].rename(columns={
                    "servicio": "Servicio",
                    "cliente": "Cliente",
                    "incidentes_mes": "# Incidentes Mes Actual",
                }),
                use_container_width=True,
                height=400,
            )
            csv_a = alertas.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Exportar Alertas CSV", csv_a, "alertas_diarias_ufinet.csv", "text/csv")

# Footer
st.markdown("---")
st.markdown(
    '<p style="text-align:center; color:#666; font-size:0.8rem;">Ufinet Monitor de Incidencias · Desarrollado con Streamlit · '
    + datetime.now().strftime("%d/%m/%Y %H:%M") + "</p>",
    unsafe_allow_html=True,
)
