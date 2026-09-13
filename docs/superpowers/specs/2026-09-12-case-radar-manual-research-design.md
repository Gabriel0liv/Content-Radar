# Case Radar — Manual Research Design

Date: 2026-09-12
Status: proposed for final review

## 1. Goal

Add a native **Case Radar** to Content Radar for manual research of mystery, horror, strange-event, true-crime, paranormal, viral-video and related cases.

The user starts a research run manually by describing a theme and optional filters. Content Radar then discovers candidate posts/videos across multiple public platforms, gathers useful social context such as comments and replies, groups duplicates/reposts into cases, researches provenance and external context, and produces a structured dossier for each usable case.

The first version is deliberately **manual only**. It does not schedule recurring searches, monitor topics in the background, or send notifications.

Primary outcome:

> Given a theme such as “strange videos recorded in forests”, return a set of well-researched cases with source links, provenance confidence, useful comments, context, alternative explanations, timestamps/transcripts where available, and enough evidence for the user to decide whether the case belongs in a compilation or script.

## 2. Product principles

1. **A case is not a post.** One case may have many posts, videos, articles, reposts and comments across several platforms.
2. **Discovery is separate from verification.** Finding a post is only the beginning of the research process.
3. **Original source is probabilistic.** The system distinguishes `earliest_known_source` from a definitively proven original source.
4. **Comments are evidence leads, not facts.** Comments and replies can contain excellent context, but claims must be cross-checked before being promoted to confirmed context.
5. **Manual first.** No scheduler, saved watch rules or continuous monitoring in this phase.
6. **Free-first provider strategy.** Free/public discovery paths should work without paid APIs. Official paid APIs remain optional providers.
7. **Provider failure must not break the run.** If X, TikTok or Instagram becomes unavailable, other providers continue and the run reports reduced coverage.
8. **Do not equate unexplained with paranormal.** The dossier separates observations, source claims, corroborated facts and alternative explanations.
9. **Reuse existing Content Radar data where possible.** Existing references, transcripts, speech jobs and discovery infrastructure should be reused instead of duplicated.
10. **Preserve source provenance.** Every material claim shown in a dossier must point back to the source or evidence item that produced it.

## 3. Explicit scope

### 3.1 In scope

- Manual creation of a research run.
- Theme/query expansion in multiple languages.
- Discovery from:
  - YouTube;
  - X/Twitter;
  - TikTok;
  - Instagram;
  - Reddit;
  - general web search.
- Pluggable discovery methods per platform.
- Collection of comments/replies where technically available.
- Collection of quote-post/context relationships where available.
- Ranking comments for investigative usefulness.
- Grouping duplicate/reposted media into a shared case.
- Researching provenance, earliest known source and external context.
- Extracting names, locations, dates, claims and links.
- Linking/transcribing media through the existing speech subsystem when useful.
- Case dossier generation.
- Manual review states such as approved, rejected, duplicate/already-used.
- Partial results when some providers fail.

### 3.2 Out of scope for this phase

- Scheduled monitoring.
- Automatic alerts.
- Automatic creation/rotation of social accounts after suspension.
- Circumvention of access controls, CAPTCHAs or platform security measures.
- A general-purpose social-media archiver.
- Automatic publishing/downloading/reuploading of copyrighted clips.
- Video editing.
- Rights/licensing determination for publication.
- Attempting to prove supernatural explanations.

## 4. User workflow

The user opens **Case Radar** and creates a manual run.

Example request:

```text
Theme: strange videos recorded in forests
Desired usable cases: 10
Languages: Portuguese, English, Spanish
Prioritize:
- identifiable original source
- meaningful context
- low Portuguese-language coverage
Exclude:
- known ARGs
- obviously staged content
- cases already used
```

The run progresses through visible stages:

```text
queued
  -> generating_queries
  -> discovering
  -> enriching_sources
  -> collecting_social_context
  -> clustering_cases
  -> researching_cases
  -> finalizing
  -> completed | partially_completed | failed | cancelled
```

The run does **not** stop as soon as it finds ten links. `desired_usable_cases=10` means the system should try to produce ten cases that survive deduplication and minimum research-quality checks, subject to configured search budgets and provider availability.

