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
st.set_page_config(page_title="Desviación Procesal COS", layout="wide")
st.title("📊 Desviación Procesal COS")

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
# 📆 PASO 4 — CALCULAR VAR_FECHA_CALCULADA Y DEPURAR
# (Resta de fecha normalizando a medianoche para ignorar horas)
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

# Errores de fecha (nulos o negativos)
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

# Base limpia (sin errores)
base_limpia = inv.dropna(subset=["VAR_FECHA_CALCULADA"])
base_limpia = base_limpia[base_limpia["VAR_FECHA_CALCULADA"] >= 0].copy()

# ============================================
# 🧮 Utilidad: asegurar métricas (PORC_DESVIACION, numéricos, etc.)
# ============================================
def ensure_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza numéricos y calcula PORC_DESVIACION si no existe."""
    out = df.copy()
    for c in ["DIAS_POR_ETAPA", "VAR_FECHA_CALCULADA", "CAPITAL_ACT"]:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    out["DIAS_POR_ETAPA"] = out.get("DIAS_POR_ETAPA", 0).fillna(0)
    out["VAR_FECHA_CALCULADA"] = out.get("VAR_FECHA_CALCULADA", 0).fillna(0)
    out["CAPITAL_ACT"] = out.get("CAPITAL_ACT", 0).fillna(0)
    if "PORC_DESVIACION" not in out.columns:
        out["PORC_DESVIACION"] = out.apply(
            lambda x: max(((x["VAR_FECHA_CALCULADA"] - x["DIAS_POR_ETAPA"]) / x["DIAS_POR_ETAPA"]) * 100, 0)
            if x["DIAS_POR_ETAPA"] and x["DIAS_POR_ETAPA"] > 0 else 0,
            axis=1
        )
    else:
        out["PORC_DESVIACION"] = pd.to_numeric(out["PORC_DESVIACION"], errors="coerce").fillna(0)
    return out

# ============================================
# 🔀 FILTRO ESTRATÉGICO: COS vs BANCO
# (solo estas 2 subetapas cuentan para desviación COS)
# ============================================
COS_VALIDAS = [
    ("PASE A LEGAL", "ENTREGA DE GARANTIAS"),
    ("PASE A LEGAL", "ENTREGA PODER"),
]
SUB_BANCO = {"EN TRAMITE", "RECEPCION GARANTIAS", "PODER PARA FIRMA", "RECEPCION PODER", "RETIRO"}

# Normalizar llaves
base_limpia["ETAPA_JURIDICA"] = base_limpia["ETAPA_JURIDICA"].astype(str).str.upper()
base_limpia["SUB_ETAPA_JURIDICA"] = base_limpia["SUB_ETAPA_JURIDICA"].astype(str).str.upper()
base_limpia["_KEY"] = list(zip(base_limpia["ETAPA_JURIDICA"], base_limpia["SUB_ETAPA_JURIDICA"]))

# df_cos = solo 2 subetapas medibles
df_cos = base_limpia[base_limpia["_KEY"].isin(COS_VALIDAS)].copy()
df_cos = ensure_metrics(df_cos)

# df_banco = resto bajo control del banco (en PASE A LEGAL y dentro de SUB_BANCO)
df_banco = base_limpia[
    (base_limpia["ETAPA_JURIDICA"] == "PASE A LEGAL") &
    (base_limpia["SUB_ETAPA_JURIDICA"].isin(SUB_BANCO))
].copy()

# Guardar en sesión
st.session_state["base_limpia"] = base_limpia
st.session_state["df_cos"] = df_cos
st.session_state["df_banco"] = df_banco

# ============================================
# 📊 PASO 5 — % Avance, % Desviación y Clasificación (solo COS)
# ============================================
if not df_cos.empty:
    df5 = df_cos.copy()
    df5.columns = [c.upper().replace("-", "_").replace(" ", "_") for c in df5.columns]

    # Capital en millones
    df5["CAPITAL_MILLONES"] = pd.to_numeric(df5["CAPITAL_ACT"], errors="coerce").fillna(0) / 1_000_000

    # Porcentajes (ya garantizados en ensure_metrics, pero reforzamos avance)
    df5["PORC_AVANCE"] = df5.apply(
        lambda x: (x["VAR_FECHA_CALCULADA"] / x["DIAS_POR_ETAPA"] * 100) if x["DIAS_POR_ETAPA"] > 0 else 0, axis=1
    )

    # Clasificación visual
    def clasif_desviacion(p):
        if p <= 30: return "LEVE"
        if 31 <= p <= 70: return "MODERADA"
        if p > 70: return "GRAVE"
        return "SIN_DATO"

    df5["NIVEL_DESVIACION"] = df5["PORC_DESVIACION"].apply(clasif_desviacion)
    df5["ESTADO_TIEMPO"] = df5["PORC_DESVIACION"].apply(lambda x: "A TIEMPO" if x == 0 else "FUERA DE TIEMPO")

    total_procesos = len(df5)
    total_clientes = df5["DEUDOR"].nunique() if "DEUDOR" in df5.columns else 0
    capital_total = df5["CAPITAL_MILLONES"].sum()
    desviados = (df5["ESTADO_TIEMPO"] == "FUERA DE TIEMPO").sum()

    st.header("📊 Paso 5 | % Avance, % Desviación y Clasificación (COS)")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🧾 Procesos totales", f"{total_procesos:,}")
    c2.metric("👤 Clientes únicos", f"{total_clientes:,}")
    c3.metric("💰 Capital total", f"${capital_total:,.1f} M")
    c4.metric("⚠️ Procesos con desviación", f"{desviados:,}")

    resumen_estado = df5.groupby("ESTADO_TIEMPO").agg(
        PROCESOS=("ESTADO_TIEMPO", "count"),
        CAPITAL=("CAPITAL_MILLONES", "sum")
    ).reset_index()
    resumen_estado["% DEL TOTAL"] = (resumen_estado["PROCESOS"] / total_procesos * 100).round(1)

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
        gravedad["% CAPITAL DESVIADO"] = (gravedad["CAPITAL"] / max(gravedad["CAPITAL"].sum(), 1) * 100).round(1)

        st.subheader("📋 Niveles de gravedad de desviación")
        st.dataframe(
            gravedad.style.background_gradient(subset=["% CAPITAL DESVIADO"], cmap="RdYlGn_r").format({
                "CAPITAL": "{:,.1f}", "% CAPITAL DESVIADO": "{:.1f} %"
            }),
            use_container_width=True, height=180
        )

    # Ranking por Etapa (COS)
    if "ETAPA_JURIDICA" in df5.columns:
        etapa_rank = df5.groupby("ETAPA_JURIDICA").agg(
            PROCESOS=("DEUDOR", "count"), CAPITAL=("CAPITAL_MILLONES", "sum"),
            PROM_DESV=("PORC_DESVIACION", "mean")
        ).reset_index().sort_values("CAPITAL", ascending=False)
        etapa_rank["PROM_DESV"] = etapa_rank["PROM_DESV"].round(1)
        st.subheader("🏛️ Ranking por Etapa Jurídica (COS)")
        st.dataframe(
            etapa_rank.style.background_gradient(subset=["PROM_DESV"], cmap="RdYlGn_r").format({
                "CAPITAL": "{:,.1f}", "PROM_DESV": "{:.1f} %"
            }),
            use_container_width=True, height=300
        )

    # Ranking por Subetapa (COS)
    if "SUB_ETAPA_JURIDICA" in df5.columns:
        sub_rank = df5.groupby("SUB_ETAPA_JURIDICA").agg(
            PROCESOS=("DEUDOR", "count"), CAPITAL=("CAPITAL_MILLONES", "sum"),
            PROM_DESV=("PORC_DESVIACION", "mean")
        ).reset_index().sort_values("PROM_DESV", ascending=False)
        sub_rank["PROM_DESV"] = sub_rank["PROM_DESV"].round(1)
        st.subheader("📚 Ranking por Subetapa Jurídica (COS)")
        st.dataframe(
            sub_rank.style.background_gradient(subset=["PROM_DESV"], cmap="RdYlGn_r").format({
                "CAPITAL": "{:,.1f}", "PROM_DESV": "{:.1f} %"
            }),
            use_container_width=True, height=350
        )

    # Descarga (inventario COS calculado)
    out5 = BytesIO()
    df5.to_excel(out5, index=False, engine="openpyxl")
    out5.seek(0)
    st.download_button(
        "⬇️ Descargar Inventario Clasificado (Paso 5 - COS)",
        data=out5, file_name="Inventario_Paso5_Clasificado_COS.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

# ============================================
# 📊 PASO 6 — Ranking visual Etapa × Subetapa (solo COS)
# ============================================
if not df_cos.empty:
    df6 = df_cos.copy()
    df6.columns = [c.upper().replace("-", "_").replace(" ", "_") for c in df6.columns]

    # Asegurar métrica
    df6 = ensure_metrics(df6)
    df6["CAPITAL_MILLONES"] = pd.to_numeric(df6.get("CAPITAL_ACT", 0), errors="coerce").fillna(0) / 1_000_000

    resumen = df6.groupby(["ETAPA_JURIDICA", "SUB_ETAPA_JURIDICA"]).agg(
        PROCESOS=("DEUDOR", "count"),
        CAPITAL_M=("CAPITAL_MILLONES", "sum"),
        PROM_DESV=("PORC_DESVIACION", "mean")
    ).reset_index()

    resumen["PROM_DESV"] = resumen["PROM_DESV"].round(1)
    resumen["CAPITAL_M"] = resumen["CAPITAL_M"].round(1)

    def nivel(p): return "🟢 Leve" if p <= 30 else ("🟡 Moderada" if p <= 70 else "🔴 Grave")
    resumen["NIVEL"] = resumen["PROM_DESV"].apply(nivel)
    resumen["INDICADOR"] = resumen["PROM_DESV"].apply(lambda x: "█" * int(min(x/5, 20)))

    resumen = resumen.sort_values("PROM_DESV", ascending=False).reset_index(drop=True)

    st.header("📊 Paso 6 | Ranking Visual Etapa × Subetapa (COS)")
    st.subheader("🔎 Desviación promedio, procesos y capital (solo subetapas COS)")

    st.dataframe(
        resumen[["ETAPA_JURIDICA", "SUB_ETAPA_JURIDICA", "PROCESOS", "CAPITAL_M", "PROM_DESV", "NIVEL", "INDICADOR"]]
        .style.format({"CAPITAL_M": "{:,.1f}", "PROM_DESV": "{:.1f} %", "PROCESOS": "{:,}"}),
        use_container_width=True, height=600
    )

    out6 = BytesIO()
    resumen.to_excel(out6, index=False, sheet_name="Ranking_Visual_COS", engine="openpyxl")
    out6.seek(0)
    st.download_button(
        "⬇️ Descargar Ranking Visual (Paso 6 - COS)",
        data=out6, file_name="Ranking_Visual_Paso6_COS.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

# ============================================
# 📊 PASO 7 — Clientes Críticos (COS) con Buscador Multicliente + Obligación
# (PARCHE: sin exigir PORC_DESVIACION; se calcula con ensure_metrics)
# ============================================
df7 = df_cos.copy()
if not df7.empty:
    df7.columns = [c.upper().replace("-", "_").replace(" ", "_") for c in df7.columns]

    columnas_necesarias_7 = {
        "DEUDOR", "OPERACION", "ETAPA_JURIDICA", "SUB_ETAPA_JURIDICA",
        "CAPITAL_ACT", "DIAS_POR_ETAPA", "VAR_FECHA_CALCULADA"
    }
    faltan_7 = columnas_necesarias_7 - set(df7.columns)
    if not faltan_7:
        df7 = ensure_metrics(df7)

        df7["CAPITAL_MILLONES"] = pd.to_numeric(df7["CAPITAL_ACT"], errors="coerce").fillna(0) / 1_000_000
        df7["DIAS_EXCESO"] = df7.apply(
            lambda x: max(x["VAR_FECHA_CALCULADA"] - x["DIAS_POR_ETAPA"], 0)
            if pd.notnull(x["VAR_FECHA_CALCULADA"]) and pd.notnull(x["DIAS_POR_ETAPA"]) else 0,
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
            return "🟢 Leve" if p <= 30 else ("🟡 Moderada" if p <= 70 else "🔴 Grave")
        resumen_cliente["NIVEL"] = resumen_cliente["PROM_DESV"].apply(nivel_c)
        graves = resumen_cliente[resumen_cliente["NIVEL"] == "🔴 Grave"]

        total_clientes = len(resumen_cliente)
        total_capital = resumen_cliente["CAPITAL_M"].sum()

        st.header("📊 Paso 7 | Clientes Críticos (COS) con Buscador Multicliente y Obligación")
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
            data=out7, file_name="Clientes_Graves_Paso7.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# ============================================
# 📊 PASO 8 — Próximos a Vencer (COS) + Resumen por Subetapa + Filtro
# ============================================
if not df_cos.empty:
    df8 = df_cos.copy()
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

        st.header("📊 Paso 8 | Próximos a Vencer (Riesgo del Mes Actual) — COS")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📁 Procesos totales", f"{procesos_totales:,}")
        c2.metric("👤 Clientes únicos", f"{clientes_totales:,}")
        c3.metric("💰 Capital en riesgo", f"${capital_riesgo:,.1f} M")
        c4.metric("🟠 Procesos próximos a vencer", f"{procesos_riesgo:,}")

        # Resumen por subetapa
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

        # Tabla principal con filtro por subetapa
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

if not df_banco.empty:
    dfb = df_banco.copy()
    dfb["CAPITAL_ACT"] = pd.to_numeric(dfb.get("CAPITAL_ACT", 0), errors="coerce").fillna(0)
    dfb["CAPITAL_MILLONES"] = dfb["CAPITAL_ACT"] / 1_000_000

    # Asegurar columnas de periodo: AÑO/MES. Si no existen, derivar desde FECHA_ACT_ETAPA
    if "AÑO_PASE_JURIDICO" not in dfb.columns or "MES_PASE_JURIDICO" not in dfb.columns:
        dfb["FECHA_PASE_JURIDICO"] = pd.to_datetime(dfb.get("FECHA_ACT_ETAPA", pd.NaT), errors="coerce")
        dfb["AÑO_PASE_JURIDICO"] = dfb["FECHA_PASE_JURIDICO"].dt.year
        dfb["MES_NUM"] = dfb["FECHA_PASE_JURIDICO"].dt.month
        dfb["MES_PASE_JURIDICO"] = dfb["MES_NUM"].map(MESES_ES)
    else:
        # Normalizar mes si viene numérico
        if pd.api.types.is_numeric_dtype(dfb["MES_PASE_JURIDICO"]):
            dfb["MES_PASE_JURIDICO"] = dfb["MES_PASE_JURIDICO"].map(MESES_ES)

    # 1) Resumen mensual general (Año x Mes)
    resumen_mensual = dfb.groupby(["AÑO_PASE_JURIDICO", "MES_PASE_JURIDICO"]).agg(
        PROCESOS=("OPERACION", "count"),
        CAPITAL_M=("CAPITAL_MILLONES", "sum"),
        CLIENTES=("DEUDOR", "nunique")
    ).reset_index()

    # Orden cronológico
    if "MES_NUM" in dfb.columns:
        orden = dfb.groupby(["AÑO_PASE_JURIDICO", "MES_PASE_JURIDICO"])["MES_NUM"].min().reset_index()
        resumen_mensual = resumen_mensual.merge(orden, on=["AÑO_PASE_JURIDICO", "MES_PASE_JURIDICO"], how="left")
        resumen_mensual = resumen_mensual.sort_values(["AÑO_PASE_JURIDICO", "MES_NUM"]).drop(columns=["MES_NUM"])
    else:
        mes_order = {v: k for k, v in MESES_ES.items()}
        resumen_mensual["MES_ORD"] = resumen_mensual["MES_PASE_JURIDICO"].map(mes_order)
        resumen_mensual = resumen_mensual.sort_values(["AÑO_PASE_JURIDICO", "MES_ORD"]).drop(columns=["MES_ORD"])

    total_procesos_banco = resumen_mensual["PROCESOS"].sum() if not resumen_mensual.empty else 0
    if total_procesos_banco > 0:
        resumen_mensual["% PROCESOS"] = (resumen_mensual["PROCESOS"] / total_procesos_banco * 100).round(1)
    resumen_mensual["CAPITAL_M"] = resumen_mensual["CAPITAL_M"].round(1)

    st.subheader("🗓️ Resumen mensual (Año × Mes)")
    st.dataframe(
        resumen_mensual.style.background_gradient(subset=["CAPITAL_M"], cmap="YlOrRd")
        .format({"CAPITAL_M": "{:,.1f}", "PROCESOS": "{:,}", "CLIENTES": "{:,}", "% PROCESOS": "{:.1f} %"}),
        use_container_width=True, height=260
    )

    # 2) Resumen por Subetapa + Mes + Año
    resumen_sub_mensual = dfb.groupby(["AÑO_PASE_JURIDICO", "MES_PASE_JURIDICO", "SUB_ETAPA_JURIDICA"]).agg(
        PROCESOS=("OPERACION", "count"),
        CAPITAL_M=("CAPITAL_MILLONES", "sum"),
        CLIENTES=("DEUDOR", "nunique")
    ).reset_index()

    # Orden igual que mensual
    if "MES_NUM" in dfb.columns:
        orden2 = dfb.groupby(["AÑO_PASE_JURIDICO", "MES_PASE_JURIDICO"])["MES_NUM"].min().reset_index()
        resumen_sub_mensual = resumen_sub_mensual.merge(orden2, on=["AÑO_PASE_JURIDICO", "MES_PASE_JURIDICO"], how="left")
        resumen_sub_mensual = resumen_sub_mensual.sort_values(["AÑO_PASE_JURIDICO", "MES_NUM", "SUB_ETAPA_JURIDICA"]).drop(columns=["MES_NUM"])
    else:
        mes_order = {v: k for k, v in MESES_ES.items()}
        resumen_sub_mensual["MES_ORD"] = resumen_sub_mensual["MES_PASE_JURIDICO"].map(mes_order)
        resumen_sub_mensual = resumen_sub_mensual.sort_values(["AÑO_PASE_JURIDICO", "MES_ORD", "SUB_ETAPA_JURIDICA"]).drop(columns=["MES_ORD"])

    total_procesos_banco2 = resumen_sub_mensual["PROCESOS"].sum() if not resumen_sub_mensual.empty else 0
    if total_procesos_banco2 > 0:
        resumen_sub_mensual["% PROCESOS"] = (resumen_sub_mensual["PROCESOS"] / total_procesos_banco2 * 100).round(1)
    resumen_sub_mensual["CAPITAL_M"] = resumen_sub_mensual["CAPITAL_M"].round(1)

    st.subheader("⚖️ Resumen por Subetapa × Mes × Año (Banco)")
    st.dataframe(
        resumen_sub_mensual.style.background_gradient(subset=["CAPITAL_M"], cmap="YlOrRd")
        .format({"CAPITAL_M": "{:,.1f}", "PROCESOS": "{:,}", "CLIENTES": "{:,}", "% PROCESOS": "{:.1f} %"}),
        use_container_width=True, height=350
    )

    # Descarga única (ambos resúmenes)
    out_banco = BytesIO()
    with pd.ExcelWriter(out_banco, engine="openpyxl") as writer:
        resumen_mensual.to_excel(writer, index=False, sheet_name="Resumen_Mensual")
        resumen_sub_mensual.to_excel(writer, index=False, sheet_name="Resumen_Subetapa_Mensual")
    out_banco.seek(0)
    st.download_button(
        "⬇️ Descargar Procesos del Banco (ambos resúmenes)",
        data=out_banco, file_name="Procesos_Banco_Resumen.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

