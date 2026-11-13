# [0001] - Documentar instalação, execução e testes do MediFlow

- **Data:** 2026-11-10
- **Autor(es):** Pedro-Araujo04 (via Assistente IA)
- **Status:** Proposto

---

## 1. Por quê? (Contexto e Motivação)

O README não oferece passos de instalação e execução que correspondam ao repositório atual. Sua descrição de pastas inclui módulos inexistentes e não explica como instalar dependências ou executar os testes.

---

## 2. Para quê? (Objetivo e Resultados Esperados)

Permitir que uma pessoa desenvolvedora prepare o ambiente, inicie os serviços disponíveis e execute backend, frontend e testes sem depender de instruções implícitas. Delimitar também quais integrações são opcionais e não cobertas por testes locais.

---

## 3. Como? (Implementação Técnica e Alternativas)

### Alternativas Consideradas:
- **Alternativa A (Descartada):** Manter o guia existente e acrescentar comandos isolados; isso preservaria descrições de arquitetura e caminhos que não correspondem aos arquivos atuais.
- **Alternativa B (Escolhida):** Reescrever o README com base nos manifests, configurações, entrypoints e testes existentes, distinguindo execução local e serviços opcionais.

### Detalhamento da Solução:

Atualizar somente a documentação central, sem adicionar dependências nem alterar o comportamento da aplicação. Documentar dependências Python separadas, Docker Compose existente, comandos observados para API, interface e pytest, variáveis relevantes e limites de validação. O README não deve reproduzir a listagem extensa de regras de arquitetura existente nos guias internos.

---

## 4. Onde? (Impacto no Código e Arquitetura)
- **Módulos / Diretórios Afetados:** documentação raiz do projeto.
- **Arquivos Criados / Modificados:** `README.md`, `DECISIONS/Pedro-Araujo04/0001-documentar-instalacao-execucao-testes.md`.
- **Banco de Dados / Infra:** nenhuma alteração; referenciar os serviços e valores padrão já definidos em `docker-compose.yml` e `backend/app/config/settings.py`.

---

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** instruções rastreáveis e alinhadas aos entrypoints e testes que existem no checkout.
- **Riscos / Trade-offs:** comandos e variáveis podem ficar desatualizados quando os manifests mudarem; manter o README junto dessas mudanças.
- **Validação / Testes:** revisar os caminhos e comandos contra os arquivos do repositório e executar a suíte pytest local; integrações reais dependentes de serviços externos devem ser identificadas como não verificadas quando não executadas.
