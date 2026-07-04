from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Literal, Protocol
import unicodedata

LanguageMode = Literal["auto", "bilingual", "pt", "en"]

DEFAULT_INITIAL_PROMPT = (
    "Transcribe exactly what is spoken. Do not translate. Preserve the original language. "
    "The speaker may use English or Brazilian Portuguese only, including technical terms, code names, "
    "file paths, product names, and agent instructions. Use Latin alphabet. Never output Japanese, "
    "Chinese, Korean, Cyrillic, or other unrelated scripts."
)
PORTUGUESE_INITIAL_PROMPT = (
    "Transcreva exatamente o que foi falado em português brasileiro. Não traduza. "
    "Use alfabeto latino. Nunca escreva japonês, chinês ou coreano. "
    "Reconheça palavras comuns como: olá, tudo bem, testando, um, dois, três, "
    "estamos, jogando, projeto, texto, comando."
)
ENGLISH_INITIAL_PROMPT = (
    "Transcribe exactly what is spoken in English. Do not translate. Use Latin alphabet. "
    "Never output Japanese, Chinese, Korean, Cyrillic, or other unrelated scripts."
)
_UNEXPECTED_SCRIPT_RE = re.compile(
    r"[\u3040-\u309f\u30a0-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uac00-\ud7af\u3000-\u303f]+"
)
_LEADING_ORPHAN_PUNCTUATION_RE = re.compile(r"^[\s\.,;:!?…\-–—]+")
_WORD_RE = re.compile(r"[\w']+", re.UNICODE)
ENGLISH_HINT_WORDS = {
    "a",
    "about",
    "are",
    "do",
    "hello",
    "how",
    "learn",
    "like",
    "more",
    "project",
    "testing",
    "texting",
    "the",
    "to",
    "would",
    "you",
}
PORTUGUESE_HINT_WORDS = {
    "bem",
    "comando",
    "dois",
    "estamos",
    "jogando",
    "ola",
    "olá",
    "pois",
    "projeto",
    "sim",
    "testando",
    "texto",
    "tres",
    "três",
    "tudo",
    "um",
}


def normalize_language_mode(language: str | None) -> LanguageMode:
    if language is None:
        return "auto"
    normalized = language.strip().lower().replace("_", "-").replace("/", "-")
    if normalized in {"", "auto", "detect"}:
        return "auto"
    if normalized in {"pt-en", "en-pt", "bilingual", "mixed", "dual"}:
        return "bilingual"
    if normalized in {"pt-br", "pt", "portuguese", "português"}:
        return "pt"
    if normalized in {"en", "en-us", "en-gb", "english"}:
        return "en"
    raise ValueError("STT language must be pt-en, bilingual, auto, pt-BR, pt, en, or english")


def normalize_language(language: str | None) -> str | None:
    mode = normalize_language_mode(language)
    if mode in {"auto", "bilingual"}:
        return None
    return mode


def initial_prompt_for_language(language: str | None) -> str:
    mode = normalize_language_mode(language)
    if mode == "pt":
        return PORTUGUESE_INITIAL_PROMPT
    if mode == "en":
        return ENGLISH_INITIAL_PROMPT
    return DEFAULT_INITIAL_PROMPT


def contains_unexpected_script(text: str) -> bool:
    return bool(_UNEXPECTED_SCRIPT_RE.search(text))


def _strip_accents(text: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char)
    )


def _word_set(text: str) -> set[str]:
    lowered = text.lower()
    words = set(_WORD_RE.findall(lowered))
    words.update(_WORD_RE.findall(_strip_accents(lowered)))
    return words


def english_hint_score(text: str) -> int:
    return len(_word_set(text) & ENGLISH_HINT_WORDS)


def portuguese_hint_score(text: str) -> int:
    return len(_word_set(text) & PORTUGUESE_HINT_WORDS)


def sanitize_transcript(text: str) -> str:
    sanitized = _UNEXPECTED_SCRIPT_RE.sub(" ", text)
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    sanitized = _LEADING_ORPHAN_PUNCTUATION_RE.sub("", sanitized)
    return sanitized.strip()


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    language: str | None = None
    language_probability: float | None = None


@dataclass(frozen=True)
class _RawTranscription:
    result: TranscriptionResult
    raw_text: str


class SttAdapter(Protocol):
    def transcribe(self, audio_path: str | Path) -> str:
        ...


