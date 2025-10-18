import pandas as pd
import unicodedata
import streamlit as st

# ============================
# ⚙️ CONFIGURACIÓN INICIAL
# ============================
st.set_page_config(page_title="Paso 3 — Cruce de días por etapa", layout="wide")
st.title("📅 Paso 3 | Completar 'DIAS POR ETAPA' automáticamente")

# ============================
# 📂 RUTA DE ARCHIVOS
# ============================
tiempos_path = "Tabla_tiempos_etapas_desviacion.xlsx"  # 📁 desde el repositorio raíz
inventario_file = st.file_uploader("Sube el Inventario (.xlsx)", type=["xlsx"])

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
# 🚀 EJECUCIÓN
# ============================
if inventario_file:
    # Cargar datos (los encabezados ya se limpian en memoria, sin mostrar)
    inventario = pd.read_excel(inventario_file)
    tiempos = pd.read_excel(tiempos_path)

    inventario.columns = [normalizar_columna(c) for c in inventario.columns]
    tiempos.columns = [normalizar_columna(c) for c in tiempos.columns]

    # Columnas clave
    col_sub_inv = "SUB_ETAPA_JURIDICA"
    col_sub_time = "DESCRIPCION_DE_LA_SUBETAPA"
    col_dias = "DIAS_POR_ETAPA"
    col_duracion = "DURACION_MAXIMA_EN_DIAS"

    # Conteo antes del cruce
    vacias_antes = inventario[col_dias].isna().sum() if col_dias in inventario.columns else len(inventario)

    # Si no existe la columna DIAS_POR_ETAPA, la creamos vacía
    if col_dias not in inventario.columns:
        inventario[col_dias] = None

    # Cruce (merge)
    inventario = inventario.merge(
        tiempos[[col_sub_time, col_duracion]],
        how="left",
        left_on=col_sub_inv,
        right_on=col_sub_time,
        suffixes=("", "_TIEMPOS")
    )

    # Completar valores faltantes
    inventario[col_dias] = inventario[col_dias].fillna(inventario[col_duracion])

    # Conteo después
    vacias_despues = inventario[col_dias].isna().sum()

    # Subetapas sin match
    sin_match = inventario[inventario[col_dias].isna()][col_sub_inv].dropna().unique().tolist()

    # ============================
    # 📊 RESULTADOS EN PANTALLA
    # ============================
    st.subheader("📈 Resultados del Cruce")
    st.write(f"Filas con 'DIAS_POR_ETAPA' vacías antes del cruce: **{vacias_antes:,}**")
    st.write(f"Filas que permanecen vacías después del cruce: **{vacias_despues:,}**")

    if len(sin_match) > 0:
        st.warning(f"⚠️ Hay {len(sin_match)} subetapas sin coincidencia. Revisa el catálogo:")
        st.dataframe(pd.DataFrame(sin_match, columns=["SUB_ETAPA_SIN_MATCH"]))
    else:
        st.success("✅ Todas las subetapas encontraron su duración máxima correctamente.")

    # Guardar copia del inventario actualizado
    st.download_button(
        label="⬇️ Descargar Inventario actualizado con DIAS_POR_ETAPA",
        data=inventario.to_excel(index=False, engine="openpyxl"),
        file_name="Inventario_Actualizado_Paso3.xlsx"
    )
else:
    st.info("Sube el archivo de Inventario para ejecutar el cruce automático del Paso 3.")
