from pathlib import Path
import types

from fastwispr.stt import FasterWhisperStt, normalize_language, sanitize_transcript


class FakeWhisperModel:
    kwargs = None
    transcribe_kwargs = None

    def __init__(self, model, **kwargs):
        self.model = model
        FakeWhisperModel.kwargs = kwargs

    def transcribe(self, path, **kwargs):
        FakeWhisperModel.transcribe_kwargs = kwargs
        info = types.SimpleNamespace(language="pt", language_probability=0.91)
        return [types.SimpleNamespace(text=" oi Rodrigo ")], info


class FakeEnglishWhisperModel(FakeWhisperModel):
    def transcribe(self, path, **kwargs):
        FakeWhisperModel.transcribe_kwargs = kwargs
        info = types.SimpleNamespace(language="en", language_probability=0.94)
        return [types.SimpleNamespace(text=" Would you like to learn more about the project? ")], info


class FakeHallucinatingThenPortugueseWhisperModel(FakeWhisperModel):
    calls = []

    def transcribe(self, path, **kwargs):
        FakeHallucinatingThenPortugueseWhisperModel.calls.append(kwargs)
        FakeWhisperModel.transcribe_kwargs = kwargs
        if len(FakeHallucinatingThenPortugueseWhisperModel.calls) == 1:
            info = types.SimpleNamespace(language="ja", language_probability=0.52)
            return [types.SimpleNamespace(text=" テスタンド、テスタンド.Olá, tudo bem? Testando. ")], info
        info = types.SimpleNamespace(language="pt", language_probability=0.98)
        return [types.SimpleNamespace(text=" Olá, tudo bem? Testando. ")], info


class FakeAccentEnglishDetectedAsPortugueseWhisperModel(FakeWhisperModel):
    calls = []

    def transcribe(self, path, **kwargs):
        FakeAccentEnglishDetectedAsPortugueseWhisperModel.calls.append(kwargs)
        FakeWhisperModel.transcribe_kwargs = kwargs
        if len(FakeAccentEnglishDetectedAsPortugueseWhisperModel.calls) == 1:
            info = types.SimpleNamespace(language="pt", language_probability=0.64)
            return [types.SimpleNamespace(text=" Poder o like ter ou ler no more about the project. ")], info
        info = types.SimpleNamespace(language="en", language_probability=1.0)
        return [types.SimpleNamespace(text=" Or do like to learn more about the project. ")], info


class FakePortugueseDetectedAsLowConfidencePortugueseWhisperModel(FakeWhisperModel):
    calls = []

    def transcribe(self, path, **kwargs):
        FakePortugueseDetectedAsLowConfidencePortugueseWhisperModel.calls.append(kwargs)
        FakeWhisperModel.transcribe_kwargs = kwargs
        if len(FakePortugueseDetectedAsLowConfidencePortugueseWhisperModel.calls) == 1:
            info = types.SimpleNamespace(language="pt", language_probability=0.62)
            return [types.SimpleNamespace(text=" Olá, tudo bem? Testando um, dois, três. ")], info
        info = types.SimpleNamespace(language="en", language_probability=1.0)
        return [types.SimpleNamespace(text=" All are too bang testing one do is trace. ")], info


class FakeHallucinatingWhisperModel(FakeWhisperModel):
    def transcribe(self, path, **kwargs):
        FakeWhisperModel.transcribe_kwargs = kwargs
        info = types.SimpleNamespace(language="ja", language_probability=0.52)
        return [types.SimpleNamespace(text=" テスタンド、テスタンド.Olá, tudo bem? Testando. ")], info


def test_normalize_language_accepts_bilingual_mode():
    assert normalize_language("pt-en") is None
    assert normalize_language("bilingual") is None


def test_faster_whisper_uses_cpu_int8_and_returns_language(monkeypatch):
    monkeypatch.setitem(__import__("sys").modules, "faster_whisper", types.SimpleNamespace(WhisperModel=FakeWhisperModel))

    stt = FasterWhisperStt(model="small", device="cpu", compute_type="int8")
    result = stt.transcribe_result(Path("sample.wav"))

    assert FakeWhisperModel.kwargs == {"device": "cpu", "compute_type": "int8"}
    assert result.text == "oi Rodrigo"
    assert result.language == "pt"
    assert result.language_probability == 0.91


def test_bilingual_mode_preserves_english_instead_of_forcing_portuguese(monkeypatch):
    monkeypatch.setitem(__import__("sys").modules, "faster_whisper", types.SimpleNamespace(WhisperModel=FakeEnglishWhisperModel))

    stt = FasterWhisperStt(model="small", device="cpu", compute_type="int8", language="pt-en")
    result = stt.transcribe_result(Path("sample.wav"))

    assert result.text == "Would you like to learn more about the project?"
    assert result.language == "en"
    assert FakeWhisperModel.transcribe_kwargs["language"] is None
    assert FakeWhisperModel.transcribe_kwargs["multilingual"] is True
    assert FakeWhisperModel.transcribe_kwargs["task"] == "transcribe"


