# Case Radar — Manual Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar um Case Radar nativo e manual dentro do Content Radar que recebe um tema, descobre fontes em YouTube/X/TikTok/Instagram/Reddit/web, coleta contexto social útil, agrupa reposts no mesmo caso, pesquisa proveniência e contexto, e entrega dossiês verificáveis com fontes e níveis de confiança.

**Architecture:** O FastAPI cria e consulta runs duráveis em PostgreSQL. Um `case_worker` leve e separado reclama runs com lease/heartbeat, executa a pipeline por estágios e persiste tudo incrementalmente. Providers são adapters intercambiáveis atrás de um contrato canônico; falhas individuais degradam para cobertura parcial. `ResearchCase` agrega várias `ResearchSource`, comentários ficam em `SocialContextItem`, alegações em `CaseClaim` e sua proveniência em `CaseEvidence`. YouTube/referências/transcrições reutilizam o subsistema existente; o Case Radar não cria uma segunda stack de STT.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, PostgreSQL 16, Alembic, httpx/requests, YouTube Data API/yt-dlp já existentes, providers sociais opcionais, pytest, Docker Compose, Next.js 14, React 18, TypeScript, Tailwind CSS.

**Spec:** `docs/superpowers/specs/2026-09-12-case-radar-manual-research-design.md`

## Global Constraints

- Implementação somente manual nesta fase: sem scheduler, watchers, alertas ou monitoramento contínuo.
- Não sobrecarregar `ContentItem` para representar um caso; `ResearchCase` é uma entidade própria.
- Não depender de n8n para executar Case Radar.
- Não executar pesquisas longas com `FastAPI BackgroundTasks`; a execução durável pertence ao `case_worker`.
- Não adicionar Redis/Celery nesta fase; usar PostgreSQL com `FOR UPDATE SKIP LOCKED`, lease e recuperação de jobs órfãos.
- Providers falham de forma isolada. Um provider indisponível não derruba o run inteiro quando outros produziram material utilizável.
- Toda fonte persiste `platform`, `discovery_method`, URL canônica e snapshot bruto suficiente para auditoria.
- Comentários/replies são pistas; engagement nunca transforma uma alegação em fato.
- Distinguir sempre `earliest_known_source`, `likely_original_source` e origem confirmada.
- Nenhum provider logado implementa criação/rotação automática de contas, CAPTCHA/challenge bypass ou evasão de bloqueio.
- Credenciais/cookies/sessões nunca são persistidos no banco nem retornados pela API; configuração somente por ambiente/arquivo local ignorado pelo git.
- Providers pagos/oficiais são opcionais. O sistema deve conseguir operar em modo free-first com cobertura reduzida.
- `0019` e `0020` são migrations já aplicadas e não podem ser reescritas. A fundação Case Radar começa em `0021` com `down_revision = "0020_allow_whisperx_source"`.
- Reutilizar `ReferenceSource`, `Transcript`, `SpeechJob` e o importer atual quando uma fonte vira referência/transcrição.
- Downloads de mídia não são requisito da descoberta; fingerprint de bytes só é usado quando os bytes já estiverem legitimamente disponíveis no storage do projeto.
- Antes de declarar conclusão, rodar a suíte Case Radar, regressão backend relevante, migration smoke e build TypeScript/Next.

---

## Locked file map

### Domain/database
- Create: `src/models/case_radar.py`
- Create: `src/schemas/case_radar.py`
- Create: `src/repositories/case_radar.py`
- Modify: `src/db/base.py`
- Create: `alembic/versions/0021_add_case_radar_foundation.py`

### Provider/core research modules
- Create: `src/case_radar/__init__.py`
- Create: `src/case_radar/types.py`
- Create: `src/case_radar/providers/__init__.py`
- Create: `src/case_radar/providers/base.py`
- Create: `src/case_radar/providers/registry.py`
- Create: `src/case_radar/providers/web_search.py`
- Create: `src/case_radar/providers/youtube.py`
- Create: `src/case_radar/providers/reddit.py`
- Create: `src/case_radar/providers/x.py`
- Create: `src/case_radar/providers/tiktok.py`
- Create: `src/case_radar/providers/instagram.py`
- Create: `src/case_radar/url_normalization.py`
- Create: `src/case_radar/query_generator.py`
- Create: `src/case_radar/social_context.py`
- Create: `src/case_radar/clustering.py`
- Create: `src/case_radar/provenance.py`
- Create: `src/case_radar/dossier.py`
- Create: `src/case_radar/orchestrator.py`

