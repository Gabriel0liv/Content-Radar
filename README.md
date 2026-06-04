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

### 3. Regras de Conexão e Portas (Evitando conflito com porta 5432)

O Postgres deste projeto está exposto no host na porta **5433** (`5433:5432`) para evitar conflito caso você já possua outro container ou serviço utilizando a porta padrão `5432` no seu sistema.

Dependendo de onde o serviço de consulta está rodando, utilize as seguintes configurações:

#### Regra 1: Acesso pelo Windows / Host (Fora do Docker)
Para ferramentas locais (DBeaver, pgAdmin) ou Streamlit rodando nativamente no terminal da sua máquina:
```ini
DATABASE_URL=postgresql://radar:radar@localhost:5433/dark_content_radar
```

#### Regra 2: n8n conectado à rede Docker `content_radar_net`
Ao configurar o nó do **PostgreSQL** dentro do workflow do n8n:
* **Host:** `dark_content_postgres`
* **Port:** `5432` (porta interna do container Postgres)
* **Database:** `dark_content_radar`
* **User:** `radar`
* **Password:** `radar`
* **SSL:** `Disable`

#### Regra 3: Streamlit rodando dentro do docker-compose
Se você futuramente encapsular o painel do Streamlit para rodar como um serviço dentro da mesma rede Docker do Compose:
```ini
DATABASE_URL=postgresql://radar:radar@postgres:5432/dark_content_radar
```

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

---

## Backend FastAPI e Migrations Alembic

O projeto possui um backend em **FastAPI** integrado ao banco Postgres por meio do **SQLAlchemy** ORM e controle de versão de schemas gerenciado pelo **Alembic**. A partir desta etapa, o Alembic é a fonte oficial de evolução de schemas.

### 1. Configurações de Conexão (DATABASE_URL)

O projeto separa as conexões dependendo do contexto de execução:

* **Rodando Alembic/FastAPI localmente no Windows (Host):**
  ```ini
  DATABASE_URL=postgresql://radar:radar@localhost:5433/dark_content_radar
  ```
* **Rodando dentro do Docker Compose (Container-to-Container):**
  ```ini
  DATABASE_URL=postgresql://radar:radar@postgres:5432/dark_content_radar
  ```
* **Para o n8n conectado à rede Docker `content_radar_net`:**
  * **Host:** `dark_content_postgres`
  * **Port:** `5432`

---

### 2. Fluxo de Migrations (Alembic)

> [!WARNING]
> Como removemos o auto-mount da pasta `initdb` no Docker Compose para evitar conflito com migrations, **bancos de dados novos sobem completamente vazios** até que as migrations sejam executadas.
> As migrations do Alembic não rodam automaticamente na inicialização do backend nesta fase. Devem ser rodadas manualmente.

#### Opção A: Para Bancos de Dados Existentes (Já criados pelo initdb)
Como sua base de dados atual já possui a tabela `content_items` e dados salvos, siga este procedimento para evitar erros de criação duplicada:

1. Confirme se a estrutura da migração inicial (`alembic/versions/*_initial_schema.py`) bate com o schema atual do banco.
2. Defina a variável de ambiente `DATABASE_URL` apontando para o host local e execute o comando `stamp head` (isso registra a revisão inicial como aplicada sem rodar queries SQL):
   ```powershell
   $env:DATABASE_URL="postgresql://radar:radar@localhost:5433/dark_content_radar"
   .venv\Scripts\alembic stamp head
   ```
3. Verifique se o banco foi marcado corretamente:
   ```powershell
   .venv\Scripts\alembic current
   ```

#### Opção B: Para Bancos de Dados Novos (Do Zero)
Para inicializar o banco em uma instalação limpa:

1. Suba o container do Postgres:
   ```bash
   docker compose up -d postgres
   ```
2. Defina a variável de ambiente `DATABASE_URL` local e rode o upgrade:
   ```powershell
   $env:DATABASE_URL="postgresql://radar:radar@localhost:5433/dark_content_radar"
   .venv\Scripts\alembic upgrade head
   ```
   Ou aplique a migração diretamente de dentro do Docker usando o container do backend:
   ```bash
   docker compose run --rm backend alembic upgrade head
   ```

#### Como Criar e Aplicar Novas Migrações no Futuro
Se alterar os arquivos em `src/models/`, gere e aplique a migração com:
```bash
# Gerar
$env:DATABASE_URL="postgresql://radar:radar@localhost:5433/dark_content_radar"
.venv\Scripts\alembic revision --autogenerate -m "descricao_da_mudanca"

# Aplicar
.venv\Scripts\alembic upgrade head
```

---

### 3. Como Rodar o Backend

#### Execução Local (Windows)
1. Certifique-se de que o container Postgres está ativo (`docker compose up -d postgres`).
2. Defina `DATABASE_URL` no `.env` como:
   `DATABASE_URL=postgresql://radar:radar@localhost:5433/dark_content_radar`
3. Execute o servidor:
   ```bash
   .venv\Scripts\uvicorn src.api.main:app --reload
   ```

#### Execução via Docker Compose
Para subir o backend encapsulado em container na porta 8000:
```bash
docker compose up -d backend
```

#### Documentação Interativa da API (Swagger)
Com o backend rodando, acesse a documentação do Swagger para testar as rotas interativamente:
* **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Rotas Disponíveis:**
  * `GET /health` - Status da API
  * `GET /content-items` - Filtro e listagem
  * `GET /content-items/{item_id}` - Detalhes do item
  * `PATCH /content-items/{item_id}/status` - Transição de status
  * `POST /ingest/n8n` - Upsert em lote para o n8n (futuro)
