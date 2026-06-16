import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Doações - Anjos da Madrugada", layout="centered")

st.image("Anjos_da_Madrugada.jpg")
st.subheader("Ação Solidária: Preparo do Estrogonofe - 23/06/2026")

# --- AVISO DE PRAZO EM DESTAQUE ---
st.error("🚨 **ATENÇÃO - PRAZO DE ENTREGA:** Para a organização logística da ação, todas as doações deverão estar disponíveis na Igreja, impreterivelmente, até a **segunda-feira, 22/06/2026**.")

st.markdown("---")
# Função para conectar ao Google Sheets (com cache para não sobrecarregar a API)
@st.cache_resource
def conectar_planilha():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    # O Streamlit lê o JSON que colocaremos nas configurações secretas do servidor
    cred_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(cred_dict, scope)
    client = gspread.authorize(creds)
    return client.open("Arrecadacao_Estrogonofe") # Nome exato da sua planilha

try:
    planilha = conectar_planilha()
    aba_estoque = planilha.worksheet("Estoque")
    aba_historico = planilha.worksheet("Historico")
except Exception as e:
    st.error(f"Erro detalhado: {e}")
    st.stop()

# Lendo os dados da planilha
registros_estoque = aba_estoque.get_all_records()
estoque = {}

# Monta o dicionário de estoque e mapeia a linha da planilha para atualização futura
for i, linha in enumerate(registros_estoque):
    estoque[linha['Item']] = {
        "meta": float(linha['Meta']),
        "doado": float(linha['Doado']),
        "linha_planilha": i + 2 # +2 porque a linha 1 é o cabeçalho
    }

st.write("### 📝 Formulário de Doação")
st.write("Preencha o seu nome abaixo e digite a quantidade que deseja doar ao lado dos itens escolhidos.")

with st.form("form_multiplas_doacoes"):
    nome_doador = st.text_input("👤 Seu Nome completo:", placeholder="Ex: Maria da Silva")
    st.write("---")
    
    doacoes_atuais = {}
    
    for item, dados in estoque.items():
        falta = dados["meta"] - dados["doado"]
        
        col1, col2, col3 = st.columns([2, 1.2, 1.2], vertical_alignment="center")
        
        with col1:
            st.write(f"**{item}**")
        with col2:
            if falta > 0:
                st.info(f"Faltam: **{falta:.2f}**")
            else:
                st.success("✅ Completo!")
        with col3:
            if falta > 0:
                doacoes_atuais[item] = st.number_input(
                    "Qtd", min_value=0.0, max_value=float(falta), step=0.5, 
                    key=f"in_{item}", label_visibility="collapsed"
                )
            else:
                st.number_input(
                    "Qtd", value=0.0, disabled=True, 
                    key=f"in_{item}", label_visibility="collapsed"
                )
                
    st.write("---")
    submit_button = st.form_submit_button("💖 Confirmar Minhas Doações", width='stretch')

    if submit_button:
        if not nome_doador.strip():
            st.error("⚠️ Por favor, preencha o seu nome no topo do formulário.")
        elif sum(doacoes_atuais.values()) <= 0:
            st.warning("⚠️ Preencha a quantidade de pelo menos um item para doar.")
        else:
            with st.spinner('Registrando sua doação no sistema...'):
                # Atualiza a planilha
                for item, qtd in doacoes_atuais.items():
                    if qtd > 0:
                        # Grava na aba Histórico
                        data_atual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                        aba_historico.append_row([data_atual, nome_doador, item, qtd])
                        
                        # Atualiza a quantidade doada na aba Estoque
                        nova_qtd_doada = estoque[item]['doado'] + qtd
                        aba_estoque.update_cell(estoque[item]['linha_planilha'], 3, nova_qtd_doada)
                
                st.cache_resource.clear() # Limpa o cache para forçar a leitura dos novos dados
                st.success(f"🎉 Muito obrigado, {nome_doador}! Sua doação foi registrada com sucesso!")
                st.rerun()

st.write("---")
with st.expander("📊 Ver Resumo Completo das Arrecadações"):
    df = pd.DataFrame(registros_estoque)
    df['Status'] = df.apply(lambda row: "✅ Concluído" if (row['Meta'] - row['Doado']) <= 0 else f"Faltam {(row['Meta'] - row['Doado']):.2f}", axis=1)
    st.dataframe(df, width='stretch')