The user can inspect candidates while the run is in progress and can manually reject obvious junk before deeper research finishes.

## 5. Search request model

A manual research request contains:

- `theme`: required free-text description;
- `desired_usable_cases`: target number of final cases;
- `languages`: preferred discovery/research languages;
- `platforms`: enabled providers;
- `date_from` / `date_to`: optional;
- `include_terms`: optional;
- `exclude_terms`: optional;
- `priorities`: structured or free-text preferences;
- `exclusions`: known ARG, obviously staged, already used, etc.;
- `research_depth`: initially `quick`, `balanced`, `deep`;
- per-provider budgets and global result budget.

`balanced` is the default.

The query generator expands the theme into multiple search intents rather than merely translating one sentence. For example:

```text
strange forest footage
creature caught on trail camera
unexplained forest video
weird security camera forest
vídeo estranho floresta
criatura gravada floresta
video extraño bosque
criatura grabada en bosque
```

Generated terms are persisted so the run is reproducible and debuggable.

## 6. Provider architecture

All discovery providers implement the same conceptual contract:

```text
search(request, query, cursor?) -> CandidatePage
fetch_source(candidate) -> SourceSnapshot
fetch_social_context(source, options) -> SocialContextPage
```

A provider may support only a subset of operations. Capabilities are declared explicitly rather than inferred from platform name.

### 6.1 Shared provider capabilities

Each configured provider exposes flags such as:

- `search_supported`;
- `source_fetch_supported`;
- `comments_supported`;
- `replies_supported`;
- `quote_posts_supported`;
- `media_metadata_supported`;
- `historical_search_supported`;
- `authenticated`;
- `official_api`;
- `cost_class`: `free`, `metered`, `paid`.

The orchestration layer never assumes that every X/TikTok/Instagram method has the same access.

### 6.2 X/Twitter

Three interchangeable methods are designed behind one X platform adapter:

1. **Web search provider**
   - discovers indexed public X URLs through a general search provider;
   - free-first and stable fallback;
   - incomplete coverage;
   - comments/replies may be unavailable unless the discovered page can be fetched normally.

2. **Logged-in session provider**
   - optional experimental adapter using a user-configured authenticated session;
   - better direct discovery and thread/reply coverage when functioning;
   - isolated from the rest of the application;
   - failure/challenge/login expiry marks the provider unavailable for the run;
   - no automated account creation, challenge bypass or ban evasion.

3. **Official X API provider**
   - optional;
   - used only when credentials and a suitable plan are configured;
   - preferred when the user explicitly prioritizes official coverage.

### 6.3 TikTok

TikTok uses the same layered pattern where technically viable:

- web-search discovery;
- optional authenticated-session provider;
- optional official/research API provider when eligibility and credentials exist.

Comments are high-value research material and should be collected when the active provider supports them.

### 6.4 Instagram

Instagram uses:

- web-search discovery;
- optional authenticated-session provider;
- optional official Meta API path for scopes that are actually supported by the configured account/application.

The design must not assume Meta's official API provides arbitrary global Reel search.

### 6.5 Reddit

Reddit is both a discovery provider and a high-value context provider. Posts and comments should preserve hierarchy because investigation often happens in reply chains.

### 6.6 YouTube

Use the existing YouTube discovery infrastructure where possible rather than creating a second YouTube integration. Comments are optional context input; transcripts/captions and existing Speech/Reference features are more important than exhaustive comment collection.

### 6.7 General web search

A generic search provider serves two roles:

- normal web/context discovery;
- indirect discovery of indexed posts on X/TikTok/Instagram.

Search-provider cost and quota are modeled explicitly because web search at scale can become a paid dependency.

## 7. Provider selection and fallback

Platform and transport are separate concepts.

Example:

```text
platform = x
method = logged_in
```

or:

```text
platform = x
method = web_search
```

A run stores which method produced every candidate.

Default behavior is free-first. Example strategy:

```text
X:         logged_in -> web_search -> official_api (if configured and allowed by budget)
TikTok:    logged_in -> web_search -> official/research (if configured)
Instagram: logged_in -> web_search -> official (where useful)
YouTube:   official quota-backed provider
Reddit:    configured public/official provider
Web:       configured search provider
```

