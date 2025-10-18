# ============================================================
# ⚖️ COS JudicIA – Tablero Jurídico Inteligente (v2.2 Cloud)
# Autor: Andrés Cruz / Contacto Solutions LegalTech
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import io, calendar, unicodedata
from datetime import datetime

# ===============================
# 🖤 CONFIGURACIÓN GENERAL
# ===============================
st.set_page_config(page_title="⚖️ COS JudicIA – Tablero Jurídico Inteligente", layout="wide")

st.markdown("""
<style>
body, .stApp {background-color:#000!important;color:#FFF!important;}
h1,h2,h3,h4,h5,h6,p,div,label{color:#FFF!important;}
.alerta{font-size:18px;font-weight:600;padding:10px;border-radius:8px;
margin:10px 0;animation:pulse 2s infinite;}
@keyframes pulse{0%{opacity:1;}50%{opacity:.6;}100%{opacity:1;}}
.verde{color:#00FF00;}.amarillo{color:#FFFF00;}
.rojo{color:#FF0000;}.morado{color:#B388FF;}
table td,table th{color:#FFF!important;}
</style>
""", unsafe_allow_html=True)

st.title("⚖️ COS JudicIA – Tablero Jurídico Inteligente")
st.markdown("Cargue el **inventario mensual** y la **tabla de tiempos por etapa**:")

# ===============================
# 📂 CARGA DE ARCHIVOS
# ===============================
inventario_file = st.file_uploader("📂 Inventario mensual (.xlsx)", type=["xlsx"])
tiempos_file = st.file_uploader("⏱️ Tabla tiempos etapas (.xlsx)", type=["xlsx"])

# ===============================
# 🔧 NORMALIZADOR DE COLUMNAS
# ===============================
def normalizar_col(col):
    col = str(col).upper().strip()
    col = ''.join(c for c in unicodedata.normalize('NFD', col) if unicodedata.category(c) != 'Mn')
    col = col.replace(" ", "_")
    return col