### Service/API/worker
- Create: `src/services/case_radar_service.py`
- Create: `src/services/case_radar_reference_service.py`
- Create: `src/api/routes/case_radar.py`
- Modify: `src/api/main.py`
- Create: `case_worker/__init__.py`
- Create: `case_worker/worker.py`
- Modify: `docker-compose.yml`
- Modify: `.env.example`

### Frontend
- Create: `frontend/app/case-radar/page.tsx`
- Create: `frontend/app/case-radar/[id]/page.tsx`
- Create: `frontend/components/case-radar/research-form.tsx`
- Create: `frontend/components/case-radar/run-status.tsx`
- Create: `frontend/components/case-radar/case-list.tsx`
- Create: `frontend/components/case-radar/case-dossier.tsx`
- Modify: `frontend/components/layout/sidebar.tsx`
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/lib/types.ts`

### Tests
- Create: `src/test_case_radar_models.py`
- Create: `src/test_case_radar_repository.py`
- Create: `src/test_case_radar_api.py`
- Create: `src/test_case_radar_query_generator.py`
- Create: `src/test_case_radar_providers.py`
- Create: `src/test_case_radar_web_search.py`
- Create: `src/test_case_radar_youtube.py`
- Create: `src/test_case_radar_reddit.py`
- Create: `src/test_case_radar_social_context.py`
- Create: `src/test_case_radar_clustering.py`
- Create: `src/test_case_radar_provenance.py`
- Create: `src/test_case_radar_dossier.py`
- Create: `src/test_case_radar_reference_service.py`
- Create: `src/test_case_radar_orchestrator.py`
- Create: `src/test_case_worker_bootstrap.py`

---

## Milestone 1 — Fundação durável e API manual

### Task 1: Definir contratos canônicos e validação da request

**Files:** `src/case_radar/types.py`, `src/schemas/case_radar.py`, `src/test_case_radar_models.py`.

**Interfaces obrigatórias:**

```python
Platform = Literal["youtube", "x", "tiktok", "instagram", "reddit", "web"]
ResearchDepth = Literal["quick", "balanced", "deep"]
CostClass = Literal["free", "metered", "paid"]

class ProviderCapabilities(BaseModel):
    search_supported: bool
    source_fetch_supported: bool
    comments_supported: bool
    replies_supported: bool
    quote_posts_supported: bool
    media_metadata_supported: bool
    historical_search_supported: bool
    authenticated: bool
    official_api: bool
    cost_class: CostClass

class Candidate(BaseModel):
    platform: Platform
    external_id: str | None
    canonical_url: str
    author_handle: str | None
    author_display_name: str | None
    title_or_caption: str | None
    text: str | None
    published_at: datetime | None
    media_type: str | None
    thumbnail_url: str | None
    duration_seconds: float | None
    language: str | None
    engagement: dict[str, int]
    hashtags: list[str]
    relation: dict[str, Any] | None
    discovery_query: str
    discovery_method: str
    raw_json: dict[str, Any]
    source_confidence: float
