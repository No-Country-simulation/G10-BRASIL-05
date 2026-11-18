# [0015] - Autenticação OCI e rollback compensatório da triagem

- **Data:** 2026-11-17
- **Autor(es):** @patrick-jala (via Assistente IA)
- **Status:** Aprovado

---

## 1. Por quê? (Contexto e Motivação)

O backend autentica no OCI Object Storage apenas com API key e o fluxo de upload web/WhatsApp grava os documentos originais localmente, embora exista um repositório OCI ainda não conectado a esses fluxos. Além disso, falhas na persistência de JSONs podem ser devolvidas como sucesso simulado ou deixar arquivos parciais. A gravação do documento, dos artefatos e da linha relacional precisa falhar como uma única operação lógica.

## 2. Para quê? (Objetivo e Resultados Esperados)

Permitir autenticação por API key no desenvolvimento local e Instance Principal na Compute OCI. Enviar originais e resultados para Object Storage e, se uma etapa crítica de armazenamento ou banco falhar, remover os artefatos criados pela tentativa, desfazer a transação relacional e devolver erro explícito sem registrar a triagem como concluída.

## 3. Como? (Implementação Técnica e Alternativas)

### Alternativas Consideradas:
- **Somente API key também na Compute (descartada):** exige distribuir e proteger uma chave privada de longa duração no servidor.
- **Autenticação selecionável por ambiente (escolhida):** API key local e Instance Principal em Compute OCI, sem PEM no servidor.
- **Ignorar falha de armazenamento e seguir com cópia local (descartada no modo OCI):** mascara perda da cópia remota e cria respostas inconsistentes.
- **Rollback compensatório entre OCI, disco local e banco (escolhida):** arquivos remotos/locais não participam de transação SQL; remover artefatos novos e executar rollback SQL quando qualquer gravação crítica falhar.

### Detalhamento da Solução:

Adicionar `OCI_AUTH_MODE` com modos explícitos `api_key` e `instance_principal`. A autenticação OCI existente permanece para execução local; a Compute usa `InstancePrincipalsSecurityTokenSigner`. O endpoint de upload web e o worker WhatsApp passam a persistir o original via `ArquivosOCIRepository` (mantendo cópia local apenas conforme a política do ambiente). O service acompanha os objetos e caminhos criados durante a tentativa. Falhas de gravação devem levantar erro, acionar exclusão compensatória dos artefatos dessa tentativa e `Session.rollback()`. A exclusão compensatória é idempotente e registra falhas de limpeza; por ser operação distribuída, não pode garantir atomicidade absoluta se o próprio serviço OCI estiver indisponível durante a exclusão.

## 4. Onde? (Impacto no Código e Arquitetura)

- **Módulos / Diretórios Afetados:** `backend/app/config/`, `backend/app/repositories/`, `backend/app/services/`, `backend/app/controllers/`, `backend/.env.example`.
- **Arquivos Criados / Modificados:** configurações OCI, `storage.py`, `arquivos_oci.py`, `triagem.py`, `triagem_upload.py`, `evolution_triage_worker.py` e documentação de ambiente.
- **Banco de Dados / Infra:** Dynamic Group e política IAM limitados aos objetos do bucket da aplicação; nenhum PEM de usuário no servidor OCI.

## 5. Consequências e Débitos Técnicos

- **Pontos Positivos:** autenticação de produção sem chave de usuário no servidor; falhas de armazenamento não ficam mascaradas; arquivos órfãos e registros parciais são compensados.
- **Riscos / Trade-offs:** exclusão compensatória depende de conectividade OCI; se a própria remoção falhar, o erro precisa ser logado para reconciliação posterior. Cópias locais e MongoDB/Redis precisam de uma política clara de criticidade separada dos arquivos de triagem.
- **Validação / Testes:** verificar API key local e Instance Principal; simular falha no upload do original, upload do JSON e commit SQL; confirmar ausência de arquivos e linha de triagem após falha e sucesso completo após operação bem-sucedida.
