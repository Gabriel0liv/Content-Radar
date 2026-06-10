# Dark Content Radar

Portal de inteligência de conteúdo para encontrar oportunidades editoriais a partir de vídeos (Shorts) e notícias.

---

## Direção Arquitetural: Backend FastAPI & Futuro Frontend Next.js

> [!NOTE]
> A arquitetura de produção do projeto está centrada no **FastAPI** como backend principal e fonte da verdade para dados e curadoria de conteúdos persistidos no Postgres. 
> * **Streamlit (app.py)**: Tratado agora como painel legado / MVP rápido. Não receberá novas atualizações de funcionalidades complexas.
> * **FastAPI Backend (src/api)**: O backend oficial que fornece APIs completas de curadoria, paginação e estatísticas para alimentar integrações e o futuro frontend.
> * **Frontend Futuro**: Um painel moderno em **Next.js** consumirá as APIs FastAPI para realizar a consulta, curadoria e fluxos de trabalho.

## Postgres local para integração com n8n

O projeto utiliza PostgreSQL local rodando via Docker Compose como infraestrutura de armazenamento principal compartilhada com workflows do n8n. O Streamlit atua como painel de consulta, curadoria e análise posterior dos resultados coletados.

### 1. Como subir o Postgres

Para iniciar o banco de dados PostgreSQL persistente local:

```bash
docker compose up -d postgres
```

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

O Alembic é a **fonte oficial** de evolução do schema do banco de dados.

> [!WARNING]
> Como o Docker Compose não inicializa mais as tabelas via `initdb` automaticamente, **bancos de dados novos sobem vazios** até que as migrations sejam aplicadas.
> As migrations do Alembic não rodam automaticamente no startup do backend e devem ser executadas manualmente.

#### Opção A: Para Bancos de Dados Existentes (Banco já criado com dados)
Se a base de dados já possui a tabela `content_items` sem a constraint de status, siga este fluxo para aplicar a nova constraint sem perder nenhum dado e sem gerar erros de criação duplicada:

1. Registre o baseline do schema atual (0001_baseline) no banco de dados existente:
   ```powershell
   $env:DATABASE_URL="postgresql://radar:radar@localhost:5433/dark_content_radar"
   .venv\Scripts\alembic stamp 0001_baseline
   ```
2. Aplique a migração que adiciona a check constraint de status (0002_add_status_check_constraint):
   ```powershell
   .venv\Scripts\alembic upgrade head
   ```
3. Verifique se o banco está na revisão correta:
   ```powershell
   .venv\Scripts\alembic current
   ```

#### Opção B: Para Bancos de Dados Novos (Do Zero)
Para inicializar uma instalação limpa do banco de dados:

1. Suba o container do Postgres:
   ```bash
   docker compose up -d postgres
   ```
2. Aplique todas as migrations a partir do zero até o head:
   ```powershell
   $env:DATABASE_URL="postgresql://radar:radar@localhost:5433/dark_content_radar"
   .venv\Scripts\alembic upgrade head
   ```
   Ou de dentro do Docker usando o container do backend:
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
  * `GET /health` - Status de saúde e conexão da API.
  * `GET /content-items` - Filtro, busca textual (com `coalesce` no banco), ordenação dinâmica (incluindo `last_seen_at`) e paginação.
  * `GET /content-items/summary` - Estatísticas consolidadas para os cards do dashboard.
  * `GET /content-items/{item_id}` - Detalhes individuais do conteúdo.
  * `PATCH /content-items/{item_id}` - Atualização exclusiva de curadoria (status, notas, notas de produção, motivo de rejeição).
  * `PATCH /content-items/{item_id}/status` - Atualização rápida de status (compatibilidade).
  * `POST /ingest/n8n` - Endpoint de ingestão em lote utilizando schema semântico `ContentItemIngest`.

---

## Frontend Next.js (Painel de Curadoria)

O painel de curadoria é uma aplicação moderna desenvolvida com **Next.js 14 (App Router)**, **TypeScript**, **Tailwind CSS** e **Lucide Icons** para interagir com o backend FastAPI.

### 1. Requisitos Prévios
Certifique-se de possuir o **Node.js (v18 ou superior)** instalado na sua máquina.

### 2. Configuração do Ambiente
Crie um arquivo de variáveis de ambiente dentro da pasta `frontend/`:
```bash
cd frontend
cp .env.example .env.local
```
O arquivo `.env.local` virá configurado por padrão para se conectar ao backend local em `http://localhost:8000`.

### 3. Instalação e Inicialização
Execute os comandos no seu terminal para instalar as dependências e iniciar o servidor de desenvolvimento:

```bash
# Navegar até a pasta do frontend
cd frontend

# Instalar as dependências
npm install

# Iniciar em modo de desenvolvimento
npm run dev
```

