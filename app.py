import pandas as pd
import streamlit as st
from io import BytesIO

# ============================
# ⚙️ CONFIGURACIÓN
# ============================
st.set_page_config(page_title="Paso 4 — Recalcular VAR_FECHA_CALCULADA", layout="wide")
st.title("📆 Paso 4 | Recalcular 'VAR FECHA ACT - FECHA INV' (VAR_FECHA_CALCULADA)")

# ============================
# 📤 SUBIR INVENTARIO
# ============================
inventario_file = st.file_uploader("Sube el inventario con 'DIAS_POR_ETAPA' completado", type=["xlsx"])

if inventario_file:
    # Leer archivo
    df = pd.read_excel(inventario_file)

    # Normalizar encabezados
    df.columns = [c.upper().replace("-", "_").replace(" ", "_") for c in df.columns]

    # Columnas clave
    col_fecha_inv = "FECHA_ACT_INVENTARIO"
    col_fecha_etapa = "FECHA_ACT_ETAPA"

    # Asegurar formato fecha
    df[col_fecha_inv] = pd.to_datetime(df[col_fecha_inv], errors="coerce")
    df[col_fecha_etapa] = pd.to_datetime(df[col_fecha_etapa], errors="coerce")

    # Crear nueva columna VAR_FECHA_CALCULADA
    df["VAR_FECHA_CALCULADA"] = (df[col_fecha_inv] - df[col_fecha_etapa]).dt.days

    # Contar vacíos y negativos
    nulos = df["VAR_FECHA_CALCULADA"].isna().sum()
    negativos = df[df["VAR_FECHA_CALCULADA"] < 0]

    # Mostrar métricas
    st.subheader("📊 Resultados del cálculo")
    st.write(f"Total registros: **{len(df):,}**")
    st.write(f"Fechas incompletas (nulos): **{nulos:,}**")
    st.write(f"Inconsistencias (días negativos): **{len(negativos):,}**")

    if len(negativos) > 0:
        st.warning("⚠️ Se encontraron inconsistencias de fechas (valores negativos):")
        st.dataframe(
            negativos[
                ["DEUDOR", "OPERACION", col_fecha_etapa, col_fecha_inv, "VAR_FECHA_CALCULADA"]
            ].head(20)
        )
    else:
        st.success("✅ No se encontraron inconsistencias. Todas las fechas son coherentes.")

    # Descarga
    output = BytesIO()
    df.to_excel(output, index=False, engine="openpyxl")
    output.seek(0)
    st.download_button(
        label="⬇️ Descargar Inventario con VAR_FECHA_CALCULADA",
        data=output,
        file_name="Inventario_Actualizado_Paso4.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("Sube el inventario con 'DIAS_POR_ETAPA' completado para calcular la variación entre fechas.")

