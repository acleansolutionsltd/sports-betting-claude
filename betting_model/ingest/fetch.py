"""Controlled, cached downloads into data/raw/<source>/<date>/.

Raw files are never modified. Every download is recorded in a manifest with the
URL, fetch time, the server's Last-Modified time and a SHA-256, so every number
downstream can be traced to a file and a timestamp.
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from ..config import RAW, load_config

FOOTBALL_URL = "https://www.football-data.co.uk/mmz4281/{season}/{league}.csv"
FIXTURES_URL = "https://www.football-data.co.uk/fixtures.csv"
NFL_GAMES_URL = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
NFL_STATS_URL = ("https://github.com/nflverse/nflverse-data/releases/download/"
                 "stats_player/stats_player_week_{season}.csv")


class FetchBudgetExceeded(RuntimeError):
    pass


class Fetcher:
    def __init__(self, cfg: dict | None = None, raw_dir: Path = RAW):
        f = (cfg or load_config())["fetch"]
        self.cache_minutes = f["cache_minutes"]
        self.max_calls = f["max_calls_per_run"]
        self.min_gap = f["min_seconds_between_calls"]
        self.raw_dir = raw_dir
        self.calls = 0
        self._last_call = 0.0
        self.errors: list[str] = []

    # -- manifest helpers
    def _manifest_path(self, source: str) -> Path:
        return self.raw_dir / source / "manifest.json"

    def manifest(self, source: str) -> list[dict]:
        p = self._manifest_path(source)
        return json.loads(p.read_text()) if p.exists() else []

    def latest(self, source: str, name: str) -> dict | None:
        """Most recent manifest entry for a file, or None if never fetched."""
        hits = [m for m in self.manifest(source) if m["name"] == name]
        return hits[-1] if hits else None

    def path_of(self, entry: dict) -> Path:
        return self.raw_dir / entry["path"]

    # -- download
    def get(self, source: str, name: str, url: str, force: bool = False) -> dict | None:
        """Fetch ``url`` unless a copy younger than the cache window exists.

        Returns the manifest entry, or None on failure (the error is recorded in
        ``self.errors`` for the alerting step; nothing is fabricated).
        """
        now = datetime.now(timezone.utc)
        prev = self.latest(source, name)
        if prev and not force:
            age = (now - datetime.fromisoformat(prev["fetched_at_utc"])).total_seconds() / 60
            if age < self.cache_minutes and self.path_of(prev).exists():
                return prev
        if self.calls >= self.max_calls:
            raise FetchBudgetExceeded(f"more than {self.max_calls} downloads in one run")
        wait = self.min_gap - (time.time() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self.calls += 1
        self._last_call = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "betting-model-fetch"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read()
                lm = resp.headers.get("Last-Modified")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:  # includes SSL errors
            self.errors.append(f"fetch failed: {source}/{name}: {exc}")
            return None
        day_dir = self.raw_dir / source / now.strftime("%Y-%m-%d")
        day_dir.mkdir(parents=True, exist_ok=True)
        path = day_dir / name
        path.write_bytes(body)
        entry = {
            "name": name,
            "url": url,
            "path": str(path.relative_to(self.raw_dir)),
            "fetched_at_utc": now.isoformat(timespec="seconds"),
            "source_last_modified_utc": (
                parsedate_to_datetime(lm).astimezone(timezone.utc).isoformat(timespec="seconds")
                if lm else None),
            "sha256": hashlib.sha256(body).hexdigest(),
            "bytes": len(body),
        }
        man = self.manifest(source) + [entry]
        self._manifest_path(source).write_text(json.dumps(man, indent=1))
        return entry


def fetch_all(cfg: dict | None = None, force: bool = False, history: bool = True) -> Fetcher:
    """Download everything the models need. Completed seasons are fetched once
    and then served from the raw folder; only live files are refreshed."""
    cfg = cfg or load_config()
    f = Fetcher(cfg)
    seasons = cfg["football"]["seasons"]
    for league in cfg["football"]["leagues"]:
        for season in seasons:
            name = f"{league}_{season}.csv"
            live = season == seasons[-1]
            if not live and f.latest("football_data", name) and not force:
                continue  # finished season already on disk
            if live or history:
                f.get("football_data", name, FOOTBALL_URL.format(season=season, league=league), force)
    f.get("football_data", "fixtures.csv", FIXTURES_URL, force)
    f.get("nflverse", "games.csv", NFL_GAMES_URL, force)
    stats = cfg["nfl"]["stats_seasons"]
    for season in stats:
        name = f"stats_player_week_{season}.csv"
        live = season == stats[-1]
        if not live and f.latest("nflverse", name) and not force:
            continue
        if live or history:
            f.get("nflverse", name, NFL_STATS_URL.format(season=season), force)
    return f


if __name__ == "__main__":
    fx = fetch_all()
    print(f"downloads this run: {fx.calls}; errors: {fx.errors or 'none'}")