```

`CaseResearchCreate` deve aceitar `theme`, `desired_usable_cases`, `languages`, `platforms`, datas opcionais, include/exclude terms, priorities, exclusions, `research_depth`, `provider_budgets` e `global_result_budget`. Limites: tema não vazio, target 1–50, budget global 1–5000, datas coerentes.

- [ ] Escrever testes que rejeitem tema vazio, target 0/51, budget inválido e `date_from > date_to`.
- [ ] Rodar `python -m pytest src/test_case_radar_models.py -q` e confirmar falha.
- [ ] Implementar apenas os contratos/validators necessários.
- [ ] Rodar novamente e confirmar verde.
- [ ] Commit: `feat: define Case Radar contracts`.

### Task 2: Criar modelos SQLAlchemy e migration 0021

**Files:** `src/models/case_radar.py`, `src/db/base.py`, `alembic/versions/0021_add_case_radar_foundation.py`, `src/test_case_radar_models.py`.

Criar as tabelas: `case_research_runs`, `case_research_queries`, `research_sources`, `research_cases`, `case_sources`, `social_context_items`, `case_claims`, `case_evidence`, `media_fingerprints`.

`CaseResearchRun` deve incluir queue durability: `status`, `stage`, `progress_percent`, `request_json`, `provider_coverage_json`, contadores, `worker_id`, `lease_expires_at`, `heartbeat_at`, `cancel_requested_at`, `errors_json`, timestamps.

`ResearchSource` deve poder apontar opcionalmente para `content_items.id` e `reference_sources.id`. `CaseEvidence` pode apontar para source, social item ou transcript segment, exigindo ao menos um alvo por check constraint.

- [ ] Adicionar testes de colunas/constraints/relationships antes do modelo.
- [ ] Confirmar falha.
- [ ] Implementar modelos e registrar todos em `src/db/base.py`.
- [ ] Criar `0021_add_case_radar_foundation.py` com `down_revision = "0020_allow_whisperx_source"`.
- [ ] Smoke local/CI: `alembic upgrade head`, `alembic downgrade 0020_allow_whisperx_source`, `alembic upgrade head` em banco de teste descartável.
- [ ] Rodar `python -m pytest src/test_case_radar_models.py src/test_speech_worker_bootstrap.py -q` para garantir que o registro dos mappers continua válido.
- [ ] Commit: `feat: add Case Radar data model`.

### Task 3: Implementar repository de runs, leases e dados de pesquisa

**Files:** `src/repositories/case_radar.py`, `src/test_case_radar_repository.py`.

Interfaces mínimas:

```python
create_run(request_json) -> CaseResearchRun
get_run(run_id) -> CaseResearchRun | None
list_runs(limit, offset) -> tuple[list[CaseResearchRun], int]
request_cancel(run_id) -> CaseResearchRun | None
claim_next(worker_id, lease_seconds) -> CaseResearchRun | None
heartbeat(run_id, worker_id, lease_seconds, *, stage, progress_percent, message=None)
recover_stale_leases(now=None) -> int
complete(run_id, worker_id, *, partial: bool, summary: dict)
fail(run_id, worker_id, error_code, error_message)
upsert_query(...)
upsert_source(candidate, run_id, query_id) -> ResearchSource
create_social_item(...)
create_case(...)
link_case_source(...)
```

`claim_next()` usa `SELECT ... FOR UPDATE SKIP LOCKED`. Run queued cancelado termina imediatamente; running recebe `cancel_requested_at`. Lease vencido reencaminha para queued, salvo cancelamento solicitado.

- [ ] Escrever testes com session fake/DB de teste para claim exclusivo, heartbeat, cancel e stale recovery.
- [ ] Confirmar falha.
- [ ] Implementar repository mínimo.
- [ ] Rodar `python -m pytest src/test_case_radar_repository.py -q`.
- [ ] Commit: `feat: add durable Case Radar repository`.

### Task 4: Expor API manual de runs e revisão

**Files:** `src/services/case_radar_service.py`, `src/api/routes/case_radar.py`, `src/api/main.py`, `src/test_case_radar_api.py`.

Endpoints:

```text
POST   /case-radar/runs
GET    /case-radar/runs
GET    /case-radar/runs/{run_id}
POST   /case-radar/runs/{run_id}/cancel
GET    /case-radar/runs/{run_id}/queries
GET    /case-radar/runs/{run_id}/sources
GET    /case-radar/runs/{run_id}/cases
GET    /case-radar/cases/{case_id}
PATCH  /case-radar/cases/{case_id}
```

Patch manual aceita apenas curadoria (`status`, `manual_notes`, `already_used`, `selected_primary_source_id`) e não deixa o cliente falsificar confidence/provenance automática.

- [ ] Testar 201 ao criar, 404 ausente, cancel, paginação e patch restrito via dependency override como `test_speech_api.py`.
- [ ] Confirmar falha.
- [ ] Implementar service/router e registrar no `main.py` com prefix `/case-radar`.
- [ ] Rodar `python -m pytest src/test_case_radar_api.py -q`.
- [ ] Commit: `feat: expose manual Case Radar API`.

---

## Milestone 2 — Query generation e providers

### Task 5: Gerar e persistir queries multilíngues reproduzíveis

**Files:** `src/case_radar/query_generator.py`, `src/test_case_radar_query_generator.py`.

Implementar baseline determinístico que produza intents `core`, `source_hunt`, `context`, `debunk`, `local_language` por idioma solicitado. PT/EN/ES devem ter vocabulário nativo inicial; outros idiomas podem começar com tema original + variantes neutras, sem fingir tradução de alta qualidade.

A saída é `GeneratedQuery(language, intent, query_text, target_platforms)`. Deduplicar por texto normalizado. `include_terms` entra em pelo menos uma variante; `exclude_terms` vira filtro downstream, não texto destrutivo da query quando o provider não suporta operadores.

A melhoria por LLM é opcional e posterior ao baseline: falha de IA nunca impede pesquisa.

- [ ] Testar determinismo, dedupe, PT/EN/ES, include terms e limites por depth.
- [ ] Confirmar falha.
- [ ] Implementar baseline.
- [ ] Persistir queries no início do run pelo orchestrator somente em task posterior; aqui testar função pura.
- [ ] Commit: `feat: generate Case Radar research queries`.

### Task 6: Criar contrato de provider, registry, budgets e fallback

**Files:** `src/case_radar/providers/base.py`, `src/case_radar/providers/registry.py`, `src/test_case_radar_providers.py`.

Contrato:

```python
class CaseRadarProvider(Protocol):
    name: str
    platform: Platform
    capabilities: ProviderCapabilities
    def search(self, request, query, cursor=None) -> CandidatePage: ...
    def fetch_source(self, candidate) -> SourceSnapshot: ...
    def fetch_social_context(self, source, options) -> SocialContextPage: ...
