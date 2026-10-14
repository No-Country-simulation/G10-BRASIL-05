# Diretrizes de Uso de IA - Equipe G10-BRASIL-05

Este documento define as regras, restrições e padrões obrigatórios para qualquer agente de IA (Gemini, Claude, Cursor, Copilot, ChatGPT, etc.) ou desenvolvedor atuando no repositório **G10-BRASIL-05**.

---

## 1. Escopo e Papel da IA
- **SKILLS Obrigatórias:** Consultar e aplicar rigorosamente [Grill-Me Protocol](AGENTS/SKILLS/GRILL-ME.MD).
- **Modo de Operação:** Co-piloto e assistente técnico.
- **Autoridade Final:** Toda alteração de código deve ser validada e compreendida por um desenvolvedor humano da equipe antes de ser integrada à branch principal.
- **Registro de Decisões:** Toda decisão técnica/arquitetural tomada ao final da entrevista deve ser documentada antes de qualquer código ser escrito:
  - **Local:** `DECISIONS/<nome_do_usuario>/` (onde `<nome_do_usuario>` é obtido automaticamente via `git config user.name`).
  - **Nomenclatura:** Sequencial e descritiva (`0001-nome-da-decisao.md`).
  - **Estrutura:** Deve seguir estritamente o [DECISIONS/TEMPLATE.md](DECISIONS/TEMPLATE.md), respondendo obrigatoriamente: **Por quê**, **Para quê**, **Como** e **Onde**.
  - **Regra de Ouro:** *Documente a decisão primeiro e depois faça o código, nunca o inverso.* 


---

## 2. Linhas Vermelhas e Restrições Críticas (O que a IA NUNCA deve fazer)
- 🚫 **Segredos e Credenciais:** Jamais inserir, expor ou sugerir commit de chaves de API, senhas, tokens ou arquivos `.env`.
- 🚫 **Invenção de Dependências:** Não adicionar bibliotecas ou pacotes externos sem validação prévia de necessidade e licença (evitar inchaço desnecessário).
- 🚫 **Código sem Testes:** Qualquer função, endpoint ou lógica de negócio gerada por IA deve ser acompanhada dos respectivos testes automatizados.
- 🚫 **Refatorações Destrutivas:** Não reescrever módulos inteiros ou alterar padrões de arquitetura estabelecidos sem solicitação explícita do desenvolvedor.
- 🚫 **Alucinações de Contexto:** Não assumir regras de negócio inexistentes; em caso de dúvida, a IA deve parar e perguntar ao desenvolvedor.

---

## 3. Padrões de Código e Qualidade
- **Estilo:** Seguir estritamente os linters e formatadores configurados no projeto.
- **Tipagem:** Priorizar tipagem estática e interfaces explícitas.
- **Documentação:** Preservar comentários e docstrings existentes; documentar apenas decisões arquiteturais não óbvias.

---

## 4. Rastreabilidade e Fiscalização
- **Commits:** Mensagens de commit claras e sem textos genéricos gerados automaticamente.
- **Revisão Humana:** O autor do Pull Request é 100% responsável pelo código gerado por IA que submeter.
