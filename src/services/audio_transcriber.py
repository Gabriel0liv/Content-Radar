import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import yt_dlp


class AudioTranscriber:
    """Temporary YouTube-audio transcription using faster-whisper."""

    def transcribe_youtube(self, url: str) -> Dict[str, Any]:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError("faster-whisper não está instalado.") from exc

        model_name = os.getenv("FASTER_WHISPER_MODEL", "small")
        device = os.getenv("FASTER_WHISPER_DEVICE", "cpu")
        compute_type = os.getenv(
            "FASTER_WHISPER_COMPUTE_TYPE",
            "int8" if device == "cpu" else "float16",
        )

        with tempfile.TemporaryDirectory(prefix="content-radar-audio-") as temp_dir:
            output_template = str(Path(temp_dir) / "audio.%(ext)s")
            with yt_dlp.YoutubeDL({
                "format": "bestaudio/best",
                "outtmpl": output_template,
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
                "socket_timeout": 30,
            }) as ydl:
                info = ydl.extract_info(url, download=True)
                audio_path = Path(ydl.prepare_filename(info))

            if not audio_path.exists():
                candidates = list(Path(temp_dir).glob("audio.*"))
                if not candidates:
                    raise RuntimeError("Arquivo temporário de áudio não foi localizado.")
                audio_path = candidates[0]

            model = WhisperModel(model_name, device=device, compute_type=compute_type)
            segment_iter, detected = model.transcribe(
                str(audio_path),
                beam_size=5,
                vad_filter=True,
                condition_on_previous_text=True,
            )
            raw_segments: List[Dict[str, Any]] = [
                {"start": seg.start, "end": seg.end, "text": seg.text}
                for seg in segment_iter
            ]

        return {
            "language": getattr(detected, "language", None),
            "language_probability": getattr(detected, "language_probability", None),
            "model": model_name,
            "segments": raw_segments,
        }