```

Registry resolve `platform + method`, expõe disponibilidade e respeita prioridade configurável. `ProviderBudget` rastreia requests/resultados/custo lógico e impede uma fonte de consumir o run inteiro. Erros são normalizados em `ProviderUnavailable`, `ProviderAuthExpired`, `ProviderRateLimited`, `ProviderPermanentError`.

- [ ] Testar provider sem capability, fallback A→B, budget esgotado e erro parcial.
- [ ] Confirmar falha.
- [ ] Implementar abstrações sem rede real.
- [ ] Commit: `feat: add Case Radar provider registry`.

### Task 7: Implementar normalização de URLs + Web Search provider

**Files:** `src/case_radar/url_normalization.py`, `src/case_radar/providers/web_search.py`, `src/test_case_radar_web_search.py`.

Normalizar URLs de `x.com`, `twitter.com`, `tiktok.com`, `instagram.com`, `reddit.com`, `youtu.be/youtube.com` removendo tracking sem destruir IDs. Web provider deve usar uma interface de search backend configurável; não acoplar lógica de Case Radar a Google/Bing específico. Primeiro backend pode ser um HTTP search endpoint configurado por `CASE_RADAR_WEB_SEARCH_URL`/key ou um adapter explicitamente desabilitado quando não configurado.

Para descoberta social indireta, construir `site:x.com`, `site:tiktok.com`, etc. e converter resultados em `Candidate` com `discovery_method="web_search"`.

- [ ] Testar canonicalização e parsing com fixtures; nenhum teste chama internet.
- [ ] Testar backend ausente retorna provider indisponível, não crash global.
- [ ] Implementar.
- [ ] Commit: `feat: add web discovery provider`.

### Task 8: Adaptar YouTube sem duplicar infraestrutura

**Files:** `src/case_radar/providers/youtube.py`, `src/test_case_radar_youtube.py`.

Reusar a configuração `YOUTUBE_API_KEY` e a lógica de descoberta/metadados existente onde for possível. Converter resultados a `Candidate`; `fetch_source` pode enriquecer metadata. Não criar uma segunda tabela de transcript/caption.

- [ ] Testar normalização de vídeo, ausência de key e quota/error mapping com client fake.
- [ ] Implementar adapter.
- [ ] Garantir que nenhuma importação Case Radar puxa WhisperX/Torch.
- [ ] Commit: `feat: add YouTube Case Radar provider`.

### Task 9: Implementar Reddit com árvore de comentários preservada

**Files:** `src/case_radar/providers/reddit.py`, `src/test_case_radar_reddit.py`.

Provider aceita modo público/configurado. Normalizar post e comentários mantendo `platform_item_id`, `parent_id`, depth, author, body, score, created_at, permalink e links externos. Limitar comments por depth budget.

- [ ] Testar post search fixture, parent/child comments, deleted author/body, rate-limit mapping.
- [ ] Implementar sem dependência obrigatória nova se HTTP oficial/publico for suficiente.
- [ ] Commit: `feat: add Reddit research provider`.

### Task 10: Implementar família X com três métodos

**Files:** `src/case_radar/providers/x.py`, `src/test_case_radar_providers.py`, `.env.example`.

Métodos registrados: `x:web_search`, `x:logged_in`, `x:official_api`.

- `web_search` delega ao provider genérico com domínio X.
- `official_api` só fica available quando token/config estiver presente.
- `logged_in` é adapter opcional carregado preguiçosamente; sessão vem de `CASE_RADAR_X_SESSION_FILE` ou configuração equivalente local. Se biblioteca/session não existir, retorna unavailable. Challenge/login expirado retorna `ProviderAuthExpired`; não tentar contornar.
- Replies/quote posts só são declarados capability quando o método realmente os suporta.

- [ ] Testar registry/capabilities e normalização com fixtures, sem login real.
- [ ] Testar que session/token nunca aparece em `raw_json` ou erro serializado.
- [ ] Implementar lazy import para dependência experimental.
- [ ] Commit: `feat: add layered X providers`.

### Task 11: Implementar famílias TikTok e Instagram

**Files:** `src/case_radar/providers/tiktok.py`, `src/case_radar/providers/instagram.py`, `src/test_case_radar_providers.py`, `.env.example`.

Cada plataforma expõe `web_search`, `logged_in` opcional e `official` quando realmente configurado. TikTok official/research não pode ser tratado como universal; Instagram official não promete busca global de Reels. Capabilities refletem o que o adapter ativo consegue fazer.

- [ ] Testar normalização de URLs/posts, disponibilidade por configuração, comments capability e auth-expired.
- [ ] Implementar lazy adapters.
- [ ] Garantir que a aplicação sobe mesmo sem nenhuma biblioteca experimental instalada.
- [ ] Commit: `feat: add TikTok and Instagram providers`.

---

## Milestone 3 — Contexto, deduplicação e investigação

### Task 12: Rankear contexto social por utilidade investigativa

**Files:** `src/case_radar/social_context.py`, `src/test_case_radar_social_context.py`.

Funções puras primeiro:

```python
classify_social_item(text, *, author_reply, pinned, language) -> set[str]
score_social_item(item, unresolved_questions=()) -> float
select_social_context(items, limit) -> list[RankedSocialItem]
```

Categorias: `origin`, `context`, `correction`, `debunk`, `link`, `author_response`, `witness_claim`, `technical_explanation`. Sinais: URL, datas, lugares/entidades, vocabulário PT/EN/ES, author reply, pinned, engagement log-scaled, reply depth. Reaction-only recebe score baixo.

- [ ] Testar comentários úteis acima de “que medo kkk”, mas sem marcar comentário popular como corroborado.
- [ ] Testar limite/depth e parent chain preservada.
- [ ] Implementar.
- [ ] Commit: `feat: rank investigative social context`.

### Task 13: Clusterizar fontes sem merges destrutivos

**Files:** `src/case_radar/clustering.py`, `src/test_case_radar_clustering.py`.

Criar `ClusterDecision(score, reasons, action)` onde action é `merge`, `suggest`, `separate`. Sinais v1: external-id/URL exatos, linked URL, texto/caption normalizado, entidades, alleged date/location, thumbnail hash quando já disponível, transcript similarity quando existe. Media perceptual fingerprint fica plugável, não bloqueante.

Thresholds iniciais devem ser explícitos/configuráveis e testados; baixo confidence gera sugestão e não merge automático.

- [ ] Testar repost óbvio, casos parecidos mas diferentes, canonical URL duplicate e ambiguous suggestion.
- [ ] Implementar funções puras antes de persistência.
- [ ] Adicionar persistência de `MediaFingerprint` apenas para hashes que já existirem.
- [ ] Commit: `feat: cluster Case Radar sources`.

### Task 14: Resolver proveniência e claims/evidence

**Files:** `src/case_radar/provenance.py`, `src/test_case_radar_provenance.py`.

Resolver separadamente:

```python
ProvenanceResult(
    earliest_known_source_id,
    likely_original_source_id,
    origin_status,  # unknown | likely | confirmed
    confidence,
    reasons,
)
```

Claims usam status `source_claimed`, `corroborated`, `contradicted`, `unverified`. Uma claim só vira corroborated com evidência independente suficiente segundo regra explícita; comentário isolado não basta. Persistir `CaseEvidence.stance = supports|contradicts|context_only`.

- [ ] Testar repost de 2026 apontando para post de 2021: earliest conhecido = 2021.
- [ ] Testar comentário “isso foi no Canadá” sem outra fonte: claim unverified/source_claimed.
- [ ] Testar duas fontes independentes e uma fonte contraditória.
- [ ] Implementar.
- [ ] Commit: `feat: resolve case provenance and evidence`.

### Task 15: Gerar dossiê factual e auditável

**Files:** `src/case_radar/dossier.py`, `src/test_case_radar_dossier.py`.

Dossiê retornado pela API contém: title, summary, what_happens, primary/earliest/likely-original sources, alleged date/location, verified context, unverified claims, contradictions, alternative explanations/debunks, useful social context, transcript/timestamps quando ligados, provenance/research confidence, provider coverage e source links.

O gerador pode ter camada de texto assistida por IA, mas o objeto factual base é construído deterministicamente das entidades persistidas. IA nunca cria source IDs/links; resposta gerada é validada contra evidence IDs existentes.

- [ ] Testar que toda claim material do objeto factual tem evidence IDs.
- [ ] Testar separação verified/unverified/contradicted.
- [ ] Implementar deterministic dossier builder.
- [ ] Deixar summarizer IA opcional atrás de adapter, com fallback ao factual builder.
- [ ] Commit: `feat: build auditable case dossiers`.

### Task 16: Integrar ResearchSource com Biblioteca e Speech

**Files:** `src/services/case_radar_reference_service.py`, `src/test_case_radar_reference_service.py`.

Operações:

```python
promote_to_reference(source_id) -> ReferenceSource
request_transcription(source_id, preset="balanced") -> SpeechJob | ReferenceImportJob
```

YouTube usa `ReferenceSource(source_type="youtube_video")`/import path existente e deduplica por video id. Fonte não-YouTube só pode virar referência se o `ReferenceSource` suportar o tipo; se a constraint atual não suportar, criar migration futura separada e pequena apenas quando essa promoção realmente for implementada. Não esconder plataformas como `manual` para contornar schema.

Quando transcript existe, `CaseEvidence` pode apontar para `TranscriptSegment`. Não duplicar texto/timestamps como uma segunda transcript table.

- [ ] Testar reuse de reference YouTube existente.
- [ ] Testar source novo e transcription request sem criar job duplicado.
- [ ] Testar evidence ligado a transcript segment.
- [ ] Implementar inicialmente YouTube + referências já suportadas; expansão de source_type deve ter migration própria se necessária.
- [ ] Commit: `feat: connect Case Radar to references and speech`.

---

## Milestone 4 — Orquestração, worker e UI

### Task 17: Implementar orchestrator por estágios e conclusão parcial

**Files:** `src/case_radar/orchestrator.py`, `src/test_case_radar_orchestrator.py`.

Pipeline:

```text
generating_queries
-> discovering
-> enriching_sources
-> collecting_social_context
-> clustering_cases
-> researching_cases
-> finalizing
```

Cada estágio é idempotente o bastante para replay após lease vencido: queries usam unique key do run, sources fazem upsert, social items dedupam por platform item id, case-source links têm unique constraint. O orchestrator verifica cancelamento entre chamadas caras.

Critério terminal:
- `completed`: atingiu target ou encerrou naturalmente com cobertura suficiente e sem falha material.
- `partially_completed`: produziu casos/dossiês, mas provider failure/budget impediu cobertura/target.
- `failed`: nenhuma saída útil e erro terminal.
- `cancelled`: pedido do usuário.

- [ ] Criar fakes de providers e testar happy path, fallback, budget, cancel e retry idempotente.
- [ ] Confirmar falha.
- [ ] Implementar um estágio de cada vez até teste verde.
- [ ] Commit: `feat: orchestrate manual Case Radar research`.

### Task 18: Criar case_worker durável e Compose

**Files:** `case_worker/__init__.py`, `case_worker/worker.py`, `src/test_case_worker_bootstrap.py`, `docker-compose.yml`, `.env.example`.

Worker semelhante ao speech worker, mas leve e sem GPU:

```python
while True:
    repo.recover_stale_leases()
    run = repo.claim_next(worker_id, lease_seconds)
    if run:
        orchestrator.execute(run, heartbeat=..., cancel_check=...)
    else:
        sleep(poll_seconds)