Provider order is configuration, not hard-coded business logic.

A failure in one method can fall back to the next method if the run budget permits it. Provider errors are persisted with enough detail for the UI to say, for example, “X logged-in search unavailable; X web discovery continued.”

## 8. Canonical candidate model

All providers normalize raw results into a common discovery object before case research begins.

Conceptual fields:

```text
Candidate
- id
- platform
- external_id
- canonical_url
- author_handle
- author_display_name
- title_or_caption
- text
- published_at
- discovered_at
- media_type
- media_urls / platform media identifiers
- thumbnail_url
- duration_seconds
- language
- engagement metrics
- hashtags/tags
- parent/reply/quote relationship
- discovery_query
- discovery_method
- raw_json
- source_confidence
```

The canonical model preserves platform-specific raw data in `raw_json` but does not expose raw payload shape to downstream case logic.

## 9. Domain model

The Case Radar requires entities separate from `ContentItem` because the existing content model represents an individual discovered content item, while a research case aggregates many heterogeneous sources.

### 9.1 `CaseResearchRun`

Represents one manually initiated research session.

Core fields:

- request/configuration snapshot;
- status/stage/progress;
- target usable-case count;
- started/completed timestamps;
- provider coverage summary;
- counts for discovered candidates, clustered cases, usable cases and rejected cases;
- structured error/partial-completion summary.

### 9.2 `CaseResearchQuery`

Stores generated queries per run:

- language;
- platform/provider target;
- query text;
- query intent;
- execution state/result counts.

### 9.3 `ResearchSource`

Represents a durable external source/post/video/article.

Core fields:

- platform/source type;
- external identifier;
- canonical URL;
- author;
- title/caption/text;
- timestamps;
- media metadata;
- engagement snapshot;
- discovery method;
- raw snapshot;
- optional relation to existing `ContentItem` or `ReferenceSource`.

Uniqueness is primarily platform + external identifier, with canonical URL fallback where no stable identifier exists.

### 9.4 `ResearchCase`

Represents the conceptual event/video/story being researched.

Core fields:

- provisional title;
- normalized summary;
- status;
- alleged date/location;
- earliest known date;
- origin confidence;
- overall research confidence;
- likely original source id;
- earliest known source id;
- selected primary source id;
- dossier version;
- manual notes;
- already-used flag/reference.

### 9.5 `CaseSource`

Many-to-many relation between cases and sources.

Each link has a role:

- `original_candidate`;
- `earliest_known`;
- `primary`;
- `mirror`;
- `repost`;
- `secondary_report`;
- `context`;
- `debunk`;
- `author_followup`;
- `unknown`.

The link also stores provenance confidence and the reason/evidence for the role.

### 9.6 `SocialContextItem`

Stores comments, replies, quote posts or equivalent social context.

Fields include:

- source id;
- platform item id;
- parent social-context id when threaded;
- author;
- body;
- created timestamp;
- engagement;
- pinned flag;
- author-reply flag;
- URLs/entities extracted;
- usefulness score;
- classifier categories;
- raw snapshot.

### 9.7 `CaseClaim`

Represents an explicit research claim rather than a blob of generated prose.

Examples:

- “The video was recorded in Chile.”
- “This clip first appeared in 2021.”
- “The creature is a costume from a short film.”

Fields:

- normalized claim text;
- claim type;
- status: `source_claimed`, `corroborated`, `contradicted`, `unverified`;
- confidence;
- extracted entities/date/location;
- supporting evidence links;
- contradicting evidence links.

### 9.8 `CaseEvidence`

Links a claim to a source, social-context item, transcript segment or external reference with a stance (`supports`, `contradicts`, `context_only`).

### 9.9 `MediaFingerprint`

Stores fingerprints useful for identifying reposts/near-duplicates of the same media.

The initial implementation should support metadata/hash-based fingerprints when media bytes are legitimately available. Perceptual video fingerprinting can be added incrementally; the schema should not require it to ship the first useful Case Radar.

## 10. Relationship to existing Content Radar models

