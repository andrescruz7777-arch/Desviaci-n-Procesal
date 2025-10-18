import pandas as pd
import unicodedata
import streamlit as st
import os
from io import BytesIO

# ============================
# ⚙️ CONFIGURACIÓN INICIAL
# ============================
st.set_page_config(page_title="Paso 3 — Cruce de Días por Etapa", layout="wide")
st.title("📅 Paso 3 | Completar 'DIAS POR ETAPA' automáticamente")

# ============================
# 📂 VALIDAR RUTA DE TIEMPOS
# ============================
tiempos_path = "Tabla_tiempos_etapas_desviacion.xlsx"

if not os.path.exists(tiempos_path):
    st.error(f"❌ No se encontró el archivo de tiempos en la raíz: {tiempos_path}")
    st.stop()
else:
    st.info("📁 Archivo de tiempos cargado automáticamente desde el repositorio raíz.")

# ============================
# 🧹 FUNCIÓN DE NORMALIZACIÓN
# ============================
def normalizar_columna(col):
    col = ''.join(c for c in unicodedata.normalize('NFD', col) if unicodedata.category(c) != 'Mn')
    col = col.upper().replace("-", "_").replace(" ", "_")
    col = ''.join(c for c in col if c.isalnum() or c == "_")
    while "__" in col:
        col = col.replace("__", "_")
    return col.strip("_")

# ============================
# 📤 SUBIR INVENTARIO
# ============================
inventario_file = st.file_uploader("Sube el Inventario (.xlsx)", type=["xlsx"])

if inventario_file:
    # ============================
    # 🔽 CARGA Y NORMALIZACIÓN
    # ============================
    inventario = pd.read_excel(inventario_file)
    tiempos = pd.read_excel(tiempos_path)

    inventario.columns = [normalizar_columna(c) for c in inventario.columns]
    tiempos.columns = [normalizar_columna(c) for c in tiempos.columns]

    # ============================
    # 🔍 DEFINIR COLUMNAS CLAVE
    # ============================
    col_sub_inv = "SUB_ETAPA_JURIDICA"
    col_sub_time = "DESCRIPCION_DE_LA_SUBETAPA"
    col_dias = "DIAS_POR_ETAPA"
    col_duracion = "DURACION_MAXIMA_EN_DIAS"

    # Crear columna si no existe
    if col_dias not in inventario.columns:
        inventario[col_dias] = None

    # ============================
    # 📊 CRUCE Y COMPLETADO
    # ============================
    vacias_antes = inventario[col_dias].isna().sum()

    inventario = inventario.merge(
        tiempos[[col_sub_time, col_duracion]],
        how="left",
        left_on=col_sub_inv,
        right_on=col_sub_time,
        suffixes=("", "_TIEMPOS")
    )

    inventario[col_dias] = inventario[col_dias].fillna(inventario[col_duracion])
    vacias_despues = inventario[col_dias].isna().sum()

    # Subetapas sin match
    sin_match = inventario[inventario[col_dias].isna()][col_sub_inv].dropna().unique().tolist()

    # ============================
    # 🧾 RESULTADOS EN PANTALLA
    # ============================
    st.subheader("📈 Resultados del Cruce")
    st.write(f"Filas con 'DIAS_POR_ETAPA' vacías antes del cruce: **{vacias_antes:,}**")
    st.write(f"Filas que permanecen vacías después del cruce: **{vacias_despues:,}**")

    if len(sin_match) > 0:
        st.warning(f"⚠️ {len(sin_match)} subetapas sin coincidencia en el catálogo de tiempos:")
        st.dataframe(pd.DataFrame(sin_match, columns=["SUB_ETAPA_SIN_MATCH"]))
    else:
        st.success("✅ Todas las subetapas encontraron su duración máxima correctamente.")

    # ============================
    # 💾 DESCARGA DEL INVENTARIO ACTUALIZADO
    # ============================
    output = BytesIO()
    inventario.to_excel(output, index=False, engine="openpyxl")
    output.seek(0)
    st.download_button(
        label="⬇️ Descargar Inventario Actualizado con DIAS_POR_ETAPA",
        data=output,
        file_name="Inventario_Actualizado_Paso3.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("Sube el archivo de Inventario (.xlsx) para ejecutar el cruce automático del Paso 3.")