def test_bilingual_mode_falls_back_to_portuguese_when_auto_detects_unrelated_script(monkeypatch):
    FakeHallucinatingThenPortugueseWhisperModel.calls = []
    monkeypatch.setitem(
        __import__("sys").modules,
        "faster_whisper",
        types.SimpleNamespace(WhisperModel=FakeHallucinatingThenPortugueseWhisperModel),
    )

    stt = FasterWhisperStt(model="small", device="cpu", compute_type="int8", language="pt-en")
    result = stt.transcribe_result(Path("sample.wav"))

    assert result.text == "Olá, tudo bem? Testando."
    assert [call["language"] for call in FakeHallucinatingThenPortugueseWhisperModel.calls] == [None, "pt"]


def test_bilingual_mode_tries_forced_english_when_accented_english_is_detected_as_portuguese(monkeypatch):
    FakeAccentEnglishDetectedAsPortugueseWhisperModel.calls = []
    monkeypatch.setitem(
        __import__("sys").modules,
        "faster_whisper",
        types.SimpleNamespace(WhisperModel=FakeAccentEnglishDetectedAsPortugueseWhisperModel),
    )

    stt = FasterWhisperStt(model="small", device="cpu", compute_type="int8", language="pt-en")
    result = stt.transcribe_result(Path("sample.wav"))

    assert result.text == "Or do like to learn more about the project."
    assert result.language == "en"
    assert [call["language"] for call in FakeAccentEnglishDetectedAsPortugueseWhisperModel.calls] == [None, "en"]


def test_bilingual_mode_keeps_portuguese_when_forced_english_is_worse(monkeypatch):
    FakePortugueseDetectedAsLowConfidencePortugueseWhisperModel.calls = []
    monkeypatch.setitem(
        __import__("sys").modules,
        "faster_whisper",
        types.SimpleNamespace(WhisperModel=FakePortugueseDetectedAsLowConfidencePortugueseWhisperModel),
    )

    stt = FasterWhisperStt(model="small", device="cpu", compute_type="int8", language="pt-en")
    result = stt.transcribe_result(Path("sample.wav"))

    assert result.text == "Olá, tudo bem? Testando um, dois, três."
    assert result.language == "pt"
    assert [call["language"] for call in FakePortugueseDetectedAsLowConfidencePortugueseWhisperModel.calls] == [None, "en"]


def test_faster_whisper_explicitly_transcribes_and_preserves_original_language(monkeypatch):
    monkeypatch.setitem(__import__("sys").modules, "faster_whisper", types.SimpleNamespace(WhisperModel=FakeWhisperModel))

    stt = FasterWhisperStt(model="small", device="cpu", compute_type="int8", language="auto")
    stt.transcribe_result(Path("sample.wav"))

    assert FakeWhisperModel.transcribe_kwargs["task"] == "transcribe"
    assert FakeWhisperModel.transcribe_kwargs["language"] is None
    assert FakeWhisperModel.transcribe_kwargs["condition_on_previous_text"] is False
    assert "Do not translate" in FakeWhisperModel.transcribe_kwargs["initial_prompt"]
    assert "Japanese" in FakeWhisperModel.transcribe_kwargs["initial_prompt"]


def test_faster_whisper_uses_conservative_decoding_and_vad(monkeypatch):
    monkeypatch.setitem(__import__("sys").modules, "faster_whisper", types.SimpleNamespace(WhisperModel=FakeWhisperModel))

    stt = FasterWhisperStt(model="small", device="cpu", compute_type="int8", language="pt-BR")
    stt.transcribe_result(Path("sample.wav"))

    assert FakeWhisperModel.transcribe_kwargs["temperature"] == 0.0
    assert FakeWhisperModel.transcribe_kwargs["vad_filter"] is True
    assert FakeWhisperModel.transcribe_kwargs["vad_parameters"]["min_silence_duration_ms"] == 500
    assert FakeWhisperModel.transcribe_kwargs["no_speech_threshold"] == 0.55
    assert FakeWhisperModel.transcribe_kwargs["suppress_blank"] is True


def test_faster_whisper_normalizes_brazilian_portuguese_language(monkeypatch):
    monkeypatch.setitem(__import__("sys").modules, "faster_whisper", types.SimpleNamespace(WhisperModel=FakeWhisperModel))

    stt = FasterWhisperStt(model="small", device="cpu", compute_type="int8", language="pt-BR")
    stt.transcribe_result(Path("sample.wav"))

    assert FakeWhisperModel.transcribe_kwargs["language"] == "pt"
    assert "português brasileiro" in FakeWhisperModel.transcribe_kwargs["initial_prompt"]


def test_sanitize_transcript_removes_unexpected_asian_script_hallucination():
    text = "テスタンド、テスタンド.Olá, tudo bem? Testando."

    assert sanitize_transcript(text) == "Olá, tudo bem? Testando."


def test_transcribe_result_sanitizes_hallucinated_script(monkeypatch):
    monkeypatch.setitem(
        __import__("sys").modules,
        "faster_whisper",
        types.SimpleNamespace(WhisperModel=FakeHallucinatingWhisperModel),
    )

    stt = FasterWhisperStt(model="small", device="cpu", compute_type="int8", language="pt-BR")
    result = stt.transcribe_result(Path("sample.wav"))

    assert result.text == "Olá, tudo bem? Testando."
