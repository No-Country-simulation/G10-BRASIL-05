# [0028] - Preservar login durante recarregamentos da aba

- **Data:** 2026-11-20
- **Autor(es):** @patrick-jala (via Assistente IA)
- **Status:** Aprovado

---

## 1. Por quê? (Contexto e Motivação)
O frontend guarda o token JWT somente no `st.session_state`. Ao recarregar a página, a sessão WebSocket do Streamlit é recriada e a pessoa precisa autenticar novamente.

## 2. Para quê? (Objetivo e Resultados Esperados)
Manter o login após recarregar a página na mesma aba, sem estender o prazo do token nem manter uma sessão aberta depois que a aba for fechada.

## 3. Como? (Implementação Técnica e Alternativas)
### Alternativas Consideradas:
- **Alternativa A (Descartada):** Colocar o JWT na URL ou query string; isso pode expor a credencial em histórico, logs e links compartilhados.
- **Alternativa B (Escolhida):** Guardar o access token no `sessionStorage` do navegador por meio de um componente local do Streamlit, revalidá-lo na API ao abrir a aplicação e limpar a credencial ao sair ou quando for rejeitada/expirada.

### Detalhamento da Solução:
O token permanece limitado à aba do navegador e mantém seu prazo original definido pela API. No recarregamento, o frontend recupera o token e chama `/auth/me`; só repõe a sessão do Streamlit se a API confirmar a conta. Logout e rejeição da sessão removem o token do armazenamento.

## 4. Onde? (Impacto no Código e Arquitetura)
- **Módulos / Diretórios Afetados:** `frontend/`, `DECISIONS/`.
- **Arquivos Criados / Modificados:** Componente browser storage, fluxo central da aplicação e autenticação/login.
- **Banco de Dados / Infra:** Sem alteração de banco, token, segredo ou prazo de expiração.

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** Recarregar a página não exige novo login enquanto o JWT for válido; fechar a aba encerra a persistência no navegador.
- **Riscos / Trade-offs:** `sessionStorage` pode ser acessado por JavaScript da própria origem; a proteção depende de evitar vulnerabilidades de script e a expiração continua sendo controlada pela API.
- **Validação / Testes:** Revisar restauração, renovação de perfil via API, logout e remoção do token inválido; não executar testes nesta solicitação.
