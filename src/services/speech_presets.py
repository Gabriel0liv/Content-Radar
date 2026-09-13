from __future__ import annotations

from src.schemas.speech import (
    ResolvedSpeechSttConfig,
    SpeechSttOptions,
    SpeechSttPresetSummary,
)


_BUILTIN_PRESETS = (
    SpeechSttPresetSummary(
        name="fast",
        label="Rápido",
        description="Para rascunhos e extração rápida, usando um modelo leve.",
    ),
    SpeechSttPresetSummary(
        name="balanced",
        label="Equilibrado",
        description="Modo recomendado para uso geral, com boa precisão e custo moderado.",
    ),
    SpeechSttPresetSummary(
        name="max_quality",
        label="Máxima qualidade",
        description="Prioriza fidelidade e usa configurações conservadoras de memória.",
    ),
)


def list_builtin_stt_presets() -> list[SpeechSttPresetSummary]:
    return [preset.model_copy(deep=True) for preset in _BUILTIN_PRESETS]


def resolve_stt_config(options: SpeechSttOptions) -> ResolvedSpeechSttConfig:
    if options.preset == "fast":
        model = "small"
        batch_size = 2
    elif options.preset == "balanced":
        model = "medium"
        batch_size = 2
    else:
        model = "large-v3"
        batch_size = 1

    if options.quiet_speech:
        vad_onset = 0.1
        vad_offset = 0.1
    else:
        vad_onset = 0.500
        vad_offset = 0.363

    num_speakers = options.num_speakers
    min_speakers = None if num_speakers is not None else options.min_speakers
    max_speakers = None if num_speakers is not None else options.max_speakers

    return ResolvedSpeechSttConfig(
        model=model,
        language=options.language,
        device="auto",
        compute_type="int8",
        batch_size=batch_size,
        no_diarization=not options.identify_speakers,
        num_speakers=num_speakers,
        min_speakers=min_speakers,
        max_speakers=max_speakers,
        vad_onset=vad_onset,
        vad_offset=vad_offset,
        initial_prompt=options.initial_prompt,
    )