class PlaceholderStt:
    def transcribe(self, audio_path: str | Path) -> str:
        raise RuntimeError("No STT provider configured. Install the stt extra and use provider=faster-whisper.")

    def transcribe_result(self, audio_path: str | Path) -> TranscriptionResult:
        return TranscriptionResult(text=self.transcribe(audio_path))


class FasterWhisperStt:
    def __init__(
        self,
        model: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str | None = "pt-en",
        initial_prompt: str | None = None,
        beam_size: int = 5,
        condition_on_previous_text: bool = False,
    ):
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError("Install STT support with: python -m pip install -e '.[stt]'") from exc
        self.model_name = model
        self.language_mode = normalize_language_mode(language)
        self.language = normalize_language(language)
        self.initial_prompt = initial_prompt or initial_prompt_for_language(language)
        self.beam_size = beam_size
        self.condition_on_previous_text = condition_on_previous_text
        self.model = WhisperModel(model, device=device, compute_type=compute_type)

    def _transcribe_once(self, audio_path: str | Path, *, language: str | None, prompt: str) -> _RawTranscription:
        segments, info = self.model.transcribe(
            str(audio_path),
            language=language,
            task="transcribe",
            beam_size=self.beam_size,
            temperature=0.0,
            condition_on_previous_text=self.condition_on_previous_text,
            initial_prompt=prompt,
            vad_filter=True,
            vad_parameters={
                "min_speech_duration_ms": 120,
                "min_silence_duration_ms": 500,
                "speech_pad_ms": 250,
            },
            no_speech_threshold=0.55,
            suppress_blank=True,
            multilingual=language is None,
        )
        raw_text = " ".join(segment.text.strip() for segment in segments).strip()
        result = TranscriptionResult(
            text=sanitize_transcript(raw_text),
            language=getattr(info, "language", None),
            language_probability=getattr(info, "language_probability", None),
        )
        return _RawTranscription(result=result, raw_text=raw_text)

    def _needs_bilingual_portuguese_fallback(self, transcription: _RawTranscription) -> bool:
        if self.language_mode != "bilingual":
            return False
        detected_language = transcription.result.language
        if detected_language not in {None, "pt", "en"}:
            return True
        return contains_unexpected_script(transcription.raw_text)

    def _needs_bilingual_english_probe(self, transcription: _RawTranscription) -> bool:
        if self.language_mode != "bilingual":
            return False
        if transcription.result.language != "pt":
            return False
        probability = transcription.result.language_probability or 0.0
        if probability < 0.80:
            return True
        return english_hint_score(transcription.result.text) > portuguese_hint_score(transcription.result.text) + 1

    def _prefer_english_candidate(
        self,
        original: _RawTranscription,
        english: _RawTranscription,
    ) -> bool:
        if not english.result.text:
            return False
        english_score = english_hint_score(english.result.text)
        original_english_score = english_hint_score(original.result.text)
        english_portuguese_score = portuguese_hint_score(english.result.text)
        original_portuguese_score = portuguese_hint_score(original.result.text)
        if (
            english.result.language == "en"
            and english_score >= max(2, english_portuguese_score + 2)
            and english_score > original_portuguese_score
        ):
            return True
        return english_score > original_english_score + 1 and english_score > original_portuguese_score

    def transcribe_result(self, audio_path: str | Path) -> TranscriptionResult:
        transcription = self._transcribe_once(audio_path, language=self.language, prompt=self.initial_prompt)
        if self._needs_bilingual_portuguese_fallback(transcription):
            transcription = self._transcribe_once(
                audio_path,
                language="pt",
                prompt=PORTUGUESE_INITIAL_PROMPT,
            )
        elif self._needs_bilingual_english_probe(transcription):
            english_transcription = self._transcribe_once(
                audio_path,
                language="en",
                prompt=ENGLISH_INITIAL_PROMPT,
            )
            if self._prefer_english_candidate(transcription, english_transcription):
                transcription = english_transcription
        return transcription.result

    def transcribe(self, audio_path: str | Path) -> str:
        return self.transcribe_result(audio_path).text


def make_stt(
    provider: str = "placeholder",
    model: str = "small",
    device: str = "cpu",
    compute_type: str = "int8",
    language: str | None = "pt-en",
) -> SttAdapter:
    if provider == "placeholder":
        return PlaceholderStt()
    if provider == "faster-whisper":
        return FasterWhisperStt(model=model, device=device, compute_type=compute_type, language=language)
    raise ValueError(f"Unknown STT provider: {provider}")
