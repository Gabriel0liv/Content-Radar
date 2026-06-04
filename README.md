# Dark Content Radar

Portal de inteligência de conteúdo para encontrar oportunidades editoriais a partir de vídeos (Shorts) e notícias.

---

## Postgres local para integração com n8n

O projeto utiliza PostgreSQL local rodando via Docker Compose como infraestrutura de armazenamento principal compartilhada com workflows do n8n. O Streamlit atua como painel de consulta, curadoria e análise posterior dos resultados coletados.

### 1. Como subir o Postgres

Para iniciar o banco de dados PostgreSQL persistente local:

```bash
docker compose up -d
```

> [!WARNING]
> Os scripts contidos na pasta `./initdb/` (como o `001_schema.sql`) **só executam automaticamente na primeira criação do volume do banco de dados**. 
> Se você alterar os schemas posteriormente e o volume Docker já existir, as alterações não serão aplicadas de forma automática. Nesses casos, você precisará recriar o volume (ex: `docker compose down -v` e subir novamente) ou rodar as queries manuais de alteração.

### 2. Como conectar o n8n à rede Docker

Como o n8n normalmente roda em seu próprio container Docker fora deste compose, você precisa uni-lo à rede criada para este banco (`content_radar_net`):

```bash
docker network connect content_radar_net n8n
```

### 3. Credenciais para Configuração no n8n

Ao configurar o nó do **PostgreSQL** no n8n, utilize as seguintes credenciais:

* **Host:** `dark_content_postgres` (se o n8n estiver na mesma rede Docker) ou `localhost` (se rodar fora do Docker local)
* **Port:** `5432`
* **Database:** `dark_content_radar`
* **User:** `radar`
* **Password:** `radar`
* **SSL:** `Disable`

Consulte o arquivo de documentação [n8n-postgres-upsert.md](file:///d:/documentos/Projetos/dark-content-radar/docs/n8n-postgres-upsert.md) para ver como estruturar a query SQL de upsert de forma segura e parametrizada dentro do n8n.

### 4. Como testar a BD

Para validar se as tabelas foram criadas e consultar os dados inseridos diretamente pelo terminal do container Postgres:

```bash
docker exec -it dark_content_postgres psql -U radar -d dark_content_radar
```

Dentro do prompt psql, você pode listar as tabelas com:
```sql
\dt
```

Ou verificar a quantidade de itens coletados:
```sql
SELECT COUNT(*) FROM content_items;
```

### 5. Como rodar o Streamlit usando Postgres

Por padrão, o app roda em modo SQLite. Para ativar o modo de leitura do Postgres local:

```bash
# Definindo a flag e rodando o app
$env:USE_POSTGRES="true"; streamlit run app.py
```

Ou defina `USE_POSTGRES=true` diretamente no seu arquivo `.env` local e rode normalmente:

```bash
streamlit run app.py
```

---

## Configuração SQLite (Legado / Compatibilidade)

Para manter o modo de coleta legado via Python e banco local SQLite, configure seu arquivo `.env` para apontar o caminho do banco SQLite:

* `USE_POSTGRES=false`
* `DATABASE_PATH=data/database.sqlite`

Execute a coleta tradicional via Python:
```bash
python main.py
```
E visualize no painel com `USE_POSTGRES=false`.
