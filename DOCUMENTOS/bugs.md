# Bugs e melhorias

- [ ] Enfermeiro não vê a tela de usuários nem o próprio perfil para editar, ao contrário dos outros perfis.
  > **Por que acontece:**  
  > 1. **No frontend ([frontend/telas/usuario/index.py](file:///home/patrick/Documentos/Hackathon/main/frontend/telas/usuario/index.py#L99-L103)):** A função `render()` possui uma trava prematura:  
  >    `if nivel_atual not in {NIVEL_ADMIN_GERAL, NIVEL_DIRETOR, NIVEL_MEDICO}: st.info(...) st.stop()`.  
  >    Como o perfil `ENFERMEIRO` é barrado logo na entrada da página, o Streamlit encerra a renderização antes mesmo de exibir a seção *"Meu perfil"* ([L343-L386](file:///home/patrick/Documentos/Hackathon/main/frontend/telas/usuario/index.py#L343-L386)), impedindo o enfermeiro de consultar ou alterar seus próprios dados.  
  > 2. **No backend ([backend/app/controllers/auth.py](file:///home/patrick/Documentos/Hackathon/main/backend/app/controllers/auth.py#L149)):** A rota `PATCH /auth/usuarios/{id}` exige `Depends(exigir_papeis("ADMIN_GERAL", "DIRETOR", "MEDICO"))`, retornando HTTP 403 Forbidden caso um enfermeiro tente submeter alterações no seu próprio cadastro.

- [ ] Enfermeiro não tem acesso à tela de auditoria.
  > **Por que acontece:**  
  > 1. **No menu do frontend ([frontend/app.py](file:///home/patrick/Documentos/Hackathon/main/frontend/app.py#L102-L109)):** A página `pages/2_Auditoria_Humana.py` só é incluída na navegação para papéis específicos:  
  >    `if nivel in {NIVEL_ADMIN_GERAL, NIVEL_DIRETOR, NIVEL_MEDICO}: paginas.append(...)`. O papel `NIVEL_ENFERMEIRO` foi excluído dessa condição.  
  > 2. **No backend ([backend/app/controllers/auditoria.py](file:///home/patrick/Documentos/Hackathon/main/backend/app/controllers/auditoria.py#L65-L90)):** Os endpoints de auditoria (`bloquear_documento_auditoria` e `registrar_decisao_auditoria`) utilizam `Depends(exigir_papeis("ADMIN_GERAL", "DIRETOR", "MEDICO"))`, impedindo requisições de enfermeiros com erro HTTP 403 Forbidden.

- [ ] Incluir extração do CNS em documentos clínicos.
  > **Por que acontece:**  
  > 1. **No schema de extração ([backend/app/schemas/dados_extraidos.py](file:///home/patrick/Documentos/Hackathon/main/backend/app/schemas/dados_extraidos.py#L6-L13)):** A classe `PacienteExtraido` modela apenas `nome`, `cpf`, `idade` e `data_nascimento`. Não existe o campo `cns` (Cartão Nacional de Saúde - 15 dígitos).  
  > 2. **No banco de dados ([backend/app/models/triagem.py](file:///home/patrick/Documentos/Hackathon/main/backend/app/models/triagem.py#L140-L150)):** A tabela de pacientes (`PacienteModel`) também não possui coluna para armazenar o CNS.  
  > 3. **No prompt do agente LLM ([backend/app/agent/prompts/extracao.py](file:///home/patrick/Documentos/Hackathon/main/backend/app/agent/prompts/extracao.py#L35-L47)):** O template de extração não orienta o modelo a capturar o número do CNS contido nas guias TISS, receitas ou cabeçalhos do SUS.

- [ ] Validar dados manuscritos.
  > **Por que acontece:**  
  > 1. **No parser de arquivos ([backend/app/services/document_parser.py](file:///home/patrick/Documentos/Hackathon/main/backend/app/services/document_parser.py) e [backend/app/agent/nodes/qualidade_documento.py](file:///home/patrick/Documentos/Hackathon/main/backend/app/agent/nodes/qualidade_documento.py)):** Não há detector ou classificador de presença de texto manuscrito (*handwriting*), tratando o texto OCR/visão de forma homogênea.  
  > 2. **Nos validadores ([backend/app/agent/nodes/validador.py](file:///home/patrick/Documentos/Hackathon/main/backend/app/agent/nodes/validador.py) e [validadores_clinicos.py](file:///home/patrick/Documentos/Hackathon/main/backend/app/agent/nodes/validadores_clinicos.py)):** Não existem regras específicas para dados manuscritos (como aplicação de limiar de confiança mais rigoroso ou obrigatoriedade de encaminhamento para a auditoria humana quando campos sensíveis como prescrição, dosagem ou CID forem manuscritos).

- [ ] Restringir o acesso do diretor ao controle de usuários do hospital sob sua responsabilidade.
  > **Por que acontece:**  
  > 1. **Na listagem ([backend/app/controllers/auth.py](file:///home/patrick/Documentos/Hackathon/main/backend/app/controllers/auth.py#L108-L117)):** A função `listar_usuarios` busca globalmente todos os registros da tabela `usuarios_sistema` sem filtrar pelo hospital:  
  >    `consulta.filter(UsuarioSistemaModel.papel.in_(["DIRETOR", "MEDICO", "ENFERMEIRO"]))`.  
  > 2. **Na gestão de contas:** Nem `provisionar_usuario` nem `atualizar_usuario` cruzam os dados com a tabela `HospitalDiretorModel` ([backend/app/models/triagem.py](file:///home/patrick/Documentos/Hackathon/main/backend/app/models/triagem.py#L195-L201)). Isso permite que um Diretor Clínico visualize, edite e crie usuários de outros hospitais da rede.

- [ ] Revisar o fluxo de auditoria por completo.
  > **Por que acontece:**  
  > O fluxo possui divergências críticas entre as camadas:  
  > 1. **Listagem de auditados:** O frontend ([frontend/telas/auditoria/index.py](file:///home/patrick/Documentos/Hackathon/main/frontend/telas/auditoria/index.py#L483)) busca por status com prefixo `auditoria_`, inexistente no banco após a normalização do modelo.  
  > 2. **Dependência de Checkpoint LangGraph:** Ao registrar a decisão médica, o backend ([backend/app/services/triagem.py](file:///home/patrick/Documentos/Hackathon/main/backend/app/services/triagem.py#L321)) tenta executar `retomar_agente_triagem`. Se o caso não tiver checkpoint ativo de `revisao_humana` persistido no PostgreSQL (cenário comum em seeds, testes e documentos antigos), a API recusa com HTTP 409 Conflict.  
  > 3. **Conflito com a constraint de destino final:** Ao aprovar ou corrigir, o status é alterado para `ROTEADO` antes de atribuir `destino_id`, disparando erro de integridade relacional no banco.  
  > 4. **Locks de concorrência:** O lock temporário via Redis ([backend/app/controllers/auditoria.py](file:///home/patrick/Documentos/Hackathon/main/backend/app/controllers/auditoria.py#L88)) impede auditoria simultânea, mas se um auditor fechar a aba sem concluir, o documento fica bloqueado até o TTL expirar.

- [ ] Corrigir os filtros de auditoria.
  > **Por que acontece:**  
  > 1. **Filtro "Já auditado":** Em [frontend/telas/auditoria/index.py](file:///home/patrick/Documentos/Hackathon/main/frontend/telas/auditoria/index.py#L483), o código avalia `st_proc.startswith("auditoria_")`. Como os status finais são normalizados no modelo para `ROTEADO` e `REJEITADO`, a lista de auditados fica sempre vazia e o KPI correspondente fica zerado.  
  > 2. **Ordenação por data:** A opção *"Mais recentes primeiro"* ([L645](file:///home/patrick/Documentos/Hackathon/main/frontend/telas/auditoria/index.py#L645)) apenas aplica um `documentos_filtrados.reverse()` sobre a fila que já veio ordenada por criticidade médica (`ordenar_fila`), em vez de realizar um ordenamento cronológico real baseado nos timestamps (`created_at` / `data_hora`).

- [ ] Corrigir as ações da auditoria para aceitar e corrigir registros; atualmente, apenas rejeitar está funcionando.
  > **Por que acontece:**  
  > 1. **Violação da constraint `ck_documento_destino_final` no PostgreSQL:**  
  >    No modelo [backend/app/models/triagem.py](file:///home/patrick/Documentos/Hackathon/main/backend/app/models/triagem.py#L266), a constraint define:  
  >    `CheckConstraint("status_processamento NOT IN ('ROTEADO','CONCLUIDO') OR destino_id IS NOT NULL", name="ck_documento_destino_final")`.  
  >    - Ao **Rejeitar**, o status vai para `REJEITADO` (que não está em `ROTEADO` nem `CONCLUIDO`), logo a constraint é atendida mesmo sem `destino_id`.  
  >    - Ao **Aprovar** ou **Corrigir**, o status vai para `ROTEADO`. O repositório ([backend/app/repositories/auditoria_database.py](file:///home/patrick/Documentos/Hackathon/main/backend/app/repositories/auditoria_database.py#L72-L76)) define `documento.status_processamento = "ROTEADO"` e executa `self.db.flush()` **antes** de atribuir `destino_id`. O banco dispara `IntegrityError`, forçando rollback e retornando erro para a interface.  
  > 2. **Exigência de checkpoint e contrato estrito:**  
  >    `TriagemService.registrar_decisao_medica` tenta retomar o grafo LangGraph; se o checkpoint não existir, retorna 409 Conflict. Além disso, para a ação "Corrigir", `DecisaoAuditoriaRequest` exige estritamente o preenchimento de `dados_corrigidos` válidos e `versao: int` idêntica, sob pena de erro 422 Unprocessable Entity.

- [ ] Na versão em nuvem do Streamlit, o usuário é desconectado ao atualizar a página (F5); manter o token/sessão.
  > **Por que acontece:**  
  > No Streamlit Cloud, o F5 reinicia a conexão WebSocket e limpa toda a memória do `st.session_state`.  
  > A rotina em [frontend/app.py](file:///home/patrick/Documentos/Hackathon/main/frontend/app.py#L28-L34) tenta restaurar a sessão via `st.context.cookies`. Contudo, em ambientes em nuvem rodando sob iframes ou proxies cross-domain, navegadores modernos bloqueiam cookies de terceiros sem atributos `SameSite=None; Secure; Partitioned`.  
  > Embora o projeto já possua um componente nativo de persistência via `localStorage` ([frontend/services/browser_session.py](file:///home/patrick/Documentos/Hackathon/main/frontend/services/browser_session.py)), a função `obter_token_persistido()` nunca foi integrada ao ciclo de inicialização do `app.py` nem da tela de login, fazendo com que o token se perca no refresh.

- [ ] Corrigir o erro ao alterar os próprios dados do usuário.
  > **Por que acontece:**  
  > 1. **No backend ([backend/app/controllers/auth.py](file:///home/patrick/Documentos/Hackathon/main/backend/app/controllers/auth.py#L157-L158)):** A validação `if ator.papel == "MEDICO" and alvo.papel != "ENFERMEIRO": raise HTTPException(status_code=403, detail="Médicos podem gerenciar somente enfermeiros.")` é executada antes de checar se o usuário está editando a própria conta (`ator.id == alvo.id`). Quando o médico edita seu perfil, `alvo.papel` é `"MEDICO"`, resultando em 403 Forbidden.  
  > 2. **No frontend ([frontend/telas/usuario/index.py](file:///home/patrick/Documentos/Hackathon/main/frontend/telas/usuario/index.py#L105-L110)):** Para médicos, as opções de papel são fixadas em `opcoes_papel = [NIVEL_ENFERMEIRO]`. Ao salvar, o formulário envia o papel alterado para Enfermeiro, ativando a trava do backend ([L166-L167](file:///home/patrick/Documentos/Hackathon/main/backend/app/controllers/auth.py#L166-L167)): *"Não é possível alterar o próprio perfil"*.  
  > 3. **Para enfermeiros:** Eles são bloqueados tanto no frontend quanto no endpoint do backend por não constarem na lista de papéis autorizados.

- [ ] Em casos de emergência ou risco, exibir modal de alerta com nome do paciente, CPF, telefone de contato e documento.
  > **Por que acontece:**  
  > Nas telas de triagem ([frontend/telas/triagem/index.py](file:///home/patrick/Documentos/Hackathon/main/frontend/telas/triagem/index.py#L193-L206)) e de análise ([frontend/telas/analise/index.py](file:///home/patrick/Documentos/Hackathon/main/frontend/telas/analise/index.py)), após o processamento o fluxo exibe apenas badges/banners estáticos na tabela. Não há nenhum gatilho de diálogo modal interativo (`@st.dialog`) disparado quando `is_urgente == True` ou `nivel_prioridade == "EMERGENCIA"`, deixando de apresentar os dados de contato imediato (telefone, nome e CPF) para conduta clínica imediata.

- [ ] Na triagem clínica, converter textos enviados pelo usuário em arquivo TXT e enviar o arquivo ao bucket.
  > **Por que acontece:**  
  > No envio de texto clínico ([frontend/telas/triagem/index.py](file:///home/patrick/Documentos/Hackathon/main/frontend/telas/triagem/index.py#L157-L158)), os dados são submetidos via JSON diretamente para a rota `/triagem/texto/enfileirar`.  
  > No backend ([backend/app/services/triagem_queue.py](file:///home/patrick/Documentos/Hackathon/main/backend/app/services/triagem_queue.py#L176-L177)), o job do RQ é disparado com `caminho_arquivo=None` e `caminho_objeto_fonte=None`. Como nenhum arquivo `.txt` é gerado fisicamente no disco nem enviado ao bucket de armazenamento (OCI/Storage), o documento não possui fonte original anexada, impossibilitando download e quebrando a padronização em relação aos documentos PDF e imagem.

- [ ] Nos campos de CPF, permitir entrada em formato válido, com algoritmo de validação e máscara.
  > **Por que acontece:**  
  > Os campos de entrada de CPF na interface (como na auditoria em [frontend/telas/auditoria/index.py](file:///home/patrick/Documentos/Hackathon/main/frontend/telas/auditoria/index.py#L346)) utilizam `st.text_input` padrão, sem componente de máscara interativa (`000.000.000-00`) e sem execução do algoritmo de validação dos dígitos verificadores (Módulo 11) no frontend. Embora o backend possua o algoritmo em `backend/app/agent/normalizacao_texto.py:validar_cpf`, a falta de máscara e validação client-side permite o envio de valores arbitrários e mal formatados.

- [ ] Ao criar usuários pelo sistema, definir a obrigatoriedade de troca da primeira senha para que seja solicitada no primeiro acesso.
  > **Por que acontece:**  
  > 1. **No backend ([backend/app/controllers/auth.py](file:///home/patrick/Documentos/Hackathon/main/backend/app/controllers/auth.py#L134)):** O método `provisionar_usuario` fixa no código `trocar_senha_obrigatorio=False`:  
  >    ```python
  >    novo = UsuarioSistemaModel(
  >        ...
  >        trocar_senha_obrigatorio=False,
  >        ...
  >    )
  >    ```  
  > 2. **No frontend ([frontend/telas/usuario/index.py](file:///home/patrick/Documentos/Hackathon/main/frontend/telas/usuario/index.py#L292-L299)):** O valor da checkbox `troca_obrigatoria` não é repassado no payload enviado à função `provisionar_usuario`.  
  > Com isso, nenhum usuário recém-criado tem a flag ativada e não é redirecionado para a tela de troca obrigatória de senha ([frontend/pages/6_Trocar_Senha.py](file:///home/patrick/Documentos/Hackathon/main/frontend/pages/6_Trocar_Senha.py)) no primeiro acesso.
