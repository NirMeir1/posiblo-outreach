from conftest import REPO

TEMPLATE = REPO / "templates" / "consent_request_v1.txt"


def _prompt2_text() -> str:
    doc = (REPO / "docs" / "build-prompts.md").read_text(encoding="utf-8").replace("\r\n", "\n")
    marker = "filled from config at send time:\n\n"
    start = doc.index(marker) + len(marker)
    end = doc.index("\n\n   Add a short note", start)
    return doc[start:end]


def test_template_matches_prompt_2_character_for_character() -> None:
    actual = TEMPLATE.read_bytes().decode("utf-8")
    expected = _prompt2_text()
    assert actual == expected
    assert len(expected.split("\n")) == 4 and expected.startswith("פרסומת\n")


def test_template_has_only_the_address_placeholder_and_no_todo() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    assert text.count("{") == text.count("}") == 1
    assert "{address}" in text
    assert "TODO" not in text


def test_template_bytes_are_clean() -> None:
    data = TEMPLATE.read_bytes()
    assert not data.startswith(b"\xef\xbb\xbf")  # no BOM
    assert b"\r" not in data                     # LF only (.gitattributes pins eol=lf)


def test_docs_note_says_pending_legal_review() -> None:
    note = (REPO / "docs" / "message-template.md").read_text(encoding="utf-8")
    assert "pending legal review" in note.lower()
    assert "version" in note.lower() and "consent_request_v1.txt" in note
