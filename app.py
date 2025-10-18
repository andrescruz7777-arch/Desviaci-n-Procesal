# ============================
# 📊 PASO 5 — Avance, Desviación y Clasificación (toma base desde sesión)
# ============================
st.header("📊 Paso 5 | % Avance, % Desviación y Clasificación (usa base del Paso 4)")

# Verificar base en sesión
if "base_limpia_paso4" not in st.session_state or st.session_state["base_limpia_paso4"] is None or len(st.session_state["base_limpia_paso4"]) == 0:
    st.warning("⚠️ No hay base limpia en memoria. Ejecuta el Paso 4 y asegúrate de que se cargue correctamente.")
else:
    df5 = st.session_state["base_limpia_paso4"].copy()

    # Normalizar por seguridad
    df5.columns = [normalizar_columna(c) for c in df5.columns]

    # Columnas requeridas
    for needed in ["DIAS_POR_ETAPA", "VAR_FECHA_CALCULADA"]:
        if needed not in df5.columns:
            st.error(f"❌ Falta la columna requerida: {needed}. Revisa el Paso 4.")
            st.stop()

    # Tipos numéricos
    df5["DIAS_POR_ETAPA"] = pd.to_numeric(df5["DIAS_POR_ETAPA"], errors="coerce")
    df5["VAR_FECHA_CALCULADA"] = pd.to_numeric(df5["VAR_FECHA_CALCULADA"], errors="coerce")

    # Cálculos
    df5["PORC_AVANCE"] = df5.apply(
        lambda x: (x["VAR_FECHA_CALCULADA"] / x["DIAS_POR_ETAPA"] * 100) if pd.notna(x["DIAS_POR_ETAPA"]) and x["DIAS_POR_ETAPA"] > 0 else 0,
        axis=1
    )
    df5["PORC_DESVIACION"] = df5.apply(
        lambda x: max(((x["VAR_FECHA_CALCULADA"] - x["DIAS_POR_ETAPA"]) / x["DIAS_POR_ETAPA"]) * 100, 0) if pd.notna(x["DIAS_POR_ETAPA"]) and x["DIAS_POR_ETAPA"] > 0 else 0,
        axis=1
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

    # Métricas ejecutivas
    total_procesos = len(df5)
    total_clientes = df5["DEUDOR"].nunique() if "DEUDOR" in df5.columns else 0
    capital_total = df5["CAPITAL_ACT"].sum() if "CAPITAL_ACT" in df5.columns else 0
    desviados = (df5["PORC_DESVIACION"] > 0).sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🧾 Procesos totales", f"{total_procesos:,}")
    c2.metric("👤 Clientes únicos", f"{total_clientes:,}")
    c3.metric("💰 Capital total", f"${capital_total:,.0f}")
    c4.metric("⚠️ Procesos con desviación", f"{desviados:,}")

    # Vista previa mínima (sin validaciones ruidosas)
    st.caption("Vista previa (10 filas):")
    cols_preview = [c for c in [
        "DEUDOR", "OPERACION", "ETAPA_JURIDICA", "SUB_ETAPA_JURIDICA",
        "DIAS_POR_ETAPA", "VAR_FECHA_CALCULADA", "PORC_AVANCE",
        "PORC_DESVIACION", "DIAS_EXCESO", "CLASIFICACION_%", "CLASIFICACION_DIAS", "CAPITAL_ACT"
    ] if c in df5.columns]
    st.dataframe(df5[cols_preview].head(10), use_container_width=True)

    # Descarga final
    out5 = BytesIO()
    df5.to_excel(out5, index=False, engine="openpyxl")
    out5.seek(0)
    st.download_button(
        "⬇️ Descargar Inventario Paso 5 (clasificado)",
        data=out5,
        file_name="Inventario_Paso5_Clasificado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="dl_paso5"
    )

