"""
=========================================================================
GERADOR DE EMAIL DE ENTREGA
=========================================================================
App que lê o documento de entrega (alvará, licença, projeto) em PDF,
extrai os dados com IA (Gemini) e monta um email HTML pronto pra
copiar e colar no Outlook/Gmail com a formatação preservada.

Aceita também arquivos DWG (que vão como anexo, sem leitura pela IA).
=========================================================================
"""

import os
import json
import html as html_lib
import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai


# =========================================================================
# CONFIGURAÇÕES (edite aqui se quiser personalizar)
# =========================================================================
MODEL_NAME = "gemini-2.5-flash"
ASSINATURA_PADRAO = "Equipe Comercial"


# =========================================================================
# CARREGAMENTO DA CHAVE DA API
# =========================================================================
def carregar_api_key() -> str:
    """
    Busca a chave da API em duas fontes, nessa ordem:
    1. Dos Secrets do Streamlit (produção / Streamlit Cloud)
    2. De variável de ambiente GEMINI_API_KEY (rodando local)
    """
    try:
        chave = st.secrets.get("GEMINI_API_KEY", "")
        if chave:
            return chave
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY", "")


# =========================================================================
# EXTRAÇÃO DE DADOS DO PDF COM GEMINI
# =========================================================================
def extrair_dados_documento(arquivo_pdf, api_key: str) -> dict:
    """
    Envia o PDF pro Gemini e pede pra ele extrair as informações
    necessárias pra montar o email, retornando um JSON estruturado.
    """
    genai.configure(api_key=api_key)
    modelo = genai.GenerativeModel(MODEL_NAME)

    prompt = """
Você é um assistente que lê documentos brasileiros de licenciamento e
projetos técnicos (alvarás, licenças, AVCB, projetos aprovados de
arquitetura, incêndio, publicidade, etc.) e extrai informações para
preparar um email formal de entrega ao cliente.

Leia o documento anexo e retorne APENAS um JSON válido (sem texto
adicional, sem markdown, sem ```json), com essa estrutura:

{
  "cliente": "nome do cliente ou empresa destinatária",
  "tipo_entrega": "tipo do documento (ex.: 'Alvará de Funcionamento', 'Projeto Executivo de Incêndio', 'Licença Publicitária')",
  "numero_protocolo": "número de protocolo/processo/registro (ou null)",
  "validade": "data de validade no formato DD/MM/AAAA (ou null)",
  "orgao_emissor": "órgão emissor (ex.: Prefeitura de São Paulo, Corpo de Bombeiros) ou null",
  "endereco_obra": "endereço do imóvel/obra mencionado (ou null)",
  "resumo_entrega": "1 frase curta dizendo o que está sendo entregue",
  "proximos_passos": ["até 3 ações", "que o cliente deve tomar", "depois de receber"],
  "assunto_email": "assunto sugerido pro email, no formato: 'Entrega: [Tipo] - [Cliente]'"
}

Para campos não encontrados, use null. Para 'proximos_passos', sugira
ações típicas pro tipo de documento (ex.: alvará → manter cópia visível
e renovar com antecedência; projeto de incêndio → contratar manutenção
periódica dos equipamentos).

Retorne APENAS o JSON, nada mais.
"""

    arquivo_pdf.seek(0)
    pdf_bytes = arquivo_pdf.read()

    resposta = modelo.generate_content(
        [{"mime_type": "application/pdf", "data": pdf_bytes}, prompt]
    )

    # Limpa cercas de markdown que o modelo possa ter incluído
    texto = resposta.text.strip()
    if texto.startswith("```"):
        # Remove primeira e última linha (```json e ```)
        linhas = texto.split("\n")
        if len(linhas) >= 3:
            texto = "\n".join(linhas[1:-1])
    texto = texto.strip()

    return json.loads(texto)


