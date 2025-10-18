import pandas as pd
import streamlit as st
from io import BytesIO
import unicodedata

# ============================
# ⚙️ CONFIGURACIÓN INICIAL
# ============================
st.set_page_config(page_title="Paso 5 — Avance y Desviación", layout="wide")
st.title("📊 Paso 5 | % Avance, % Desviación y Clasificación de Desviados")

# ============================
# 🔤 FUNCIÓN PARA NORMALIZAR ENCABEZADOS
# ============================
def normalizar_columna(col):
    col = ''.join(
        c for c in unicodedata.normalize('NFD', col)
        if unicodedata.category(c) != 'Mn'
    )
    col = col.upper().replace("-", "_").replace(" ", "_")
    col = ''.join(c for c in col if c.isalnum() or c == "_")
    while "__" in col:
        col = col.replace("__", "_")
    return col.strip("_")

# ============================
# 📤 CARGA DE BASE LIMPIA
# ============================
inventario_file = st.file_uploader("Sube la base limpia del Paso 4 (.xlsx)", type=["xlsx"])

if inventario_file:
    df = pd.read_excel(inventario_file)
    df.columns = [normalizar_columna(c) for c in df.columns]

    # ============================
    # 🔍 DETECCIÓN DE COLUMNAS CLAVE
    # ============================
    posibles_var = [c for c in df.columns if "VAR_FECHA_CALCULADA" in c]
    posibles_dias = [c for c in df.columns if "DIAS_POR_ETAPA" in c]
    posibles_capital = [c for c in df.columns if "CAPITAL_ACT" in c]

    if not posibles_var:
        st.error("❌ No se encontró la columna 'VAR_FECHA_CALCULADA'. Asegúrate de cargar la base limpia del Paso 4.")
        st.stop()

    col_var_fecha = posibles_var[0]
    col_dias = posibles_dias[0] if posibles_dias else None
    col_capital = posibles_capital[0] if posibles_capital else None

    # ============================
    # 🧮 CÁLCULOS DE INDICADORES
    # ============================
    df[col_dias] = pd.to_numeric(df[col_dias], errors="coerce")
    df[col_var_fecha] = pd.to_numeric(df[col_var_fecha], errors="coerce")

    # % Avance
    df["PORC_AVANCE"] = df.apply(
        lambda x: (x[col_var_fecha] / x[col_dias] * 100)
        if x[col_dias] and x[col_dias] > 0 else 0,
        axis=1,
    )

    # % Desviación
    df["PORC_DESVIACION"] = df.apply(
        lambda x: max(((x[col_var_fecha] - x[col_dias]) / x[col_dias]) * 100, 0)
        if x[col_dias] and x[col_dias] > 0 else 0,
        axis=1,
    )

    # Días de exceso
    df["DIAS_EXCESO"] = df[col_var_fecha] - df[col_dias]

    # Clasificaciones
    def clasif_porcentaje(p):
        if p <= 30:
            return "LEVE 🟢"
        elif 31 <= p <= 70:
            return "MODERADA 🟡"
        elif p > 70:
            return "GRAVE 🔴"
        return "SIN_DATO ⚪️"

    def clasif_dias(d):
        if d <= 0:
            return "A TIEMPO ⚪️"
        elif 1 <= d <= 15:
            return "LEVE 🟢"
        elif 16 <= d <= 30:
            return "MEDIA 🟡"
        elif d > 30:
            return "ALTA 🔴"
        return "SIN_DATO ⚪️"

    df["CLASIFICACION_%"] = df["PORC_DESVIACION"].apply(clasif_porcentaje)
    df["CLASIFICACION_DIAS"] = df["DIAS_EXCESO"].apply(clasif_dias)

    # ============================
    # 📈 MÉTRICAS GLOBALES
    # ============================
    total_procesos = len(df)
    total_clientes = df["DEUDOR"].nunique() if "DEUDOR" in df.columns else 0
    capital_total = df[col_capital].sum() if col_capital else 0
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
    cols_vista = [c for c in ["DEUDOR", "OPERACION", "ETAPA_JURIDICA", "SUB_ETAPA_JURIDICA",
                              col_dias, col_var_fecha, "PORC_AVANCE", "PORC_DESVIACION",
                              "DIAS_EXCESO", "CLASIFICACION_%", "CLASIFICACION_DIAS", col_capital]
                  if c in df.columns]
    st.dataframe(df[cols_vista].head(15), use_container_width=True)

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
