# ============================================================
# ⚖️ COS JudicIA – Tablero Jurídico Inteligente (v3.3 Cloud)
# Robusto contra: encabezados desplazados, nombres variables,
# columnas duplicadas, objetos no 1-D y vacíos.
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import io, calendar, unicodedata
from datetime import datetime

# =============== UI / PAGE CONFIG ===============
st.set_page_config(page_title="⚖️ COS JudicIA – Tablero Jurídico Inteligente", layout="wide")
st.markdown("""
<style>
body, .stApp {background-color:#000!important;color:#FFF!important;}
h1,h2,h3,h4,h5,h6,p,div,label{color:#FFF!important;}
.alerta{font-size:18px;font-weight:600;padding:10px;border-radius:8px;margin:10px 0;animation:pulse 2s infinite;}
@keyframes pulse{0%{opacity:1;}50%{opacity:.6;}100%{opacity:1;}}
.verde{color:#00FF00;}.amarillo{color:#FFFF00;}.rojo{color:#FF0000;}.morado{color:#B388FF;}
table td,table th{color:#FFF!important;}
</style>
""", unsafe_allow_html=True)

st.title("⚖️ COS JudicIA – Tablero Jurídico Inteligente")
st.markdown("Cargue el **Inventario mensual (.xlsx)** y la **Tabla de tiempos por etapa (.xlsx)** para generar el análisis completo:")

# =============== HELPERS ===============
def normalizar_col(col: str) -> str:
    """Mayúsculas, sin tildes, espacios -> _"""
    col = str(col).upper().strip()
    col = ''.join(c for c in unicodedata.normalize('NFD', col) if unicodedata.category(c) != 'Mn')
    col = col.replace(" ", "_")
    return col

def detectar_header_xlsx(file, keywords=("DEUDOR","OPERACION","SUB","ETAPA","CAPITAL"), max_buscar=50):
    """
    Busca la fila de encabezados: la primera fila que contenga ≥2 palabras clave.
    """
    tmp = pd.read_excel(file, header=None, nrows=max_buscar)
    for i in range(len(tmp)):
        fila = tmp.iloc[i].astype(str).str.upper()
        hits = sum(fila.str.contains("|".join(keywords), na=False))
        if hits >= 2:
            return i
    return None

def encontrar_columna(df: pd.DataFrame, patrones):
    for col in df.columns:
        for p in patrones:
            if p in col:
                return col
    return None

def asegurar_series_1d(df: pd.DataFrame, cols):
    """
    Garantiza que cols existan, sean 1-D, tipo string y sin NaN.
    Si faltan, las crea como 'NO_REGISTRA'.
    Convierte listas/tuplas a primer elemento.
    """
    df = df.loc[:, ~df.columns.duplicated()]  # quitar duplicados de nombre
    for c in cols:
        if c not in df.columns:
            df[c] = "NO_REGISTRA"
        else:
            df[c] = df[c].apply(lambda x: x[0] if isinstance(x, (list, tuple)) and len(x) > 0 else x)
            df[c] = df[c].astype(str)
            df[c] = df[c].fillna("NO_REGISTRA")
    return df

def safe_to_datetime(s):
    try:
        return pd.to_datetime(s, errors='coerce')
    except Exception:
        return pd.to_datetime(pd.Series([None]))  # fallback

def validar_col_exist(df, cols_necesarias, titulo="Validación de columnas"):
    faltantes = [c for c in cols_necesarias if c not in df.columns]
    if faltantes:
        st.error(f"❌ Faltan columnas necesarias en {titulo}: {faltantes}")
        st.stop()

# =============== FILE UPLOADS ===============
inv_file = st.file_uploader("📂 Inventario mensual (.xlsx)", type=["xlsx"])
tms_file = st.file_uploader("⏱️ Tabla tiempos etapas (.xlsx)", type=["xlsx"])