# =========================================================================
# MONTAGEM DO EMAIL HTML A PARTIR DOS DADOS
# =========================================================================
def montar_email_html(dados: dict, nomes_anexos: list, remetente: str) -> str:
    """
    Monta o HTML final do email usando um template fixo + os dados
    extraídos do documento. O HTML usa estilos inline (compatível
    com Outlook/Gmail) e fica pronto pra colar.
    """
    cliente = dados.get("cliente") or "Cliente"
    tipo = dados.get("tipo_entrega") or "documento"
    protocolo = dados.get("numero_protocolo")
    validade = dados.get("validade")
    orgao = dados.get("orgao_emissor")
    endereco = dados.get("endereco_obra")
    resumo = dados.get("resumo_entrega") or f"Segue em anexo o {tipo}."
    passos = dados.get("proximos_passos") or []

    # --- Bloco de detalhes técnicos (só inclui linhas preenchidas) ---
    linhas = []
    if protocolo:
        linhas.append(("Protocolo / processo", protocolo))
    if validade:
        linhas.append(("Validade", validade))
    if orgao:
        linhas.append(("Órgão emissor", orgao))
    if endereco:
        linhas.append(("Endereço", endereco))

    bloco_detalhes = ""
    if linhas:
        linhas_html = "".join(
            f"<tr>"
            f"<td style='padding:5px 12px 5px 0;color:#666;font-size:13px;'>{rotulo}</td>"
            f"<td style='padding:5px 0;font-size:13px;font-weight:600;color:#222;'>{valor}</td>"
            f"</tr>"
            for rotulo, valor in linhas
        )
        bloco_detalhes = (
            "<div style='background:#f6f6f1;border-radius:6px;padding:14px 16px;margin:16px 0;'>"
            "<p style='font-size:11px;color:#666;margin:0 0 8px;text-transform:uppercase;letter-spacing:0.6px;font-weight:600;'>Detalhes do documento</p>"
            f"<table style='width:100%;border-collapse:collapse;'>{linhas_html}</table>"
            "</div>"
        )

    # --- Bloco de próximos passos ---
    bloco_passos = ""
    if passos:
        itens = "".join(
            f"<li style='margin:6px 0;'>{p}</li>" for p in passos
        )
        bloco_passos = (
            "<p style='margin:18px 0 6px;font-weight:600;'>Próximos passos:</p>"
            f"<ul style='margin:0 0 16px;padding-left:22px;'>{itens}</ul>"
        )

    # --- Bloco de anexos ---
    bloco_anexos = ""
    if nomes_anexos:
        itens_anexos = "".join(
            f"<li style='margin:3px 0;font-size:13px;list-style:none;'>📎 {nome}</li>"
            for nome in nomes_anexos
        )
        bloco_anexos = (
            "<p style='margin:18px 0 6px;font-weight:600;font-size:14px;'>Arquivos em anexo:</p>"
            f"<ul style='margin:0 0 16px;padding-left:8px;'>{itens_anexos}</ul>"
        )

    # --- Montagem final ---
    html = (
        "<div style='font-family:Arial,Helvetica,sans-serif;color:#222;line-height:1.6;font-size:14px;max-width:620px;'>"
        f"<p style='margin:0 0 14px;'>Olá, equipe da <strong>{cliente}</strong>,</p>"
        f"<p style='margin:0 0 14px;'>{resumo}</p>"
        f"{bloco_detalhes}"
        f"{bloco_passos}"
        f"{bloco_anexos}"
        "<p style='margin:18px 0 4px;color:#555;font-size:13px;'>Qualquer dúvida, estamos à disposição.</p>"
        f"<p style='margin:14px 0 0;font-size:14px;'>Atenciosamente,<br><strong>{remetente}</strong></p>"
        "</div>"
    )
    return html


