# [0030] - Organização das responsabilidades do frontend

- **Data:** 2026-11-21
- **Autor(es):** @patrick-jala (via Assistente IA)
- **Status:** Aprovado

---

## 1. Por quê? (Contexto e Motivação)

Páginas extensas misturam layout, estilos, estado de sessão, preparação de dados e chamadas à API. Isso dificulta localizar mudanças e revisar o comportamento visual. A comunicação HTTP também está distribuída entre módulos com nomes diferentes.

## 2. Para quê? (Objetivo e Resultados Esperados)

Separar apresentação, estilos, preparação de dados e integração HTTP, mantendo a navegação multipage do Streamlit e os contratos existentes. A reorganização deve reduzir o tamanho e a responsabilidade dos módulos mais extensos sem alterar regras de negócio.

## 3. Como? (Implementação Técnica e Alternativas)

### Alternativas Consideradas:
- **Alternativa A (Descartada):** Trocar Streamlit ou adotar uma arquitetura de frontend diferente. Isso aumentaria o escopo e contrariaria a arquitetura já definida.
- **Alternativa B (Escolhida):** Preservar Streamlit, manter entradas pequenas em `pages/`, organizar implementações por tela em `telas/<tela>/index.py`, mover regras visuais para `style.css`, e concentrar transporte HTTP em `api/` com módulos por domínio. Manter adaptadores temporários nos caminhos antigos quando necessário para compatibilidade.

### Detalhamento da Solução:

- As páginas em `pages/` permanecem como pontos de entrada reconhecidos pelo Streamlit.
- Cada tela carrega seu CSS a partir de arquivo próprio.
- A lógica de apresentação fica nos módulos da tela; formatação e transformação reutilizáveis permanecem em `utils/` ou `components/`.
- A pasta `api/` concentra chamadas e transporte HTTP por domínio. Autenticação mantém o gerenciamento de sessão em `services/autenticacao.py`, delegando o transporte à API.
- A reorganização é incremental e preserva chaves de estado, rotas, parâmetros, respostas e comportamento visível.
- Não serão adicionadas dependências externas.

## 4. Onde? (Impacto no Código e Arquitetura)

- **Módulos / Diretórios Afetados:** `frontend/pages/`, `frontend/telas/`, `frontend/api/`, `frontend/services/`, `frontend/utils/`, `frontend/components/`.
- **Arquivos Criados / Modificados:** módulos das telas, folhas de estilo, adaptadores de API e imports da interface.
- **Banco de Dados / Infra:** Sem alterações.

## 5. Consequências e Débitos Técnicos

- **Pontos Positivos:** Separação mais clara entre UI, estilos, transformação de dados e integração HTTP; navegação Streamlit preservada.
- **Riscos / Trade-offs:** Imports e caminhos das páginas precisam permanecer alinhados à navegação do Streamlit; a migração deve preservar os trabalhos locais já existentes.
- **Validação / Testes:** Revisar imports, caminhos, estados de sessão e contratos HTTP afetados. Nenhuma dependência ou alteração de backend faz parte desta decisão.
