# Content Radar

Content Radar é uma ferramenta de pesquisa de conteúdo com um objetivo simples:

```text
encontrar algo útil -> pesquisar/verificar -> salvar/transcrever -> registrar uma ideia -> trabalhar manualmente depois
```

Ele não tenta ser editor de roteiro, gestor de produção ou ferramenta de design.

## Áreas principais

### Radar

`/content`

Serve para descobrir conteúdos coletados e decidir rapidamente o que merece atenção.

Mantém:

- título, fonte, data, views, views/dia e score;
- busca, filtros e ordenação;
- abertura da fonte original;
- status simples de triagem;
- notas pessoais.

### Case Radar

`/case-radar`

Pesquisa manual de casos e vídeos para investigação. O usuário descreve um tema, escolhe idiomas/plataformas e define quantos casos utilizáveis deseja. Um worker separado executa a pesquisa em estágios e mantém o progresso no PostgreSQL, então fechar a página não interrompe a execução.

O Case Radar pode descobrir e cruzar material de:

- YouTube;
- X/Twitter;
- TikTok;
- Instagram;
- Reddit;
- web geral.

O desenho é **free-first**. X, TikTok e Instagram aceitam caminhos em camadas quando configurados: descoberta via web, sessão autenticada experimental e provider oficial quando houver credenciais/acesso apropriado. Nenhum provider pago é obrigatório para a aplicação subir.

No Reddit, a ordem de fallback é: OAuth application-only quando `REDDIT_CLIENT_ID` e `REDDIT_CLIENT_SECRET` estiverem configurados, endpoint público direto quando disponível e, por fim, descoberta via web. A falta de credenciais ou o bloqueio de um caminho não deve derrubar a pesquisa inteira.

A pesquisa tenta:

- gerar consultas em PT/EN/ES;
- encontrar posts, vídeos e páginas relacionadas;
- coletar comentários/replies quando o provider suporta;
- dar prioridade a comentários com origem, contexto, correções, links, debunks e respostas do autor;
- agrupar reposts e fontes que parecem representar o mesmo caso;
- identificar a fonte mais antiga conhecida e uma provável origem sem fingir certeza;
- manter alegações como `unverified`, `source_claimed`, `corroborated` ou `contradicted`;
- produzir um dossiê auditável com links e evidências.

Comentários são tratados como **pistas/evidências**, não como fatos. Um comentário popular não é promovido a contexto confirmado só por ter muitos likes.

Consultas de `source_hunt`, `context` e `debunk` servem para enriquecer casos existentes; somente descoberta `core`/`local_language` pode iniciar um caso. O número configurado em `desired_usable_cases` também funciona como limite dos casos finais pesquisados, enquanto as fontes excedentes continuam disponíveis como material auxiliar para deduplicação e contexto.

#### Worker do Case Radar

No Docker Compose:

```bash
docker compose up -d postgres migrate backend case_worker frontend
```

O serviço `case_worker` usa o Dockerfile normal, não precisa de GPU e não depende de n8n.

Configuração básica:

```env
CASE_RADAR_WORKER_ID=case-worker-1
CASE_RADAR_WORKER_POLL_SECONDS=2
CASE_RADAR_WORKER_LEASE_SECONDS=180
CASE_RADAR_WEB_SEARCH_URL=
CASE_RADAR_WEB_SEARCH_API_KEY=
CASE_RADAR_X_SESSION_FILE=
X_BEARER_TOKEN=
CASE_RADAR_TIKTOK_SESSION_FILE=
TIKTOK_ACCESS_TOKEN=
CASE_RADAR_INSTAGRAM_SESSION_FILE=
INSTAGRAM_ACCESS_TOKEN=
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
```

Sessões/cookies ficam em arquivos locais fora do Git. Tokens e conteúdo de sessão não devem ser enviados pela API nem salvos em `raw_json`.

#### Smoke operacional

Depois de aplicar as migrations, há dois smokes manuais úteis:

```powershell
$env:PYTHONPATH="."
python scripts/case_radar_provider_smoke.py --query "unexplained footage"
python scripts/case_radar_run_smoke.py --theme "unexplained footage" --desired-cases 3
```

O primeiro registra quais providers estão disponíveis e suas capabilities sem imprimir credenciais. Providers independentes podem aparecer como `skipped`/indisponíveis quando faltam credenciais ou acesso; isso deve ser interpretado junto com os fallbacks disponíveis.

O segundo cria uma pesquisa real pequena, executa uma iteração do worker e valida que uma run `completed`/`partially_completed` produziu dossiês com URLs HTTP(S) válidas. Ele também falha se a run criar mais casos finais do que `--desired-cases`, protegendo o contrato de quantidade e evitando que todo resultado auxiliar vire um caso separado.

