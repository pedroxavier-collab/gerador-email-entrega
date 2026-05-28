"""
=========================================================================
GERADOR DE EMAIL DE ENTREGA — EXPANZIO
=========================================================================
App que lê o documento de entrega (alvará, licença, projeto) em PDF,
extrai os dados com IA (Gemini) e monta um email HTML com a identidade
visual da Expanzio, pronto pra copiar e colar no Outlook/Gmail.

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
# IDENTIDADE VISUAL — EXPANZIO
# =========================================================================
COR_LARANJA = "#FB4710"
COR_PRETO   = "#000000"
COR_BRANCO  = "#FFFFFF"
COR_CINZA   = "#666666"
COR_FUNDO_CLARO = "#F6F6F1"  # fundo da caixa de detalhes no email

# Logo da Expanzio embutido em base64 (vai junto no email, sem precisar hospedar)
LOGO_BASE64 = "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"

MODEL_NAME = "gemini-2.5-flash"
ASSINATURA_PADRAO = "Equipe Expanzio"


# =========================================================================
# CARREGAMENTO DA CHAVE DA API
# =========================================================================
def carregar_api_key() -> str:
    """
    Busca a chave da API em duas fontes:
    1. Secrets do Streamlit (produção / Streamlit Cloud)
    2. Variável de ambiente GEMINI_API_KEY (rodando local)
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
Você é um assistente da Expanzio, que lê documentos brasileiros de
licenciamento e projetos técnicos (alvarás, licenças, AVCB, projetos
aprovados de arquitetura, incêndio, publicidade, etc.) e extrai
informações pra preparar um email formal de entrega ao cliente.

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
  "assunto_email": "assunto sugerido pro email, no formato: 'Expanzio | Entrega: [Tipo] - [Cliente]'"
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
        linhas = texto.split("\n")
        if len(linhas) >= 3:
            texto = "\n".join(linhas[1:-1])
    texto = texto.strip()

    return json.loads(texto)


