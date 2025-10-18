import pandas as pd
import streamlit as st
from io import BytesIO

# ============================
# ⚙️ CONFIGURACIÓN
# ============================
st.set_page_config(page_title="Paso 4 — VAR_FECHA_CALCULADA", layout="wide")
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

    # Columnas base
    col_fecha_inv = "FECHA_ACT_INVENTARIO"
    col_fecha_etapa = "FECHA_ACT_ETAPA"
    col_var_original = "VAR_FECHA_ACT___FECHA_INV"

    # Asegurar formato de fechas
    df[col_fecha_inv] = pd.to_datetime(df[col_fecha_inv], errors="coerce")
    df[col_fecha_etapa] = pd.to_datetime(df[col_fecha_etapa], errors="coerce")

    # ============================
    # 🧮 CÁLCULO DE DÍAS CALENDARIO
    # ============================
    # Normaliza ambas fechas a medianoche y resta días calendario
    df["VAR_FECHA_CALCULADA"] = (
        df[col_fecha_inv].dt.normalize() - df[col_fecha_etapa].dt.normalize()
    ).dt.days

    # ============================
    # 📊 VALIDACIONES
    # ============================
    total_registros = len(df)
    nulos = df["VAR_FECHA_CALCULADA"].isna().sum()
    negativos = df[df["VAR_FECHA_CALCULADA"] < 0]

    st.subheader("📊 Resultados del cálculo")
    st.write(f"Total de registros: **{total_registros:,}**")
    st.write(f"Fechas incompletas (nulas): **{nulos:,}**")
    st.write(f"Inconsistencias (días negativos): **{len(negativos):,}**")

    # ============================
    # 🎨 ESTILOS VISUALES
    # ============================
    def resaltar_filas(row):
        if pd.isna(row["VAR_FECHA_CALCULADA"]):
            return ["background-color: #FFF3CD"] * len(row)  # Amarillo
        elif row["VAR_FECHA_CALCULADA"] < 0:
            return ["background-color: #F8D7DA"] * len(row)  # Rojo
        else:
            return [""] * len(row)

    # Mostrar primeros registros con color
    st.subheader("📋 Muestra de validación (primeros 15 registros)")
    st.dataframe(
        df[[
            "DEUDOR", "OPERACION", col_fecha_etapa, col_fecha_inv,
            col_var_original, "VAR_FECHA_CALCULADA"
        ]].head(15).style.apply(resaltar_filas, axis=1),
        use_container_width=True
    )

    if len(negativos) > 0:
        st.warning("⚠️ Se encontraron inconsistencias de fechas (valores negativos). Revisa las filas resaltadas en rojo.")
    elif nulos > 0:
        st.info("⚠️ Existen registros con fechas nulas (resaltadas en amarillo).")
    else:
        st.success("✅ Todas las fechas son coherentes y el cálculo de días calendario es correcto.")

    # ============================
    # 💾 DESCARGA DEL ARCHIVO ACTUALIZADO
    # ============================
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
    st.info("Sube el inventario con 'DIAS_POR_ETAPA' completado para calcular la variación de fechas.")

