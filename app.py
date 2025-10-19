# ============================================
# 📊 Desviación Procesal COS
# Pasos 1 a 8 + Bloque Banco (resúmenes)
# ============================================

import pandas as pd
import streamlit as st
import unicodedata
from io import BytesIO
from datetime import datetime
from dateutil.relativedelta import relativedelta

# ============================================
# ⚙️ CONFIGURACIÓN INICIAL
# ============================================
st.set_page_config(page_title="Desviación Procesal GNB SUDAMERIS 🌳", layout="wide")
st.title("📊 Desviación Procesal GNB SUDAMERIS 🌳")
# ============================
# 🎨 ESTILO OSCURO GLOBAL
# ============================
st.markdown("""
<style>
body, .stApp { background-color: #0E1117 !important; color: #FFFFFF !important; }
h1, h2, h3, h4, h5, h6, label, .stMetricLabel, .stMetricValue { color: #FFFFFF !important; }
.dataframe th {
  background-color: #1B1F24 !important; color: #FFFFFF !important; text-align: center !important;
  border: 1px solid #333 !important;
}
.dataframe td {
  color: #FFFFFF !important; background-color: #121417 !important; text-align: center !important;
  border: 1px solid #333 !important; font-family: 'Courier New', monospace;
}
.stDownloadButton > button {
  background-color: #1B1F24 !important; color: white !important; border: 1px solid #333;
  border-radius: 6px; padding: 0.5rem 1rem; font-weight: bold;
}
.stDownloadButton > button:hover { background-color: #2C313A !important; border-color: #555; }
.stAlert { background: #121417 !important; border: 1px solid #333 !important; }
</style>
""", unsafe_allow_html=True)
# ============================================
# 🧩 FUNCIÓN DE NORMALIZACIÓN DE COLUMNAS
# ============================================
def normalizar_columna(col: str) -> str:
    col = ''.join(c for c in unicodedata.normalize('NFD', col) if unicodedata.category(c) != 'Mn')
    col = col.upper().replace("-", "_").replace(" ", "_")
    col = ''.join(c for c in col if c.isalnum() or c == "_")
    while "__" in col:
        col = col.replace("__", "_")
    return col.strip("_")

# ============================================
# 🔠 MAPA MESES (ES)
# ============================================
MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

# ============================================
# 📘 PASOS 1–2 — CARGA Y LIMPIEZA DE ENCABEZADOS
# ============================================
inventario_file = st.file_uploader("Sube el inventario (.xlsx)", type=["xlsx"])
tiempos_path = "Tabla_tiempos_etapas_desviacion.xlsx"  # tabla fija en raíz (repositorio)

if not inventario_file:
    st.info("📥 Sube el inventario (.xlsx) para iniciar.")
    st.stop()

# Leer archivos
inv = pd.read_excel(inventario_file)
tiempos = pd.read_excel(tiempos_path)

# Normalizar encabezados
inv.columns = [normalizar_columna(c) for c in inv.columns]
tiempos.columns = [normalizar_columna(c) for c in tiempos.columns]

# ============================================
# 📗 PASO 3 — COMPLETAR DÍAS POR ETAPA (JOIN por subetapa)
# ============================================
col_sub_inv, col_sub_time = "SUB_ETAPA_JURIDICA", "DESCRIPCION_DE_LA_SUBETAPA"
col_dias, col_duracion = "DIAS_POR_ETAPA", "DURACION_MAXIMA_EN_DIAS"
if col_dias not in inv.columns:
    inv[col_dias] = None

inv = inv.merge(
    tiempos[[col_sub_time, col_duracion]],
    how="left",
    left_on=col_sub_inv,
    right_on=col_sub_time,
    suffixes=("", "_T")
)
inv[col_dias] = inv[col_dias].fillna(inv[col_duracion])

# ============================================
# 📆 PASO 4 — CALCULAR VAR_FECHA_CALCULADA Y DEPURAR (normalizando día)
# ============================================
for c in ["FECHA_ACT_INVENTARIO", "FECHA_ACT_ETAPA"]:
    if c not in inv.columns:
        st.error(f"❌ Falta la columna {c} en el inventario.")
        st.stop()

inv["FECHA_ACT_INVENTARIO"] = pd.to_datetime(inv["FECHA_ACT_INVENTARIO"], errors="coerce")
inv["FECHA_ACT_ETAPA"] = pd.to_datetime(inv["FECHA_ACT_ETAPA"], errors="coerce")

inv["VAR_FECHA_CALCULADA"] = (
    inv["FECHA_ACT_INVENTARIO"].dt.normalize() - inv["FECHA_ACT_ETAPA"].dt.normalize()
).dt.days

errores = inv[inv["VAR_FECHA_CALCULADA"].isna() | (inv["VAR_FECHA_CALCULADA"] < 0)].copy()
total_errores = len(errores)

