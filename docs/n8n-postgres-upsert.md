# Integração n8n com PostgreSQL (Upsert Seguro)

Este guia ensina como configurar o nó **PostgreSQL** do n8n para inserir e atualizar itens de conteúdo coletados (como vídeos do YouTube, postagens do Google News, etc.) de forma robusta e segura.

---

## ⚠️ IMPORTANTE: Use Queries Parametrizadas!

> [!CAUTION]
> **Nunca use interpolação de strings** (ex: `SELECT '{{ $json.title }}' ...`) no nó de SQL do n8n. 
> Títulos, descrições e objetos JSON brutos (`raw_json`) frequentemente contêm aspas simples (`'`), aspas duplas (`"`), quebras de linha e caracteres especiais. Fazer interpolação direta quebrará a query e causará erros de sintaxe no Postgres.
>
> **Sempre use placeholders parametrizados** (ex: `$1`, `$2`, etc.) ou a interface visual de inserção do nó Postgres do n8n, associando os parâmetros aos campos da entrada JSON de maneira nativa.

---

## Estrutura de Entrada do n8n

O workflow do n8n deve extrair e enviar ao banco os seguintes campos mínimos para a tabela `content_items`:

1. `source` (ex: `'youtube'`, `'google_news'`)
2. `external_id` (ex: ID do vídeo ou hash único da notícia)
3. `title`
4. `url`
5. `views` (BIGINT)
6. `likes` (BIGINT)
7. `comments` (BIGINT)
8. `score` (REAL)
9. `topic_seed` (Nicho ou palavra-chave de partida)
10. `discovery_query` (Termo exato de busca)
11. `raw_json` (Objeto JSON completo recebido da API)
12. `content_type` (opcional, padrão `'video'`)

---

## Query SQL de Upsert Parametrizada

No nó de PostgreSQL do n8n, configure a query com marcadores de parâmetros (`$1`, `$2`, etc.) e associe-os na lista de parâmetros do nó (na ordem correspondente):

```sql
INSERT INTO content_items (
  source,
  external_id,
  content_type,
  title,
  description,
  url,
  channel_title,
  published_at,
  views,
  likes,
  comments,
  views_per_day,
  score,
  topic_seed,
  discovery_query,
  language,
  country_code,
  raw_json,
  status,
  last_seen_at
)
VALUES (
  $1,  -- source
  $2,  -- external_id
  COALESCE($3, 'video'), -- content_type
  $4,  -- title
  $5,  -- description
  $6,  -- url
  $7,  -- channel_title
  $8,  -- published_at (TIMESTAMPTZ)
  $9,  -- views
  $10, -- likes
  $11, -- comments
  $12, -- views_per_day
  $13, -- score
  $14, -- topic_seed
  $15, -- discovery_query
  $16, -- language
  $17, -- country_code
  $18::jsonb, -- raw_json (necessário cast explicativo)
  'new', -- status
  NOW() -- last_seen_at
)
ON CONFLICT (source, external_id)
DO UPDATE SET
  title = EXCLUDED.title,
  description = EXCLUDED.description,
  url = EXCLUDED.url,
  channel_title = EXCLUDED.channel_title,
  published_at = EXCLUDED.published_at,
  views = EXCLUDED.views,
  likes = EXCLUDED.likes,
  comments = EXCLUDED.comments,
  views_per_day = EXCLUDED.views_per_day,
  score = EXCLUDED.score,
  topic_seed = EXCLUDED.topic_seed,
  discovery_query = EXCLUDED.discovery_query,
  language = EXCLUDED.language,
  country_code = EXCLUDED.country_code,
  raw_json = EXCLUDED.raw_json,
  last_seen_at = NOW();
```

### Como funciona a restrição de duplicados:
A tabela possui a constraint `UNIQUE(source, external_id)`. 
* Se o par `(source, external_id)` **ainda não existir**, uma nova linha é criada com `status = 'new'` e os timestamps preenchidos.
* Se o par `(source, external_id)` **já existir**, o bloco `ON CONFLICT` ativa e atualiza as estatísticas de visualização/engajamento (`views`, `likes`, `comments`, `views_per_day`), o `score`, o `last_seen_at` e o `raw_json`. 
* **Importante**: O campo `status` **não** é modificado durante o `UPDATE`. Isso garante que se o usuário já tiver alterado o status do item no painel (ex: de `'new'` para `'reviewed'` ou `'selected'`), a coleta do n8n não sobrescreverá a decisão de curadoria.
