# Content Radar + Speech Studio Integration Design

Date: 2026-09-05
Status: approved direction, implementation pending plan

## 1. Goal

Turn Dark Content Radar into the user's single working platform for content research, references, ideas, transcription, speech generation, voices, and speech-job history without merging the heavy Speech Studio AI stack into the Content Radar backend process.

The Content Radar remains the primary product and UI. Speech Studio becomes the local speech engine behind it.

## 2. Product principles

1. One main frontend: Content Radar.
2. Speech parameters should be hidden during normal use.
3. The user chooses intent and quality; the system chooses technical parameters.
4. Advanced controls remain available when needed, with plain-language explanations.
5. Speech Studio remains a separate service/process so WhisperX, pyannote, PyTorch, CUDA, and TTS dependencies do not destabilize the Content Radar backend.
6. Existing fast transcription remains available for lightweight jobs.
7. No return to the previous over-broad production-suite scope: speech tooling is an auxiliary module, not a full video editor.

## 3. Architecture

```text
Browser
  |
  v
Content Radar Frontend
  |
  v
Content Radar API + PostgreSQL
  |
  +---- lightweight transcription (existing faster-whisper path)
  |
  +---- Speech Engine Client
          |
          v
      Speech Studio API
          |
          +---- WhisperX
          +---- pyannote
          +---- TTS
          +---- voice management
          +---- GPU/CPU execution
```

Speech Studio continues as its own repository and runtime. The old Speech Studio frontend is not the final user-facing application; it remains a reference and optional development/debugging UI.

## 4. Main navigation

Content Radar sidebar becomes:

- Radar
- Pesquisas
- Biblioteca
- Ideias
- divider
- Áudio

Settings can expose speech-engine status/configuration later without becoming a main daily-use area.

## 5. Áudio module

The new `/audio` area has four primary views:

### 5.1 Transcrever

Normal mode asks only:

- file
- preset/quality
- language
- whether to identify speakers

Recommended presets:

#### Rápido
For drafts and quick extraction.

Suggested engine profile:
- model: small
- compute_type: int8
- batch_size: 2
- device: auto
- diarization: off by default
- normal VAD

#### Equilibrado
Default general-purpose mode.

Suggested engine profile:
- model: medium
- compute_type: int8
- batch_size: 2 where hardware permits, otherwise 1
- device: auto
- diarization: optional/on when requested
- alignment enabled by WhisperX
- normal VAD

#### Máxima qualidade
For important source material, interviews, podcasts, and difficult audio.

Suggested engine profile:
- model: large-v3 when hardware supports it, otherwise medium
- compute_type: int8 by default on constrained VRAM
- batch_size: 1
- diarization: optional/on when requested
- word alignment
- more conservative memory usage

The exact resolved parameters must be returned/displayable so the user can understand what the preset actually used.

### 5.2 Guided options

A guided section translates real-world questions into technical parameters:

- "Quantas pessoas falam?" -> num_speakers or min/max speakers
- "Tem falas baixas/sussurradas?" -> more sensitive VAD values
- "Há nomes ou termos incomuns?" -> initial prompt/context when the engine supports it
- "Prioridade" -> preset selection

The user should not need to know what VAD, compute type, or batch size mean.

### 5.3 Advanced options

Advanced mode exposes the real parameters:

- model
- language
- device
- compute_type
- batch_size
- diarization
- num/min/max speakers
- speaker profile
- vad_onset
- vad_offset
- chunk_size
- output formats
- initial prompt when available through Speech Studio API

Every control includes a short plain-language explanation and safe/recommended values.

### 5.4 Personal presets

Users can save named STT presets such as:

- Vídeo YouTube normal
- Podcast 2 pessoas
- Drathos - entrevistas
- Áudio ruim
- Máxima qualidade

A personal preset stores the resolved STT configuration, not only a label.

Built-in presets cannot be deleted; personal presets can be edited/deleted.

## 6. TTS and voices

The same `/audio` module includes:

- Transcrever
- Gerar voz
- Vozes
- Histórico
- Presets

TTS and voice management use Speech Studio's existing API capabilities but are surfaced using Content Radar components and terminology.

The first implementation phase focuses on STT integration and the shared engine connection. TTS/voices follow after STT is stable.

## 7. Library integration

YouTube/reference import gets a transcription method selector:

- Automático
- Legenda do YouTube
- Rápida (local)
- Speech Studio - Equilibrado
- Speech Studio - Máxima qualidade

`Automático` remains optimized for convenience and cost/latency. It should not silently trigger the most expensive local pipeline unless configured to do so.

Speech Studio output is normalized into Content Radar's existing transcript model rather than stored only as exported files.

Normalized transcript data includes:

- language
- source method/engine
- model/profile metadata
- full text
- segments
- speaker label when available
- start/end timestamps
- optional word-level timestamps/metadata

The existing transcript versioning remains authoritative in Content Radar.

## 8. Speaker handling

Diarized transcript segments preserve labels such as `SPEAKER_00`.

Content Radar allows a user-facing speaker mapping:

- SPEAKER_00 -> Gabriel
- SPEAKER_01 -> João

Renaming a speaker changes the display mapping without destructively rewriting raw engine output.

Speaker mappings belong to the transcript/job context initially. Reusable speaker profiles remain owned by Speech Studio until a later explicit unification is justified.

## 9. Jobs and progress

Long speech operations must be asynchronous from the browser's perspective.

Content Radar stores/integrates a speech job record containing at minimum:

- id
- operation type (stt/tts)
- status
- created/updated timestamps
- source/reference link when applicable
- speech-engine job identifier
- selected preset
- resolved parameters
- progress stage
- error summary
- resulting transcript/artifact references

