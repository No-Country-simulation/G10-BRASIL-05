# Diário de Infraestrutura — P5 (OCI Object Storage Always Free)

Registro do que foi feito na OCI. Os prints de evidência ficam nesta pasta.

> ⚠️ Nunca colocar aqui: chaves `.pem`, fingerprint, OCIDs, senhas ou tokens.

---

## Ambiente

| Item | Valor |
|---|---|
| Conta | OCI Always Free |
| Região | US East (Ashburn) — `us-ashburn-1` |
| Bucket | `mediflow-documentos-clinicos` (Standard, Private) |
| Grupo | `mediflow` |
| Política | `mediflow-devs-bucket` |
| Limite gratuito | 20 GiB |

---

## 21/10/2026 — Conta e bucket (SCRUM-48, SCRUM-70)

- [x] Conta OCI criada (Always Free)
- [x] Bucket criado no compartimento root

![Bucket criado](bucket%20criado.png)

---

## 22/10/2026 — Pastas e acesso dos colegas (SCRUM-70)

- [x] Pastas criadas:
  ```
  recebidos/
  processados/urgentes/
  processados/rotina/
  auditoria_humana/
  nao_classificados/   (adicionada em 11/11)
  ```
- [x] Grupo `mediflow` criado e colegas adicionados
- [x] Política criada, com acesso só a este bucket:
  ```
  Allow group mediflow to read objectstorage-namespaces in tenancy
  Allow group mediflow to read buckets in tenancy
  Allow group mediflow to manage objects in tenancy where target.bucket.name='mediflow-documentos-clinicos'
  ```
- [x] Testado com um usuário do grupo: vê o bucket e não pode criar buckets

**Aprendido:** o nome do grupo na política tem que ser igual ao do grupo criado.

---

## 27/10/2026 — Autenticação do SDK (SCRUM-71)

- [x] Chave de API gerada no meu usuário. O `.pem` fica em `~/.oci/`, fora do projeto
- [x] Valores reais só no `backend/.env` (não vai para o GitHub)
- [x] Região corrigida para `us-ashburn-1` e `*.pem` no `.gitignore`
- [x] Teste: o SDK listou as pastas do bucket

**Aprendido:** cada colega usa o seu próprio usuário e a sua chave. Ninguém partilha credenciais.

---

## 27/10/2026 — Upload e leitura (SCRUM-72)

- [x] `backend/app/repositories/arquivos_oci.py`: guarda o original em `recebidos/` e lê arquivos e JSONs
- [x] Herda a autenticação do `storage.py` sem alterá-lo
- [x] Testado no bucket real (enviar → ler → apagar)

---

## 29/10/2026 — Mover por status (SCRUM-73)

- [x] `mover_por_status`: `recebidos/` → `processados/urgentes/`, `processados/rotina/` ou `auditoria_humana/`
- [x] Usa `rename_object` (uma chamada só). A política atual já permite
- [x] Testado no bucket real

---

## 29/10/2026 — Falhas e modo local (SCRUM-74)

- [x] Sem credenciais: os arquivos ficam em `backend/storage_local/` (mesmas pastas do bucket)
- [x] Se a OCI cair: o arquivo fica no disco e entra na lista de pendentes
- [x] Tentativas automáticas do SDK para erros passageiros
- [x] Quando a OCI voltar: `python scripts/sincronizar_oci.py`
- [x] Testado no bucket real: queda simulada → disco → sincronização → bucket

---

## 11/11/2026 — Ajustes

- [x] `.env.example` corrigido na `main` e na `develop` (bucket `mediflow-documentos-clinicos`, região `us-ashburn-1`)
- [x] Nova pasta `nao_classificados/` para documentos que não são clínicos (código pronto)
- [ ] Criar a pasta `nao_classificados/` no bucket
- [ ] Apagar a imagem de teste de `auditoria_humana/`

---

## Próximos passos

- [ ] SCRUM-75 — Alerta de custo (budget) e script de uso
- [ ] PRs na ordem 70 → 71 → 72 → 73 → 74
- [ ] Ligar os métodos na triagem (combinar com P1/P4)