if total_errores > 0:
    st.warning(f"⚠️ {total_errores:,} registros con errores de fecha (nulos o negativos).")
    out_err = BytesIO()
    errores.to_excel(out_err, index=False, engine="openpyxl")
    out_err.seek(0)
    st.download_button(
        "⬇️ Descargar registros con errores (Paso 4)",
        data=out_err,
        file_name="Errores_Fechas_Paso4.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.success("✅ No se encontraron errores de fecha.")

base_limpia = inv.dropna(subset=["VAR_FECHA_CALCULADA"])
base_limpia = base_limpia[base_limpia["VAR_FECHA_CALCULADA"] >= 0].copy()

# ============================================
# 🧮 Utilidad: asegurar métricas globales con SLA condicional
# ============================================
COS_SLA_SUBS = {"ENTREGA DE GARANTIAS", "ENTREGA PODER"}

def ensure_metrics_all(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in ["DIAS_POR_ETAPA", "VAR_FECHA_CALCULADA", "CAPITAL_ACT"]:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    out["DIAS_POR_ETAPA"] = out.get("DIAS_POR_ETAPA", 0).fillna(0)
    out["VAR_FECHA_CALCULADA"] = out.get("VAR_FECHA_CALCULADA", 0).fillna(0)
    out["CAPITAL_ACT"] = out.get("CAPITAL_ACT", 0).fillna(0)
    out["ETAPA_JURIDICA"] = out.get("ETAPA_JURIDICA", "").astype(str).str.upper()
    out["SUB_ETAPA_JURIDICA"] = out.get("SUB_ETAPA_JURIDICA", "").astype(str).str.upper()

    def calc_row(r):
        etapa = r["ETAPA_JURIDICA"]
        sub = r["SUB_ETAPA_JURIDICA"]
        dias = r["DIAS_POR_ETAPA"]
        var = r["VAR_FECHA_CALCULADA"]
        if etapa == "PASE A LEGAL" and sub not in COS_SLA_SUBS:
            return 0.0, "SIN SLA"
        if dias and dias > 0:
            porc = max(((var - dias) / dias) * 100, 0)
            if porc == 0:
                return 0.0, "A TIEMPO"
            elif porc <= 30:
                return porc, "LEVE"
            elif porc <= 70:
                return porc, "MODERADA"
            else:
                return porc, "GRAVE"
        else:
            return 0.0, "SIN SLA"

    results = out.apply(lambda r: calc_row(r), axis=1, result_type="expand")
    out["PORC_DESVIACION"] = pd.to_numeric(results[0], errors="coerce").fillna(0)
    out["NIVEL_DESVIACION"] = results[1]

    def estado(r):
        if r["NIVEL_DESVIACION"] == "SIN SLA":
            return "SIN SLA"
        return "FUERA DE TIEMPO" if r["PORC_DESVIACION"] > 0 else "A TIEMPO"
    out["ESTADO_TIEMPO"] = out.apply(estado, axis=1)

    out["PORC_AVANCE"] = out.apply(
        lambda x: (x["VAR_FECHA_CALCULADA"] / x["DIAS_POR_ETAPA"] * 100)
        if x["DIAS_POR_ETAPA"] > 0 else 0, axis=1
    )
    return out

df_all = ensure_metrics_all(base_limpia.copy())
st.session_state["base_limpia"] = df_all.copy()

# ============================================
# 📊 % Avance, % Desviación y Clasificación (Global)
# ============================================
df5 = df_all.copy()
df5.columns = [c.upper().replace("-", "_").replace(" ", "_") for c in df5.columns]
df5["CAPITAL_MILLONES"] = pd.to_numeric(df5.get("CAPITAL_ACT", 0), errors="coerce").fillna(0) / 1_000_000

total_procesos = len(df5)
total_clientes = df5["DEUDOR"].nunique() if "DEUDOR" in df5.columns else 0
capital_total = df5["CAPITAL_MILLONES"].sum()
desviados = (df5["ESTADO_TIEMPO"] == "FUERA DE TIEMPO").sum()

st.header("📊 % Avance, % Desviación y Clasificación (Global)")
c1, c2, c3, c4 = st.columns(4)
c1.metric("🧾 Procesos totales", f"{total_procesos:,}")
c2.metric("👤 Clientes únicos", f"{total_clientes:,}")
c3.metric("💰 Capital total", f"${capital_total:,.1f} M")
c4.metric("⚠️ Procesos con desviación", f"{desviados:,}")

resumen_estado = df5.groupby("ESTADO_TIEMPO").agg(
    PROCESOS=("ESTADO_TIEMPO", "count"),
    CAPITAL=("CAPITAL_MILLONES", "sum")
).reset_index()
resumen_estado["% DEL TOTAL"] = (resumen_estado["PROCESOS"] / max(total_procesos,1) * 100).round(1)

st.subheader("📋 Estado general de los procesos")
st.dataframe(
    resumen_estado.style.background_gradient(subset=["CAPITAL"], cmap="Greens").format({
        "CAPITAL": "{:,.1f}", "% DEL TOTAL": "{:.1f} %"
    }),
    use_container_width=True, height=150
)

desviados_df = df5[df5["ESTADO_TIEMPO"] == "FUERA DE TIEMPO"]
if not desviados_df.empty:
    gravedad = desviados_df.groupby("NIVEL_DESVIACION").agg(
        PROCESOS=("NIVEL_DESVIACION", "count"), CAPITAL=("CAPITAL_MILLONES", "sum")
    ).reindex(["LEVE", "MODERADA", "GRAVE"]).fillna(0)
    gravedad["% CAPITAL DESVIADO"] = (gravedad["CAPITAL"] / max(gravedad["CAPITAL"].sum(),1) * 100).round(1)
    st.subheader("📋 Niveles de gravedad de desviación")
    st.dataframe(
        gravedad.style.background_gradient(subset=["% CAPITAL DESVIADO"], cmap="RdYlGn_r").format({
            "CAPITAL": "{:,.1f}", "% CAPITAL DESVIADO": "{:.1f} %"
        }),
        use_container_width=True, height=180
    )

if "ETAPA_JURIDICA" in df5.columns:
    etapa_rank = df5.groupby("ETAPA_JURIDICA").agg(
        PROCESOS=("DEUDOR", "count"), CAPITAL=("CAPITAL_MILLONES", "sum"),
        PROM_DESV=("PORC_DESVIACION", "mean")
    ).reset_index().sort_values("CAPITAL", ascending=False)
    etapa_rank["PROM_DESV"] = etapa_rank["PROM_DESV"].round(1)
    st.subheader("🏛️ Ranking por Etapa Jurídica (todas)")
    st.dataframe(
        etapa_rank.style.background_gradient(subset=["PROM_DESV"], cmap="RdYlGn_r").format({
            "CAPITAL": "{:,.1f}", "PROM_DESV": "{:.1f} %"
        }),
        use_container_width=True, height=300
    )

if "SUB_ETAPA_JURIDICA" in df5.columns:
    sub_rank = df5.groupby("SUB_ETAPA_JURIDICA").agg(
        PROCESOS=("DEUDOR", "count"), CAPITAL=("CAPITAL_MILLONES", "sum"),
        PROM_DESV=("PORC_DESVIACION", "mean")
    ).reset_index().sort_values("PROM_DESV", ascending=False)
    sub_rank["PROM_DESV"] = sub_rank["PROM_DESV"].round(1)
    st.subheader("📚 Ranking por Subetapa Jurídica (todas)")
    st.dataframe(
        sub_rank.style.background_gradient(subset=["PROM_DESV"], cmap="RdYlGn_r").format({
            "CAPITAL": "{:,.1f}", "PROM_DESV": "{:.1f} %"
        }),
        use_container_width=True, height=350
    )

out5 = BytesIO()
df5.to_excel(out5, index=False, engine="openpyxl")
out5.seek(0)
st.download_button(
    "⬇️ Descargar Inventario Clasificado (Paso 5 - Global)",
    data=out5, file_name="Inventario_Paso5_Clasificado_Global.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

# ============================================
# 📊 Ranking visual Etapa × Subetapa (Global)
# ============================================
df6 = df_all.copy()
df6.columns = [c.upper().replace("-", "_").replace(" ", "_") for c in df6.columns]
df6["CAPITAL_MILLONES"] = pd.to_numeric(df6.get("CAPITAL_ACT", 0), errors="coerce").fillna(0) / 1_000_000

resumen = df6.groupby(["ETAPA_JURIDICA", "SUB_ETAPA_JURIDICA"]).agg(
    PROCESOS=("DEUDOR", "count"),
    CAPITAL_M=("CAPITAL_MILLONES", "sum"),
    PROM_DESV=("PORC_DESVIACION", "mean")
).reset_index()

resumen["PROM_DESV"] = resumen["PROM_DESV"].round(1)
resumen["CAPITAL_M"] = resumen["CAPITAL_M"].round(1)

def nivel(p): 
    if p == 0: return "A TIEMPO"
    return "🟢 Leve" if p <= 30 else ("🟡 Moderada" if p <= 70 else "🔴 Grave")
resumen["NIVEL"] = resumen["PROM_DESV"].apply(nivel)
resumen["INDICADOR"] = resumen["PROM_DESV"].apply(lambda x: "█" * int(min(x/5, 20)) if x>0 else "")

resumen = resumen.sort_values("PROM_DESV", ascending=False).reset_index(drop=True)

st.header("📊 Ranking Visual Etapa × Subetapa (Global)")
st.subheader("🔎 Desviación promedio, procesos y capital (todas las etapas/subetapas)")
st.dataframe(
    resumen[["ETAPA_JURIDICA", "SUB_ETAPA_JURIDICA", "PROCESOS", "CAPITAL_M", "PROM_DESV", "NIVEL", "INDICADOR"]]
    .style.format({"CAPITAL_M": "{:,.1f}", "PROM_DESV": "{:.1f} %", "PROCESOS": "{:,}"}),
    use_container_width=True, height=600
)

out6 = BytesIO()
resumen.to_excel(out6, index=False, sheet_name="Ranking_Visual_Global", engine="openpyxl")
out6.seek(0)
st.download_button(
    "⬇️ Descargar Ranking Visual (Paso 6 - Global)",
    data=out6, file_name="Ranking_Visual_Paso6_Global.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

# ============================================
# 📊 Clientes Críticos (Global) (Busqueda segmentada)
# ============================================
df7 = df_all.copy()
df7.columns = [c.upper().replace("-", "_").replace(" ", "_") for c in df7.columns]
df7["CAPITAL_MILLONES"] = pd.to_numeric(df7.get("CAPITAL_ACT", 0), errors="coerce").fillna(0) / 1_000_000
df7["DIAS_EXCESO"] = df7.apply(
    lambda x: max(x["VAR_FECHA_CALCULADA"] - x["DIAS_POR_ETAPA"], 0)
    if pd.notnull(x.get("VAR_FECHA_CALCULADA")) and pd.notnull(x.get("DIAS_POR_ETAPA")) else 0,
    axis=1
)

resumen_cliente = df7.groupby("DEUDOR").agg(
    OPERACIONES=("OPERACION", "count"),
    CAPITAL_M=("CAPITAL_MILLONES", "sum"),
    PROM_DESV=("PORC_DESVIACION", "mean"),
    DIAS_EXCESO_PROM=("DIAS_EXCESO", "mean")
).reset_index()

resumen_cliente["CAPITAL_M"] = resumen_cliente["CAPITAL_M"].round(1)
resumen_cliente["PROM_DESV"] = resumen_cliente["PROM_DESV"].round(1)
resumen_cliente["DIAS_EXCESO_PROM"] = resumen_cliente["DIAS_EXCESO_PROM"].round(1)

def nivel_c(p):
    if p == 0: return "A TIEMPO"
    return "🟢 Leve" if p <= 30 else ("🟡 Moderada" if p <= 70 else "🔴 Grave")
resumen_cliente["NIVEL"] = resumen_cliente["PROM_DESV"].apply(nivel_c)

graves = resumen_cliente[resumen_cliente["NIVEL"] == "🔴 Grave"]

total_clientes = len(resumen_cliente)
total_capital = resumen_cliente["CAPITAL_M"].sum()

st.header("📊 Clientes Críticos (Global) con Buscador Multicliente y Obligación")
c1, c2, c3, c4 = st.columns(4)
c1.metric("👤 Clientes totales", f"{total_clientes:,}")
c2.metric("📁 Operaciones totales", f"{df7.shape[0]:,}")
c3.metric("💰 Capital total", f"${total_capital:,.1f} M")
c4.metric("🔴 Clientes críticos (Grave)", f"{len(graves):,}")

st.subheader("🔴 Clientes Críticos (Grave) — Selecciona uno o varios para ver detalle")
st.dataframe(
    graves[["DEUDOR", "OPERACIONES", "CAPITAL_M", "PROM_DESV", "DIAS_EXCESO_PROM"]]
    .style.background_gradient(subset=["PROM_DESV"], cmap="Reds")
    .format({"CAPITAL_M": "{:,.1f}", "PROM_DESV": "{:.1f} %", "DIAS_EXCESO_PROM": "{:.0f} días"}),
    use_container_width=True, height=400
)

st.markdown("### 🔎 Buscar clientes y ver detalle de sus operaciones (con obligación)")
seleccion_clientes = st.multiselect(
    "Escribe para buscar uno o varios clientes:",
    options=graves["DEUDOR"].sort_values().unique(),
    help="Puedes escribir parte del nombre o número y seleccionar varios."
)

if seleccion_clientes:
    detalle = df7[df7["DEUDOR"].isin(seleccion_clientes)][
        ["DEUDOR", "OPERACION", "ETAPA_JURIDICA", "SUB_ETAPA_JURIDICA",
         "VAR_FECHA_CALCULADA", "DIAS_EXCESO", "CAPITAL_ACT", "PORC_DESVIACION"]
    ].copy()

    st.markdown(f"#### 📂 Detalle de operaciones — {len(detalle)} registros seleccionados")
    st.dataframe(
        detalle.style.background_gradient(subset=["PORC_DESVIACION"], cmap="Reds")
        .format({"CAPITAL_ACT": "${:,.0f}", "PORC_DESVIACION": "{:.1f} %", "DIAS_EXCESO": "{:.0f} días"}),
        use_container_width=True, height=450
    )

    resumen_sel = detalle.agg({"CAPITAL_ACT": "sum", "DIAS_EXCESO": "mean"})
    st.info(f"**Resumen de selección:** Capital total ${resumen_sel['CAPITAL_ACT']:,.0f} — "
            f"Promedio días exceso {resumen_sel['DIAS_EXCESO']:.0f}")

    out_det = BytesIO()
    detalle.to_excel(out_det, index=False, sheet_name="Detalle_Seleccion", engine="openpyxl")
    out_det.seek(0)
    st.download_button(
        "⬇️ Descargar detalle filtrado",
        data=out_det, file_name="Detalle_Clientes_Seleccionados.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

out7 = BytesIO()
graves.to_excel(out7, index=False, sheet_name="Clientes_Graves", engine="openpyxl")
out7.seek(0)
st.download_button(
    "⬇️ Descargar listado completo de Clientes Críticos",
    data=out7, file_name="Clientes_Graves_Paso7_Global.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

# ============================================
# 📊 Próximos a Vencer (Global) + Resumen por Subetapa 
# ============================================
df8 = df_all.copy()
df8.columns = [c.upper().replace("-", "_").replace(" ", "_") for c in df8.columns]

cols_need_8 = {"DEUDOR", "OPERACION", "ETAPA_JURIDICA", "SUB_ETAPA_JURIDICA",
               "CAPITAL_ACT", "DIAS_POR_ETAPA", "VAR_FECHA_CALCULADA", "FECHA_ACT_INVENTARIO"}
faltan_8 = cols_need_8 - set(df8.columns)
if not faltan_8:
    df8["FECHA_ACT_INVENTARIO"] = pd.to_datetime(df8["FECHA_ACT_INVENTARIO"], errors="coerce")
    df8["DIAS_POR_ETAPA"] = pd.to_numeric(df8["DIAS_POR_ETAPA"], errors="coerce")
    df8["VAR_FECHA_CALCULADA"] = pd.to_numeric(df8["VAR_FECHA_CALCULADA"], errors="coerce")

    df8["DIAS_RESTANTES"] = df8["DIAS_POR_ETAPA"] - df8["VAR_FECHA_CALCULADA"]
    df8["DIAS_RESTANTES"] = df8["DIAS_RESTANTES"].apply(lambda x: x if x > 0 else 0)

    df8["FECHA_LIMITE"] = df8.apply(
        lambda x: x["FECHA_ACT_INVENTARIO"] + pd.Timedelta(days=x["DIAS_RESTANTES"])
        if pd.notnull(x["FECHA_ACT_INVENTARIO"]) else pd.NaT, axis=1
    )

    hoy = datetime.now()
    fin_mes = datetime(hoy.year, hoy.month, 1) + relativedelta(months=1) - relativedelta(days=1)
    df8["DIAS_FIN_MES"] = (fin_mes - hoy).days

    df8["RIESGO_MES"] = df8.apply(
        lambda x: "🟠 Próximo a vencer" if 0 < x["DIAS_RESTANTES"] <= x["DIAS_FIN_MES"] else "", axis=1
    )

    proximos = df8[df8["RIESGO_MES"] == "🟠 Próximo a vencer"].copy()
    proximos["CAPITAL_MILLONES"] = pd.to_numeric(proximos["CAPITAL_ACT"], errors="coerce").fillna(0) / 1_000_000

    procesos_totales = len(df8)
    clientes_totales = df8["DEUDOR"].nunique()
    capital_riesgo = proximos["CAPITAL_MILLONES"].sum()
    procesos_riesgo = len(proximos)

    st.header("📊 Próximos a Vencer (Riesgo del Mes Actual) — Global")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📁 Procesos totales", f"{procesos_totales:,}")
    c2.metric("👤 Clientes únicos", f"{clientes_totales:,}")
    c3.metric("💰 Capital en riesgo", f"${capital_riesgo:,.1f} M")
    c4.metric("🟠 Procesos próximos a vencer", f"{procesos_riesgo:,}")

    if len(proximos) > 0:
        st.subheader("📋 Resumen por Subetapa Jurídica (Riesgo del Mes)")
        resumen_subetapa = proximos.groupby("SUB_ETAPA_JURIDICA").agg(
            PROCESOS=("OPERACION", "count"),
            CLIENTES=("DEUDOR", "nunique"),
            CAPITAL_M=("CAPITAL_MILLONES", "sum")
        ).reset_index()
        resumen_subetapa["% PROCESOS"] = (
            resumen_subetapa["PROCESOS"] / max(resumen_subetapa["PROCESOS"].sum(), 1) * 100
        ).round(1)
        resumen_subetapa = resumen_subetapa.sort_values("PROCESOS", ascending=False)

        st.dataframe(
            resumen_subetapa.style.background_gradient(subset=["CAPITAL_M"], cmap="YlOrRd")
            .format({"CAPITAL_M": "{:,.1f}", "% PROCESOS": "{:.1f} %", "PROCESOS": "{:,}", "CLIENTES": "{:,}"}),
            use_container_width=True, height=250
        )

    if len(proximos) == 0:
        st.info("✅ No hay procesos próximos a vencer este mes.")
    else:
        st.subheader("🟠 Procesos próximos a vencer dentro del mes")

        subetapas_unicas = sorted(proximos["SUB_ETAPA_JURIDICA"].dropna().unique())
        filtro_subetapas = st.multiselect(
            "🔍 Filtrar por Subetapa Jurídica:",
            options=subetapas_unicas, default=[],
            help="Selecciona una o varias subetapas para filtrar la tabla. Si no seleccionas ninguna, se mostrarán todas."
        )
        if filtro_subetapas:
            proximos_filtrados = proximos[proximos["SUB_ETAPA_JURIDICA"].isin(filtro_subetapas)]
        else:
            proximos_filtrados = proximos.copy()

        columnas_mostrar = ["DEUDOR", "OPERACION", "ETAPA_JURIDICA", "SUB_ETAPA_JURIDICA",
                            "DIAS_RESTANTES", "FECHA_LIMITE", "CAPITAL_ACT"]
        if "CIUDAD" in df8.columns: columnas_mostrar.append("CIUDAD")
        if "JUZGADO" in df8.columns: columnas_mostrar.append("JUZGADO")

        st.dataframe(
            proximos_filtrados[columnas_mostrar].sort_values("DIAS_RESTANTES")
            .style.background_gradient(subset=["DIAS_RESTANTES"], cmap="YlOrRd_r")
            .format({
                "CAPITAL_ACT": "${:,.0f}",
                "DIAS_RESTANTES": "{:.0f} días",
                "FECHA_LIMITE": lambda x: x.strftime("%Y-%m-%d") if pd.notnull(x) else ""
            }),
            use_container_width=True, height=550
        )

        out8 = BytesIO()
        with pd.ExcelWriter(out8, engine="openpyxl") as writer:
            proximos_filtrados.to_excel(writer, index=False, sheet_name="Proximos_a_Vencer")
            if len(proximos) > 0:
                resumen_subetapa.to_excel(writer, index=False, sheet_name="Resumen_Subetapa")
        out8.seek(0)
        st.download_button(
            "⬇️ Descargar Próximos a Vencer (según filtro)",
            data=out8, file_name="Proximos_a_Vencer_Filtrado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# ============================================
# 🏦 BLOQUE FINAL — Procesos bajo control del Banco (No incluidos en SLA COS)
# ============================================
st.header("🏦 Procesos bajo control del Banco (No incluidos en SLA COS)")

SUB_BANCO = {"EN TRAMITE", "RECEPCION GARANTIAS", "PODER PARA FIRMA", "RECEPCION PODER", "RETIRO"}
df_banco = df_all[
    (df_all["ETAPA_JURIDICA"].astype(str).str.upper() == "PASE A LEGAL") &
    (df_all["SUB_ETAPA_JURIDICA"].astype(str).str.upper().isin(SUB_BANCO))
].copy()

if df_banco.empty:
    st.info("✅ No hay procesos bajo control del banco para mostrar.")
else:
    dfb = df_banco.copy()
    dfb["CAPITAL_ACT"] = pd.to_numeric(dfb.get("CAPITAL_ACT", 0), errors="coerce").fillna(0)
    dfb["CAPITAL_MILLONES"] = dfb["CAPITAL_ACT"] / 1_000_000

    if "AÑO_PASE_JURIDICO" not in dfb.columns or "MES_PASE_JURIDICO" not in dfb.columns:
        dfb["FECHA_PASE_JURIDICO"] = pd.to_datetime(dfb.get("FECHA_ACT_ETAPA", pd.NaT), errors="coerce")
        dfb["AÑO_PASE_JURIDICO"] = dfb["FECHA_PASE_JURIDICO"].dt.year
        dfb["MES_NUM"] = dfb["FECHA_PASE_JURIDICO"].dt.month
        dfb["MES_PASE_JURIDICO"] = dfb["MES_NUM"].map(MESES_ES)
    else:
        if pd.api.types.is_numeric_dtype(dfb.get("MES_PASE_JURIDICO")):
            dfb["MES_NUM"] = pd.to_numeric(dfb["MES_PASE_JURIDICO"], errors="coerce")
            dfb["MES_PASE_JURIDICO"] = dfb["MES_NUM"].map(MESES_ES)

    resumen_mensual = dfb.groupby(["AÑO_PASE_JURIDICO", "MES_PASE_JURIDICO"]).agg(
        PROCESOS=("OPERACION", "count"),
        CLIENTES=("DEUDOR", "nunique"),
        CAPITAL_M=("CAPITAL_MILLONES", "sum")
    ).reset_index()

    if "MES_NUM" in dfb.columns:
        orden = dfb.groupby(["AÑO_PASE_JURIDICO", "MES_PASE_JURIDICO"])["MES_NUM"].min().reset_index()
        resumen_mensual = resumen_mensual.merge(orden, on=["AÑO_PASE_JURIDICO", "MES_PASE_JURIDICO"], how="left")
        resumen_mensual = resumen_mensual.sort_values(["AÑO_PASE_JURIDICO", "MES_NUM"]).drop(columns=["MES_NUM"])
    else:
        mes_order = {v: k for k, v in MESES_ES.items()}
        resumen_mensual["MES_ORD"] = resumen_mensual["MES_PASE_JURIDICO"].map(mes_order)
        resumen_mensual = resumen_mensual.sort_values(["AÑO_PASE_JURIDICO", "MES_ORD"]).drop(columns=["MES_ORD"])

    total_procesos_banco = resumen_mensual["PROCESOS"].sum() if not resumen_mensual.empty else 0
    total_capital_banco = resumen_mensual["CAPITAL_M"].sum() if not resumen_mensual.empty else 0

    if total_procesos_banco > 0:
        resumen_mensual["% PROCESOS"] = (resumen_mensual["PROCESOS"] / total_procesos_banco * 100).round(1)
    resumen_mensual["CAPITAL_M"] = resumen_mensual["CAPITAL_M"].round(1)

    total_row_mensual = pd.DataFrame({
        "AÑO_PASE_JURIDICO": ["TOTAL"],
        "MES_PASE_JURIDICO": [""],
        "PROCESOS": [total_procesos_banco],
        "CLIENTES": [dfb["DEUDOR"].nunique()],
        "CAPITAL_M": [round(total_capital_banco,1)],
        "% PROCESOS": [100.0 if total_procesos_banco>0 else 0.0]
    })
    resumen_mensual_tot = pd.concat([resumen_mensual, total_row_mensual], ignore_index=True)

    st.subheader("🗓️ Resumen mensual (Año × Mes) — Banco")
    st.dataframe(
        resumen_mensual_tot.style.background_gradient(subset=["CAPITAL_M"], cmap="YlOrRd")
        .format({"CAPITAL_M": "{:,.1f}", "PROCESOS": "{:,}", "CLIENTES": "{:,}", "% PROCESOS": "{:.1f} %"}),
        use_container_width=True, height=300
    )

    resumen_sub_mensual = dfb.groupby(["AÑO_PASE_JURIDICO", "MES_PASE_JURIDICO", "SUB_ETAPA_JURIDICA"]).agg(
        PROCESOS=("OPERACION", "count"),
        CLIENTES=("DEUDOR", "nunique"),
        CAPITAL_M=("CAPITAL_MILLONES", "sum")
    ).reset_index()

    if "MES_NUM" in dfb.columns:
        orden2 = dfb.groupby(["AÑO_PASE_JURIDICO", "MES_PASE_JURIDICO"])["MES_NUM"].min().reset_index()
        resumen_sub_mensual = resumen_sub_mensual.merge(orden2, on=["AÑO_PASE_JURIDICO", "MES_PASE_JURIDICO"], how="left")
        resumen_sub_mensual = resumen_sub_mensual.sort_values(["AÑO_PASE_JURIDICO", "MES_NUM", "SUB_ETAPA_JURIDICA"]).drop(columns=["MES_NUM"])
    else:
        mes_order = {v: k for k, v in MESES_ES.items()}
        resumen_sub_mensual["MES_ORD"] = resumen_sub_mensual["MES_PASE_JURIDICO"].map(mes_order)
        resumen_sub_mensual = resumen_sub_mensual.sort_values(["AÑO_PASE_JURIDICO", "MES_ORD", "SUB_ETAPA_JURIDICA"]).drop(columns=["MES_ORD"])

    total_procesos_banco2 = resumen_sub_mensual["PROCESOS"].sum() if not resumen_sub_mensual.empty else 0
    total_capital_banco2 = resumen_sub_mensual["CAPITAL_M"].sum() if not resumen_sub_mensual.empty else 0

    if total_procesos_banco2 > 0:
        resumen_sub_mensual["% PROCESOS"] = (resumen_sub_mensual["PROCESOS"] / total_procesos_banco2 * 100).round(1)
    resumen_sub_mensual["CAPITAL_M"] = resumen_sub_mensual["CAPITAL_M"].round(1)

    total_row_sub = pd.DataFrame({
        "AÑO_PASE_JURIDICO": ["TOTAL"],
        "MES_PASE_JURIDICO": [""],
        "SUB_ETAPA_JURIDICA": [""],
        "PROCESOS": [total_procesos_banco2],
        "CLIENTES": [dfb["DEUDOR"].nunique()],
        "CAPITAL_M": [round(total_capital_banco2,1)],
        "% PROCESOS": [100.0 if total_procesos_banco2>0 else 0.0]
    })
    resumen_sub_mensual_tot = pd.concat([resumen_sub_mensual, total_row_sub], ignore_index=True)

    st.subheader("⚖️ Resumen por Subetapa × Mes × Año (Banco)")
    st.dataframe(
        resumen_sub_mensual_tot.style.background_gradient(subset=["CAPITAL_M"], cmap="YlOrRd")
        .format({"CAPITAL_M": "{:,.1f}", "PROCESOS": "{:,}", "CLIENTES": "{:,}", "% PROCESOS": "{:.1f} %"}),
        use_container_width=True, height=380
    )

    out_banco = BytesIO()
    with pd.ExcelWriter(out_banco, engine="openpyxl") as writer:
        resumen_mensual_tot.to_excel(writer, index=False, sheet_name="Resumen_Mensual")
        resumen_sub_mensual_tot.to_excel(writer, index=False, sheet_name="Resumen_Subetapa_Mensual")
    out_banco.seek(0)
    st.download_button(
        "⬇️ Descargar Procesos del Banco (ambos resúmenes)",
        data=out_banco, file_name="Procesos_Banco_Resumen.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
  # ============================================
# 🤖 ANÁLISIS AUTOMÁTICO CON IA — CHRIS IA 🩵 (Versión Jurídica Bancaria)
# ============================================

st.markdown("### 🤖 Análisis Automático con IA — Informe Jurídico Comercial (CHRIS IA 🩵)")

try:
    from openai import OpenAI
    from datetime import datetime

    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    fecha_actual = datetime.now().strftime("%d/%m/%Y")

    if st.button("🧠 Generar Informe Jurídico con IA"):
        with st.spinner("CHRIS IA está analizando los resultados..."):
            # Resumen rápido del dataset
            total = len(df_all)
            promedio = df_all.get("PORC_DESVIACION", pd.Series([0])).mean()
            fuera = df_all[df_all.get("PORC_DESVIACION", 0) > 0.3].shape[0]
            etapas_top = ", ".join(df_all["ETAPA_JURIDICA"].value_counts().head(3).index)

            resumen = (
                f"Total de procesos: {total}. "
                f"Promedio de desviación: {promedio:.2%}. "
                f"Procesos fuera de tiempo (>30%): {fuera}. "
                f"Etapas más frecuentes: {etapas_top}."
            )

            prompt = f"""
Eres un abogado especializado en procesos comerciales y demandas a clientes en mora del sector bancario colombiano.

Con base en la siguiente información estadística sobre los procesos judiciales en curso:

{resumen}

Redacta un **Informe Gerencial Jurídico** para Contacto Solutions que incluya:

1. Interpretación general de los resultados con lenguaje técnico-jurídico.
2. Identificación de las etapas con mayor desviación y explicación de las posibles causas desde una perspectiva legal y operativa.
3. Recomendaciones concretas para optimizar la gestión procesal, prevenir incumplimientos y mejorar la eficiencia.
4. Un tono formal, objetivo y propio de un abogado litigante del área de cobranza judicial bancaria.
5. Al final, agrega un bloque de firma con esta estructura:

---
**Informe Jurídico elaborado por:** CHRIS IA 🩵  
**Área:** Control Procesal Bancario – Contacto Solutions  
**Fecha:** {fecha_actual}
---
"""

            respuesta = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un abogado colombiano experto en derecho comercial y procesos ejecutivos bancarios.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=700,
            )

            texto_ia = respuesta.choices[0].message.content.strip()

            st.success("✅ Informe jurídico generado correctamente por CHRIS IA 🩵")
            st.markdown("#### 📋 Resultado del Análisis Jurídico:")
            st.markdown(texto_ia)

            st.session_state["analisis_ia_chris"] = {
                "texto": texto_ia,
                "fecha": fecha_actual
            }

except Exception as e:
    st.warning(f"⚠️ No se pudo ejecutar el análisis IA: {e}")
    st.info("Verifica que tu archivo `.streamlit/secrets.toml` contenga la clave `OPENAI_API_KEY`.")
  # ============================================
# 🧠 IA CORRECTIVA — Diagnóstico de Desviaciones (CHRIS IA 🩵)
# ============================================

st.markdown("### 🧩 Diagnóstico IA — Análisis Correctivo de Desviaciones (CHRIS IA 🩵)")

try:
    from openai import OpenAI
    from datetime import datetime

    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    fecha_actual = datetime.now().strftime("%d/%m/%Y")

    if st.button("🔍 Analizar Causas y Errores con CHRIS IA"):
        with st.spinner("CHRIS IA está revisando las desviaciones..."):
            # Seleccionamos los 10 casos con mayor desviación
            if "PORC_DESVIACION" in df_all.columns:
                top_df = df_all.nlargest(10, "PORC_DESVIACION")[[
                    "OPERACION", "ETAPA_JURIDICA", "SUB_ETAPA_JURIDICA", "PORC_DESVIACION"
                ]]
                muestra = top_df.to_markdown(index=False)
            else:
                muestra = "No se encontró la columna PORC_DESVIACION en el dataset."

            prompt = f"""
Eres un abogado especialista en control procesal del sector bancario. 
Tu tarea es revisar la siguiente muestra de procesos judiciales con mayor desviación:

{muestra}

Analiza las posibles causas jurídicas y operativas que podrían estar generando las desviaciones 
(en errores de fechas, tipificación, carga judicial o demoras del banco).
Redacta una tabla explicativa con las siguientes columnas:

1. ETAPA_JURIDICA  
2. POSIBLE CAUSA DE DESVIACIÓN  
3. RECOMENDACIÓN CORRECTIVA  

Sé concreto, utiliza terminología jurídica colombiana y redacta con tono técnico-profesional.
Al final, agrega un párrafo resumen con la visión global del problema y su impacto operativo.
Firma como:

---
**Análisis Correctivo elaborado por:** CHRIS IA 🩵  
**Fecha:** {fecha_actual}
---
"""

            respuesta = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un abogado litigante experto en procesos ejecutivos del sector bancario colombiano.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=900,
            )

            texto_ia_corr = respuesta.choices[0].message.content.strip()

            st.success("✅ Diagnóstico correctivo generado correctamente por CHRIS IA 🩵")
            st.markdown("#### 📋 Resultado del Análisis Correctivo:")
            st.markdown(texto_ia_corr)

            st.session_state["analisis_ia_correctivo"] = {
                "texto": texto_ia_corr,
                "fecha": fecha_actual
            }

except Exception as e:
    st.warning(f"⚠️ No se pudo ejecutar el análisis IA: {e}")
    st.info("Verifica tu archivo `.streamlit/secrets.toml` con la clave `OPENAI_API_KEY`.")
  # ============================================
# 💬 CHRIS IA 🩵 — Analista Jurídico + Data Analyst Procesal y Financiero
# ============================================

st.markdown("### 💬 CHRIS IA 🩵 — Análisis Conversacional con Cálculos Reales y Contexto Completo")

try:
    from openai import OpenAI
    import pandas as pd

    # Inicializar cliente de OpenAI
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    # =======================================================
    # 🎯 CONTEXTO Y PERSONALIDAD DEL MODELO (ROL DUAL)
    # =======================================================
    if "chat_chris" not in st.session_state:
        st.session_state["chat_chris"] = [
            {
                "role": "system",
                "content": """
Eres CHRIS IA 🩵, analista senior de bases de datos procesales y abogado experto en cobranza judicial bancaria.

Tu función principal es analizar datos reales del DataFrame `df_all` de Contacto Solutions, que contiene:
- JUZGADO, CIUDAD, DEPARTAMENTO
- ETAPA_JURIDICA, SUB_ETAPA_JURIDICA, PORC_DESVIACION
- CAPITAL, SUBTOTAL, CAPITAL_ACT, CAPITAL_TOTAL
- CICLOS_MORA, DIAS_RESTANTES_VENCIMIENTO
- NOMBRE_CLIENTE, CEDULA_CLIENTE, OPERACION

Debes comportarte como un **data analyst jurídico**, con estas reglas:

1️⃣ **Prioriza los datos exactos.**  
   Si existen cálculos (conteos, promedios, sumas, porcentajes), repórtalos directamente con cifras.  
   Si no hay datos suficientes, especifica qué columnas faltan.

2️⃣ **Calcula y analiza.**  
   Usa los resultados entregados por Python (promedios, sumas o conteos) para generar conclusiones numéricas.

3️⃣ **Habla con lenguaje técnico-financiero y jurídico.**  
   Redacta conclusiones claras, precisas y con base en números concretos.

4️⃣ **Estructura las respuestas en este formato:**
   - Resumen numérico o hallazgo exacto  
   - Interpretación jurídica y operativa  
   - Recomendación o conclusión  

Si se te proporcionan resultados de cálculos, utiliza los porcentajes y montos como fundamento de tus análisis.
"""
            }
        ]

    # =======================================================
    # 💬 HISTORIAL Y CAMPO DE CHAT
    # =======================================================
    for msg in st.session_state["chat_chris"][1:]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    pregunta = st.chat_input("Escribe tu pregunta jurídica o financiera sobre la base...")

    if pregunta:
        st.session_state["chat_chris"].append({"role": "user", "content": pregunta})
        with st.chat_message("user"):
            st.markdown(pregunta)

        # =======================================================
        # 📊 CÁLCULOS AUTOMÁTICOS SEGÚN LA BASE
        # =======================================================
        calculos_texto = ""
        try:
            df_temp = df_all.copy()

            # Asegurar que la desviación sea numérica
            df_temp["PORC_DESVIACION"] = pd.to_numeric(df_temp.get("PORC_DESVIACION", 0), errors="coerce")

            # Filtrar procesos desviados (>30%)
            df_desv = df_temp[df_temp["PORC_DESVIACION"] > 0.3]

            # --- Cálculo del juzgado con más procesos desviados ---
            if not df_desv.empty and all(c in df_temp.columns for c in ["JUZGADO", "CIUDAD F"]):
                resumen = (
                    df_desv.groupby(["CIUDAD F", "JUZGADO"])
                    .agg(
                        PROCESOS=("OPERACION", "count"),
                        DESVIACION_PROM=("PORC_DESVIACION", "mean"),
                        CAPITAL_TOTAL=("CAPITAL_ACT", "sum")
                    )
                    .reset_index()
                    .sort_values(["PROCESOS", "DESVIACION_PROM"], ascending=[False, False])
                )

                # Top 1 y Top 5
                top = resumen.head(1)
                top5 = resumen.head(5)

                ciudad_top = top.iloc[0]["CIUDAD F"]
                juzgado_top = top.iloc[0]["JUZGADO"]
                procesos_top = int(top.iloc[0]["PROCESOS"])
                desv_top = top.iloc[0]["DESVIACION_PROM"]
                capital_top = top.iloc[0]["CAPITAL_TOTAL"]

                calculos_texto = f"""
📊 Cálculos automáticos sobre la base:
• Juzgado con más procesos desviados: **{juzgado_top}**
• Ciudad: **{ciudad_top}**
• Procesos desviados: **{procesos_top}**
• Desviación promedio: **{desv_top:.2%}**
• Capital total gestionado: **${capital_top:,.0f}**

Top 5 Juzgados con más procesos desviados:
{top5.to_string(index=False)}
"""
            else:
                calculos_texto = "⚠️ No se encontraron columnas suficientes para calcular (JUZGADO, CIUDAD F o PORC_DESVIACION)."

        except Exception as calc_err:
            calculos_texto = f"⚠️ Error durante el cálculo: {calc_err}"

        # =======================================================
        # 🧠 PROMPT IA CON CÁLCULOS REALES
        # =======================================================
        prompt = f"""
Pregunta del usuario:
{pregunta}

Resultados de los cálculos realizados sobre la base:
{calculos_texto}

Actúa como abogado-analista de datos procesales. 
Responde con precisión numérica, interpreta los resultados en contexto jurídico y financiero,
y entrega recomendaciones de control procesal o mejora operativa.
"""

        # =======================================================
        # 🗣️ RESPUESTA DE CHRIS IA 🩵
        # =======================================================
        with st.chat_message("assistant"):
            with st.spinner("CHRIS IA 🩵 está analizando los resultados y redactando el informe..."):
                respuesta = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=st.session_state["chat_chris"]
                    + [{"role": "user", "content": prompt}],
                    max_tokens=900,
                )
                texto_resp = respuesta.choices[0].message.content.strip()
                st.markdown(texto_resp)

        st.session_state["chat_chris"].append({"role": "assistant", "content": texto_resp})

except Exception as e:
    st.warning(f"⚠️ Error en CHRIS IA 🩵: {e}")
    st.info("Verifica que tu archivo `.streamlit/secrets.toml` contenga la clave OPENAI_API_KEY correctamente configurada.")