Progress stages should map Speech Studio stages into user-friendly labels, e.g.:

- Preparando áudio
- Carregando modelo
- Transcrevendo
- Alinhando
- Identificando vozes
- Exportando
- Concluído

A single heavy-job limitation from Speech Studio must be represented clearly as queued/busy rather than surfacing a cryptic HTTP 409.

## 10. History

The Audio page has a speech-specific history first, because that is actionable and scoped.

A platform-wide unified activity feed is deferred. It should not be built until there is a clear need to combine research actions, ideas, imports, STT, and TTS into one chronology.

## 11. Engine configuration and health

Content Radar needs a Speech Studio client with:

- base URL from environment
- health check
- timeout handling
- connection error normalization
- capability discovery/version information where possible

The UI should show states such as:

- Speech Studio online
- Speech Studio unavailable
- GPU detected / CPU mode, when exposed by engine health/dashboard APIs
- Hugging Face/diarization unavailable, when determinable

Content Radar core functionality must continue working if Speech Studio is offline.

## 12. Runtime/deployment

Do not install WhisperX/pyannote/PyTorch/CUDA in the main Content Radar backend image.

Development setup supports:

- Content Radar in Docker as today
- Speech Studio running separately on the host or as a dedicated service when GPU/container support is deliberately configured

The integration uses a configurable `SPEECH_STUDIO_BASE_URL`.

A future compose profile may add a Speech Studio service, but this is not required for the first integration and must not block CPU/GPU host execution.

## 13. Data ownership

Content Radar owns:

- references
- canonical transcripts and transcript versions
- transcript segments used by search/research
- speech jobs initiated from Content Radar
- user-friendly STT presets
- mappings from speech results to references/transcripts

Speech Studio owns:

- model execution
- temporary uploads
- engine-native output artifacts
- TTS engine/voice internals
- reusable engine speaker/voice profiles until later explicitly migrated

This prevents duplicated sources of truth.

## 14. API boundary

Content Radar talks to Speech Studio through a dedicated service/client layer, never from arbitrary route code.

Initial client operations:

- health/status
- submit STT job or call current STT endpoint through a controlled adapter
- read result/artifacts
- later: TTS
- later: voices

The current Speech Studio `/stt/transcribe` endpoint is synchronous and accepts model, language, device, compute type, batch size, diarization, speaker counts/profile, formats, VAD values, and chunk size. The integration layer must shield Content Radar from that raw parameter surface.

If true asynchronous engine jobs are not yet available for STT, the first implementation may use a Content Radar-side background job adapter while preserving an API shape that can later switch to native Speech Studio jobs.

## 15. Error handling

User-facing errors are translated into actionable messages:

- Speech engine offline
- Engine busy
- Not enough VRAM / model too large
- Diarization unavailable / HF token missing
- Unsupported or invalid file
- Transcription failed
- Result could not be imported into the library

Raw logs remain accessible in an advanced/debug section, not as the primary error message.

## 16. Security and privacy

- HF tokens and other secrets remain server-side/environment-only.
- Content Radar frontend never receives secret tokens.
- Uploaded local media is not retained indefinitely by default.
- Temporary Speech Studio uploads keep the existing cleanup behavior.
- Raw filesystem paths from Speech Studio must not be treated as browser-download URLs without an explicit safe artifact endpoint.

## 17. Implementation phases

### Phase 1 - Integration foundation

- Speech Studio client in Content Radar
- health/status
- STT preset model/resolver
- tests for parameter resolution
- configuration/env variables
- no UI-heavy expansion yet

### Phase 2 - Audio STT UI

- `/audio`
- simple/guided/advanced modes
- upload
- job/progress presentation
- result view
- personal STT presets

### Phase 3 - Library STT integration

- choose Speech Studio during reference import
- normalize results into Transcript/TranscriptSegment
- preserve versioning
- speakers and timestamps
- deep links/search compatibility

### Phase 4 - TTS and voices

- Generate voice tab
- voice browser/management
- history/artifacts

### Phase 5 - polish

- hardware-aware recommendations
- improved diagnostics
- optional compose profile
- optional broader activity feed only if still useful

## 18. Testing strategy

Backend tests:

- preset resolution for fast/balanced/max-quality
- hardware-safe fallback rules
- Speech Studio client request construction
- busy/offline/error normalization
- result normalization into transcript segments
- diarization speaker preservation
- transcript versioning remains correct

Contract tests use mocked Speech Studio responses so Content Radar tests do not require WhisperX/GPU.

Speech Studio tests should cover endpoint compatibility independently.

Frontend validation:

- type checking/build
- simple/guided/advanced parameter behavior
- engine offline/busy states
- job/result rendering

Manual integration smoke test:

1. Speech Studio online
2. upload short audio
3. transcribe using Equilibrado
4. confirm progress/result
5. save/import transcript to Biblioteca
6. verify speaker/timestamps if diarization enabled
7. repeat with Speech Studio offline and confirm graceful degradation

## 19. Explicit non-goals

- Merging both Python dependency trees into one process
- Rebuilding WhisperX/pyannote inside Content Radar
- Keeping two primary frontends for daily use
- Full video editing
- Automatic script writing/production planning
- Platform-wide activity feed in the first integration
- Vector search or unrelated AI infrastructure

## 20. Success criteria

The integration is successful when the user can open only Content Radar for normal work, choose understandable speech actions/presets without remembering technical flags, use high-fidelity Speech Studio transcription when needed, and still use the rest of Content Radar normally when the speech engine is unavailable.
