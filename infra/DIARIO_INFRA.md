# Diário de Infraestrutura — P5 (OCI Object Storage Always Free)

Registro do que foi feito na infraestrutura OCI, com prints como evidência.
Os prints ficam nesta mesma pasta (`infra/`).

> ⚠️ Nunca colocar aqui: chaves `.pem`, fingerprint, OCIDs de usuário, senhas ou tokens.

---

## Resumo do ambiente

| Item | Valor |
|---|---|
| Provedor | Oracle Cloud Infrastructure (OCI) — Always Free |
| Serviço | Object Storage |
| Bucket | `mediflow-documentos-clinicos` |
| Storage tier | Standard |
| Visibilidade | Private |
| Limite gratuito | 20 GiB (Object Storage + Archive somados) |

---

## Registro por data

### 21/10/2026 — Conta OCI e bucket (SCRUM-48, SCRUM-70)

**Feito:**
- [x] Conta OCI criada e usando apenas recursos Always Free (SCRUM-48)
- [x] Bucket `mediflow-documentos-clinicos` criado — Standard, Private (SCRUM-70)
- [ ] Criar as pastas `recebidos/`, `processados/` e `auditoria_humana/` dentro do bucket

**Evidência:** `bucket criado.png`

![Bucket criado](bucket%20criado.png)

**Observações:**
- Uso no momento da criação: 0 bytes de 20 GiB.
- O bucket está no compartimento raiz (root) da conta.

---

### 21/10/2026 — Acesso dos colegas ao bucket (em andamento)

**Objetivo:** dar acesso ao bucket só para quem precisa, com o mínimo de permissão.

**Plano:**
- [ ] Criar o grupo `mediflow-devs` (Identity & Security → Domains → Default → Groups)
- [ ] Criar os usuários dos colegas que precisam de acesso e adicioná-los ao grupo
- [ ] Criar a política de acesso limitada ao bucket (ver abaixo)
- [ ] Testar com um colega se ele consegue ver o bucket e fazer upload

**Política planejada:**
```
Allow group mediflow-devs to read buckets in tenancy
Allow group mediflow-devs to manage objects in tenancy where target.bucket.name='mediflow-documentos-clinicos'
```

**Evidência:** _(adicionar prints do grupo e da política)_

---

## Próximos passos

- [ ] SCRUM-71 — Chave de API e `.env.example`
- [ ] SCRUM-74 — Modo local (sem nuvem)
- [ ] SCRUM-72 — Upload e leitura
- [ ] SCRUM-73 — Mover entre pastas
- [ ] SCRUM-75 — Monitorar uso gratuito
