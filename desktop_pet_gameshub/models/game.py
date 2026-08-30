"""Модели каталога игр."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Game:
    id: int | None = None
    title: str = ""
    year: int | None = None
    cover_url: str | None = None
    service_id: int | None = None
    account_id: int | None = None
    status_id: int | None = None
    mgl_id: str | None = None
    developers: list[str] = field(default_factory=list)
    publishers: list[str] = field(default_factory=list)
    genres: list[str] = field(default_factory=list)
    platforms: list[str] = field(default_factory=list)


@dataclass
class GameFilter:
    year: int | None = None
    status_id: int | None = None
    service_id: int | None = None
    account_id: int | None = None
    platform_ids: tuple[int, ...] = ()
    developer_ids: tuple[int, ...] = ()
    publisher_ids: tuple[int, ...] = ()
    sort_by: str = "title"  # "title" | "year"


@dataclass
class MGLGameData:
    title: str | None = None
    year: int | None = None
    cover_url: str | None = None
    developers: list[str] = field(default_factory=list)
    publishers: list[str] = field(default_factory=list)
    genres: list[str] = field(default_factory=list)
    platforms: list[str] = field(default_factory=list)