if inv_file and tms_file:
    with st.spinner("🔄 Detectando encabezados y cargando archivos..."):
        # Detectar encabezado dinámico en inventario
        header_row = detectar_header_xlsx(inv_file)
        if header_row is None:
            st.error("❌ No se detectó una fila de encabezados válida en el inventario (busqué las primeras ~50 filas). Verifique el archivo.")
            st.stop()
        # Importante: reposicionar el puntero del archivo para releerlo
        inv_file.seek(0)

        df = pd.read_excel(inv_file, header=header_row)
        tiempos = pd.read_excel(tms_file)

        # Normalizar encabezados
        df.columns = [normalizar_col(c) for c in df.columns]
        tiempos.columns = [normalizar_col(c) for c in tiempos.columns]

    st.write("📘 Columnas inventario detectadas:", list(df.columns))
    st.write("📗 Columnas tiempos detectadas:", list(tiempos.columns))

    # =============== MAPEO FLEXIBLE DE COLUMNAS INVENTARIO ===============
    # Definir patrones amplios para localizar campos clave sin depender del nombre exacto
    mapa = {
        "DEUDOR": encontrar_columna(df, ["DEUDOR","CEDULA","IDENTIFICACION","DOC","NIT"]),
        "ETAPA_JURIDICA": encontrar_columna(df, ["ETAPA_JURIDICA","ETAPA"]),
        "SUB-ETAPA_JURIDICA": encontrar_columna(df, ["SUB-ETAPA","SUB_ETAPA","SUBETAPA","SUB_ETAPA_JURIDICA","SUB-ETAPA_JURIDICA","SUB"]),
        "CAPITAL_ACT": encontrar_columna(df, ["CAPITAL_ACT","CAPITAL","SALDO"]),
        "CIUDAD": encontrar_columna(df, ["CIUDAD","REGIONAL","MUNICIPIO"]),
        "JUZGADO": encontrar_columna(df, ["JUZGADO","DESPACHO"]),
        "FECHA_ACT_INVENTARIO": encontrar_columna(df, ["FECHA_ACT_INVENTARIO","FECHA_INVENTARIO","F_INV"]),
        "FECHA_ACT_ETAPA": encontrar_columna(df, ["FECHA_ACT_ETAPA","FECHA_ETAPA","F_ETAPA"]),
        "DIAS_POR_ETAPA": encontrar_columna(df, ["DIAS_POR_ETAPA","DIAS_ETAPA","SLA"]),
    }

    st.markdown("🔍 **Columnas identificadas automáticamente (inventario):**")
    st.json(mapa)

    # Renombrar a nombres estándar internos
    for key, val in mapa.items():
        if val and key != val:
            df.rename(columns={val: key}, inplace=True)

    # =============== VALIDACIONES BÁSICAS ===============
    # Si algo crítico no está, paramos y mostramos diagnóstico útil
    validar_col_exist(df, ["SUB-ETAPA_JURIDICA"], "Inventario (campo de cruce)")
    validar_col_exist(tiempos, ["DESCRIPCION_DE_LA_SUBETAPA","DURACION_MAXIMA_EN_DIAS"], "Tabla de tiempos")

    # =============== CRUCE CON TIEMPOS ===============
    with st.spinner("🔗 Cruzando inventario con la tabla de tiempos..."):
        df = df.merge(
            tiempos[["DESCRIPCION_DE_LA_SUBETAPA","DURACION_MAXIMA_EN_DIAS"]],
            how="left",
            left_on="SUB-ETAPA_JURIDICA",
            right_on="DESCRIPCION_DE_LA_SUBETAPA"
        )
        # Completar DIAS_POR_ETAPA
        if "DIAS_POR_ETAPA" not in df.columns:
            df["DIAS_POR_ETAPA"] = None
        df["DIAS_POR_ETAPA"] = df["DIAS_POR_ETAPA"].fillna(df["DURACION_MAXIMA_EN_DIAS"])
        df.drop(columns=["DESCRIPCION_DE_LA_SUBETAPA","DURACION_MAXIMA_EN_DIAS"], inplace=True, errors="ignore")

    # =============== FECHAS Y CÁLCULOS BASE ===============
    with st.spinner("🗓️ Calculando variaciones y estados..."):
        if "FECHA_ACT_INVENTARIO" not in df.columns or "FECHA_ACT_ETAPA" not in df.columns:
            st.warning("⚠️ No encontré alguna de las fechas. Intentaré detectar columnas de fechas por contenido.")
            # detección heurística por contenido
            for c in df.columns:
                if ("INVENT" in c or "INV" in c) and "FECHA" in c:
                    df.rename(columns={c: "FECHA_ACT_INVENTARIO"}, inplace=True)
                if ("ETAPA" in c) and "FECHA" in c:
                    df.rename(columns={c: "FECHA_ACT_ETAPA"}, inplace=True)

        df["FECHA_ACT_INVENTARIO"] = pd.to_datetime(df.get("FECHA_ACT_INVENTARIO"), errors="coerce")
        df["FECHA_ACT_ETAPA"] = pd.to_datetime(df.get("FECHA_ACT_ETAPA"), errors="coerce")

        # VAR_FECHA_CALCULADA: si falta alguna fecha, resultado NaN -> luego 0
        df["VAR_FECHA_CALCULADA"] = (df["FECHA_ACT_INVENTARIO"] - df["FECHA_ACT_ETAPA"]).dt.days
        df["VAR_FECHA_CALCULADA"] = df["VAR_FECHA_CALCULADA"].fillna(0).clip(lower=0)

        # Asegurar DIAS_POR_ETAPA numérico
        df["DIAS_POR_ETAPA"] = pd.to_numeric(df["DIAS_POR_ETAPA"], errors="coerce")

        # % Avance y % Desviacion (evitar división por 0/NaN)
        df["%_AVANCE"] = (df["VAR_FECHA_CALCULADA"] / df["DIAS_POR_ETAPA"] * 100).where(df["DIAS_POR_ETAPA"] > 0).round(2)
        df["%_AVANCE"] = df["%_AVANCE"].fillna(0)

        df["%_DESVIACION"] = ((df["VAR_FECHA_CALCULADA"] - df["DIAS_POR_ETAPA"]) / df["DIAS_POR_ETAPA"] * 100)\
                                .where(df["DIAS_POR_ETAPA"] > 0)\
                                .clip(lower=0).round(2)
        df["%_DESVIACION"] = df["%_DESVIACION"].fillna(0)

        # Estado
        def clasificar_estado(row):
            if pd.isna(row["DIAS_POR_ETAPA"]) or row["DIAS_POR_ETAPA"] <= 0:
                return "SIN_TIEMPO"
            if row["VAR_FECHA_CALCULADA"] > row["DIAS_POR_ETAPA"]:
                return "DESVIADO"
            return "A_TIEMPO"
        df["ESTADO"] = df.apply(clasificar_estado, axis=1)

    # =============== POSIBLES DESVÍOS EN EL MES ===============
    with st.spinner("🕒 Calculando posibles desvíos del mes..."):
        hoy = df["FECHA_ACT_INVENTARIO"].dropna().max()
        if pd.isna(hoy):
            # si no hay fecha inventario, usar hoy del servidor
            hoy = pd.to_datetime(datetime.utcnow().date())
        ultimo_dia = calendar.monthrange(hoy.year, hoy.month)[1]
        dias_fin_mes = ultimo_dia - hoy.day
        df["DIAS_RESTANTES"] = df["DIAS_POR_ETAPA"] - df["VAR_FECHA_CALCULADA"]
        df["ALERTA_MES"] = df.apply(
            lambda x: "POSIBLE_DESVIO_EN_EL_MES" if (pd.notna(x["DIAS_RESTANTES"]) and x["DIAS_RESTANTES"] > 0 and x["DIAS_RESTANTES"] <= dias_fin_mes) else "",
            axis=1
        )

    # =============== ALERTAS VISUALES ===============
    desviados = df[df["ESTADO"] == "DESVIADO"]
    posibles = df[df["ALERTA_MES"] != ""]
    tiempo = df[df["ESTADO"] == "A_TIEMPO"]
    sin_dias = df[df["ESTADO"] == "SIN_TIEMPO"]

    if len(desviados): st.markdown(f"<div class='alerta rojo'>🚨 {len(desviados)} procesos desviados.</div>", unsafe_allow_html=True)
    if len(posibles): st.markdown(f"<div class='alerta amarillo'>⚠️ {len(posibles)} procesos podrían desviarse este mes.</div>", unsafe_allow_html=True)
    if len(tiempo): st.markdown(f"<div class='alerta verde'>✅ {len(tiempo)} procesos dentro del plazo.</div>", unsafe_allow_html=True)
    if len(sin_dias): st.markdown(f"<div class='alerta morado'>🧩 {len(sin_dias)} sin días definidos.</div>", unsafe_allow_html=True)

    # =============== RANKINGS ===============
    # Asegurar columnas 1-D para groupby
    df = asegurar_series_1d(df, ["ETAPA_JURIDICA","SUB-ETAPA_JURIDICA","DEUDOR"])

    # Capital por si falta
    if "CAPITAL_ACT" not in df.columns:
        df["CAPITAL_ACT"] = 0
    df["CAPITAL_ACT"] = pd.to_numeric(df["CAPITAL_ACT"], errors="coerce").fillna(0)

    st.write("🔎 Verificación agrupamiento:", df[["ETAPA_JURIDICA","SUB-ETAPA_JURIDICA","DEUDOR"]].head(10))

    with st.spinner("📊 Calculando rankings..."):
        # Cliente (Deudor) cuenta una sola vez por subetapa; si una operación desviada -> desviado
        df_ranking = df.groupby(["ETAPA_JURIDICA","SUB-ETAPA_JURIDICA","DEUDOR"], as_index=False).agg(
            DESVIADO=("ESTADO", lambda s: any(s == "DESVIADO")),
            CAPITAL=("CAPITAL_ACT","sum")
        )

        resumen = df_ranking.groupby(["ETAPA_JURIDICA","SUB-ETAPA_JURIDICA"], as_index=False).agg(
            CLIENTES_TOTALES=("DEUDOR","nunique"),
            CLIENTES_DESVIADOS=("DESVIADO","sum"),
            CAPITAL_TOTAL=("CAPITAL","sum")
        )
        # Evitar división por 0
        resumen["%_DESVIACION"] = (resumen["CLIENTES_DESVIADOS"] / resumen["CLIENTES_TOTALES"].replace(0, pd.NA) * 100).round(2)
        resumen["%_DESVIACION"] = resumen["%_DESVIACION"].fillna(0)
        resumen["NIVEL"] = resumen["%_DESVIACION"].apply(lambda x: "🔴 ALTA" if x > 70 else ("🟡 MEDIA" if x > 30 else "🟢 OK"))

        st.subheader("📈 Ranking por Subetapa Jurídica")
        st.dataframe(resumen.sort_values("%_DESVIACION", ascending=False), use_container_width=True)

        if not resumen.empty:
            fig = px.bar(
                resumen.sort_values("%_DESVIACION", ascending=False),
                x="%_DESVIACION", y="SUB-ETAPA_JURIDICA",
                color="NIVEL", text="CLIENTES_TOTALES",
                color_discrete_map={"🔴 ALTA":"red","🟡 MEDIA":"yellow","🟢 OK":"green"},
                title="Ranking de Subetapas Jurídicas"
            )
            fig.update_layout(template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

        ranking_etapas = resumen.groupby("ETAPA_JURIDICA", as_index=False).agg(
            CLIENTES_TOTALES=("CLIENTES_TOTALES","sum"),
            CLIENTES_DESVIADOS=("CLIENTES_DESVIADOS","sum"),
            CAPITAL_TOTAL=("CAPITAL_TOTAL","sum")
        )
        ranking_etapas["%_DESVIACION"] = (ranking_etapas["CLIENTES_DESVIADOS"] / ranking_etapas["CLIENTES_TOTALES"].replace(0, pd.NA) * 100).round(2)
        ranking_etapas["%_DESVIACION"] = ranking_etapas["%_DESVIACION"].fillna(0)
        ranking_etapas["NIVEL"] = ranking_etapas["%_DESVIACION"].apply(lambda x: "🔴 ALTA" if x > 70 else ("🟡 MEDIA" if x > 30 else "🟢 OK"))

        st.subheader("📊 Ranking por Etapa Jurídica")
        st.dataframe(ranking_etapas.sort_values("%_DESVIACION", ascending=False), use_container_width=True)

    # =============== DETALLES Y OTRAS VISTAS ===============
    columnas_detalle = [c for c in [
        "DEUDOR","ETAPA_JURIDICA","SUB-ETAPA_JURIDICA","ESTADO","CAPITAL_ACT","CIUDAD","JUZGADO",
        "DIAS_POR_ETAPA","VAR_FECHA_CALCULADA","%_AVANCE","%_DESVIACION","ALERTA_MES","DIAS_RESTANTES"
    ] if c in df.columns]
    clientes_sub = df[columnas_detalle]

    st.subheader("📙 Detalle Clientes–Subetapa")
    st.dataframe(clientes_sub, use_container_width=True)

    st.subheader("🕒 Próximos a vencer en el mes")
    proximos = df[df["ALERTA_MES"] != ""]
    cols_prox = [c for c in ["DEUDOR","ETAPA_JURIDICA","SUB-ETAPA_JURIDICA","DIAS_RESTANTES","CAPITAL_ACT","CIUDAD","JUZGADO"] if c in proximos.columns]
    st.dataframe(proximos[cols_prox], use_container_width=True)

    st.subheader("🚦 Semaforización por Etapa y Subetapa")
    if not resumen.empty:
        semaf = resumen.pivot(index="ETAPA_JURIDICA", columns="SUB-ETAPA_JURIDICA", values="%_DESVIACION")
        st.dataframe(semaf.style.background_gradient(cmap="RdYlGn_r"), use_container_width=True)
    else:
        st.info("No hay datos para semaforización.")

    # =============== EXPORT EXCEL ===============
    st.subheader("💾 Exportar resultados")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Base_Depurada")
        resumen.to_excel(writer, index=False, sheet_name="Ranking_Subetapas")
        ranking_etapas.to_excel(writer, index=False, sheet_name="Ranking_Etapas")
        clientes_sub.to_excel(writer, index=False, sheet_name="Clientes_Subetapa")
        proximos[cols_prox].to_excel(writer, index=False, sheet_name="Proximos_a_Vencer")
        if not resumen.empty:
            semaf.to_excel(writer, sheet_name="Semaforizacion_Etapas")
    output.seek(0)
    st.download_button("⬇️ Exportar Inventario Depurado",
                       data=output,
                       file_name="Inventario_Depurado_Completo.xlsx",
                       mime="application/vnd.ms-excel")

else:
    st.info("📤 Cargue los dos archivos para iniciar el análisis.")
