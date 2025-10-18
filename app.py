# ============================================
# ⚖️ ANÁLISIS DE DESVIACIÓN PROCESAL — COS
# Pasos 1 a 5 (flujo completo con descarga de errores)
# ============================================

import pandas as pd
import streamlit as st
import unicodedata
from io import BytesIO

# ============================================
# ⚙️ CONFIGURACIÓN INICIAL
# ============================================
st.set_page_config(page_title="Desviación Procesal COS", layout="wide")
st.title("⚖️ Análisis de Desviación Procesal — Contacto Solutions")

# ============================================
# 🧩 FUNCIÓN DE NORMALIZACIÓN DE COLUMNAS
# ============================================
def normalizar_columna(col):
    col = ''.join(c for c in unicodedata.normalize('NFD', col) if unicodedata.category(c) != 'Mn')
    col = col.upper().replace("-", "_").replace(" ", "_")
    col = ''.join(c for c in col if c.isalnum() or c == "_")
    while "__" in col:
        col = col.replace("__", "_")
    return col.strip("_")

# ============================================
# 📘 PASOS 1–2 — CARGA Y LIMPIEZA DE ENCABEZADOS
# ============================================
inventario_file = st.file_uploader("Sube el inventario (.xlsx)", type=["xlsx"])
tiempos_path = "Tabla_tiempos_etapas_desviacion.xlsx"  # tabla fija en raíz

if inventario_file:
    # Leer archivos
    inv = pd.read_excel(inventario_file)
    tiempos = pd.read_excel(tiempos_path)
    inv.columns = [normalizar_columna(c) for c in inv.columns]
    tiempos.columns = [normalizar_columna(c) for c in tiempos.columns]

    # ============================================
    # 📗 PASO 3 — COMPLETAR DÍAS POR ETAPA
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

    # Detectar errores
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

    # Crear base limpia (sin errores)
    base_limpia = inv.dropna(subset=["VAR_FECHA_CALCULADA"])
    base_limpia = base_limpia[base_limpia["VAR_FECHA_CALCULADA"] >= 0].copy()

   # ============================================
# 📊 PASO 5 — Tablas visuales completas, tema oscuro (sin límite de filas)
# ============================================
import pandas as pd
import streamlit as st
from io import BytesIO

# ============================
# 🎨 ESTILO OSCURO GLOBAL
# ============================
st.markdown("""
    <style>
    body, .stApp {
        background-color: #0E1117 !important;
        color: #FFFFFF !important;
    }
    h1, h2, h3, h4, h5, h6, label, .stMetricLabel, .stMetricValue {
        color: #FFFFFF !important;
    }
    .stDownloadButton > button {
        background-color: #1B1F24 !important;
        color: white !important;
        border: 1px solid #333;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
    .stDownloadButton > button:hover {
        background-color: #2C313A !important;
        border-color: #555;
    }
    </style>
""", unsafe_allow_html=True)

# ============================
# ⚙️ CARGA BASE
# ============================
if "base_limpia" not in locals() and "base_limpia" not in st.session_state:
    st.error("❌ No se encontró la base limpia del Paso 4. Ejecuta los pasos previos primero.")
