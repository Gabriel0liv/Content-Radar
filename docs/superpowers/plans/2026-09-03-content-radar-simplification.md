# Content Radar Simplification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refocus Content Radar on discovery, reference/transcript collection, and lightweight video ideas while removing the active video-production workspace.

**Architecture:** Preserve the current Postgres schema and reuse `VideoProject` only as persistence for lightweight ideas. Replace the broad workshop API registration with a minimal ideas-facing router, simplify the existing Radar curation UI, keep `/references` as the transcript library, and remove the rich `/scripts` frontend plus Tiptap/Canva dependencies from the normal product path.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, PostgreSQL, Pydantic, Next.js 14, React 18, TypeScript, Tailwind CSS.

**Spec:** `docs/superpowers/specs/2026-09-03-content-radar-simplification-design.md`

## Global Constraints

- Preserve migrations/tables 0006-0010; do not add a destructive migration.
- Existing workshop and Canva rows must remain untouched.
- Keep transcript import, YouTube captions, audio fallback, timestamps, version history, and `max_fidelity` behavior.
- New idea UI exposes only title, description, niche/topic, lightweight status, priority, and dates.
- Active idea statuses are `idea`, `researching`, `ready`, and `archived`; legacy statuses render safely without automatic mutation.
- Do not add script comparison, script generation, AI script analysis, production management, thumbnail/music planning, Canva replacement, collaborative editing, or publishing tracking.

---

### Task 1: Minimal Ideas API and Backend Startup

**Files:**
- Create: `src/schemas/ideas.py`
- Create: `src/services/ideas_service.py`
- Create: `src/api/routes/ideas.py`
- Create: `src/test_ideas.py`
- Modify: `src/api/main.py`
- Reuse: `src/models/video_workshop.py`
- Reuse: `src/repositories/video_workshop_repository.py`

**Interfaces:**
- Produces `IdeaCreate`, `IdeaUpdate`, `IdeaRead`, and `IdeaListResponse`.
- Produces REST endpoints `POST /video-projects`, `GET /video-projects`, `GET /video-projects/{id}`, `PATCH /video-projects/{id}`, `POST /video-projects/{id}/archive`, and `DELETE /video-projects/{id}`.
- Does not register child workshop, Canva OAuth, or external-board routes.

- [ ] **Step 1: Write failing API tests for the simplified surface**

Create `src/test_ideas.py` with tests that instantiate `TestClient(app)` and assert:

```python
def test_active_api_exposes_ideas_but_not_workshop_children():
    paths = {route.path for route in app.routes}
    assert "/video-projects" in paths
    assert "/video-projects/{id}" in paths
    assert "/video-projects/{id}/items" not in paths
    assert "/canva/oauth/start" not in paths
    assert "/video-projects/{id}/external-boards" not in paths
```

Add CRUD validation tests that create an idea with `title`, `description`, `niche`, `status="idea"`, and `priority`, then update it to `researching`, archive it, and verify listing/search still returns legacy rows without mutating their status.

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
python -m pytest src/test_ideas.py -v
```

Expected: fail because the minimal ideas router/schemas do not exist and workshop/Canva routes are still registered.

- [ ] **Step 3: Implement minimal idea schemas**

In `src/schemas/ideas.py`, define fields only for the active UI. Validate writes with:

```python
ACTIVE_IDEA_STATUSES = {"idea", "researching", "ready", "archived"}
```

`IdeaRead.status` remains `str` so old rows such as `scripting`, `reviewing`, and `produced` remain readable.

- [ ] **Step 4: Implement `IdeasService` by reusing `VideoProject` persistence**

Use `VideoWorkshopRepository` for create/get/list/update/delete, but construct only `VideoProjectCreate`/`VideoProjectUpdate` fields relevant to ideas. Do not calculate script word counts or access child resources.

- [ ] **Step 5: Implement the minimal router**

Create `src/api/routes/ideas.py` with only the six project-level endpoints listed above. Keep the `/video-projects` URLs to minimize frontend/API migration risk.

- [ ] **Step 6: Remove legacy routers from FastAPI startup**

Change `src/api/main.py` imports to:

```python
from src.api.routes import content_items, health, ideas, ingest, references, search
```

Register `ideas.router`, and remove registration/imports for `video_workshop`, `external_boards`, and `canva_oauth`.

- [ ] **Step 7: Run backend tests**

Run:

```bash
python -m pytest src/test_ideas.py -v
python src/test_captions.py
```

Expected: simplified API tests pass and transcript regression tests remain green.

- [ ] **Step 8: Commit**

```bash
git add src/schemas/ideas.py src/services/ideas_service.py src/api/routes/ideas.py src/api/main.py src/test_ideas.py
git commit -m "refactor: expose lightweight ideas API"
```

---

### Task 2: Simplified Navigation, Root Redirect, and Ideas UI

**Files:**
- Create: `frontend/app/ideas/page.tsx`
- Modify: `frontend/components/layout/sidebar.tsx`
- Modify: `frontend/app/page.tsx`
- Modify: `frontend/app/layout.tsx`
- Remove after replacement: `frontend/app/scripts/page.tsx`
- Remove after replacement: `frontend/app/scripts/[id]/page.tsx`

**Interfaces:**
- Navigation destinations: `/content`, `/search-configs`, `/references`, `/ideas`.
- `/ideas` consumes the minimal `/video-projects` REST surface from Task 1.

- [ ] **Step 1: Establish the expected frontend behavior before editing**

Record the current failure conditions:

```bash
cd frontend
npm run build
```

Also verify source currently contains `/scripts`, `Produção`, and `Configurações` in the sidebar and that `app/page.tsx` returns `null`.

- [ ] **Step 2: Replace sidebar navigation**

Use exactly four active menu items:

```ts
const menuItems = [
  { name: "Radar", href: "/content", icon: Radar },
  { name: "Pesquisas", href: "/search-configs", icon: Search },
  { name: "Biblioteca", href: "/references", icon: Library },
  { name: "Ideias", href: "/ideas", icon: Lightbulb },
];
```

Remove inactive production/settings placeholders and the `Roteiros` entry.

- [ ] **Step 3: Redirect the root route**

Replace `frontend/app/page.tsx` with:

```tsx
import { redirect } from "next/navigation";

