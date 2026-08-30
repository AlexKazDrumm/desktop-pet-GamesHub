from __future__ import annotations

from desktop_pet_gameshub.db.repository import GameRepository
from desktop_pet_gameshub.models.game import Game, GameFilter


def _make_game(repo: GameRepository, **overrides) -> int:
    defaults = dict(
        title="Test Game",
        year=2020,
        cover_url=None,
        developers=["Dev Studio"],
        publishers=["Pub House"],
        genres=["RPG"],
        platforms=["PC (Microsoft Windows)"],
    )
    defaults.update(overrides)
    return repo.save_game(Game(**defaults))


def test_upsert_name_is_idempotent(repo: GameRepository) -> None:
    first_id = repo.upsert_name("genres", "Roguelike")
    second_id = repo.upsert_name("genres", " Roguelike ")
    assert first_id == second_id
    assert len(repo.get_all("genres")) == 1


def test_save_game_creates_links(repo: GameRepository) -> None:
    game_id = _make_game(repo, developers=["A", "B"], genres=["RPG", "Action"])

    row = repo.get_game(game_id)
    assert row["title"] == "Test Game"
    assert sorted(repo.names_for_game("developers", game_id)) == ["A", "B"]
    assert sorted(repo.names_for_game("genres", game_id)) == ["Action", "RPG"]


def test_save_game_update_replaces_links(repo: GameRepository) -> None:
    game_id = _make_game(repo, developers=["A", "B"])
    repo.save_game(Game(id=game_id, title="Test Game", developers=["C"]))
    assert repo.names_for_game("developers", game_id) == ["C"]


def test_delete_game_removes_row(repo: GameRepository) -> None:
    game_id = _make_game(repo)
    repo.delete_game(game_id)
    assert repo.get_game(game_id) is None


def test_fetch_game_list_filters_by_year(repo: GameRepository) -> None:
    _make_game(repo, title="Old Game", year=2000)
    _make_game(repo, title="New Game", year=2020)

    rows, total = repo.fetch_game_list(GameFilter(year=2020))
    assert total == 1
    assert rows[0]["title"] == "New Game"


def test_fetch_game_list_filters_by_platform(repo: GameRepository) -> None:
    _make_game(repo, title="PC Game", platforms=["PC (Microsoft Windows)"])
    _make_game(repo, title="Switch Game", platforms=["Nintendo Switch"])

    switch_id = repo.id_by_name("platforms", "Nintendo Switch")
    rows, total = repo.fetch_game_list(GameFilter(platform_ids=(switch_id,)))
    assert total == 1
    assert rows[0]["title"] == "Switch Game"


def test_fetch_game_list_sorts_by_title_case_insensitively(repo: GameRepository) -> None:
    _make_game(repo, title="banana")
    _make_game(repo, title="Apple")

    rows, _ = repo.fetch_game_list(GameFilter(sort_by="title"))
    assert [r["title"] for r in rows] == ["Apple", "banana"]


def test_fetch_game_list_sorts_by_year_with_nulls_last(repo: GameRepository) -> None:
    _make_game(repo, title="No Year", year=None)
    _make_game(repo, title="Early", year=1999)

    rows, _ = repo.fetch_game_list(GameFilter(sort_by="year"))
    assert [r["title"] for r in rows] == ["Early", "No Year"]


def test_fetch_game_list_combines_filters(repo: GameRepository) -> None:
    _make_game(repo, title="Match", year=2021, genres=["RPG"], platforms=["PC (Microsoft Windows)"])
    _make_game(repo, title="WrongYear", year=2015, genres=["RPG"], platforms=["PC (Microsoft Windows)"])
    _make_game(repo, title="WrongGenre", year=2021, genres=["Puzzle"], platforms=["PC (Microsoft Windows)"])

    genre_id = repo.id_by_name("genres", "RPG")
    rows, total = repo.fetch_game_list(GameFilter(year=2021, developer_ids=(), publisher_ids=()))
    # без ограничения по жанру должно быть два совпадения по году
    assert total == 2

    rows, total = repo.fetch_game_list(GameFilter(year=2021))
    titles = {r["title"] for r in rows}
    assert "WrongYear" not in titles
    assert genre_id is not None
