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

@st.cache_resource(ttl=10) # Limpa a conexão periodicamente para garantir dados frescos
def conectar_planilha():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    cred_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(cred_dict, scope)
    client = gspread.authorize(creds)
    return client.open("Arrecadacao_Estrogonofe")

try:
    planilha = conectar_planilha()
    aba_estoque = planilha.worksheet("Estoque")
    aba_historico = planilha.worksheet("Historico")
except Exception as e:
    st.error(f"Erro detalhado de conexão: {e}")
    st.stop()

# Leitura dos dados brutos
registros_estoque = aba_estoque.get_all_records()
registros_historico = aba_historico.get_all_records()

# --- NOVO NÚCLEO DE PROCESSAMENTO (Single Source of Truth) ---
# Se houver histórico, cria um DataFrame e soma as quantidades agrupadas pelo Item
if registros_historico:
    df_hist = pd.DataFrame(registros_historico)
    doacoes_por_item = df_hist.groupby('Item')['Quantidade'].sum().to_dict()
else:
    doacoes_por_item = {}

estoque = {}
for linha in registros_estoque:
    item = linha['Item']
    meta = float(linha['Meta'])
    doado = float(doacoes_por_item.get(item, 0.0)) 
    passo = float(linha['Passo']) # <-- Nova linha lendo a coluna da planilha
    
    estoque[item] = {
        "meta": meta,
        "doado": doado,
        "passo": passo # <-- Armazenando o passo no dicionário
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
                    "Qtd", min_value=0.0, max_value=float(falta), step=float(dados["passo"]), 
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
                linhas_para_adicionar = []
                data_atual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                
                for item, qtd in doacoes_atuais.items():
                    if qtd > 0:
                        linhas_para_adicionar.append([data_atual, nome_doador, item, qtd])
                
                # Envia todas as doações de uma vez só para a aba Histórico
                if linhas_para_adicionar:
                    aba_historico.append_rows(linhas_para_adicionar)
                
                st.cache_resource.clear()
                st.success(f"🎉 Muito obrigado, {nome_doador}! Sua doação foi registrada com sucesso!")
                st.rerun()

st.write("---")
with st.expander("📊 Ver Resumo Completo das Arrecadações"):
    dados_tabela = []
    for item, dados in estoque.items():
        restante = dados["meta"] - dados["doado"]
        dados_tabela.append({
            "Item": item,
            "Meta": dados["meta"],
            "Arrecadado": dados["doado"],
            "Status": "✅ Concluído" if restante <= 0 else f"Faltam {restante:.2f}"
        })
    df_resumo = pd.DataFrame(dados_tabela)
    st.dataframe(df_resumo, width='stretch')