`ContentItem` remains the normal discovery/library item and is not overloaded into a case container.

Case Radar may link a `ResearchSource` to:

- an existing `ContentItem` when the source already exists in discovery;
- an existing/new `ReferenceSource` when it becomes a research reference;
- an existing `Transcript` through the current reference/speech path.

This avoids duplicate transcript systems and preserves the current Speech integration.

A YouTube video discovered by Case Radar should therefore be able to reuse the existing YouTube/reference/transcript path rather than creating a second transcript stack.

## 11. Social context collection

Comments are treated as a first-class research input where providers permit collection.

The collector should avoid storing unlimited low-value reactions. It works in two stages:

1. fetch a bounded window of comments/replies according to provider capabilities and run depth;
2. rank for investigative usefulness.

High-value categories:

- `origin` — claims to identify the original source;
- `context` — date/location/background;
- `correction` — fixes a widespread attribution;
- `debunk` — staged/film/ARG/explanation claim;
- `link` — contains an external source;
- `author_response` — uploader/creator clarification;
- `witness_claim` — personal testimony;
- `technical_explanation` — plausible mechanism/object identification.

Low-value reaction-only comments receive very low usefulness scores and can be omitted from the dossier while retaining aggregate collection statistics.

Ranking signals include:

- URLs;
- dates/places/named entities;
- source/original/debunk vocabulary in relevant languages;
- author response;
- pinned state;
- engagement;
- reply depth and meaningful follow-up;
- semantic similarity to unresolved case questions.

No comment is automatically promoted to a factual claim merely because it has high engagement.

## 12. Candidate clustering and deduplication

The clustering layer answers: “Do these sources appear to describe/show the same underlying case?”

Signals, from cheapest to more expensive:

- exact platform/external id;
- canonical URL normalization;
- shared linked source URL;
- matching titles/captions/entities;
- same alleged date/location;
- thumbnail/image hash where available;
- media metadata similarities;
- transcript/text similarity;
- media fingerprints when bytes are legitimately available.

Clustering outputs a confidence score and reasons. Low-confidence merges remain suggestions rather than destructive automatic merges.

The user can manually split or merge cases later; the model should preserve source records independently so reclustering does not lose data.

## 13. Provenance resolution

For each cluster, the researcher attempts to resolve source history.

Important distinction:

- **earliest known source**: oldest source the current run can substantiate;
- **likely original source**: best current hypothesis about origin;
- **confirmed original source**: only used when evidence actually establishes it.

Resolution uses:

- timestamps;
- author statements;
- links between posts;
- quote/repost relationships;
- comments identifying earlier versions;
- external articles;
- matching media fingerprints;
- archived/indexed references where legitimately accessible.

The dossier must display uncertainty rather than silently treating the oldest discovered timestamp as proof of authorship.

## 14. Research loop

Once a candidate cluster becomes a case, research becomes recursive but budgeted.

```text
case
  -> unresolved questions
  -> extract entities/claims/links
  -> generate targeted searches
  -> collect new sources
  -> evaluate claims
  -> update unresolved questions
  -> stop on quality threshold or budget
```

Examples of follow-up searches:

- exact quoted phrase from a caption;
- uploader handle + event name;
- location + date + incident keywords;
- unique filename/watermark/username;
- claim from a high-value comment;
- alleged debunk title.

The loop must have hard depth/query/source budgets to avoid runaway searches.

## 15. Claim and confidence semantics

The system should avoid one opaque “AI confidence” number for everything.

At minimum expose:

- `origin_confidence`;
- `event_context_confidence`;
- per-claim confidence/status;
- `duplicate_cluster_confidence`;
- `research_completeness`.

Suggested qualitative labels:

- high;
- medium;
- low;
- unknown.

A claim can be highly confident even if the source origin is uncertain, and vice versa.

## 16. Transcript and media analysis integration

When a source contains speech and a usable media/reference path exists, Case Radar should reuse the existing Speech system:

1. create or reuse `ReferenceSource`;
2. request STT through the existing speech-job workflow;
3. import the transcript through the existing importer;
4. attach relevant transcript segments/timestamps to evidence.