# =========================================================================
# BOTÃO QUE COPIA O HTML COMO RICH TEXT (formatação preservada no Outlook)
# =========================================================================
def botao_copiar(html_email: str, assunto: str):
    """
    Renderiza dois botões: um copia o ASSUNTO (texto simples) e outro
    copia o CORPO DO EMAIL como HTML rico — quando colado no Outlook/
    Gmail, a formatação vem junto (negritos, tabela, espaçamento).
    """
    # Escapa pra colocar dentro de <textarea> sem quebrar HTML
    html_para_textarea = html_lib.escape(html_email)
    assunto_para_textarea = html_lib.escape(assunto)

    componente = f"""
<div style="font-family:-apple-system,Arial,sans-serif;display:flex;flex-direction:column;gap:8px;">

  <button id="btn-assunto" onclick="copiarAssunto()" style="
    width:100%;padding:11px;font-size:14px;font-weight:500;
    background:#f0f2f6;color:#222;border:1px solid #d0d7de;
    border-radius:8px;cursor:pointer;
  ">
    📝 Copiar assunto
  </button>

  <button id="btn-corpo" onclick="copiarCorpo()" style="
    width:100%;padding:14px;font-size:15px;font-weight:600;
    background:#0066cc;color:white;border:none;
    border-radius:8px;cursor:pointer;
  ">
    📧 Copiar corpo do email (formatado)
  </button>

  <p id="status" style="text-align:center;font-size:12px;color:#666;margin:4px 0 0;">
    Cole no Outlook/Gmail com Ctrl+V — a formatação será preservada
  </p>

  <textarea id="conteudo-html" style="display:none;">{html_para_textarea}</textarea>
  <textarea id="conteudo-assunto" style="display:none;">{assunto_para_textarea}</textarea>

  <script>
    async function copiarAssunto() {{
      const t = document.getElementById('conteudo-assunto').value;
      try {{
        await navigator.clipboard.writeText(t);
        const b = document.getElementById('btn-assunto');
        b.innerHTML = '✅ Assunto copiado!';
        setTimeout(() => b.innerHTML = '📝 Copiar assunto', 2500);
      }} catch(e) {{
        document.getElementById('status').innerText = '⚠️ Não foi possível copiar. Tente manualmente.';
      }}
    }}

    async function copiarCorpo() {{
      const html = document.getElementById('conteudo-html').value;
      const textoPuro = html.replace(/<[^>]+>/g, '');
      try {{
        const blobHtml = new Blob([html], {{ type: 'text/html' }});
        const blobTxt = new Blob([textoPuro], {{ type: 'text/plain' }});
        await navigator.clipboard.write([
          new ClipboardItem({{ 'text/html': blobHtml, 'text/plain': blobTxt }})
        ]);
        const b = document.getElementById('btn-corpo');
        b.innerHTML = '✅ Copiado! Cole no Outlook agora';
        document.getElementById('status').innerText = 'Tudo pronto — abra um novo email e use Ctrl+V';
        setTimeout(() => b.innerHTML = '📧 Copiar corpo do email (formatado)', 3000);
      }} catch(e) {{
        document.getElementById('status').innerText = '⚠️ Seu navegador bloqueou. Copie do preview acima manualmente.';
      }}
    }}
  </script>
</div>
"""
    components.html(componente, height=180)


# =========================================================================
# INTERFACE STREAMLIT
# =========================================================================
st.set_page_config(
    page_title="Gerador de Email de Entrega",
    page_icon="📧",
    layout="centered",
)

st.title("📧 Gerador de Email de Entrega")
st.caption("Envie o documento, copie o email pronto pro cliente.")

api_key = carregar_api_key()

# ---- Barra lateral ------------------------------------------------------
with st.sidebar:
    st.header("ℹ️ Configurações")

    if api_key:
        st.success("✅ Chave da API configurada")
    else:
        st.warning("⚠️ Chave da API não configurada")
        api_key = st.text_input(
            "Chave da API Gemini",
            type="password",
            help="Configure GEMINI_API_KEY nos Secrets do Streamlit.",
        )

    st.markdown("---")
    remetente = st.text_input(
        "Seu nome / equipe",
        value=ASSINATURA_PADRAO,
        help="Aparece no rodapé do email após 'Atenciosamente'."
    )

    st.markdown("---")
    st.caption("📄 **PDF** — lido pela IA")
    st.caption("📐 **DWG** — incluído como anexo (não é lido)")
    st.caption(f"Modelo: `{MODEL_NAME}`")


# ---- Passo 1: Upload ----------------------------------------------------
st.markdown("### 1️⃣ Envie os arquivos")
arquivos = st.file_uploader(
    "Arraste o PDF do documento aqui. Pode incluir DWGs no mesmo upload.",
    type=["pdf", "dwg"],
    accept_multiple_files=True,
)