# ============================================================
# 🚀 PROCESAMIENTO PRINCIPAL
# ============================================================
if inventario_file and tiempos_file:

    # === DETECCIÓN AUTOMÁTICA DE ENCABEZADO ===
    temp = pd.read_excel(inventario_file, header=None)
    header_row = None
    for i, row in temp.iterrows():
        fila = row.astype(str).str.upper()
        if any(fila.str.contains("DEUDOR|OPERACION|SUB-ETAPA|ETAPA", na=False)):
            header_row = i
            break

    if header_row is None:
        st.error("❌ No se pudo detectar encabezado válido en el inventario.")
        st.stop()

    df = pd.read_excel(inventario_file, header=header_row)
    tiempos = pd.read_excel(tiempos_file)

    # Normalizar encabezados
    df.columns = [normalizar_col(c) for c in df.columns]
    tiempos.columns = [normalizar_col(c) for c in tiempos.columns]

    st.write("📘 Columnas inventario detectadas:", list(df.columns))
    st.write("📗 Columnas tiempos detectadas:", list(tiempos.columns))

    # === CRUCE CON TABLA DE TIEMPOS ===
    df = df.merge(
        tiempos[['DESCRIPCION_DE_LA_SUBETAPA', 'DURACION_MAXIMA_EN_DIAS']],
        how='left',
        left_on='SUB-ETAPA_JURIDICA',
        right_on='DESCRIPCION_DE_LA_SUBETAPA'
    )

    if 'DIAS_POR_ETAPA' not in df.columns:
        df['DIAS_POR_ETAPA'] = None
    df['DIAS_POR_ETAPA'] = df['DIAS_POR_ETAPA'].fillna(df['DURACION_MAXIMA_EN_DIAS'])
    df.drop(columns=['DESCRIPCION_DE_LA_SUBETAPA', 'DURACION_MAXIMA_EN_DIAS'], inplace=True, errors='ignore')

    # === CONVERSIÓN DE FECHAS ===
    df['FECHA_ACT_INVENTARIO'] = pd.to_datetime(df.get('FECHA_ACT_INVENTARIO', None), errors='coerce')
    df['FECHA_ACT_ETAPA'] = pd.to_datetime(df.get('FECHA_ACT_ETAPA', None), errors='coerce')

    # === CÁLCULO DE VAR FECHA ===
    df['VAR_FECHA_CALCULADA'] = (df['FECHA_ACT_INVENTARIO'] - df['FECHA_ACT_ETAPA']).dt.days.clip(lower=0)

    # === PORCENTAJES ===
    df['%_AVANCE'] = (df['VAR_FECHA_CALCULADA'] / df['DIAS_POR_ETAPA'] * 100).round(2)
    df['%_DESVIACION'] = ((df['VAR_FECHA_CALCULADA'] - df['DIAS_POR_ETAPA']) / df['DIAS_POR_ETAPA'] * 100).clip(lower=0).round(2)

    # === CLASIFICACIÓN ESTADO ===
    def clasificar_estado(row):
        if pd.isna(row['DIAS_POR_ETAPA']):
            return 'SIN_TIEMPO'
        if row['VAR_FECHA_CALCULADA'] > row['DIAS_POR_ETAPA']:
            return 'DESVIADO'
        return 'A_TIEMPO'
    df['ESTADO'] = df.apply(clasificar_estado, axis=1)

    # === POSIBLES A VENCER ===
    today = df['FECHA_ACT_INVENTARIO'].max()
    ultimo_dia = calendar.monthrange(today.year, today.month)[1]
    dias_fin_mes = ultimo_dia - today.day
    df['DIAS_RESTANTES'] = df['DIAS_POR_ETAPA'] - df['VAR_FECHA_CALCULADA']
    df['ALERTA_MES'] = df.apply(
        lambda x: 'POSIBLE_DESVIO_EN_EL_MES' if (x['DIAS_RESTANTES'] <= dias_fin_mes and x['DIAS_RESTANTES'] > 0) else '',
        axis=1
    )

    # ===============================
    # ⚠️ ALERTAS
    # ===============================
    desviados = df[df['ESTADO'] == 'DESVIADO']
    posibles = df[df['ALERTA_MES'] != '']
    tiempo = df[df['ESTADO'] == 'A_TIEMPO']
    sin_dias = df[df['ESTADO'] == 'SIN_TIEMPO']

    if len(desviados) > 0:
        st.markdown(f"<div class='alerta rojo'>🚨 {len(desviados)} procesos desviados detectados.</div>", unsafe_allow_html=True)
    if len(posibles) > 0:
        st.markdown(f"<div class='alerta amarillo'>⚠️ {len(posibles)} procesos podrían desviarse este mes.</div>", unsafe_allow_html=True)
    if len(tiempo) > 0:
        st.markdown(f"<div class='alerta verde'>✅ {len(tiempo)} procesos dentro del plazo.</div>", unsafe_allow_html=True)
    if len(sin_dias) > 0:
        st.markdown(f"<div class='alerta morado'>🧩 {len(sin_dias)} registros sin días definidos.</div>", unsafe_allow_html=True)

    # ===============================
    # 📊 RANKING SUBETAPAS / ETAPAS
    # ===============================
    df_ranking = df.groupby(['ETAPA_JURIDICA','SUB-ETAPA_JURIDICA','DEUDOR']).agg(
        DESVIADO=('ESTADO', lambda s: any(s == 'DESVIADO')),
        CAPITAL=('CAPITAL_ACT','sum')
    ).reset_index()

    resumen = df_ranking.groupby(['ETAPA_JURIDICA','SUB-ETAPA_JURIDICA']).agg(
        CLIENTES_TOTALES=('DEUDOR','nunique'),
        CLIENTES_DESVIADOS=('DESVIADO','sum'),
        CAPITAL_TOTAL=('CAPITAL','sum')
    ).reset_index()

    resumen['%_DESVIACION'] = (resumen['CLIENTES_DESVIADOS']/resumen['CLIENTES_TOTALES']*100).round(2)
    resumen['NIVEL'] = resumen['%_DESVIACION'].apply(lambda x:'🔴 ALTA' if x>70 else('🟡 MEDIA' if x>30 else '🟢 OK'))

    st.subheader("📈 Ranking por Subetapa Jurídica")
    st.dataframe(resumen.sort_values('%_DESVIACION', ascending=False), use_container_width=True)

    fig = px.bar(
        resumen.sort_values('%_DESVIACION', ascending=False),
        x='%_DESVIACION', y='SUB-ETAPA_JURIDICA',
        color='NIVEL', text='CLIENTES_TOTALES',
        color_discrete_map={'🔴 ALTA':'red','🟡 MEDIA':'yellow','🟢 OK':'green'},
        title='Ranking de Subetapas Jurídicas'
    )
    fig.update_layout(template='plotly_dark')
    st.plotly_chart(fig, use_container_width=True)

    # --- Ranking de Etapas ---
    ranking_etapas = resumen.groupby('ETAPA_JURIDICA').agg(
        CLIENTES_TOTALES=('CLIENTES_TOTALES','sum'),
        CLIENTES_DESVIADOS=('CLIENTES_DESVIADOS','sum'),
        CAPITAL_TOTAL=('CAPITAL_TOTAL','sum')
    ).reset_index()
    ranking_etapas['%_DESVIACION'] = (ranking_etapas['CLIENTES_DESVIADOS']/ranking_etapas['CLIENTES_TOTALES']*100).round(2)
    ranking_etapas['NIVEL'] = ranking_etapas['%_DESVIACION'].apply(lambda x:'🔴 ALTA' if x>70 else('🟡 MEDIA' if x>30 else '🟢 OK'))

    st.subheader("📊 Ranking por Etapa Jurídica")
    st.dataframe(ranking_etapas.sort_values('%_DESVIACION', ascending=False), use_container_width=True)

    # --- Clientes por Subetapa ---
    clientes_sub = df[['DEUDOR','ETAPA_JURIDICA','SUB-ETAPA_JURIDICA','ESTADO',
                       'CAPITAL_ACT','CIUDAD','JUZGADO','DIAS_POR_ETAPA','VAR_FECHA_CALCULADA',
                       '%_AVANCE','%_DESVIACION']]

    st.subheader("📙 Detalle Clientes–Subetapa")
    st.dataframe(clientes_sub, use_container_width=True)

    # --- Próximos a vencer ---
    st.subheader("🕒 Próximos a vencer en el mes")
    proximos = df[df['ALERTA_MES'] != '']
    st.dataframe(proximos[['DEUDOR','ETAPA_JURIDICA','SUB-ETAPA_JURIDICA',
                           'DIAS_RESTANTES','CAPITAL_ACT','CIUDAD','JUZGADO']], use_container_width=True)

    # --- Semaforización ---
    st.subheader("🚦 Semaforización por Etapa y Subetapa")
    semaf = resumen.pivot(index='ETAPA_JURIDICA', columns='SUB-ETAPA_JURIDICA', values='%_DESVIACION')
    st.dataframe(semaf.style.background_gradient(cmap='RdYlGn_r'), use_container_width=True)

    # --- Exportación Excel ---
    st.subheader("💾 Exportar resultados")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Base_Depurada')
        resumen.to_excel(writer, index=False, sheet_name='Ranking_Subetapas')
        ranking_etapas.to_excel(writer, index=False, sheet_name='Ranking_Etapas')
        clientes_sub.to_excel(writer, index=False, sheet_name='Clientes_Subetapa')
        proximos.to_excel(writer, index=False, sheet_name='Proximos_a_Vencer')
        semaf.to_excel(writer, sheet_name='Semaforizacion_Etapas')
    output.seek(0)
    st.download_button("⬇️ Exportar Inventario Depurado",
                       data=output,
                       file_name="Inventario_Depurado_Completo.xlsx",
                       mime="application/vnd.ms-excel")

else:
    st.info("📤 Cargue los dos archivos para iniciar el análisis.")

