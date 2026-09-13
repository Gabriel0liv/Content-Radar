class SttEngineError(RuntimeError):
    """Base error for native STT execution."""


class SttCancelled(SttEngineError):
    pass


class SttNoSpeech(SttEngineError):
    pass


class SttModelLoadError(SttEngineError):
    pass


class SttAudioConversionError(SttEngineError):
    pass