# =========================================================================
# MONTAGEM DO EMAIL HTML — IDENTIDADE EXPANZIO
# =========================================================================
def montar_email_html(dados: dict, nomes_anexos: list, remetente: str) -> str:
    """
    Monta o HTML do email usando estrutura de tabelas (compatível com
    Outlook) e a identidade visual da Expanzio aplicada nos detalhes.
    """
    cliente   = dados.get("cliente") or "Cliente"
    tipo      = dados.get("tipo_entrega") or "documento"
    protocolo = dados.get("numero_protocolo")
    validade  = dados.get("validade")
    orgao     = dados.get("orgao_emissor")
    endereco  = dados.get("endereco_obra")
    resumo    = dados.get("resumo_entrega") or f"Segue em anexo o {tipo}."
    passos    = dados.get("proximos_passos") or []

    # ---- Bloco de detalhes técnicos (só com campos preenchidos) -------
    linhas = []
    if protocolo: linhas.append(("Protocolo / processo", protocolo))
    if validade:  linhas.append(("Validade", validade))
    if orgao:     linhas.append(("Órgão emissor", orgao))
    if endereco:  linhas.append(("Endereço", endereco))

    bloco_detalhes = ""
    if linhas:
        linhas_html = "".join(
            f"<tr>"
            f"<td style='padding:6px 14px 6px 0;color:{COR_CINZA};font-size:13px;'>{rotulo}</td>"
            f"<td style='padding:6px 0;font-size:13px;font-weight:600;color:{COR_PRETO};'>{valor}</td>"
            f"</tr>"
            for rotulo, valor in linhas
        )
        bloco_detalhes = (
            f"<table cellpadding='0' cellspacing='0' border='0' width='100%' "
            f"style='border-collapse:collapse;margin:20px 0;'>"
            f"<tr><td style='background:{COR_FUNDO_CLARO};border-left:4px solid {COR_LARANJA};padding:14px 18px;'>"
            f"<p style='font-size:11px;color:{COR_LARANJA};margin:0 0 10px;text-transform:uppercase;"
            f"letter-spacing:1.2px;font-weight:700;font-family:Arial,sans-serif;'>Detalhes do documento</p>"
            f"<table cellpadding='0' cellspacing='0' border='0' style='width:100%;border-collapse:collapse;'>"
            f"{linhas_html}</table>"
            f"</td></tr></table>"
        )

    # ---- Próximos passos (com marcadores laranja personalizados) ------
    bloco_passos = ""
    if passos:
        itens = "".join(
            f"<tr><td valign='top' style='padding:5px 10px 5px 0;color:{COR_LARANJA};"
            f"font-size:14px;font-weight:700;width:18px;'>▸</td>"
            f"<td style='padding:5px 0;font-size:14px;color:{COR_PRETO};'>{p}</td></tr>"
            for p in passos
        )
        bloco_passos = (
            f"<p style='margin:24px 0 8px;font-weight:700;color:{COR_PRETO};font-size:14px;'>"
            f"Próximos passos</p>"
            f"<table cellpadding='0' cellspacing='0' border='0' style='border-collapse:collapse;'>"
            f"{itens}</table>"
        )

    # ---- Anexos -------------------------------------------------------
    bloco_anexos = ""
    if nomes_anexos:
        itens_anexos = "".join(
            f"<tr><td valign='top' style='padding:4px 8px 4px 0;color:{COR_CINZA};"
            f"font-size:13px;width:18px;'>📎</td>"
            f"<td style='padding:4px 0;font-size:13px;color:{COR_PRETO};'>{nome}</td></tr>"
            for nome in nomes_anexos
        )
        bloco_anexos = (
            f"<p style='margin:24px 0 8px;font-weight:700;color:{COR_PRETO};font-size:14px;'>"
            f"Arquivos em anexo</p>"
            f"<table cellpadding='0' cellspacing='0' border='0' style='border-collapse:collapse;'>"
            f"{itens_anexos}</table>"
        )

    # ---- Estrutura completa (header preto + corpo + rodapé) -----------
    html = f"""
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="border-collapse:collapse;background:{COR_BRANCO};font-family:Arial,Helvetica,sans-serif;">
<tr>
  <td align="center" style="padding:0;">
    <table cellpadding="0" cellspacing="0" border="0" width="620" style="border-collapse:collapse;max-width:620px;">

      <!-- HEADER: faixa preta com logo Expanzio -->
      <tr>
        <td style="background:{COR_PRETO};padding:24px 32px;">
          <img src="data:image/png;base64,{LOGO_BASE64}" alt="Expanzio" width="180" height="55" style="display:block;border:0;outline:none;text-decoration:none;" />
        </td>
      </tr>

      <!-- Faixa laranja divisora -->
      <tr><td style="background:{COR_LARANJA};height:4px;line-height:4px;font-size:0;">&nbsp;</td></tr>

      <!-- CORPO DO EMAIL -->
      <tr>
        <td style="padding:32px;background:{COR_BRANCO};color:{COR_PRETO};font-size:14px;line-height:1.65;">

          <p style="margin:0 0 16px;color:{COR_PRETO};">
            Olá, equipe da <strong>{cliente}</strong>,
          </p>

          <p style="margin:0 0 16px;color:{COR_PRETO};">
            {resumo}
          </p>

          {bloco_detalhes}

          {bloco_passos}

          {bloco_anexos}

          <p style="margin:28px 0 0;color:{COR_CINZA};font-size:13px;">
            Qualquer dúvida, estamos à disposição.
          </p>

          <!-- Assinatura -->
          <table cellpadding="0" cellspacing="0" border="0" style="margin-top:24px;border-top:1px solid #e5e5e5;width:100%;border-collapse:collapse;">
            <tr><td style="padding-top:16px;">
              <p style="margin:0;font-size:14px;color:{COR_PRETO};font-weight:700;">{remetente}</p>
              <p style="margin:4px 0 0;font-size:12px;color:{COR_CINZA};">Expanzio</p>
            </td></tr>
          </table>

        </td>
      </tr>

      <!-- RODAPÉ: faixa preta -->
      <tr>
        <td style="background:{COR_PRETO};padding:16px 32px;text-align:center;">
          <p style="margin:0;color:{COR_CINZA};font-size:11px;letter-spacing:0.5px;">
            EXPANZIO &nbsp;·&nbsp; este email contém informações da entrega oficial do documento
          </p>
        </td>
      </tr>

    </table>
  </td>
</tr>
</table>
"""
    return html.strip()


