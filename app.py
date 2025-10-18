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
# 📊 PASO 5 — % Avance, % Desviación y Clasificación (Tema oscuro)
# ============================================
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import streamlit as st
import pandas as pd
from io import BytesIO

# Modo oscuro global
st.markdown("""
    <style>
    body, .stApp {
        background-color: #0E1117 !important;
        color: #FFFFFF !important;
    }
    .stMetricLabel, .stMetricValue, h1, h2, h3, h4, h5, h6, label {
        color: #FFFFFF !important;
    }
    </style>
""", unsafe_allow_html=True)

if "base_limpia" not in locals() and "base_limpia" not in st.session_state:
    st.error("❌ No se encontró la base limpia del Paso 4. Ejecuta los pasos previos primero.")
else:
    df5 = st.session_state.get("base_limpia", base_limpia).copy()

    # Normalizar nombres y tipos
    df5.columns = [c.upper().replace("-", "_").replace(" ", "_") for c in df5.columns]
    for c in ["DIAS_POR_ETAPA", "VAR_FECHA_CALCULADA", "CAPITAL_ACT"]:
        if c in df5.columns:
            df5[c] = pd.to_numeric(df5[c], errors="coerce").fillna(0)

    # Calcular capital en millones
    df5["CAPITAL_MILLONES"] = df5["CAPITAL_ACT"] / 1_000_000

    # ============================
    # 🧮 CÁLCULOS
    # ============================
    df5["PORC_AVANCE"] = df5.apply(
        lambda x: (x["VAR_FECHA_CALCULADA"] / x["DIAS_POR_ETAPA"] * 100)
        if x["DIAS_POR_ETAPA"] > 0 else 0,
        axis=1
    )

    df5["PORC_DESVIACION"] = df5.apply(
        lambda x: max(((x["VAR_FECHA_CALCULADA"] - x["DIAS_POR_ETAPA"]) / x["DIAS_POR_ETAPA"]) * 100, 0)
        if x["DIAS_POR_ETAPA"] > 0 else 0,
        axis=1
    )

    df5["DIAS_EXCESO"] = df5["VAR_FECHA_CALCULADA"] - df5["DIAS_POR_ETAPA"]

    def clasif_desviacion(p):
        if p <= 30: return "LEVE"
        if 31 <= p <= 70: return "MODERADA"
        if p > 70: return "GRAVE"
        return "SIN_DATO"

    df5["NIVEL_DESVIACION"] = df5["PORC_DESVIACION"].apply(clasif_desviacion)
    df5["ESTADO_TIEMPO"] = df5["PORC_DESVIACION"].apply(lambda x: "A TIEMPO" if x == 0 else "FUERA DE TIEMPO")

    # ============================
    # 📈 MÉTRICAS EJECUTIVAS
    # ============================
    total_procesos = len(df5)
    total_clientes = df5["DEUDOR"].nunique() if "DEUDOR" in df5.columns else 0
    capital_total = df5["CAPITAL_MILLONES"].sum()
    desviados = (df5["ESTADO_TIEMPO"] == "FUERA_DE_TIEMPO").sum()

    st.header("📊 Paso 5 | % Avance, % Desviación y Clasificación")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🧾 Procesos totales", f"{total_procesos:,}")
    c2.metric("👤 Clientes únicos", f"{total_clientes:,}")
    c3.metric("💰 Capital total", f"{capital_total:,.1f} M")
    c4.metric("⚠️ Procesos con desviación", f"{desviados:,}")

    # ============================
    # 📈 Gráfico 1 — Estado general
    # ============================
    resumen_estado = df5.groupby("ESTADO_TIEMPO").agg(
        PROCESOS=("ESTADO_TIEMPO", "count"),
        CAPITAL=("CAPITAL_MILLONES", "sum")
    ).reset_index()

    fig1, ax1 = plt.subplots(figsize=(3.8, 3.8), facecolor="#0E1117")
    colores_estado = ["#2ECC71" if e == "A TIEMPO" else "#E74C3C" for e in resumen_estado["ESTADO_TIEMPO"]]
    wedges, texts, autotexts = ax1.pie(
        resumen_estado["PROCESOS"],
        labels=[f"{e}\n{p:,} proc\n${c:,.1f} M" for e, p, c in zip(resumen_estado["ESTADO_TIEMPO"], resumen_estado["PROCESOS"], resumen_estado["CAPITAL"])],
        autopct="%1.0f%%",
        colors=colores_estado,
        startangle=90,
        textprops={"color": "white", "fontsize": 9}
    )
    ax1.set_title("📈 Estado general de los procesos", color="white", fontsize=11)
    plt.setp(autotexts, color="white")
    st.pyplot(fig1)

    # ============================
    # 📊 Gráfico 2 — Gravedad
    # ============================
    desviados_df = df5[df5["ESTADO_TIEMPO"] == "FUERA_DE_TIEMPO"]
    if not desviados_df.empty:
        gravedad = desviados_df.groupby("NIVEL_DESVIACION").agg(
            PROCESOS=("NIVEL_DESVIACION", "count"),
            CAPITAL=("CAPITAL_MILLONES", "sum")
        ).reindex(["LEVE", "MODERADA", "GRAVE"]).fillna(0)

        fig2, ax2 = plt.subplots(figsize=(4.8, 2.8), facecolor="#0E1117")
        colores = ["#27AE60", "#F1C40F", "#E74C3C"]
        ax2.barh(gravedad.index, gravedad["PROCESOS"], color=colores, alpha=0.7)
        for i, (p, c) in enumerate(zip(gravedad["PROCESOS"], gravedad["CAPITAL"])):
            ax2.text(p + 5, i, f"{int(p):,} | ${c:,.1f} M", va="center", color="white", fontsize=9)
        ax2.set_xlabel("Procesos", color="white")
        ax2.set_title("📊 Niveles de gravedad (Procesos y Capital)", color="white")
        ax2.tick_params(colors="white")
        st.pyplot(fig2)

    # ============================
    # 🏛️ Gráfico 3 — Ranking por Etapa
    # ============================
    if "ETAPA_JURIDICA" in df5.columns:
        etapa_rank = df5.groupby("ETAPA_JURIDICA").agg(
            PROCESOS=("DEUDOR", "count"),
            CAPITAL=("CAPITAL_MILLONES", "sum"),
            PROM_DESV=("PORC_DESVIACION", "mean")
        ).sort_values("CAPITAL", ascending=False).head(10)

        fig3, ax3 = plt.subplots(figsize=(5, 3), facecolor="#0E1117")
        bars = ax3.bar(etapa_rank.index, etapa_rank["PROCESOS"],
                       color=plt.cm.RdYlGn_r(etapa_rank["PROM_DESV"] / etapa_rank["PROM_DESV"].max()))
        ax3.set_title("🏛️ Ranking por Etapa Jurídica (Top 10)", color="white", fontsize=11)
        ax3.set_ylabel("Procesos", color="white")
        ax3.set_xticklabels(etapa_rank.index, rotation=45, ha="right", color="white")
        for i, (p, c) in enumerate(zip(etapa_rank["PROCESOS"], etapa_rank["CAPITAL"])):
            ax3.text(i, p + 3, f"${c:,.1f} M", ha="center", color="white", fontsize=8)
        ax3.tick_params(colors="white")
        st.pyplot(fig3)

    # ============================
    # 📚 Gráfico 4 — Ranking por Subetapa
    # ============================
    if "SUB_ETAPA_JURIDICA" in df5.columns:
        sub_rank = df5.groupby("SUB_ETAPA_JURIDICA").agg(
            PROCESOS=("DEUDOR", "count"),
            CAPITAL=("CAPITAL_MILLONES", "sum"),
            PROM_DESV=("PORC_DESVIACION", "mean")
        ).sort_values("PROM_DESV", ascending=False).head(10)

        fig4, ax4 = plt.subplots(figsize=(5.5, 4), facecolor="#0E1117")
        bars = ax4.barh(sub_rank.index, sub_rank["PROM_DESV"],
                        color=plt.cm.RdYlGn_r(sub_rank["PROM_DESV"] / sub_rank["PROM_DESV"].max()))
        ax4.xaxis.set_major_formatter(mticker.PercentFormatter())
        ax4.set_title("📚 Ranking por Subetapa Jurídica (Top 10)", color="white", fontsize=11)
        ax4.set_xlabel("% Desviación promedio", color="white")
        for i, (p, c) in enumerate(zip(sub_rank["PROCESOS"], sub_rank["CAPITAL"])):
            ax4.text(sub_rank["PROM_DESV"].iloc[i] + 1, i, f"{int(p)} proc | ${c:,.1f} M", va="center", color="white", fontsize=8)
        ax4.tick_params(colors="white")
        st.pyplot(fig4)

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