The Case Radar must not import WhisperX/torch directly into its own domain services.

Transcription is optional per source and controlled by research depth/budget. A five-second silent CCTV clip should not create an STT job merely because it is a video.

## 17. Dossier output

Each final case dossier should provide a concise top section and expandable evidence.

Required fields:

- provisional case title;
- why it matches the requested theme;
- concise description of what is visible/reported;
- primary candidate video/post;
- earliest known source;
- likely original source, if different;
- earliest substantiated date;
- alleged location;
- uploader/creator information available from sources;
- source history/repost chain;
- important comments/replies;
- external context;
- corroborated facts;
- unverified claims;
- contradictions;
- debunks/alternative explanations;
- provenance confidence;
- research completeness;
- transcript excerpts/timestamps where useful;
- links to all important sources;
- suggested useful segment/timestamp for editorial review, where derivable;
- notes explaining why the system stopped researching.

The dossier should never present generated prose without access to the underlying evidence links.

## 18. Run quality and stopping rules

A case is “usable” for satisfying `desired_usable_cases` only when it meets a minimum threshold:

- has at least one accessible primary source;
- is not a high-confidence duplicate of an already accepted case;
- has enough context to describe what is allegedly happening;
- has provenance status, even if only “origin unknown”;
- has at least one research path attempted beyond the discovery result;
- has no hard exclusion triggered by the request.

Research stops when one of these occurs:

- target usable-case count reached and minimum quality is met;
- global/provider query budget exhausted;
- source budget exhausted;
- no meaningful unresolved research question remains;
- enabled providers are unavailable;
- user cancels the run.

A run may complete as `partially_completed` if it produces useful dossiers but cannot hit the requested count.

## 19. Cost controls

Every provider declares cost class and usage counters.

Run configuration supports:

- maximum search calls per provider;
- maximum source fetches;
- maximum comments fetched per source;
- maximum research recursion depth;
- maximum STT jobs;
- whether paid providers are allowed;
- optional monetary/request quota ceilings where measurable.

Default mode does not require paid X/TikTok/Instagram access.

Caching and source deduplication occur before repeated provider calls whenever possible.

## 20. Error handling

Provider errors are classified into categories such as:

- unavailable;
- authentication expired;
- permission/plan limitation;
- rate limited;
- challenge/manual-login required;
- not found/deleted/private;
- malformed response;
- transient network error;
- unsupported operation.

A single provider failure should normally downgrade coverage, not fail the whole run.

Case/research errors are attached to the affected source/case and surfaced in the dossier when they materially reduce confidence.

The run fails completely only when it cannot perform meaningful discovery/research at all or encounters an unrecoverable internal error.

## 21. UI design

Add a dedicated **Case Radar** area rather than mixing this workflow into the ordinary discovery list.

Initial screens:

### 21.1 New research

Simple form with:

- theme;
- desired number of cases;
- languages;
- platform toggles;
- priorities/exclusions;
- research depth;
- advanced provider/budget controls collapsed by default.

### 21.2 Run view

Shows:

- stage/progress;
- enabled/available providers;
- coverage warnings;
- generated queries;
- candidate count;
- case cluster count;
- usable case count;
- partial failures;
- live case cards as they mature.

### 21.3 Case dossier

Top summary plus tabs/sections for:

- Overview;
- Sources;
- Comments & social context;
- Claims & evidence;
- Transcript/timestamps;
- Provenance;
- Research log.

Manual actions:

- approve/select;
- reject with reason;
- mark already used;
- merge with another case;
- split sources into a new case;
- set/override primary source;
- add research note.

## 22. Security and credentials

Provider credentials/sessions must not be stored in source code or committed configuration.

Requirements:

- environment/secret-backed official API credentials;
- authenticated social sessions isolated per provider account;
- sensitive session material never returned in normal API payloads;
- provider status exposes only non-secret account labels and health;
- logs redact tokens/cookies/session secrets.

The system may support manually replacing a failed logged-in account/session, but must not automate account creation, suspension evasion or challenge bypass.

## 23. Compliance boundary

The Case Radar is a research and provenance tool. Its design should prefer official APIs and publicly accessible/indexed data when practical.

