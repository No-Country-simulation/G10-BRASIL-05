# [0018] - Autenticação e Autorização no Backend

- **Data:** 2026-11-19
- **Autor(es):** @patrick-jala (via Assistente IA)
- **Status:** Aprovado

---

## 1. Por quê? (Contexto e Motivação)

A tela Streamlit atualmente autentica perfis a partir de dados locais, aceita qualquer senha com tamanho mínimo quando a API não responde e emite JWT no próprio frontend. O token contém dados pessoais e a inspeção da sessão decodifica claims sem validar a assinatura. No backend, as rotas clínicas não exigem identidade verificada e a conta institucional do WhatsApp é criada com uma credencial padrão e hash com salt compartilhado.

Isso permite autenticação sem prova de senha real, falsificação de identidade/perfil no frontend e acesso direto às rotas sem autorização central. Também dificulta atribuir decisões clínicas a uma conta autenticada e evoluir o schema com segurança.

## 2. Para quê? (Objetivo e Resultados Esperados)

- Fazer o FastAPI validar credenciais, persistir contas, assinar e verificar tokens e decidir acesso por papel.
- Remover autoinscrição pública. Contas profissionais serão provisionadas por administrador autorizado.
- Preservar os papéis `DIRETOR`, `MEDICO` e `ENFERMEIRO` e aplicar no backend a matriz de permissões já expressa na interface.
- Exigir autenticação para triagem e histórico pelos três papéis; restringir decisões médicas de auditoria a médicos e diretores; permitir à enfermagem somente operações de conferência e encaminhamento.
- Retirar fallback local, segredo JWT e exposição/inspeção do token da interface Streamlit, mantendo o layout da tela de login.
- Retirar a senha padrão da conta institucional do WhatsApp e provisionar/rotacionar sua credencial por processo seguro de implantação.
- Reduzir claims e respostas aos dados necessários para autenticação, autorização e apresentação.

## 3. Como? (Implementação Técnica e Alternativas)

### Alternativas Consideradas:
- **Alternativa A (Descartada):** Manter autenticação ou autorização no Streamlit e confiar em cabeçalhos enviados pelo cliente. Não protege chamadas diretas à API nem impede adulteração de identidade.
- **Alternativa B (Escolhida):** Centralizar identidade e autorização no FastAPI; persistir usuários no banco; aplicar dependências de autenticação e papel por rota; manter no frontend apenas a sessão visual e o envio Bearer.

### Detalhamento da Solução:

1. Manter uma conta de sistema por usuário, com email único, nome, papel, estado ativo e hash de senha. Derivar o hash com algoritmo de senha apropriado e salt aleatório exclusivo por conta; comparar com rotina de tempo constante. Não persistir senha em texto nem dados pessoais dispensáveis.
2. Expor `POST /api/v1/auth/login` para autenticar por email e senha e `GET /api/v1/auth/me` para retornar somente o perfil público mínimo da conta autenticada. Não criar rota de autoinscrição. Provisionar o primeiro administrador por comando operacional interativo, solicitando senha sem eco no terminal; impedir duplicidade e não definir credencial padrão. O cadastro administrativo posterior só poderá criar papéis permitidos pela matriz.
3. Assinar JWT no backend com chave configurada fora do repositório, algoritmo fixo e expiração curta configurável. Incluir somente `sub`, `role`, `iat`, `exp`, `iss` e `jti`; validar assinatura, algoritmo, emissor, expiração e estado ativo do usuário em cada requisição. Nenhuma chave terá fallback embutido.
4. Usar dependências FastAPI reutilizáveis para autenticação e papéis. Derivar o autor de decisões de auditoria da identidade validada, sem confiar em nome/email do payload. Restringir gestão do WhatsApp ao papel de sistema institucional autenticado, removendo a autorização por header/query de email.
5. Aplicar migrações versionadas com Alembic, já presente nas dependências do backend. A migração preservará as contas atuais necessárias, removerá a criação de senha padrão e exigirá rotação/provisionamento seguro da conta institucional durante a implantação.
6. Manter o layout de login. O frontend envia credenciais à API, guarda o token na sessão de interface e usa a resposta mínima do backend; não assina, decodifica, exibe nem aceita token de forma local. Em indisponibilidade da API, o login falha fechado.
7. Proteger retornos de pacientes, documentos e auditoria com os esquemas de resposta existentes ou revisados para não divulgar CPF, CNS, endereço, texto clínico ou fonte original a perfis/endpoints que não necessitem desses dados.

## 4. Onde? (Impacto no Código e Arquitetura)

- **Módulos / Diretórios Afetados:** `backend/app/controllers/`, `backend/app/services/`, `backend/app/repositories/`, `backend/app/models/`, `backend/app/schemas/`, `backend/app/config/`, `backend/migrations/`, `frontend/services/`, `frontend/pages/`, `frontend/utils/` e testes correspondentes.
- **Arquivos Criados / Modificados:** Router e serviço de auth, dependências JWT/RBAC, modelos e repositório de usuários, migração Alembic, comando de bootstrap administrativo, cliente de login e páginas que exibem identidade/token; testes de autenticação, papéis, endpoints e respostas.
- **Banco de Dados / Infra:** Migração versionada para campos/relacionamentos de identidade e auditoria; configuração externa obrigatória para chave JWT e provisionamento da conta institucional; nenhum segredo padrão em código. Alembic já consta nas dependências do backend.

## 5. Consequências e Débitos Técnicos

- **Pontos Positivos:** A API se torna a autoridade de identidade e acesso; tokens adulterados e credenciais de demonstração deixam de conceder acesso; contas e ações clínicas ficam rastreáveis; dados pessoais deixam de circular em claims desnecessários.
- **Riscos / Trade-offs:** A rotação da credencial institucional e a configuração da chave JWT são requisitos operacionais para implantação. Os tokens emitidos deixam de valer após mudança de chave/expiração e contas locais de demonstração precisam ser provisionadas no banco.
- **Validação / Testes:** Cobrir hash e verificação de senha, login válido/inválido, expiração/assinatura/emissor do JWT, conta desativada, acesso negado/permitido por papel, endpoints sem token, cadastro administrativo fechado, atribuição do autor no servidor, respostas sem dados sensíveis, migração e fluxo do frontend sem fallback local. Executar os testes pertinentes quando a implementação estiver concluída.
