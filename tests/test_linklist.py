"""Tests del parser de links."""

from pathlib import Path

import pytest

from yt_links_mp3.linklist import parse_link_file, parse_link_line


class TestParseLinkLine:
    def test_full_url(self) -> None:
        vid, desc = parse_link_line("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert vid == "dQw4w9WgXcQ"
        assert desc is None

    def test_short_url(self) -> None:
        vid, desc = parse_link_line("https://youtu.be/dQw4w9WgXcQ")
        assert vid == "dQw4w9WgXcQ"
        assert desc is None

    def test_bare_id(self) -> None:
        vid, desc = parse_link_line("dQw4w9WgXcQ")
        assert vid == "dQw4w9WgXcQ"
        assert desc is None

    def test_with_description(self) -> None:
        vid, desc = parse_link_line("dQw4w9WgXcQ   Rick Astley clásico")
        assert vid == "dQw4w9WgXcQ"
        assert desc == "Rick Astley clásico"

    def test_invalid_token(self) -> None:
        vid, desc = parse_link_line("not a link")
        assert vid is None
        assert desc is None


class TestParseLinkFile:
    def test_full_file(self, tmp_path: Path) -> None:
        f = tmp_path / "links.txt"
        f.write_text(
            """# comment
// another comment

https://www.youtube.com/watch?v=dQw4w9WgXcQ
https://youtu.be/jNQXAC9IVRw   Rick Astley
dQw4w9WgXcQ                          # dedupe de arriba
not a link at all

jNQXAC9IVRw
""",
            encoding="utf-8",
        )
        result = parse_link_file(f)
        assert result.total == 2
        ids = {e.video_id for e in result.entries}
        assert ids == {"dQw4w9WgXcQ", "jNQXAC9IVRw"}

        # 2 duplicados (mismo ID 2 veces) + 1 línea inválida = 3 skipped
        assert len(result.skipped) == 3
        skip_reasons = {reason for _, _, reason in result.skipped}
        assert any("duplicado" in r for r in skip_reasons)
        assert any("válido" in r for r in skip_reasons)

    def test_empty_file(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.txt"
        f.write_text("", encoding="utf-8")
        result = parse_link_file(f)
        assert result.total == 0
        assert result.skipped == []

    def test_bom_tolerated(self, tmp_path: Path) -> None:
        f = tmp_path / "bom.txt"
        f.write_bytes("\ufeffdQw4w9WgXcQ\n".encode("utf-8"))
        result = parse_link_file(f)
        assert result.total == 1
        assert result.entries[0].video_id == "dQw4w9WgXcQ"

    def test_preserves_order(self, tmp_path: Path) -> None:
        f = tmp_path / "ordered.txt"
        f.write_text(
            "https://youtu.be/AAAAAAAAAAA\n"
            "https://youtu.be/BBBBBBBBBBB\n"
            "https://youtu.be/CCCCCCCCCCC\n",
            encoding="utf-8",
        )
        result = parse_link_file(f)
        ids = [e.video_id for e in result.entries]
        assert ids == ["AAAAAAAAAAA", "BBBBBBBBBBB", "CCCCCCCCCCC"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
