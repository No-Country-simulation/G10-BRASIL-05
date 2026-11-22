# [0025] - Troca de senha no primeiro acesso sem reinserir a senha temporária

- **Data:** 2026-11-20
- **Autor(es):** @patrick-jala (via Assistente IA)
- **Status:** Aprovado

---

## 1. Por quê? (Contexto e Motivação)
No primeiro acesso, a conta é autenticada com a senha temporária, mas a tela de troca também pede que a pessoa informe essa senha novamente. Isso duplica a etapa de autenticação na mesma sessão.

## 2. Para quê? (Objetivo e Resultados Esperados)
Manter a senha temporária para o login inicial e, após autenticação válida, permitir que a pessoa informe apenas a nova senha e sua confirmação.

## 3. Como? (Implementação Técnica e Alternativas)
### Alternativas Consideradas:
- **Alternativa A (Descartada):** Pedir a senha temporária novamente na tela de troca; isso repete uma credencial que já foi validada no login.
- **Alternativa B (Escolhida):** Autorizar a troca usando a sessão autenticada e o indicador persistente de troca obrigatória; o formulário solicita somente a nova senha e confirmação.

### Detalhamento da Solução:
O endpoint de alteração de senha exige token válido e que a conta esteja marcada para troca obrigatória. Ele valida o tamanho mínimo da nova senha, grava seu hash e limpa o indicador. A senha temporária continua obrigatória para autenticar o primeiro login.

## 4. Onde? (Impacto no Código e Arquitetura)
- **Módulos / Diretórios Afetados:** `backend/app/`, `frontend/`, `DECISIONS/`.
- **Arquivos Criados / Modificados:** Schema e controller de autenticação; serviço e página de troca de senha.
- **Banco de Dados / Infra:** Sem alteração de schema ou variáveis de ambiente.

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** Primeiro acesso tem uma etapa a menos sem remover a autenticação inicial.
- **Riscos / Trade-offs:** A troca confia no token já emitido pelo login e deve continuar restrita às contas marcadas para troca obrigatória.
- **Validação / Testes:** Revisar autorização do endpoint e fluxo da página; não executar testes nesta solicitação.