Authenticated-session providers are optional/experimental and must be isolated so the product does not depend on them for correctness.

The system does not assume that discovering a public video grants permission to download, republish or monetize it. Publication rights remain a separate editorial/legal decision.

## 24. Observability and reproducibility

A completed run should be explainable later.

Persist:

- input request snapshot;
- generated queries;
- provider and method used;
- raw source snapshots where permitted;
- discovery timestamps;
- ranking/clustering reasons;
- research follow-up queries;
- claim evidence links;
- provider errors/coverage gaps;
- dossier generation version.

This makes failures debuggable and prevents the system from becoming an opaque “AI found this somehow” feature.

## 25. Testing strategy

Tests should be provider-independent by default.

### 25.1 Unit tests

- query generation;
- provider normalization;
- provider capability/fallback selection;
- social-context usefulness ranking;
- source deduplication;
- case clustering signals;
- claim-state transitions;
- stopping/budget logic;
- confidence labeling;
- dossier assembly.

### 25.2 Service/repository tests

- manual run lifecycle;
- idempotent source persistence;
- case/source relations;
- partial provider failure;
- cancellation;
- transcript/reference linkage;
- manual merge/split operations.

### 25.3 API tests

- create/list/fetch research runs;
- inspect candidates/cases;
- approve/reject/mark-used;
- merge/split;
- provider status;
- validation and error serialization.

### 25.4 Provider contract tests

Every provider implementation runs against a shared contract using fixtures/mocked transport. Live platform tests are separate opt-in integration tests and must not be required for ordinary CI.

## 26. Implementation slicing

The architecture is one subsystem but implementation should be incremental.

### Slice 1 — Case Radar foundation

- database/domain models;
- run lifecycle;
- provider interfaces/capabilities;
- manual run API;
- basic Case Radar UI;
- source normalization;
- dossier skeleton;
- reuse existing YouTube/web discovery where practical.

### Slice 2 — Discovery breadth

- Reddit provider/context;
- X platform adapter with web + optional logged-in + optional official methods;
- TikTok adapter with available methods;
- Instagram adapter with available methods;
- provider fallback and health UI;
- query expansion per platform/language.

### Slice 3 — Investigation depth

- bounded comments/replies collection;
- usefulness ranking;
- claim/evidence extraction;
- recursive follow-up research;
- provenance resolver;
- duplicate/repost clustering;
- richer dossier.

### Slice 4 — Media intelligence

- stronger near-duplicate media matching;
- transcript-trigger heuristics;
- transcript evidence/timestamps;
- provenance hints from watermarks/usernames/media metadata;
- editorial segment suggestions.

Each slice must remain usable without requiring the next slice to exist.

## 27. Migration strategy

Do not mutate existing applied migrations.

Case Radar schema changes receive new Alembic revisions after the current speech migrations. The implementation plan must inspect the actual repository head before choosing the next revision identifier because additional migrations may exist by implementation time.

Existing `ContentItem` rows are not bulk-migrated into cases. Cases are created through Case Radar research and link to existing items when a match is found.

## 28. Acceptance criteria for the first useful release

The first release is considered useful when the user can:

1. manually enter a research theme and target case count;
2. run discovery through at least the existing YouTube/web paths plus the new provider abstraction;
3. see normalized sources grouped into research cases;
4. inspect provenance/source history rather than only raw links;
5. view high-value social context for providers that support it;
6. see claims explicitly separated into corroborated/unverified/contradicted/source-claimed states;
7. open a case dossier with links and evidence;
8. approve, reject or mark a case already used;
9. receive a partial-completion result instead of losing the whole run when a provider fails;
10. reuse Content Radar reference/transcript infrastructure instead of a duplicate STT stack.

The multi-platform design is part of the architecture from the start, but not every provider must be fully implemented before the first usable foundation slice ships.

## 29. Non-goals preserved for later

After the manual workflow is proven reliable, later specs may add:

- saved research presets;
- recurring monitoring;
- notifications;
- automatic topic watchlists;
- editorial project/episode assembly;
- deeper rights/licensing workflows.

None of these should complicate the first manual Case Radar implementation.