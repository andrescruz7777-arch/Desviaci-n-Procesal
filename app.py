import pandas as pd
import unicodedata
import streamlit as st

# ============================
# ⚙️ CONFIGURACIÓN INICIAL
# ============================
st.set_page_config(page_title="Validación de Inventario Jurídico", layout="wide")
st.title("🧭 Paso 1 → 2 | Validación de Carga y Limpieza de Encabezados")

# ============================
# 📂 CARGA DE ARCHIVOS
# ============================
st.header("📂 1️⃣ Cargar archivos de Inventario y Tiempos")

inventario_file = st.file_uploader("Sube el archivo de Inventario (.xlsx)", type=["xlsx"])
tiempos_file = st.file_uploader("Sube el archivo de Tiempos (.xlsx)", type=["xlsx"])

if inventario_file and tiempos_file:
    inventario = pd.read_excel(inventario_file, nrows=0)
    tiempos = pd.read_excel(tiempos_file, nrows=0)

    # Mostrar encabezados detectados
    st.subheader("📘 Columnas detectadas – Inventario (originales)")
    st.write(list(inventario.columns))

    st.subheader("📗 Columnas detectadas – Tiempos (originales)")
    st.write(list(tiempos.columns))

    # Verificación de claves
    col_inv_ok = any("SUB-ETAPA JURIDICA" in c for c in inventario.columns)
    col_time_ok = any("Descripción de la Subetapa" in c for c in tiempos.columns)

    st.markdown("### 🔎 Claves detectadas:")
    st.write("✅ SUB-ETAPA JURIDICA en Inventario:" if col_inv_ok else "❌ Falta SUB-ETAPA JURIDICA")
    st.write("✅ Descripción de la Subetapa en Tiempos:" if col_time_ok else "❌ Falta Descripción de la Subetapa")

    if col_inv_ok and col_time_ok:
        st.success("✅ Paso 1 OK — Archivos y encabezados correctos.")
    else:
        st.warning("⚠️ Revisa los encabezados antes de continuar.")

    # ============================
    # 🧹 2️⃣ LIMPIEZA DE ENCABEZADOS
    # ============================

    st.header("🧹 Paso 2 | Limpieza mínima de encabezados")

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

    inv_cols_original = inventario.columns.tolist()
    time_cols_original = tiempos.columns.tolist()

    inv_cols_norm = [normalizar_columna(c) for c in inv_cols_original]
    time_cols_norm = [normalizar_columna(c) for c in time_cols_original]

    st.subheader("📘 Inventario – Encabezados normalizados")
    st.write(inv_cols_norm)

    st.subheader("📗 Tiempos – Encabezados normalizados")
    st.write(time_cols_norm)

    # ✅ Chequeos
    same_inv = len(inv_cols_original) == len(inv_cols_norm)
    same_time = len(time_cols_original) == len(time_cols_norm)

    st.markdown("### ✅ Chequeos automáticos")
    st.write("Inventario: columnas iguales antes/después →", "✅" if same_inv else "❌")
    st.write("Tiempos: columnas iguales antes/después →", "✅" if same_time else "❌")

    key_inv = any("SUB_ETAPA_JURIDICA" in c for c in inv_cols_norm)
    key_time = any("DESCRIPCION_DE_LA_SUBETAPA" in c for c in time_cols_norm)

    st.write("🔑 SUB_ETAPA_JURIDICA presente:", "✅" if key_inv else "❌")
    st.write("🔑 DESCRIPCION_DE_LA_SUBETAPA presente:", "✅" if key_time else "❌")

    if same_inv and same_time and key_inv and key_time:
        st.success("✅ Paso 2 OK — Sin pérdida ni duplicados. Encabezados listos para cruce.")
    else:
        st.warning("⚠️ Revisa los encabezados normalizados antes de continuar.")

else:
    st.info("Sube ambos archivos (.xlsx) para iniciar la validación de encabezados.")