if arquivos and api_key:

    # Separa PDFs (a IA vai ler) dos demais (só viram referência no email)
    pdfs = [a for a in arquivos if a.name.lower().endswith(".pdf")]
    nomes_anexos = [a.name for a in arquivos]

    if not pdfs:
        st.error("⚠️ Você precisa enviar pelo menos 1 PDF pra IA conseguir ler o documento principal.")
        st.stop()

    # ---- Passo 2: Extração com cache na sessão --------------------------
    st.markdown("### 2️⃣ Confira os dados extraídos")
    st.caption("A IA leu o documento. Ajuste qualquer campo que esteja errado antes de gerar o email.")

    nome_pdf_atual = pdfs[0].name
    cache_valido = (
        "dados_extraidos" in st.session_state
        and st.session_state.get("ultimo_pdf") == nome_pdf_atual
    )

    if not cache_valido:
        with st.spinner("Lendo o documento com a IA..."):
            try:
                dados = extrair_dados_documento(pdfs[0], api_key)
                st.session_state.dados_extraidos = dados
                st.session_state.ultimo_pdf = nome_pdf_atual
            except json.JSONDecodeError:
                st.error("A IA retornou um formato inesperado. Tente de novo.")
                st.stop()
            except Exception as e:
                st.error(f"Erro ao processar: {e}")
                st.stop()

    dados = st.session_state.dados_extraidos

    # ---- Campos editáveis -----------------------------------------------
    col1, col2 = st.columns(2)
    with col1:
        dados["cliente"] = st.text_input(
            "Cliente",
            value=dados.get("cliente") or "",
        )
        dados["validade"] = st.text_input(
            "Validade",
            value=dados.get("validade") or "",
            placeholder="DD/MM/AAAA",
        )
        dados["orgao_emissor"] = st.text_input(
            "Órgão emissor",
            value=dados.get("orgao_emissor") or "",
        )
    with col2:
        dados["tipo_entrega"] = st.text_input(
            "Tipo de entrega",
            value=dados.get("tipo_entrega") or "",
        )
        dados["numero_protocolo"] = st.text_input(
            "Nº protocolo / processo",
            value=dados.get("numero_protocolo") or "",
        )
        dados["endereco_obra"] = st.text_input(
            "Endereço (se aplicável)",
            value=dados.get("endereco_obra") or "",
        )

    dados["assunto_email"] = st.text_input(
        "Assunto do email",
        value=dados.get("assunto_email") or "",
    )

    dados["resumo_entrega"] = st.text_area(
        "Resumo da entrega (1 frase)",
        value=dados.get("resumo_entrega") or "",
        height=70,
    )

    passos_texto = "\n".join(dados.get("proximos_passos") or [])
    passos_editados = st.text_area(
        "Próximos passos (um por linha)",
        value=passos_texto,
        height=90,
    )
    dados["proximos_passos"] = [
        p.strip() for p in passos_editados.split("\n") if p.strip()
    ]

    # ---- Passo 3: Preview + botões de cópia -----------------------------
    st.markdown("### 3️⃣ Email pronto pra enviar")

    html_email = montar_email_html(dados, nomes_anexos, remetente)
    assunto = dados.get("assunto_email") or ""

    st.markdown("**📨 Pré-visualização:**")
    st.markdown(
        f"<div style='border:1px solid #ddd;border-radius:8px;padding:18px;"
        f"background:white;margin-bottom:10px;'>{html_email}</div>",
        unsafe_allow_html=True,
    )

    botao_copiar(html_email, assunto)

    st.markdown("---")
    with st.expander("💡 Como usar"):
        st.markdown(
            """
            1. Clique em **📝 Copiar assunto** → abra o Outlook → cole no campo de assunto
            2. Clique em **📧 Copiar corpo do email** → cole no corpo da mensagem
            3. Anexe os arquivos manualmente no Outlook (PDF, DWG, etc.)
            4. Adicione os destinatários e envie
            """
        )

elif arquivos and not api_key:
    st.error("⚠️ Configure a chave da API Gemini na barra lateral antes de continuar.")

else:
    st.info("👆 Comece enviando o documento de entrega (PDF) acima.")
    st.markdown("---")
    st.markdown("##### Como funciona")
    st.markdown(
        """
        1. **Envia o PDF** da entrega (alvará, projeto aprovado, AVCB...)
        2. A **IA lê e extrai** automaticamente: cliente, tipo, validade, protocolo
        3. Você **confere/ajusta** os dados se algo estiver errado
        4. **Copia o email** pronto e cola no Outlook/Gmail — formatação preservada
        """
    )
