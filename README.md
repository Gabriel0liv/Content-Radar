# Content Radar

Content Radar é uma ferramenta de pesquisa de conteúdo com um objetivo simples:

```text
encontrar algo útil -> salvar/transcrever -> registrar uma ideia -> trabalhar manualmente depois
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

### Pesquisas

`/search-configs`

Configura nichos, sementes e buscas usadas para alimentar o Radar.

### Biblioteca

`/references`

Guarda vídeos usados como referência e suas transcrições.

A importação do YouTube suporta dois modos:

- **Rápido**: legenda manual -> legenda automática -> áudio como fallback;
- **Máxima fidelidade**: transcrição direta do áudio com `faster-whisper`.

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
- faster-whisper

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

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:3000`

## Verificações importantes

```bash
python -m pytest src/test_ideas.py -v
python src/test_captions.py
cd frontend
npm run build
```

## Compatibilidade com dados antigos

As tabelas criadas pelo antigo workshop de vídeo e pela integração com Canva não são removidas nesta simplificação. Os dados existentes continuam no banco para evitar perda acidental.

As rotas de Canva, boards e recursos filhos do workshop não fazem mais parte do startup ativo da API. Registros antigos de `video_projects` também continuam legíveis; status antigos aparecem como legado na nova tela de Ideias até que o usuário decida alterá-los.

## Fora do escopo atual

Content Radar não pretende fazer automaticamente:

- comparação de roteiros;
- geração de roteiros;
- análise de estrutura de roteiro;
- criação de thumbnails;
- planejamento de música;
- gestão de produção;
- integração de Canva no fluxo principal;
- publicação ou tracking pós-publicação.

O foco é continuar pequeno e útil: **descoberta, referências/transcrições e ideias**.