```

Importar `src.db.base` antes de configurar Session para registrar todos os mappers.

Env inicial:

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

Compose usa o Dockerfile normal, `command: python -m case_worker.worker`, mesma network/DB; sem `gpus: all`.

- [ ] Testar bootstrap com `configure_mappers()` em subprocess.
- [ ] Testar `run_once` com repo/orchestrator fake.
- [ ] Adicionar service ao Compose e envs sem valores secretos reais.
- [ ] Commit: `feat: add durable Case Radar worker`.

### Task 19: Implementar UI de criação/listagem de runs

**Files:** `frontend/lib/types.ts`, `frontend/lib/api.ts`, `frontend/components/layout/sidebar.tsx`, `frontend/components/case-radar/research-form.tsx`, `frontend/components/case-radar/run-status.tsx`, `frontend/app/case-radar/page.tsx`.

Tela principal: formulário manual + runs recentes. Defaults: `balanced`, PT/EN/ES, todas as plataformas habilitadas, budgets conservadores. Mostrar claramente provider availability/coverage quando API expuser. Não pedir credenciais na UI nesta fase.

`api.ts` adiciona `createCaseResearchRun`, `getCaseResearchRuns`, `getCaseResearchRun`, `cancelCaseResearchRun`. `types.ts` espelha schemas backend sem `any` desnecessário.

- [ ] Implementar tipos/API primeiro para TypeScript acusar inconsistências.
- [ ] Adicionar item `Case Radar` no sidebar.
- [ ] Implementar form com validação client-side equivalente aos limites principais.
- [ ] Implementar polling somente enquanto status não terminal, com cleanup de timer ao desmontar.
- [ ] Rodar `cd frontend && npx tsc --noEmit`.
- [ ] Commit: `feat: add Case Radar research UI`.

### Task 20: Implementar tela de run e dossiê por caso

**Files:** `frontend/app/case-radar/[id]/page.tsx`, `frontend/components/case-radar/case-list.tsx`, `frontend/components/case-radar/case-dossier.tsx`, `frontend/lib/api.ts`, `frontend/lib/types.ts`.

Mostrar stages/progress, provider coverage/errors, generated queries, source counts e casos. Cada case mostra origem mais antiga, provável original, confiança, fontes, contexto social útil, claims por status, debunks/alternativas, transcript timestamps e ações de curadoria (`approved`, `rejected`, duplicate/already-used conforme schema final).

- [ ] Implementar payload de detalhe sem N+1 HTTP excessivo: endpoint de case detail deve retornar dossier agregado.
- [ ] Adicionar ações patch com optimistic state somente após resposta 2xx.
- [ ] Links externos usam `target="_blank" rel="noreferrer"`.
- [ ] Rodar `cd frontend && npx tsc --noEmit && npm run build`.
- [ ] Commit: `feat: add Case Radar dossier UI`.

---

## Milestone 5 — Verificação real e fechamento

### Task 21: Teste integrado sem internet e regressão

Criar fixtures fake para uma run que descobre o mesmo clipe em X/Reddit/YouTube, um comentário com link de origem e uma matéria de contexto. O teste deve provar: query persistence -> candidates -> social ranking -> clustering -> provenance -> dossier -> partial/completed state.

- [ ] Rodar:

```powershell
docker compose run --rm --no-deps backend sh -lc "pip install pytest >/dev/null 2>&1 && python -m pytest -q src/test_case_radar_models.py src/test_case_radar_repository.py src/test_case_radar_api.py src/test_case_radar_query_generator.py src/test_case_radar_providers.py src/test_case_radar_web_search.py src/test_case_radar_youtube.py src/test_case_radar_reddit.py src/test_case_radar_social_context.py src/test_case_radar_clustering.py src/test_case_radar_provenance.py src/test_case_radar_dossier.py src/test_case_radar_reference_service.py src/test_case_radar_orchestrator.py src/test_case_worker_bootstrap.py"
```

- [ ] Rodar regressão speech relevante, porque Case Radar importa modelos/referências compartilhados:

```powershell
docker compose run --rm --no-deps backend sh -lc "pip install pytest >/dev/null 2>&1 && python -m pytest -q src/test_speech_job_models.py src/test_speech_job_repository.py src/test_speech_jobs_service.py src/test_speech_worker_bootstrap.py src/test_speech_result_importer.py src/test_speech_api.py"
```

- [ ] Rodar migration smoke em banco descartável.
- [ ] Rodar `docker compose config` e confirmar `case_worker` válido.
- [ ] Rodar `cd frontend; npx tsc --noEmit; npm run build`.
- [ ] Commit apenas correções descobertas pelos gates, separadas por causa.

### Task 22: Smoke real provider-by-provider e documentação operacional

Realizar smoke de cada provider configurado sem exigir que todos estejam disponíveis. Registrar capabilities e comportamento, não tokens.

Sequência:
1. Web Search: uma query e uma descoberta social indexada.
2. YouTube: busca real pequena e metadata.
3. Reddit: post + comentários quando configuração permitir.
4. X web; depois logged-in se sessão manual estiver configurada; official só se token/plano existir.
5. TikTok web; logged-in/official somente se configurados.
6. Instagram web; logged-in/official somente se configurados.
7. Rodar uma pesquisa manual de 2–3 casos com tema controlado e inspecionar dossiês.

Critérios de aceite:
- nenhum segredo aparece em logs/API;
- unavailable provider aparece como cobertura reduzida, não crash;
- pelo menos um run real chega a `completed` ou `partially_completed` com dossier válido;
- URLs/fontes do dossier abrem para a fonte correspondente;
- comentários não verificados permanecem marcados como tal;
- reposts óbvios não viram vários casos finais;
- cancellation interrompe entre operações externas;
- restart do worker recupera lease vencido sem duplicar sources/cases.

- [ ] Atualizar `README.md` com a nova área Case Radar, startup do `case_worker`, providers opcionais e limites conhecidos.
- [ ] Não documentar técnicas de bypass ou rotação automática de conta.
- [ ] Rodar suíte backend completa disponível (`python -m pytest -q`) antes de declarar feature pronta; qualquer falha preexistente deve ser identificada separadamente, não ignorada.
- [ ] Commit: `docs: document Case Radar operation`.

---

## Execution order and checkpoints

1. Tasks 1–4: fundação + API. Checkpoint: criar/cancelar/listar run sem executar pesquisa.
2. Tasks 5–11: discovery providers. Checkpoint: gerar queries e obter candidates normalizados com fakes + pelo menos providers estáveis configurados.
3. Tasks 12–16: inteligência de pesquisa. Checkpoint: dado um conjunto conhecido de sources/comments, produzir case cluster + provenance + dossier auditável.
4. Tasks 17–18: execução durável. Checkpoint: worker processa run end-to-end, sobrevive restart e suporta partial completion.
5. Tasks 19–20: UI. Checkpoint: criar run, acompanhar e revisar dossiers pela interface.
6. Tasks 21–22: verificação. Só depois deste gate considerar Case Radar manual pronto.

## Implementation notes

- Começar a implementação em uma branch de implementação criada a partir de `agent/case-radar-design`; não desenvolver diretamente em `main`.
- Como `agent/case-radar-design` foi baseada em Speech Phase 2 ainda não totalmente verificada, antes do merge final deve haver um gate explícito de regressão Speech. O Case Radar não deve mascarar pendências da Phase 2.
- Cada task deve seguir red-green-refactor e gerar commit pequeno. Não juntar migration, todos os providers, UI e worker em um único commit.
- Providers logados são adapters experimentais e opcionais: a primeira versão útil não depende deles para subir nem para concluir uma pesquisa com cobertura parcial.
