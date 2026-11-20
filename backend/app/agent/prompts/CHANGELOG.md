# Histórico de versões dos prompts

Toda alteração em um prompt (texto, regra ou exemplo) incrementa a constante `VERSAO` do módulo e ganha uma entrada aqui. A versão segue `MAIOR.MENOR.CORRECAO`:

- **MAIOR:** muda o formato do JSON de resposta (quebra o parser do nó).
- **MENOR:** muda regras, instruções ou exemplos sem mudar o formato.
- **CORRECAO:** corrige grafia ou redação sem mudar o sentido.

A saída de cada nó registra a versão usada em `versao_prompt`, o que permite rastrear qual prompt gerou cada classificação ou extração.

## classificacao.py

### 1.1.0 (2026-11-20, SCRUM-64)
- Exemplos few-shot: receita de rotina, laudo de emergência e documento ambíguo com score baixo.
- Nova regra: não classificar como `EMERGENCIA` sem achado crítico escrito.

### 1.0.0 (2026-10-29, SCRUM-57)
- Respostas com os códigos dos enums de `ClassificacaoDocumento` e a chave `score_confianca_classificacao`.

## transcricao.py

### 1.0.0 (2026-11-20, SCRUM-96)
- Transcrição literal de imagens e PDFs escaneados, com `[ilegível]` para trechos que não podem ser lidos e `SEM_TEXTO_LEGIVEL` quando nada é legível.

## extracao.py

### 1.1.0 (2026-11-20, SCRUM-64)
- Exemplos few-shot: receita completa e laudo sem CID escrito (`cid_sugerido: null`).
- Regra de CID reforçada com referência ao exemplo.

### 1.0.0 (2026-11-20, SCRUM-58)
- JSON no formato de `DadosExtraidos` (`crm_uf`, `medicamentos`) e regras anti-alucinação para nomes, CRM, CID e medicamentos.
