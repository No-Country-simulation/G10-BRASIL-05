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

## Próximos passos

- [ ] SCRUM-71 — Chave de API e `.env.example`
- [ ] SCRUM-74 — Modo local (sem nuvem)
- [ ] SCRUM-72 — Upload e leitura
- [ ] SCRUM-73 — Mover entre pastas
- [ ] SCRUM-75 — Monitorar uso gratuito
