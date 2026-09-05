from __future__ import annotations

from src.services.speech_worker_protocol import JobCancelled, UnsupportedOperationError


class SpeechExecutor:
    def execute(self, job, progress_callback, cancel_check) -> dict:
        if cancel_check():
            raise JobCancelled("Job cancelado antes da execução")

        if getattr(job, "operation", None) == "noop_test":
            progress_callback("running", 50, "Executando teste")
            if cancel_check():
                raise JobCancelled("Job cancelado durante a execução")
            progress_callback("finalizing", 100, "Teste concluído")
            return {"success": True, "mode": "noop_test"}

        raise UnsupportedOperationError(
            f"Operação {getattr(job, 'operation', None)!r} ainda não possui engine instalada nesta fase"
        )
