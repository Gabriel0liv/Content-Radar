from __future__ import annotations

import gc
import os
from pathlib import Path
from typing import Any, Callable

from speech_worker.stt.errors import SttCancelled, SttModelLoadError, SttNoSpeech
from speech_worker.stt.normalize import normalize_whisperx_result
from speech_worker.stt.types import NormalizedTranscriptResult, SttResolvedConfig


ProgressCallback = Callable[[str, int, str], None]
CancelCheck = Callable[[], bool]


class WhisperXSttEngine:
    def __init__(self, hf_token: str | None = None, hf_home: str | None = None) -> None:
        self.hf_token = hf_token if hf_token is not None else os.getenv("HF_TOKEN")
        self.hf_home = hf_home if hf_home is not None else os.getenv("HF_HOME")

    @staticmethod
    def _check_cancel(cancel_check: CancelCheck, message: str) -> None:
        if cancel_check():
            raise SttCancelled(message)

    @staticmethod
    def _lazy_imports():
        import torch  # type: ignore
        import whisperx  # type: ignore

        return torch, whisperx

    @staticmethod
    def _cleanup_model(model: Any, torch: Any, device: str) -> None:
        if model is not None:
            del model
        if device == "cuda" and getattr(torch, "cuda", None) is not None:
            try:
                torch.cuda.empty_cache()
            except Exception:
                pass
        gc.collect()

    @staticmethod
    def _is_model_access_error(exc: Exception) -> bool:
        text = str(exc).lower()
        name = type(exc).__name__.lower()
        return any(
            token in text or token in name
            for token in (
                "localentrynotfound",
                "offlinemodeisenabled",
                "offline",
                "connection",
                "timeout",
                "gatedrepoerror",
                "unauthorized",
                "401 client error",
                "403 client error",
            )
        )

    def transcribe(
        self,
        input_wav: Path | str,
        config: SttResolvedConfig,
        progress_callback: ProgressCallback,
        cancel_check: CancelCheck,
    ) -> NormalizedTranscriptResult:
        self._check_cancel(cancel_check, "Job cancelado antes de carregar o modelo")
        torch, whisperx = self._lazy_imports()
        device = config.device
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"

        warnings: list[str] = []
        asr_model = None
        align_model = None
        diarize_pipeline = None

        progress_callback("loading_model", 15, f"Carregando WhisperX {config.model}")
        asr_options = {"initial_prompt": config.initial_prompt} if config.initial_prompt else {}
        vad_options = {
            "vad_onset": config.vad_onset,
            "vad_offset": config.vad_offset,
            "chunk_size": config.chunk_size,
        }
        try:
            asr_model = whisperx.load_model(
                config.model,
                device,
                compute_type=config.compute_type,
                asr_options=asr_options,
                vad_method="silero",
                vad_options=vad_options,
            )
        except Exception as exc:
            reason = "modelo/cache/Hugging Face indisponível" if self._is_model_access_error(exc) else str(exc)
            raise SttModelLoadError(f"Falha ao carregar WhisperX {config.model}: {reason}") from exc

        try:
            progress_callback("transcribing", 30, "Transcrevendo áudio")
            transcription = asr_model.transcribe(
                str(input_wav),
                batch_size=config.batch_size,
                language=config.language,
            )
        finally:
            self._cleanup_model(asr_model, torch, device)
            asr_model = None

        self._check_cancel(cancel_check, "Job cancelado após a transcrição")
        if not transcription.get("segments"):
            raise SttNoSpeech("Nenhuma fala foi detectada no áudio")

        detected_language = transcription.get("language") or config.language
        aligned_result = transcription
        alignment_used = False
        progress_callback("aligning", 55, "Alinhando timestamps por palavra")
        try:
            align_model, metadata = whisperx.load_align_model(language_code=detected_language, device=device)
            aligned_result = whisperx.align(
                transcription["segments"],
                align_model,
                metadata,
                str(input_wav),
                device,
                return_char_alignments=False,
            )
            if "language" not in aligned_result and detected_language:
                aligned_result["language"] = detected_language
            alignment_used = True
        except Exception as exc:
            warnings.append(f"Alinhamento indisponível; usando timestamps brutos: {exc}")
            aligned_result = transcription
        finally:
            self._cleanup_model(align_model, torch, device)
            align_model = None

        self._check_cancel(cancel_check, "Job cancelado após o alinhamento")

        diarized = False
        final_result = aligned_result
        if config.no_diarization:
            warnings.append("Diarização desativada")
        elif not self.hf_token:
            warnings.append("Diarização ignorada: HF_TOKEN não configurado")
        else:
            progress_callback("diarizing", 75, "Separando falantes")
            try:
                from whisperx.diarize import DiarizationPipeline  # type: ignore

                kwargs: dict[str, Any] = {
                    "model_name": config.diarize_model,
                    "token": self.hf_token,
                    "device": device,
                }
                if self.hf_home:
                    kwargs["cache_dir"] = self.hf_home
                diarize_pipeline = DiarizationPipeline(**kwargs)
                diarize_segments = diarize_pipeline(
                    str(input_wav),
                    min_speakers=config.min_speakers,
                    max_speakers=config.max_speakers,
                    num_speakers=config.num_speakers,
                )
                final_result = whisperx.assign_word_speakers(diarize_segments, aligned_result)
                if "language" not in final_result and detected_language:
                    final_result["language"] = detected_language
                diarized = True
            except Exception as exc:
                warnings.append(f"Diarização indisponível; mantendo transcrição sem falantes: {exc}")
                final_result = aligned_result
            finally:
                self._cleanup_model(diarize_pipeline, torch, device)
                diarize_pipeline = None

        self._check_cancel(cancel_check, "Job cancelado após a diarização")
        progress_callback("normalizing", 90, "Normalizando resultado")
        return normalize_whisperx_result(
            final_result,
            model=config.model,
            diarized=diarized,
            alignment_used=alignment_used,
            warnings=warnings,
        )