Uma run pode terminar como `partially_completed` mesmo atingindo a quantidade pedida quando algum provider opcional falha ou fica indisponível. Isso representa cobertura reduzida, não perda dos resultados já obtidos.

#### Limites conhecidos

- Busca web indireta em X/TikTok/Instagram não cobre toda a plataforma.
- Providers logados são opcionais/experimentais e podem parar de funcionar quando a plataforma altera o site ou a sessão expira.
- Acesso oficial pode depender de plano, aprovação ou escopo da plataforma.
- O Case Radar não cria nem rotaciona contas automaticamente e não implementa CAPTCHA/challenge bypass.
- `earliest known source` significa a fonte mais antiga que a pesquisa conseguiu sustentar, não prova absoluta de autoria original.
- Pesquisa de direitos/licenciamento para reutilização de mídia permanece fora do escopo.

### Pesquisas

`/search-configs`

Configura nichos, sementes e buscas usadas para alimentar o Radar tradicional.

### Biblioteca

`/references`

Guarda vídeos usados como referência e suas transcrições.

O Case Radar reutiliza esta infraestrutura quando uma fonte pode ser promovida para referência. Não existe uma segunda tabela/pipeline de transcrição específica do Case Radar.

A importação do YouTube suporta os caminhos já existentes de captions/transcrição e o Speech Worker nativo pode executar STT/WhisperX conforme a configuração instalada.

As transcrições preservam timestamps, versões e segmentos. O objetivo é capturar o que foi dito, não analisar ou comparar roteiros automaticamente.

### Ideias

`/ideas`

Lista leve para registrar ideias de vídeo com:

- título;
- descrição;
- nicho/assunto;
- status (`idea`, `researching`, `ready`, `archived`);
- prioridade.

O roteiro final pode ser escrito e comparado manualmente onde for mais conveniente.

## Stack ativa

- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic
- Next.js 14
- React 18
- TypeScript
- Tailwind CSS
- yt-dlp
- Speech Worker / WhisperX quando instalado

## Desenvolvimento local

### Banco

```bash
docker compose up -d postgres
```

### Migrations

```powershell
$env:DATABASE_URL="postgresql://radar:radar@localhost:5433/dark_content_radar"
.venv\Scripts\alembic upgrade head
```

### Backend

```powershell
.venv\Scripts\uvicorn src.api.main:app --reload
```

API: `http://localhost:8000`

### Case Worker

```powershell
.venv\Scripts\python -m case_worker.worker
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:3000`

## Verificações importantes

Case Radar:

```powershell
python -m pytest -q src/test_case_radar_models.py src/test_case_radar_repository.py src/test_case_radar_api.py src/test_case_radar_query_generator.py src/test_case_radar_providers.py src/test_case_radar_web_search.py src/test_case_radar_youtube.py src/test_case_radar_reddit.py src/test_case_radar_reddit_oauth.py src/test_case_radar_x.py src/test_case_radar_social_platforms.py src/test_case_radar_social_context.py src/test_case_radar_clustering.py src/test_case_radar_provenance.py src/test_case_radar_dossier.py src/test_case_radar_reference_service.py src/test_case_radar_orchestrator.py src/test_case_radar_social_source_promotion.py src/test_case_worker_bootstrap.py src/test_case_worker_protocol.py
```

Regressão Speech compartilhada:

```powershell
python -m pytest -q src/test_speech_job_models.py src/test_speech_job_repository.py src/test_speech_jobs_service.py src/test_speech_worker_bootstrap.py src/test_speech_result_importer.py src/test_speech_api.py
```

Frontend:

```powershell
cd frontend
npx tsc --noEmit
npm run build
```

Compose/migrations:

```powershell
docker compose config
alembic upgrade head
```

Antes de considerar a feature pronta para merge, também deve ser executada a suíte backend completa disponível, sem deselects específicos do Case Radar:

```powershell
python -m pytest -q
```

## Compatibilidade com dados antigos

As tabelas criadas pelo antigo workshop de vídeo e pela integração com Canva não são removidas nesta simplificação. Os dados existentes continuam no banco para evitar perda acidental.

As rotas de Canva, boards e recursos filhos do workshop não fazem mais parte do startup ativo da API. Registros antigos de `video_projects` também continuam legíveis; status antigos aparecem como legado na nova tela de Ideias até que o usuário decida alterá-los.

## Fora do escopo atual

Content Radar não pretende fazer automaticamente:

- comparação de roteiros;
- geração de roteiros finais;
- análise de estrutura de roteiro;
- criação de thumbnails;
- planejamento de música;
- gestão de produção;
- publicação ou tracking pós-publicação;
- monitoramento contínuo de temas do Case Radar;
- criação/rotação automática de contas sociais;
- bypass de controles de acesso de plataformas;
- determinação automática de direitos/licenças de reutilização.

O foco continua sendo **descoberta, investigação verificável, referências/transcrições e ideias**.