A aplicação estará disponível em [http://localhost:3000](http://localhost:3000).

### 4. Principais Funcionalidades Implementadas
* **Visão Geral de Métricas (Dashboard)**: Cards com número total de itens coletados, novos sinais aguardando triagem, maior score de oportunidade e views máximas integrados com `GET /content-items/summary`.
* **Filtros Avançados**: Barra de pesquisa textual com debounce de digitação e filtros por Fonte (YouTube/Google News), Tipo de Conteúdo (Vídeo/Artigo), Status, Nicho/Semente, Score Mínimo, Views Mínimas e Ordenação.
* **Layout Responsivo Split-View**: Ao clicar em qualquer conteúdo na tabela principal, o formulário de curadoria abre em uma barra lateral no mesmo plano, mantendo a paginação e o scroll do usuário e facilitando uma triagem rápida em lote.
* **Página de Detalhes Dedicada**: Rota dinâmica `/content/[id]` com visualização completa do metadado original, descrição e formulário integral de curadoria.
* **Referências / Transcrições**: Importação e visualização de vídeos do YouTube diretamente pela URL para extração de metadados e legendas (transcrições e segmentos com timestamps) sem download de arquivos de mídia.
* **Tratamento de Erros e Status Online**: Indicador de conexão na barra de cabeçalho que avisa em tempo real se a API FastAPI cair, apresentando um banner explicativo de instrução para restabelecer a conexão.

### Quadro visual externo
O quadro interno legado do workshop foi removido do fluxo recomendado. A direção atual é usar o **Canva** como provider visual externo principal.

#### Configuração recomendada: OAuth do Canva

Configure estas variáveis no backend:

```ini
CANVA_CLIENT_ID=
CANVA_CLIENT_SECRET=
CANVA_REDIRECT_URI=http://localhost:8000/canva/oauth/callback
CANVA_BASE_URL=https://api.canva.com/rest/v1
CANVA_OAUTH_AUTHORIZE_URL=https://www.canva.com/api/oauth/authorize
CANVA_SCOPES=design:content:write design:meta:read
```

Passo a passo:
1. Crie uma integração no Canva Developer Portal.
2. Configure a redirect URI exatamente como `CANVA_REDIRECT_URI`.
3. Garanta os scopes `design:content:write` e `design:meta:read`.
4. Suba o backend.
5. Acesse [http://localhost:8000/canva/oauth/start](http://localhost:8000/canva/oauth/start).
6. Autorize a aplicação no Canva.
7. Volte ao app e crie o board externo normalmente.

Observações:
* `CANVA_ACCESS_TOKEN` ainda funciona como fallback temporário/dev se não houver token OAuth salvo.
* O backend renova automaticamente o access token usando o refresh token quando necessário.
* Se o refresh falhar, o utilizador deve reconectar o Canva.
* Os links de visualização e edição podem ser temporários; use o refresh de URL no app quando expirarem.
* Designs em branco no Canva são esperados nesta fase do fluxo.


---

## Execução via Docker Compose (Stack de Desenvolvimento Completa)

Você pode subir toda a infraestrutura local (banco Postgres, aplicação das migrations do Alembic, backend FastAPI e frontend Next.js) com um único comando:

### 1. Rodar a stack completa
```bash
docker compose up --build
```

Este comando executa a seguinte ordem de inicialização:
1. Sobe o banco Postgres e aguarda estar saudável (`pg_isready`).
2. Executa o contêiner `dark_content_migrate` aplicando todas as revisões pendentes do Alembic (`alembic upgrade head`) e finaliza com sucesso.
3. Sobe o backend FastAPI e aguarda o healthcheck (`GET /health`) retornar sucesso.
4. Sobe o frontend Next.js expondo a porta 3000 com volumes vinculados ao seu host para hot-reloading em tempo real.

### 2. URLs de Acesso
- **Frontend (Painel de Curadoria):** [http://localhost:3000](http://localhost:3000)
- **Backend Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Host do Postgres:** `localhost:5433`

### 3. Comandos Úteis

* **Rodar apenas o Postgres em segundo plano:**
  ```bash
  docker compose up -d postgres
  ```
* **Rodar as migrations manualmente:**
  ```bash
  docker compose run --rm migrate
  ```
* **Conectar o container do n8n à rede do projeto:**
  ```bash
  docker network connect content_radar_net n8n
  ```

### 4. Configuração do n8n (Acesso à BD do Projeto)
Configure o nó do **PostgreSQL** dentro do workflow do n8n com os parâmetros:
* **Host:** `dark_content_postgres`
* **Port:** `5432` (porta interna do contêiner)
* **Database:** `dark_content_radar`
* **User:** `radar`
* **Password:** `radar`
* **SSL:** `Disable`

---

## Módulo de Referências e Transcrições (YouTube URL Import)

Este novo módulo permite adicionar referências analíticas importando dados de vídeos do YouTube diretamente de sua URL. Veja os detalhes em [docs/reference-transcriptions.md](file:///d:/documentos/Projetos/dark-content-radar/docs/reference-transcriptions.md).

### Novas Rotas Adicionadas:
* `POST /reference-sources/import-youtube-url` - Dispara o job de importação em background.
* `GET /reference-sources` - Lista fontes cadastradas com filtros de busca.
* `GET /reference-sources/{id}` - Obtém dados de uma referência.
* `GET /reference-import-jobs/{id}` - Acompanha o status de importação (polling).
* `GET /reference-sources/{id}/transcripts` - Lista transcrições associadas à fonte.
* `GET /transcripts/{id}/segments` - Obtém os blocos segmentados com timestamps.

> [!CAUTION]
> **Nota Legal de Uso**: As transcrições e metadados extraídos pelo portal destinam-se exclusivamente a análises de engajamento, triagem editorial e inspiração original para criação de roteiros próprios. O sistema não deve ser utilizado para plágio ou cópia não autorizada de conteúdos protegidos por direitos autorais de terceiros.

