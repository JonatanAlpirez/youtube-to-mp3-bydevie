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


class TestParseNonYoutubeSites:
    """Tests para URLs de sitios no-YouTube (SoundCloud, Bandcamp, Vimeo, etc.)."""

    def test_soundcloud_url_accepted(self, tmp_path: Path) -> None:
        f = tmp_path / "links.txt"
        f.write_text("https://soundcloud.com/artist/track-name\n", encoding="utf-8")
        result = parse_link_file(f)
        assert result.total == 1
        e = result.entries[0]
        # Para sitios no-YouTube, video_id == url
        assert e.video_id == "https://soundcloud.com/artist/track-name"
        assert e.url == "https://soundcloud.com/artist/track-name"

    def test_bandcamp_url_accepted(self, tmp_path: Path) -> None:
        f = tmp_path / "links.txt"
        f.write_text("https://artist.bandcamp.com/track/song\n", encoding="utf-8")
        result = parse_link_file(f)
        assert result.total == 1
        assert result.entries[0].video_id == "https://artist.bandcamp.com/track/song"

    def test_vimeo_url_accepted(self, tmp_path: Path) -> None:
        f = tmp_path / "links.txt"
        f.write_text("https://vimeo.com/123456789\n", encoding="utf-8")
        result = parse_link_file(f)
        assert result.total == 1
        assert result.entries[0].video_id == "https://vimeo.com/123456789"

    def test_mixed_youtube_and_others(self, tmp_path: Path) -> None:
        f = tmp_path / "links.txt"
        f.write_text(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ\n"
            "https://soundcloud.com/artist/track\n"
            "https://bandcamp.com/track/123\n",
            encoding="utf-8",
        )
        result = parse_link_file(f)
        assert result.total == 3
        ids = [e.video_id for e in result.entries]
        assert ids[0] == "dQw4w9WgXcQ"
        assert ids[1] == "https://soundcloud.com/artist/track"
        assert ids[2] == "https://bandcamp.com/track/123"

    def test_dedupe_non_youtube_urls(self, tmp_path: Path) -> None:
        """URLs no-YouTube duplicadas se deduplican por igualdad de string."""
        f = tmp_path / "links.txt"
        f.write_text(
            "https://soundcloud.com/artist/track\nhttps://soundcloud.com/artist/track\n",
            encoding="utf-8",
        )
        result = parse_link_file(f)
        assert result.total == 1
        assert len(result.skipped) == 1
        assert "duplicado" in result.skipped[0][2]

    def test_youtube_shorts_url(self, tmp_path: Path) -> None:
        f = tmp_path / "links.txt"
        f.write_text("https://www.youtube.com/shorts/dQw4w9WgXcQ\n", encoding="utf-8")
        result = parse_link_file(f)
        assert result.total == 1
        assert result.entries[0].video_id == "dQw4w9WgXcQ"

    def test_non_youtube_with_description(self, tmp_path: Path) -> None:
        f = tmp_path / "links.txt"
        f.write_text("https://soundcloud.com/artist/track  My favorite\n", encoding="utf-8")
        result = parse_link_file(f)
        assert result.total == 1
        assert result.entries[0].description == "My favorite"

    def test_non_url_text_still_rejected(self, tmp_path: Path) -> None:
        """Texto plano sin http:// sigue siendo rechazado."""
        f = tmp_path / "links.txt"
        f.write_text("just some random text\n", encoding="utf-8")
        result = parse_link_file(f)
        assert result.total == 0
        assert len(result.skipped) == 1
        assert "válido" in result.skipped[0][2]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