else:
    df5 = st.session_state.get("base_limpia", base_limpia).copy()

    # Normalizar columnas
    df5.columns = [c.upper().replace("-", "_").replace(" ", "_") for c in df5.columns]
    for c in ["DIAS_POR_ETAPA", "VAR_FECHA_CALCULADA", "CAPITAL_ACT"]:
        if c in df5.columns:
            df5[c] = pd.to_numeric(df5[c], errors="coerce").fillna(0)

    # Capital en millones
    df5["CAPITAL_MILLONES"] = df5["CAPITAL_ACT"] / 1_000_000

    # ============================
    # 📈 CÁLCULOS
    # ============================
    df5["PORC_AVANCE"] = df5.apply(
        lambda x: (x["VAR_FECHA_CALCULADA"] / x["DIAS_POR_ETAPA"] * 100)
        if x["DIAS_POR_ETAPA"] > 0 else 0, axis=1
    )

    df5["PORC_DESVIACION"] = df5.apply(
        lambda x: max(((x["VAR_FECHA_CALCULADA"] - x["DIAS_POR_ETAPA"]) / x["DIAS_POR_ETAPA"]) * 100, 0)
        if x["DIAS_POR_ETAPA"] > 0 else 0, axis=1
    )

    def clasif_desviacion(p):
        if p <= 30: return "LEVE"
        if 31 <= p <= 70: return "MODERADA"
        if p > 70: return "GRAVE"
        return "SIN_DATO"

    df5["NIVEL_DESVIACION"] = df5["PORC_DESVIACION"].apply(clasif_desviacion)
    df5["ESTADO_TIEMPO"] = df5["PORC_DESVIACION"].apply(lambda x: "A TIEMPO" if x == 0 else "FUERA DE TIEMPO")

    # ============================
    # 🧾 MÉTRICAS EJECUTIVAS
    # ============================
    total_procesos = len(df5)
    total_clientes = df5["DEUDOR"].nunique() if "DEUDOR" in df5.columns else 0
    capital_total = df5["CAPITAL_MILLONES"].sum()
    desviados = (df5["ESTADO_TIEMPO"] == "FUERA DE TIEMPO").sum()

    st.header("📊 Paso 5 | % Avance, % Desviación y Clasificación")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🧾 Procesos totales", f"{total_procesos:,}")
    c2.metric("👤 Clientes únicos", f"{total_clientes:,}")
    c3.metric("💰 Capital total", f"${capital_total:,.1f} M")
    c4.metric("⚠️ Procesos con desviación", f"{desviados:,}")

    # ============================
    # 📋 TABLA 1 — ESTADO GENERAL
    # ============================
    resumen_estado = df5.groupby("ESTADO_TIEMPO").agg(
        PROCESOS=("ESTADO_TIEMPO", "count"),
        CAPITAL=("CAPITAL_MILLONES", "sum")
    ).reset_index()
    resumen_estado["% DEL TOTAL"] = (resumen_estado["PROCESOS"] / total_procesos * 100).round(1)

    st.subheader("📋 Estado general de los procesos")
    st.dataframe(
        resumen_estado.style.background_gradient(
            subset=["CAPITAL"], cmap="Greens"
        ).format({
            "CAPITAL": "{:,.1f}",
            "% DEL TOTAL": "{:.1f} %"
        }),
        use_container_width=True,
        height=150
    )

    # ============================
    # 📋 TABLA 2 — GRAVEDAD
    # ============================
    desviados_df = df5[df5["ESTADO_TIEMPO"] == "FUERA DE TIEMPO"]
    if not desviados_df.empty:
        gravedad = desviados_df.groupby("NIVEL_DESVIACION").agg(
            PROCESOS=("NIVEL_DESVIACION", "count"),
            CAPITAL=("CAPITAL_MILLONES", "sum")
        ).reindex(["LEVE", "MODERADA", "GRAVE"]).fillna(0)
        gravedad["% CAPITAL DESVIADO"] = (gravedad["CAPITAL"] / gravedad["CAPITAL"].sum() * 100).round(1)

        st.subheader("📋 Niveles de gravedad de desviación")
        st.dataframe(
            gravedad.style.background_gradient(
                subset=["% CAPITAL DESVIADO"], cmap="RdYlGn_r"
            ).format({
                "CAPITAL": "{:,.1f}",
                "% CAPITAL DESVIADO": "{:.1f} %"
            }),
            use_container_width=True,
            height=180
        )

    # ============================
    # 🏛️ TABLA 3 — TODAS LAS ETAPAS
    # ============================
    if "ETAPA_JURIDICA" in df5.columns:
        etapa_rank = df5.groupby("ETAPA_JURIDICA").agg(
            PROCESOS=("DEUDOR", "count"),
            CAPITAL=("CAPITAL_MILLONES", "sum"),
            PROM_DESV=("PORC_DESVIACION", "mean")
        ).sort_values("CAPITAL", ascending=False)

        etapa_rank["PROM_DESV"] = etapa_rank["PROM_DESV"].round(1)
        etapa_rank = etapa_rank.reset_index()
        etapa_rank.index = etapa_rank.index + 1

        st.subheader("🏛️ Ranking por Etapa Jurídica (todas)")
        st.dataframe(
            etapa_rank.style.background_gradient(
                subset=["PROM_DESV"], cmap="RdYlGn_r"
            ).format({
                "CAPITAL": "{:,.1f}",
                "PROM_DESV": "{:.1f} %"
            }),
            use_container_width=True,
            height=300
        )

    # ============================
    # 📚 TABLA 4 — TODAS LAS SUBETAPAS
    # ============================
    if "SUB_ETAPA_JURIDICA" in df5.columns:
        sub_rank = df5.groupby("SUB_ETAPA_JURIDICA").agg(
            PROCESOS=("DEUDOR", "count"),
            CAPITAL=("CAPITAL_MILLONES", "sum"),
            PROM_DESV=("PORC_DESVIACION", "mean")
        ).sort_values("PROM_DESV", ascending=False)

        sub_rank["PROM_DESV"] = sub_rank["PROM_DESV"].round(1)
        sub_rank = sub_rank.reset_index()
        sub_rank.index = sub_rank.index + 1

        st.subheader("📚 Ranking por Subetapa Jurídica (todas)")
        st.dataframe(
            sub_rank.style.background_gradient(
                subset=["PROM_DESV"], cmap="RdYlGn_r"
            ).format({
                "CAPITAL": "{:,.1f}",
                "PROM_DESV": "{:.1f} %"
            }),
            use_container_width=True,
            height=350
        )

    # ============================
    # 💾 DESCARGA FINAL
    # ============================
    output = BytesIO()
    df5.to_excel(output, index=False, engine="openpyxl")
    output.seek(0)
    st.download_button(
        "⬇️ Descargar Inventario Clasificado (Paso 5)",
        data=output,
        file_name="Inventario_Paso5_Clasificado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
