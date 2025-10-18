import pandas as pd
import streamlit as st
from io import BytesIO

# ============================
# ⚙️ CONFIGURACIÓN INICIAL
# ============================
st.set_page_config(page_title="Paso 4 — Recalcular VAR_FECHA_CALCULADA", layout="wide")
st.title("📆 Paso 4 | Recalcular 'VAR FECHA ACT - FECHA INV' y filtrar errores")

# ============================
# 📤 CARGA DE INVENTARIO
# ============================
inventario_file = st.file_uploader("Sube el inventario con 'DIAS_POR_ETAPA' completado", type=["xlsx"])

if inventario_file:
    df = pd.read_excel(inventario_file)
    df.columns = [c.upper().replace("-", "_").replace(" ", "_") for c in df.columns]

    # Columnas base
    col_fecha_inv = "FECHA_ACT_INVENTARIO"
    col_fecha_etapa = "FECHA_ACT_ETAPA"
    col_var_original = "VAR_FECHA_ACT___FECHA_INV"

    # Asegurar formato fecha
    df[col_fecha_inv] = pd.to_datetime(df[col_fecha_inv], errors="coerce")
    df[col_fecha_etapa] = pd.to_datetime(df[col_fecha_etapa], errors="coerce")

    # ============================
    # 🧮 CÁLCULO DE DÍAS CALENDARIO
    # ============================
    df["VAR_FECHA_CALCULADA"] = (
        df[col_fecha_inv].dt.normalize() - df[col_fecha_etapa].dt.normalize()
    ).dt.days

    # ============================
    # 🚨 DETECCIÓN DE ERRORES
    # ============================
    errores = df[
        df["VAR_FECHA_CALCULADA"].isna() | (df["VAR_FECHA_CALCULADA"] < 0)
    ].copy()

    total_errores = len(errores)
    total_registros = len(df)

    if total_errores > 0:
        st.warning(f"⚠️ Se detectaron **{total_errores:,}** registros con errores de fecha.")
        
        # Generar archivo de errores para descarga
        output_err = BytesIO()
        errores.to_excel(output_err, index=False, engine="openpyxl")
        output_err.seek(0)
        st.download_button(
            label="⬇️ Descargar registros con errores de fecha",
            data=output_err,
            file_name="Errores_Fechas_Paso4.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.success("✅ No se encontraron errores de fecha. Todas las filas son válidas.")

    # ============================
    # 🧹 FILTRAR BASE LIMPIA
    # ============================
    base_limpia = df.dropna(subset=["VAR_FECHA_CALCULADA"])
    base_limpia = base_limpia[base_limpia["VAR_FECHA_CALCULADA"] >= 0]

    st.info(f"Base depurada: **{len(base_limpia):,}** registros válidos de {total_registros:,} totales.")
    st.success("✅ Los registros con errores fueron excluidos automáticamente para los cálculos siguientes.")

    # ============================
    # 💾 DESCARGA DE BASE LIMPIA (opcional)
    # ============================
    output_clean = BytesIO()
    base_limpia.to_excel(output_clean, index=False, engine="openpyxl")
    output_clean.seek(0)
    st.download_button(
        label="⬇️ Descargar Base Limpia para Paso 5",
        data=output_clean,
        file_name="Inventario_Limpio_Paso4.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("Sube el inventario con 'DIAS_POR_ETAPA' completado para recalcular la variación entre fechas.")
