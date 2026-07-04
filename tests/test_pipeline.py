from fastwispr.db import DictionaryEntry, Snippet
from fastwispr.pipeline import process_text


def test_correction_cleanup_replaces_previous_word():
    result = process_text("meet at five actually six")
    assert result.final == "Meet at six."


def test_filler_removal():
    result = process_text("um I think we should uh deploy Friday today")
    assert result.final == "I think we should deploy Friday today."


def test_like_is_not_removed_when_it_is_a_real_verb():
    result = process_text("I like Rust")
    assert result.final == "I like Rust."


def test_dictionary_replacement():
    result = process_text(
        "send it through tail scale",
        dictionary=[DictionaryEntry(term="tail scale", replacement="Tailscale")],
    )
    assert result.final == "Send it through Tailscale."


def test_snippet_expansion():
    result = process_text(
        "insert scheduling link",
        snippets=[Snippet(cue="insert scheduling link", body="https://cal.com/rodrigo")],
    )
    assert result.final == "https://cal.com/rodrigo"
    assert result.snippet_expanded is True