# =========================================================================
# BOTÃO QUE COPIA O HTML COMO RICH TEXT (formatação preservada no Outlook)
# =========================================================================
def botao_copiar(html_email: str, assunto: str):
    """Renderiza botões pra copiar o assunto e o corpo do email."""
    html_para_textarea = html_lib.escape(html_email)
    assunto_para_textarea = html_lib.escape(assunto)

    componente = f"""
<div style="font-family:-apple-system,Arial,sans-serif;display:flex;flex-direction:column;gap:10px;">

  <button id="btn-assunto" onclick="copiarAssunto()" style="
    width:100%;padding:12px;font-size:14px;font-weight:600;
    background:transparent;color:{COR_BRANCO};
    border:1.5px solid {COR_LARANJA};border-radius:6px;cursor:pointer;
    letter-spacing:0.3px;
  ">
    📝 COPIAR ASSUNTO
  </button>

  <button id="btn-corpo" onclick="copiarCorpo()" style="
    width:100%;padding:16px;font-size:15px;font-weight:700;
    background:{COR_LARANJA};color:{COR_BRANCO};border:none;
    border-radius:6px;cursor:pointer;letter-spacing:0.5px;
  ">
    📧 COPIAR CORPO DO EMAIL
  </button>

  <p id="status" style="text-align:center;font-size:12px;color:{COR_CINZA};margin:4px 0 0;">
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
        b.innerHTML = '✅ ASSUNTO COPIADO';
        setTimeout(() => b.innerHTML = '📝 COPIAR ASSUNTO', 2500);
      }} catch(e) {{
        document.getElementById('status').innerText = '⚠️ Não foi possível copiar.';
      }}
    }}

    async function copiarCorpo() {{
      const html = document.getElementById('conteudo-html').value;
      const textoPuro = html.replace(/<[^>]+>/g, ' ').replace(/\\s+/g, ' ').trim();
      try {{
        const blobHtml = new Blob([html], {{ type: 'text/html' }});
        const blobTxt = new Blob([textoPuro], {{ type: 'text/plain' }});
        await navigator.clipboard.write([
          new ClipboardItem({{ 'text/html': blobHtml, 'text/plain': blobTxt }})
        ]);
        const b = document.getElementById('btn-corpo');
        b.innerHTML = '✅ COPIADO — COLE NO OUTLOOK';
        document.getElementById('status').innerText = 'Tudo pronto. Abra um novo email e use Ctrl+V';
        setTimeout(() => b.innerHTML = '📧 COPIAR CORPO DO EMAIL', 3500);
      }} catch(e) {{
        document.getElementById('status').innerText = '⚠️ Seu navegador bloqueou. Copie do preview manualmente.';
      }}
    }}
  </script>
</div>
"""
    components.html(componente, height=200)


