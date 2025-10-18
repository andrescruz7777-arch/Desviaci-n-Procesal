# ============================================================
# ⚖️ COS JudicIA – Tablero Jurídico Inteligente (v2 Cloud)
# Autor: Andrés Cruz / Contacto Solutions LegalTech
# Descripción: BI jurídico completo con depuración, ranking,
# próximos a vencer, semaforización y exportación Excel.
# ============================================================

# --- Librerías ---
import streamlit as st
import pandas as pd
import plotly.express as px
import io, calendar
from datetime import datetime

# --- Configuración general ---
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

# --- Carga de archivos ---
inventario_file = st.file_uploader("📂 Inventario mensual (.xlsx)", type=["xlsx"])
tiempos_file = st.file_uploader("⏱️ Tabla tiempos etapas (.xlsx)", type=["xlsx"])

if inventario_file and tiempos_file:
    df = pd.read_excel(inventario_file)
    tiempos = pd.read_excel(tiempos_file)
    df.columns = df.columns.str.strip()
    tiempos.columns = tiempos.columns.str.strip()

    # === Cruce y depuración ===
    df = df.merge(
        tiempos[['Descripción de la Subetapa', 'Duración Máxima en Días']],
        how='left',
        left_on='SUB-ETAPA JURIDICA',
        right_on='Descripción de la Subetapa'
    )
    df['DIAS POR ETAPA'] = df['DIAS POR ETAPA'].fillna(df['Duración Máxima en Días'])
    df.drop(columns=['Descripción de la Subetapa', 'Duración Máxima en Días'], inplace=True, errors='ignore')

    df['FECHA ACT INVENTARIO'] = pd.to_datetime(df['FECHA ACT INVENTARIO'], errors='coerce')
    df['FECHA ACT ETAPA'] = pd.to_datetime(df['FECHA ACT ETAPA'], errors='coerce')
    df['VAR FECHA CALCULADA'] = (df['FECHA ACT INVENTARIO'] - df['FECHA ACT ETAPA']).dt.days.clip(lower=0)

    df['% AVANCE'] = (df['VAR FECHA CALCULADA'] / df['DIAS POR ETAPA'] * 100).round(2)
    df['% DESVIACION'] = ((df['VAR FECHA CALCULADA'] - df['DIAS POR ETAPA']) / df['DIAS POR ETAPA'] * 100).clip(lower=0).round(2)

    def clasificar_estado(row):
        if row['VAR FECHA CALCULADA'] > row['DIAS POR ETAPA']:
            return 'DESVIADO'
        return 'A TIEMPO'
    df['ESTADO'] = df.apply(clasificar_estado, axis=1)

    # === Próximos a vencer ===
    today = df['FECHA ACT INVENTARIO'].max()
    ultimo_dia = calendar.monthrange(today.year, today.month)[1]
    dias_fin_mes = ultimo_dia - today.day
    df['DIAS_RESTANTES'] = df['DIAS POR ETAPA'] - df['VAR FECHA CALCULADA']
    df['ALERTA_MES'] = df.apply(
        lambda x: 'POSIBLE DESVÍO EN EL MES' if (x['DIAS_RESTANTES'] <= dias_fin_mes and x['DIAS_RESTANTES'] > 0) else '',
        axis=1
    )

    # === Alertas ===
    desviados = df[df['ESTADO'] == 'DESVIADO']
    posibles = df[df['ALERTA_MES'] != '']
    tiempo = df[df['ESTADO'] == 'A TIEMPO']
    sin_dias = df[df['DIAS POR ETAPA'].isna()]
    if len(desviados) > 0:
        st.markdown(f"<div class='alerta rojo'>🚨 {len(desviados)} procesos desviados detectados.</div>", unsafe_allow_html=True)
    if len(posibles) > 0:
        st.markdown(f"<div class='alerta amarillo'>⚠️ {len(posibles)} procesos podrían desviarse este mes.</div>", unsafe_allow_html=True)
    if len(tiempo) > 0:
        st.markdown(f"<div class='alerta verde'>✅ {len(tiempo)} procesos dentro del plazo.</div>", unsafe_allow_html=True)
    if len(sin_dias) > 0:
        st.markdown(f"<div class='alerta morado'>🧩 {len(sin_dias)} registros sin días definidos.</div>", unsafe_allow_html=True)

    # === Ranking por Subetapas y Etapas ===
    df_ranking = df.groupby(['ETAPA JURIDICA','SUB-ETAPA JURIDICA','Deudor']).agg(
        desviado=('ESTADO', lambda s: any(s == 'DESVIADO')),
        capital=('Capital Act','sum')
    ).reset_index()

    resumen = df_ranking.groupby(['ETAPA JURIDICA','SUB-ETAPA JURIDICA']).agg(
        Clientes_Totales=('Deudor','nunique'),
        Clientes_Desviados=('desviado','sum'),
        Capital_Total=('capital','sum')
    ).reset_index()
    resumen['% Desviacion'] = (resumen['Clientes_Desviados']/resumen['Clientes_Totales']*100).round(2)
    resumen['Nivel'] = resumen['% Desviacion'].apply(lambda x: '🔴 Alta' if x>70 else ('🟡 Media' if x>30 else '🟢 OK'))

    st.subheader("📈 Ranking por Subetapa Jurídica")
    st.dataframe(resumen.sort_values('% Desviacion', ascending=False), use_container_width=True)

    fig = px.bar(resumen.sort_values('% Desviacion', ascending=False),
                 x='% Desviacion', y='SUB-ETAPA JURIDICA',
                 color='Nivel', text='Clientes_Totales',
                 color_discrete_map={'🔴 Alta':'red','🟡 Media':'yellow','🟢 OK':'green'},
                 title='Ranking de Subetapas Jurídicas')
    fig.update_layout(template='plotly_dark')
    st.plotly_chart(fig, use_container_width=True)

    # --- Ranking de Etapas ---
    ranking_etapas = resumen.groupby('ETAPA JURIDICA').agg(
        Clientes_Totales=('Clientes_Totales','sum'),
        Clientes_Desviados=('Clientes_Desviados','sum'),
        Capital_Total=('Capital_Total','sum')
    ).reset_index()
    ranking_etapas['% Desviacion'] = (ranking_etapas['Clientes_Desviados']/ranking_etapas['Clientes_Totales']*100).round(2)
    ranking_etapas['Nivel'] = ranking_etapas['% Desviacion'].apply(lambda x:'🔴 Alta' if x>70 else('🟡 Media' if x>30 else '🟢 OK'))

    st.subheader("📊 Ranking por Etapa Jurídica")
    st.dataframe(ranking_etapas.sort_values('% Desviacion', ascending=False), use_container_width=True)

    # --- Clientes por Subetapa ---
    clientes_sub = df[['Deudor','ETAPA JURIDICA','SUB-ETAPA JURIDICA','ESTADO',
                       'Capital Act','Ciudad','Juzgado','DIAS POR ETAPA','VAR FECHA CALCULADA',
                       '% AVANCE','% DESVIACION']]
    st.subheader("📙 Detalle Clientes–Subetapa")
    st.dataframe(clientes_sub, use_container_width=True)

    # --- Próximos a vencer ---
    st.subheader("🕒 Próximos a vencer en el mes")
    proximos = df[df['ALERTA_MES'] != '']
    st.dataframe(proximos[['Deudor','ETAPA JURIDICA','SUB-ETAPA JURIDICA',
                           'DIAS_RESTANTES','Capital Act','Ciudad','Juzgado']], use_container_width=True)

    # --- Semaforización ---
    st.subheader("🚦 Semaforización por Etapa y Subetapa")
    semaf = resumen.pivot(index='ETAPA JURIDICA', columns='SUB-ETAPA JURIDICA', values='% Desviacion')
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
