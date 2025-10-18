import pandas as pd
import streamlit as st
from io import BytesIO

# ============================
# ⚙️ CONFIGURACIÓN INICIAL
# ============================
st.set_page_config(page_title="Paso 5 — Avance y Desviación", layout="wide")
st.title("📊 Paso 5 | % Avance, % Desviación y Clasificación de Desviados")

# ============================
# 📤 CARGA DE BASE LIMPIA
# ============================
inventario_file = st.file_uploader("Sube la base limpia del Paso 4 (.xlsx)", type=["xlsx"])

if inventario_file:
    df = pd.read_excel(inventario_file)
    df.columns = [c.upper().replace("-", "_").replace(" ", "_") for c in df.columns]

    # ============================
    # 🧮 CÁLCULOS DE INDICADORES
    # ============================
    df["DIAS_POR_ETAPA"] = pd.to_numeric(df["DIAS_POR_ETAPA"], errors="coerce")
    df["VAR_FECHA_CALCULADA"] = pd.to_numeric(df["VAR_FECHA_CALCULADA"], errors="coerce")

    # % Avance
    df["PORC_AVANCE"] = df.apply(
        lambda x: (x["VAR_FECHA_CALCULADA"] / x["DIAS_POR_ETAPA"] * 100)
        if x["DIAS_POR_ETAPA"] and x["DIAS_POR_ETAPA"] > 0 else 0,
        axis=1,
    )

    # % Desviación (solo si supera el SLA)
    df["PORC_DESVIACION"] = df.apply(
        lambda x: max(((x["VAR_FECHA_CALCULADA"] - x["DIAS_POR_ETAPA"]) / x["DIAS_POR_ETAPA"]) * 100, 0)
        if x["DIAS_POR_ETAPA"] and x["DIAS_POR_ETAPA"] > 0 else 0,
        axis=1,
    )

    # Días de exceso
    df["DIAS_EXCESO"] = df["VAR_FECHA_CALCULADA"] - df["DIAS_POR_ETAPA"]

    # Clasificación por porcentaje
    def clasificar_porcentaje(p):
        if p <= 30:
            return "LEVE 🟢"
        elif 31 <= p <= 70:
            return "MODERADA 🟡"
        elif p > 70:
            return "GRAVE 🔴"
        else:
            return "SIN_DATO ⚪️"

    df["CLASIFICACION_%"] = df["PORC_DESVIACION"].apply(clasificar_porcentaje)

    # Clasificación por días
    def clasificar_dias(d):
        if d <= 0:
            return "A TIEMPO ⚪️"
        elif 1 <= d <= 15:
            return "LEVE 🟢"
        elif 16 <= d <= 30:
            return "MEDIA 🟡"
        elif d > 30:
            return "ALTA 🔴"
        else:
            return "SIN_DATO ⚪️"

    df["CLASIFICACION_DIAS"] = df["DIAS_EXCESO"].apply(clasificar_dias)

    # ============================
    # 📈 MÉTRICAS GLOBALES
    # ============================
    total_procesos = len(df)
    total_clientes = df["DEUDOR"].nunique() if "DEUDOR" in df.columns else 0
    capital_total = df["CAPITAL_ACT"].sum() if "CAPITAL_ACT" in df.columns else 0
    desviados = (df["PORC_DESVIACION"] > 0).sum()

    st.header("📋 Resumen ejecutivo")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🧾 Procesos totales", f"{total_procesos:,}")
    c2.metric("👤 Clientes únicos", f"{total_clientes:,}")
    c3.metric("💰 Capital total", f"${capital_total:,.0f}")
    c4.metric("⚠️ Procesos con desviación", f"{desviados:,}")

    # ============================
    # 📊 TABLA DE RESULTADOS
    # ============================
    st.subheader("📄 Vista previa (primeros 15 registros)")
    st.dataframe(
        df[
            [
                "DEUDOR", "OPERACION", "ETAPA_JURIDICA", "SUB_ETAPA_JURIDICA",
                "DIAS_POR_ETAPA", "VAR_FECHA_CALCULADA", "PORC_AVANCE",
                "PORC_DESVIACION", "DIAS_EXCESO",
                "CLASIFICACION_%", "CLASIFICACION_DIAS", "CAPITAL_ACT"
            ]
        ].head(15),
        use_container_width=True
    )

    # ============================
    # 💾 DESCARGA
    # ============================
    output = BytesIO()
    df.to_excel(output, index=False, engine="openpyxl")
    output.seek(0)
    st.download_button(
        label="⬇️ Descargar Inventario con % Avance y Desviación",
        data=output,
        file_name="Inventario_Paso5_Clasificado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

else:
    st.info("Sube la base limpia del Paso 4 para calcular % Avance y % Desviación.")