export default function Home() {
  redirect("/content");
}
```

- [ ] **Step 4: Create `/ideas` as a lightweight list/editor**

Implement list, search, create, edit, archive, and delete around these fields only:

```ts
title
description
niche
status
priority
created_at
updated_at
```

Active status choices shown to the user are `idea`, `researching`, `ready`, and `archived`. For an existing record with any other status, render a neutral badge such as `Legado: scripting` without writing a replacement status until the user explicitly changes it.

Do not link to a detail/script editor page.

- [ ] **Step 5: Remove the old scripts pages**

Delete both `/scripts` page files only after `/ideas` implements the necessary list/create/edit behavior.

- [ ] **Step 6: Update product metadata wording**

Change `frontend/app/layout.tsx` metadata to describe discovery, references/transcripts, and ideas rather than a production/analysis portal.

- [ ] **Step 7: Build and inspect routes**

Run:

```bash
cd frontend
npm run build
```

Expected: `/ideas` is present, `/scripts` is absent, `/` builds as a redirect, and no page imports `@tiptap/*` or Canva APIs.

- [ ] **Step 8: Commit**

```bash
git add frontend/app/ideas frontend/components/layout/sidebar.tsx frontend/app/page.tsx frontend/app/layout.tsx frontend/app/scripts
git commit -m "refactor: replace video workshop with ideas"
```

---

### Task 3: Simplify Radar Curation to Discovery and Notes

**Files:**
- Modify: `frontend/app/content/page.tsx`
- Modify: `frontend/components/content/curation-panel.tsx`
- Modify: `frontend/components/content/content-status-badge.tsx`
- Modify: `frontend/components/content/content-summary-cards.tsx`
- Modify only if necessary for copy: `frontend/app/content/[id]/page.tsx`

**Interfaces:**
- Keep existing `ContentItem` API/status persistence for database compatibility.
- Stop sending `production_notes` from the primary UI.

- [ ] **Step 1: Identify production-oriented UI assertions to remove**

Before editing, verify the current source contains labels such as `Pronto para Roteiro`, `Produzido`, and `Notas de Produção / Roteiro`.

- [ ] **Step 2: Simplify the curation form**

Remove `productionNotes` state, conditional production textarea, and `production_notes` from the PATCH payload. Keep:

```ts
{
  status,
  notes: notes.trim() || null,
  rejected_reason: status === "rejected" ? rejectedReason.trim() || null : null,
}
```

Use discovery-oriented labels such as `Novo`, `Revisado`, `Salvo/Selecionado`, `Ignorado/Rejeitado`, and `Arquivado`. Existing `produced` values must still render safely as legacy state but do not need to be offered as a normal new selection.

- [ ] **Step 3: Update Radar headings and metric copy**

Rename `Painel de Curadoria` and production-pipeline language to `Radar` / discovery wording. Keep score, views, views/day, sources, filtering, sorting, notes, and original-source links.

- [ ] **Step 4: Build frontend**

Run:

```bash
cd frontend
npm run build
```

Expected: no TypeScript references remain to removed local `productionNotes` state and Radar still renders all existing content statuses safely.

- [ ] **Step 5: Commit**

```bash
git add frontend/app/content frontend/components/content
git commit -m "refactor: focus radar on discovery"
```

---

### Task 4: Make References the Transcript Library and Expose Max Fidelity

**Files:**
- Modify: `frontend/app/references/page.tsx`
- Modify: `frontend/app/references/[id]/page.tsx`
- Verify: `src/schemas/references.py`
- Verify: `src/services/references_service.py`
- Test: `src/test_captions.py`

**Interfaces:**
- Import payload includes `transcription_mode: "auto" | "max_fidelity"`.
- Existing transcript endpoints and persistence remain unchanged.

- [ ] **Step 1: Add a regression assertion for `transcription_mode` if not already present**

In `src/test_captions.py`, ensure request/schema behavior accepts:

```python
YouTubeUrlImportRequest(
    url="https://youtu.be/dQw4w9WgXcQ",
    transcription_mode="max_fidelity",
)
```

and rejects unknown modes.

- [ ] **Step 2: Run transcript tests and verify the assertion**

Run:

```bash
python src/test_captions.py
```

- [ ] **Step 3: Rename the frontend surface to Biblioteca**

Use wording that emphasizes saved source videos and faithful transcripts. Do not add analysis or comparison controls.

- [ ] **Step 4: Expose transcription mode in the import form**

Add a simple mode selector:

```ts
"auto"         // captions first, audio fallback
"max_fidelity" // direct audio transcription for highest fidelity
```

Send the selected mode in `importYouTubeReferenceUrl` payload. Keep preferred language selection and automatic-caption toggle where relevant.

- [ ] **Step 5: Correct outdated fallback/status copy**

Because the backend now performs audio fallback, remove UI text implying `needs_audio_transcription` is merely a future Whisper feature. If a job still lands there, describe it as an audio-transcription failure/pending retry rather than a planned future feature.

- [ ] **Step 6: Preserve detail-page transcript tools**

Keep full text, timestamps/segments, version history, copy actions, metadata, and source link. Do not add script analysis.

- [ ] **Step 7: Run backend transcript tests and frontend build**

```bash
python src/test_captions.py
cd frontend && npm run build
```

- [ ] **Step 8: Commit**

```bash
git add src/test_captions.py frontend/app/references
git commit -m "feat: make references a transcript library"
```

---

### Task 5: Remove Unused Production Dependencies and Document the New Product Boundary

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `README.md`
- Modify: `docs/PORTAL_ROADMAP.md`
- Keep untouched: `alembic/versions/0006_add_video_workshop.py` through `0010_add_canva_oauth.py`
- Keep untouched: existing workshop/Canva database models unless import cleanup requires a non-destructive code-only change.

**Interfaces:**
- Normal FastAPI startup must not require Canva runtime configuration.
- Frontend must not depend on Tiptap once `/scripts` is gone.

- [ ] **Step 1: Verify there are no remaining Tiptap imports**

Run from repository root:

```bash
git grep -n "@tiptap" -- frontend
```

Expected after Task 2: no application-source matches.

- [ ] **Step 2: Remove Tiptap dependencies using npm**

Run:

```bash
cd frontend
npm uninstall @tiptap/react @tiptap/starter-kit
```

This updates both `package.json` and `package-lock.json` consistently.

- [ ] **Step 3: Verify active backend router imports**

Run:

```bash
python -c "from src.api.main import app; print('\n'.join(sorted({r.path for r in app.routes})))"
```

Expected: health/content/search/reference/transcript routes plus project-level idea routes; no Canva OAuth, external-board, item, audio, note, or script-excerpt endpoints.

- [ ] **Step 4: Run the complete relevant verification suite**

```bash
python -m pytest src/test_ideas.py -v
python src/test_captions.py
cd frontend && npm run build
```

Also run:

```bash
git diff --name-only master...HEAD -- alembic/versions
```

Expected for the simplification work: no new destructive migration and no edits that drop historical workshop/Canva tables.

- [ ] **Step 5: Rewrite README product description**

Document the active workflow as:

```text
find something useful -> save/transcribe it -> record a video idea -> manually use the material elsewhere
```

Remove Canva/workshop setup from the recommended normal workflow. Historical implementation notes can be labeled legacy instead of deleted if still useful.

- [ ] **Step 6: Narrow the roadmap**

Update `docs/PORTAL_ROADMAP.md` so production tracking, script generation, and similar expansion are not presented as the current direction. Keep future discovery-source expansion only where it supports the Radar.

- [ ] **Step 7: Final commit**

```bash
git add frontend/package.json frontend/package-lock.json README.md docs/PORTAL_ROADMAP.md
git commit -m "chore: remove production workspace dependencies"
```

---

## Final Verification Checklist

- [ ] `python -m pytest src/test_ideas.py -v` passes.
- [ ] `python src/test_captions.py` passes.
- [ ] `cd frontend && npm run build` passes.
- [ ] Sidebar contains only Radar, Pesquisas, Biblioteca, Ideias.
- [ ] `/` redirects to `/content`.
- [ ] `/ideas` has no rich script editor, Canva, boards, audio, thumbnail, or production workflow UI.
- [ ] `/references` exposes `auto` and `max_fidelity` transcription modes.
- [ ] Radar no longer asks for production notes.
- [ ] FastAPI startup does not import/register Canva OAuth, external boards, or workshop child-resource routes.
- [ ] No destructive Alembic migration was added.
- [ ] Existing legacy statuses and database rows remain readable and untouched unless the user explicitly edits them.
