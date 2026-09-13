# Content Radar Simplification Design

Date: 2026-09-03

## Goal

Refocus Content Radar on three jobs:

1. discover potentially useful content and ideas;
2. save references and obtain faithful transcripts;
3. keep lightweight video ideas and notes for manual comparison outside the app.

Content Radar should not try to become a full video-production workspace.

## Product Direction

The active product surface becomes:

- **Radar**: collected content, search/niche configuration, lightweight curation and saving.
- **Library**: saved YouTube references and their transcripts.
- **Ideas**: a simple list of video ideas with short description/status and optional associated references.

The existing `/content`, `/search-configs`, and `/references` flows remain the foundation. The existing `/scripts` data model may be reused initially for simple ideas, but the rich workshop behavior is removed from the active product experience.

## What Leaves the Active Product

The following features are frozen/removed from the user-facing workflow:

- Canva OAuth;
- external boards;
- automatic Canva board creation;
- rich workshop item library;
- audio ideas;
- thumbnail ideas;
- production planning;
- rich Tiptap script editor;
- full video workflow/status management beyond lightweight idea states;
- automatic script analysis;
- automatic script comparison;
- attempts to produce the complete video inside Content Radar.

## Data Preservation Strategy

This simplification is intentionally non-destructive.

- Existing database tables from migrations 0006-0010 are not dropped in this phase.
- Existing workshop/Canva rows remain in the database so old local data is not lost.
- Deprecated backend modules can remain physically present temporarily, but their routers will no longer be registered by the main FastAPI app once nothing active depends on them.
- No new migrations are needed solely to delete historical tables.

A later cleanup can permanently remove legacy tables after confirming they contain nothing worth preserving.

## Frontend Navigation

Replace the current navigation with a small set of active destinations:

- **Radar** -> `/content`
- **Pesquisas** -> `/search-configs`
- **Biblioteca** -> `/references`
- **Ideias** -> `/ideas`

Remove inactive placeholders such as `Produção` and `Configurações`, and remove the active `Roteiros` workshop entry.

The root route `/` should redirect to `/content` instead of rendering an empty page.

## Radar

Keep the existing collected-content dashboard, but simplify its wording around discovery rather than production.

Keep:

- source/title/date/views/score information;
- filtering and sorting;
- quick status/notes;
- opening the original source;
- niche/search configuration.

Remove from the primary curation experience:

- production-specific notes and language that imply the item is moving into an internal production pipeline.

The Radar's responsibility ends at identifying/saving useful material.

## Library / Transcripts

`/references` remains the canonical place for saved source videos and transcripts.

Keep and emphasize:

- import YouTube URL;
- YouTube manual/automatic captions;
- audio transcription fallback and max-fidelity mode;
- timestamps;
- full transcript text;
- transcript version history;
- copy/export-oriented usage;
- search/filter references.

No script analysis or automatic comparison is added.

## Ideas

Create a lightweight `/ideas` UI. For the first simplification pass, reuse the existing `VideoProject` persistence/API instead of creating a new database subsystem.

Only expose a small subset:

- title;
- description;
- niche/topic;
- status: `idea`, `researching`, `ready`, `archived`;
- priority if useful;
- created/updated dates.

Do not expose:

- script text/editor;
- target production duration;
- Canva boards;
- audio/thumbnail/production item libraries;
- rich workflow stages such as scripting/reviewing/produced in the new UI.

Existing old records with legacy statuses must still render safely. They may be mapped to a neutral legacy label instead of being mutated automatically.

## Backend Surface

### Keep registered

- health;
- content items;
- ingestion;
- search configs/runs;
- reference sources/import jobs/transcripts;
- the minimal `video-projects` endpoints needed by `/ideas`.

### Freeze from active API registration

- Canva OAuth routes;
- external board routes;
- workshop child-resource routes that only serve notes/items/audio/script excerpts.

To minimize regression risk, the first implementation can split or replace the workshop router with an `ideas` router that only exposes the required project CRUD/list operations while reusing the existing repository/model.

## Dependency Cleanup

Once the rich script page is gone, remove Tiptap packages from the frontend if no remaining component imports them.

Canva-specific runtime code and environment configuration should no longer be required for normal startup. Historical source files may be deleted only when they are fully disconnected and tests/build confirm no imports remain.

## Testing

Before claiming completion:

1. backend import/startup test confirms FastAPI starts without Canva/workshop-only imports;
2. transcript tests continue passing;
3. idea CRUD/list behavior is covered with tests;
4. frontend production build succeeds;
5. navigation contains only the simplified destinations;
6. `/` redirects to `/content`;
7. `/ideas` works without loading Tiptap/Canva code;
8. old database schema remains compatible and no destructive migration is introduced.

## Non-Goals

This phase does not add:

- automatic script comparison;
- script generation;
- AI script analysis;
- production management;
- thumbnail/music planning;
- Canva integration replacement;
- collaborative editing;
- publishing/performance tracking.

## Success Criteria

A user should be able to open Content Radar and immediately understand the workflow:

`find something useful -> save/transcribe it -> record a video idea -> manually use the material elsewhere`

There should be no prominent UI suggesting that Content Radar is also the place to write, design, produce, or manage an entire video.