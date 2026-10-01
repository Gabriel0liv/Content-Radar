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

O Case Radar pode descobrir e cruzar material de YouTube, X/Twitter, TikTok, Instagram, Reddit e web geral. O desenho é **free-first**: providers oficiais e sessões autenticadas são opcionais e os fallbacks disponíveis continuam utilizáveis quando um caminho falha.

Comentários/replies são tratados como **pistas/evidências**, não como fatos. A pesquisa agrupa fontes relacionadas, tenta encontrar a fonte mais antiga conhecida, preserva incerteza sobre autoria e produz um dossiê auditável com links e evidências.

#### Worker do Case Radar

```bash
docker compose up -d postgres migrate backend case_worker frontend
```

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

```powershell
$env:PYTHONPATH="."
python scripts/case_radar_provider_smoke.py --query "unexplained footage"
python scripts/case_radar_run_smoke.py --theme "unexplained footage" --desired-cases 3
```

### Biblioteca

`/references`

Guarda vídeos usados como referência e suas transcrições. O Case Radar e o Speech Suite reutilizam esta infraestrutura; não há uma segunda biblioteca de transcrição paralela.

As transcrições preservam timestamps, versões e segmentos. O objetivo é capturar o que foi dito, não analisar ou comparar roteiros automaticamente.

### Áudio / Speech Suite

`/audio`

É o workspace nativo que substitui o uso diário do antigo Speech Studio. As subseções ficam dentro de uma única entrada global **Áudio**:

- Visão geral;
- Transcrever;
- Gerar voz;
- Histórico;
- Presets;
- Vozes e modelos;
- Diagnóstico;
- Configurações.

A API principal permanece leve. WhisperX, Torch, pyannote, Kokoro, Piper e demais dependências pesadas são carregadas apenas pelo `speech_worker`. Jobs STT e TTS usam a fila PostgreSQL persistente com lease, heartbeat, cancelamento, retry, progresso e histórico.

#### STT

O fluxo de transcrição suporta upload gerenciado de áudio/vídeo, presets, idioma, diarização, quantidade de speakers, quiet speech, prompt inicial e controles avançados como modelo, device, compute type, batch, VAD, chunk size, offline/cache e formatos de exportação.

Artefatos TXT/JSON/SRT/VTT ficam em armazenamento gerenciado. Labels crus como `SPEAKER_00` não são sobrescritos por nomes de exibição. Quando o job está ligado a uma referência, o resultado pode alimentar a transcrição da Biblioteca.

#### TTS

O worker possui abstração nativa para Kokoro e Piper, com registry de vozes PT-BR, chunking, análise/normalização PT-BR, preview, geração completa, WAV/MP3, amostras de voz e comparação de vozes. A disponibilidade real depende das dependências e modelos instalados no computador do worker.

#### Requisitos do Speech Worker

Base recomendada: **Python 3.11**.

Dependências gerais:

- PostgreSQL acessível pela mesma `DATABASE_URL` do backend;
- FFmpeg no `PATH` para STT e conversões MP3;
- Torch + WhisperX para STT;
- Hugging Face token quando a diarização/modelo exigir acesso (`HF_TOKEN`);
- eSpeak/eSpeak-NG quando exigido pelo motor de TTS;
- dependências/modelos do Kokoro e/ou Piper para os motores que serão usados.

As dependências leves compartilhadas ficam em `requirements.txt`. Dependências pesadas/opcionais devem permanecer no ambiente do worker, não ser importadas pelo processo principal da API.

Variáveis úteis:

```env
SPEECH_WORKER_ID=local-worker-1
SPEECH_WORKER_POLL_SECONDS=2
SPEECH_WORKER_LEASE_SECONDS=120
SPEECH_DATA_ROOT=data/speech
SPEECH_TTS_DEVICE=cpu
SPEECH_TTS_CACHE=
SPEECH_DIARIZE_MODEL=pyannote/speaker-diarization-3.1
HF_TOKEN=
HF_HOME=
```

Inicie o worker:

```powershell
$env:PYTHONPATH="."
.venv\Scripts\python -m speech_worker.worker
```

#### Smoke real do Speech Suite

Os scripts abaixo executam jobs reais pelo mesmo executor/queue do worker e verificam artefatos gerados:

```powershell
$env:PYTHONPATH="."
python scripts/speech_stt_smoke.py .\path\to\small-audio.wav --preset fast --language pt
python scripts/speech_tts_smoke.py --engine kokoro --preview
python scripts/speech_tts_smoke.py --engine piper --preview
```

Códigos de saída:

- `0`: execução real passou;
- `1`: regressão/falha de execução;
- `2`: runtime/motor opcional indisponível no ambiente atual (`SKIP`).

Um `SKIP` não conta como prova de funcionamento daquele motor. A matriz completa de paridade está em `docs/superpowers/specs/2026-09-28-unified-speech-parity-matrix.md`.

### Pesquisas

`/search-configs`

Configura nichos, sementes e buscas usadas para alimentar o Radar tradicional.

### Ideias

`/ideas`

Lista leve para registrar ideias de vídeo com título, descrição, nicho/assunto, status e prioridade. O roteiro final pode ser escrito e comparado manualmente onde for mais conveniente.

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
- Piper/Kokoro quando instalados no worker

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

### Speech Worker

```powershell
$env:PYTHONPATH="."
.venv\Scripts\python -m speech_worker.worker
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

Regressão Speech:

```powershell
python -m pytest -q src/test_speech_job_models.py src/test_speech_job_repository.py src/test_speech_jobs_service.py src/test_speech_worker_bootstrap.py src/test_speech_worker_protocol.py src/test_speech_result_importer.py src/test_speech_api.py src/test_speech_presets.py src/test_speech_settings_service.py src/test_speech_storage.py src/test_speech_tts_chunking.py src/test_speech_tts_jobs.py src/test_speech_tts_registry.py src/test_speech_tts_text.py src/test_speech_voice_registry.py src/test_speech_voice_samples.py src/test_speech_voice_compare.py src/test_speech_capabilities.py src/test_speech_diagnostics.py src/test_speech_artifact_api.py src/test_speech_history.py
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

Suíte backend completa:

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
