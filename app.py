# ============================================
# ⚖️ ANÁLISIS DE DESVIACIÓN PROCESAL — COS
# Pasos 1 a 5 integrados
# ============================================

import pandas as pd
import streamlit as st
import unicodedata
import os
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
# 📘 PASO 1 y 2 — CARGA Y LIMPIEZA DE ENCABEZADOS
# ============================================
st.header("📘 Paso 1–2 | Carga y limpieza de encabezados")

inventario_file = st.file_uploader("Sube el inventario (.xlsx)", type=["xlsx"])
tiempos_path = "Tabla_tiempos_etapas_desviacion.xlsx"  # tabla fija en raíz

if inventario_file:
    inventario = pd.read_excel(inventario_file, nrows=0)
    tiempos = pd.read_excel(tiempos_path, nrows=0)

    st.write("📋 **Encabezados detectados en Inventario:**", list(inventario.columns))
    st.write("📋 **Encabezados detectados en Tiempos:**", list(tiempos.columns))

    # Normalización silenciosa
    inventario.columns = [normalizar_columna(c) for c in inventario.columns]
    tiempos.columns = [normalizar_columna(c) for c in tiempos.columns]

    st.success("✅ Encabezados normalizados correctamente.")

    # ============================================
    # 📗 PASO 3 — CRUCE DE DÍAS POR ETAPA
    # ============================================
    st.header("📗 Paso 3 | Completar 'DIAS_POR_ETAPA' automáticamente")

    inventario_df = pd.read_excel(inventario_file)
    tiempos_df = pd.read_excel(tiempos_path)

    inventario_df.columns = [normalizar_columna(c) for c in inventario_df.columns]
    tiempos_df.columns = [normalizar_columna(c) for c in tiempos_df.columns]

    col_sub_inv = "SUB_ETAPA_JURIDICA"
    col_sub_time = "DESCRIPCION_DE_LA_SUBETAPA"
    col_dias = "DIAS_POR_ETAPA"
    col_duracion = "DURACION_MAXIMA_EN_DIAS"

    if col_dias not in inventario_df.columns:
        inventario_df[col_dias] = None

    vacias_antes = inventario_df[col_dias].isna().sum()

    merged = inventario_df.merge(
        tiempos_df[[col_sub_time, col_duracion]],
        how="left",
        left_on=col_sub_inv,
        right_on=col_sub_time,
        suffixes=("", "_TIEMPOS")
    )
    merged[col_dias] = merged[col_dias].fillna(merged[col_duracion])
    vacias_despues = merged[col_dias].isna().sum()

    st.write(f"🧮 Filas completadas: **{vacias_antes - vacias_despues:,}** | Aún vacías: **{vacias_despues:,}**")

    sin_match = merged[merged[col_dias].isna()][col_sub_inv].dropna().unique().tolist()
    if len(sin_match) > 0:
        st.warning(f"⚠️ Subetapas sin coincidencia: {len(sin_match)}")
        st.dataframe(pd.DataFrame(sin_match, columns=["SUB_ETAPA_SIN_MATCH"]))
    else:
        st.success("✅ Todas las subetapas encontraron su duración máxima.")

    # Guardar para el siguiente paso
    st.session_state["inventario_con_dias"] = merged

    # ============================================
    # 📆 PASO 4 — CALCULAR VAR_FECHA_CALCULADA Y DEPURAR
    # ============================================
    st.header("📆 Paso 4 | Recalcular fechas y depurar errores")

    df4 = merged.copy()

    for col in ["FECHA_ACT_INVENTARIO", "FECHA_ACT_ETAPA"]:
        if col not in df4.columns:
            st.error(f"❌ Falta la columna {col} en el inventario.")
            st.stop()

    df4["FECHA_ACT_INVENTARIO"] = pd.to_datetime(df4["FECHA_ACT_INVENTARIO"], errors="coerce")
    df4["FECHA_ACT_ETAPA"] = pd.to_datetime(df4["FECHA_ACT_ETAPA"], errors="coerce")

    df4["VAR_FECHA_CALCULADA"] = (
        df4["FECHA_ACT_INVENTARIO"].dt.normalize() - df4["FECHA_ACT_ETAPA"].dt.normalize()
    ).dt.days

    errores = df4[df4["VAR_FECHA_CALCULADA"].isna() | (df4["VAR_FECHA_CALCULADA"] < 0)].copy()
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

    base_limpia = df4.dropna(subset=["VAR_FECHA_CALCULADA"])
    base_limpia = base_limpia[base_limpia["VAR_FECHA_CALCULADA"] >= 0].copy()
    st.session_state["base_limpia_paso4"] = base_limpia

    st.info(f"Base depurada lista: **{len(base_limpia):,}** registros válidos.")

    # ============================================
    # 📊 PASO 5 — % AVANCE Y % DESVIACIÓN
    # ============================================
    st.header("📊 Paso 5 | % Avance, % Desviación y Clasificación")

    df5 = base_limpia.copy()
    df5.columns = [normalizar_columna(c) for c in df5.columns]

    for c in ["DIAS_POR_ETAPA", "VAR_FECHA_CALCULADA"]:
        df5[c] = pd.to_numeric(df5[c], errors="coerce")

    # Cálculos
    df5["PORC_AVANCE"] = df5.apply(
        lambda x: (x["VAR_FECHA_CALCULADA"] / x["DIAS_POR_ETAPA"] * 100)
        if pd.notna(x["DIAS_POR_ETAPA"]) and x["DIAS_POR_ETAPA"] > 0 else 0,
        axis=1,
    )
    df5["PORC_DESVIACION"] = df5.apply(
        lambda x: max(((x["VAR_FECHA_CALCULADA"] - x["DIAS_POR_ETAPA"]) / x["DIAS_POR_ETAPA"]) * 100, 0)
        if pd.notna(x["DIAS_POR_ETAPA"]) and x["DIAS_POR_ETAPA"] > 0 else 0,
        axis=1,
    )
    df5["DIAS_EXCESO"] = df5["VAR_FECHA_CALCULADA"] - df5["DIAS_POR_ETAPA"]

    # Clasificaciones
    def clasif_porcentaje(p):
        if p <= 30: return "LEVE 🟢"
        if 31 <= p <= 70: return "MODERADA 🟡"
        if p > 70: return "GRAVE 🔴"
        return "SIN_DATO ⚪️"

    def clasif_dias(d):
        if d <= 0: return "A TIEMPO ⚪️"
        if 1 <= d <= 15: return "LEVE 🟢"
        if 16 <= d <= 30: return "MEDIA 🟡"
        if d > 30: return "ALTA 🔴"
        return "SIN_DATO ⚪️"

    df5["CLASIFICACION_%"] = df5["PORC_DESVIACION"].apply(clasif_porcentaje)
    df5["CLASIFICACION_DIAS"] = df5["DIAS_EXCESO"].apply(clasif_dias)

    # Métricas globales
    total_procesos = len(df5)
    total_clientes = df5["DEUDOR"].nunique() if "DEUDOR" in df5.columns else 0
    capital_total = df5["CAPITAL_ACT"].sum() if "CAPITAL_ACT" in df5.columns else 0
    desviados = (df5["PORC_DESVIACION"] > 0).sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🧾 Procesos totales", f"{total_procesos:,}")
    c2.metric("👤 Clientes únicos", f"{total_clientes:,}")
    c3.metric("💰 Capital total", f"${capital_total:,.0f}")
    c4.metric("⚠️ Procesos con desviación", f"{desviados:,}")

    # Vista previa
    st.dataframe(
        df5[
            [
                "DEUDOR", "OPERACION", "ETAPA_JURIDICA", "SUB_ETAPA_JURIDICA",
                "DIAS_POR_ETAPA", "VAR_FECHA_CALCULADA", "PORC_AVANCE",
                "PORC_DESVIACION", "DIAS_EXCESO",
                "CLASIFICACION_%", "CLASIFICACION_DIAS", "CAPITAL_ACT"
            ]
        ].head(15),
        use_container_width=True
    )

    # Descarga final
    output = BytesIO()
    df5.to_excel(output, index=False, engine="openpyxl")
    output.seek(0)
    st.download_button(
        "⬇️ Descargar Inventario Clasificado (Paso 5)",
        data=output,
        file_name="Inventario_Paso5_Clasificado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("Sube el inventario (.xlsx) para iniciar el flujo completo (1–5).")