# =========================================================================
# CSS CUSTOMIZADO DO STREAMLIT (acentos finais da identidade)
# =========================================================================
def aplicar_css_expanzio():
    """Pequenos ajustes de CSS pra deixar a interface 100% Expanzio."""
    st.markdown(
        f"""
        <style>
        /* Botões em laranja */
        .stButton > button {{
            background-color: {COR_LARANJA} !important;
            color: {COR_BRANCO} !important;
            border: none !important;
            font-weight: 600 !important;
        }}
        .stButton > button:hover {{
            background-color: #d63a08 !important;
            color: {COR_BRANCO} !important;
        }}
        /* Inputs com borda laranja no focus */
        .stTextInput input:focus, .stTextArea textarea:focus {{
            border-color: {COR_LARANJA} !important;
            box-shadow: 0 0 0 1px {COR_LARANJA} !important;
        }}
        /* Título com cor da marca */
        h1 {{
            color: {COR_BRANCO} !important;
            letter-spacing: 1px;
        }}
        /* Linha laranja embaixo do título */
        .titulo-expanzio {{
            border-bottom: 3px solid {COR_LARANJA};
            padding-bottom: 12px;
            margin-bottom: 8px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================================
# INTERFACE STREAMLIT
# =========================================================================
st.set_page_config(
    page_title="Expanzio — Gerador de Email",
    page_icon="📧",
    layout="centered",
)

aplicar_css_expanzio()

# Cabeçalho com a marca
st.markdown(
    f"""
    <div class="titulo-expanzio">
        <p style="color:{COR_LARANJA};font-size:12px;font-weight:700;letter-spacing:3px;margin:0;">EXPANZIO</p>
        <h1 style="margin:4px 0 0;font-size:28px;">📧 Gerador de Email de Entrega</h1>
    </div>
    <p style="color:{COR_CINZA};font-size:14px;margin:8px 0 24px;">
        Envie o documento da entrega e copie o email pronto pro cliente.
    </p>
    """,
    unsafe_allow_html=True,
)

api_key = carregar_api_key()

# ---- Barra lateral ------------------------------------------------------
with st.sidebar:
    st.markdown(
        f"<p style='color:{COR_LARANJA};font-size:11px;font-weight:700;letter-spacing:2px;margin:0;'>EXPANZIO</p>"
        f"<h3 style='margin:4px 0 16px;color:{COR_BRANCO};'>Configurações</h3>",
        unsafe_allow_html=True,
    )

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
        "Seu nome",
        value=ASSINATURA_PADRAO,
        help="Aparece na assinatura do email."
    )

    st.markdown("---")
    st.caption("📄 **PDF** — lido pela IA")
    st.caption("📐 **DWG** — incluído como anexo")
    st.caption(f"Modelo: `{MODEL_NAME}`")


# ---- Passo 1: Upload ----------------------------------------------------
st.markdown(f"<h3 style='color:{COR_LARANJA};font-size:14px;letter-spacing:1.5px;margin:24px 0 8px;'>1 · ENVIE OS ARQUIVOS</h3>", unsafe_allow_html=True)
arquivos = st.file_uploader(
    "Arraste o PDF do documento. Pode incluir DWGs no mesmo upload.",
    type=["pdf", "dwg"],
    accept_multiple_files=True,
)

if arquivos and api_key:

    pdfs = [a for a in arquivos if a.name.lower().endswith(".pdf")]
    nomes_anexos = [a.name for a in arquivos]

    if not pdfs:
        st.error("⚠️ Envie pelo menos 1 PDF — a IA precisa dele pra extrair os dados.")
        st.stop()

    # ---- Passo 2: Extração com cache na sessão --------------------------
    st.markdown(f"<h3 style='color:{COR_LARANJA};font-size:14px;letter-spacing:1.5px;margin:32px 0 8px;'>2 · CONFIRA OS DADOS EXTRAÍDOS</h3>", unsafe_allow_html=True)
    st.caption("Ajuste qualquer campo que esteja errado antes de gerar o email.")

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

    col1, col2 = st.columns(2)
    with col1:
        dados["cliente"] = st.text_input("Cliente", value=dados.get("cliente") or "")
        dados["validade"] = st.text_input("Validade", value=dados.get("validade") or "", placeholder="DD/MM/AAAA")
        dados["orgao_emissor"] = st.text_input("Órgão emissor", value=dados.get("orgao_emissor") or "")
    with col2:
        dados["tipo_entrega"] = st.text_input("Tipo de entrega", value=dados.get("tipo_entrega") or "")
        dados["numero_protocolo"] = st.text_input("Nº protocolo / processo", value=dados.get("numero_protocolo") or "")
        dados["endereco_obra"] = st.text_input("Endereço (se aplicável)", value=dados.get("endereco_obra") or "")

    dados["assunto_email"] = st.text_input("Assunto do email", value=dados.get("assunto_email") or "")
    dados["resumo_entrega"] = st.text_area("Resumo da entrega (1 frase)", value=dados.get("resumo_entrega") or "", height=70)

    passos_texto = "\n".join(dados.get("proximos_passos") or [])
    passos_editados = st.text_area("Próximos passos (um por linha)", value=passos_texto, height=90)
    dados["proximos_passos"] = [p.strip() for p in passos_editados.split("\n") if p.strip()]

    # ---- Passo 3: Preview + botões --------------------------------------
    st.markdown(f"<h3 style='color:{COR_LARANJA};font-size:14px;letter-spacing:1.5px;margin:32px 0 8px;'>3 · EMAIL PRONTO PRA ENVIAR</h3>", unsafe_allow_html=True)

    html_email = montar_email_html(dados, nomes_anexos, remetente)
    assunto = dados.get("assunto_email") or ""

    st.caption("📨 Pré-visualização — assim que vai chegar pro cliente:")
    st.markdown(
        f"<div style='border:1px solid #333;border-radius:8px;padding:0;"
        f"background:white;margin:8px 0 16px;overflow:hidden;'>{html_email}</div>",
        unsafe_allow_html=True,
    )

    botao_copiar(html_email, assunto)

    with st.expander("💡 Como usar"):
        st.markdown(
            """
            1. Clique em **COPIAR ASSUNTO** → abra o Outlook → cole no campo de assunto
            2. Clique em **COPIAR CORPO DO EMAIL** → cole no corpo da mensagem
            3. Anexe os arquivos manualmente (PDF, DWG, etc.)
            4. Adicione os destinatários e envie
            """
        )

elif arquivos and not api_key:
    st.error("⚠️ Configure a chave da API Gemini na barra lateral antes de continuar.")

else:
    st.info("👆 Comece enviando o documento de entrega (PDF) acima.")
    st.markdown(
        f"""
        <div style='margin-top:24px;padding:20px;border-left:3px solid {COR_LARANJA};background:#1a1a1a;border-radius:4px;'>
        <p style='color:{COR_LARANJA};font-size:11px;font-weight:700;letter-spacing:2px;margin:0 0 12px;'>COMO FUNCIONA</p>
        <ol style='color:{COR_BRANCO};margin:0;padding-left:20px;line-height:1.8;'>
          <li>Envia o <strong>PDF</strong> da entrega (alvará, projeto aprovado, AVCB…)</li>
          <li>A <strong>IA lê e extrai</strong> cliente, tipo, validade e protocolo automaticamente</li>
          <li>Você <strong>confere e ajusta</strong> qualquer campo se necessário</li>
          <li><strong>Copia e cola</strong> no Outlook — formatação Expanzio preservada</li>
        </ol>
        </div>
        """,
        unsafe_allow_html=True,
    )
