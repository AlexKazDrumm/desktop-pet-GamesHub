from __future__ import annotations

from desktop_pet_gameshub.services.mgl_parser import parse_html

JSONLD_HTML = """
<html><body>
<main>
<h1>Test Game Title</h1>
<script type="application/ld+json">
{
  "@type": "VideoGame",
  "genre": ["Action", "RPG"],
  "gamePlatform": ["PC", "PlayStation 5"],
  "developer": {"name": "Test Dev"},
  "publisher": {"name": "Test Pub"}
}
</script>
<p>Released: 2021</p>
<img src="https://images.igdb.com/igdb/image/upload/t_cover_big/abc.jpg" width="200" height="300">
</main>
</body></html>
"""

FALLBACK_HTML = """
<html><body>
<main>
<h1>Fallback Game (2019)</h1>
<ul>
<li><span class="text-dimmed">Developer:</span><span><a>Fallback Studio</a></span></li>
<li><span class="text-dimmed">Genre:</span><span>Puzzle, Adventure</span></li>
<li><span class="text-dimmed">Platform:</span><span>Nintendo Switch</span></li>
</ul>
</main>
</body></html>
"""

EMPTY_HTML = "<html><body><p>Nothing to see here</p></body></html>"


def test_parse_html_reads_jsonld_block() -> None:
    data = parse_html(JSONLD_HTML)
    assert data.title == "Test Game Title"
    assert data.year == 2021
    assert data.cover_url is not None and "images.igdb.com" in data.cover_url
    assert data.developers == ["Test Dev"]
    assert data.publishers == ["Test Pub"]
    assert data.genres == ["Action", "RPG"]
    assert data.platforms == ["PC (Microsoft Windows)", "PlayStation 5"]


def test_parse_html_falls_back_to_html_labels() -> None:
    data = parse_html(FALLBACK_HTML)
    assert "Fallback Game" in data.title
    assert data.year == 2019
    assert data.developers == ["Fallback Studio"]
    assert data.genres == ["Adventure", "Puzzle"]
    assert data.platforms == ["Nintendo Switch"]


def test_parse_html_handles_page_without_expected_data() -> None:
    data = parse_html(EMPTY_HTML)
    assert data.title is None
    assert data.year is None
    assert data.developers == []
    assert data.platforms == []
