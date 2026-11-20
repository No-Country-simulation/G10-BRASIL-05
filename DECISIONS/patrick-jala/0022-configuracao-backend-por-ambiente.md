# [0022] - Configuração do backend por ambiente

- **Data:** 2026-11-20
- **Autor(es):** @patrick-jala (via Assistente IA)
- **Status:** Aprovado

---

## 1. Por quê? (Contexto e Motivação)
Valores que mudam entre desenvolvimento, testes e produção estavam definidos como padrões no código de configuração do backend.

## 2. Para quê? (Objetivo e Resultados Esperados)
Manter os valores configuráveis em arquivos de ambiente, permitindo alterar o ambiente sem editar código.

## 3. Como? (Implementação Técnica e Alternativas)
### Alternativas Consideradas:
- **Padrões no código:** descartado porque exige alterações no código para personalizar ambientes.
- **Configuração por ambiente:** escolhida; `Settings` declara os tipos e carrega os valores dos arquivos `.env` ou do ambiente do processo.

### Detalhamento da Solução:
Remover valores padrão dos campos de `Settings` e documentar todas as opções no `backend/.env.example`. Os arquivos `.env` locais continuam fora do versionamento.

## 4. Onde? (Impacto no Código e Arquitetura)
- **Módulos / Diretórios Afetados:** `backend/app/config/`, configuração de ambiente do backend.
- **Arquivos Criados / Modificados:** `backend/app/config/settings.py`, `backend/.env.example`, `.env` local.
- **Banco de Dados / Infra:** sem alteração de infraestrutura; as opções devem estar presentes na configuração de ambiente.

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** configurações explícitas por ambiente e ausência de valores variáveis embutidos em `Settings`.
- **Riscos / Trade-offs:** a aplicação falha ao iniciar se algum campo obrigatório não estiver definido.
- **Validação / Testes:** conferir que cada campo de `Settings` está documentado no `.env.example` e nos ambientes de execução.
