from dataclasses import dataclass
from typing import Mapping, Tuple
import os

DEFAULT_PAGES = ("previas", "vigentes", "posprevias", "credits")

def _parse_pages(raw: str, default: Tuple[str, ...]) -> Tuple[str, ...]:
    if raw is None or not raw.strip():
        return default
    tokens = [token.strip().lower() for token in raw.split(",")]
    return tuple(token for token in tokens if token)
@dataclass(frozen=True)
class ScraperConfig:
    username: str
    password: str
    browser: str
    debug: bool
    pages: Tuple[str, ...]

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "ScraperConfig":
        env = dict(environ) if environ is not None else os.environ
        username = env.get("DOCUMENTO", "").strip()
        password = env.get("CONTRASENA", "").strip()
        browser = env.get("BROWSER", "firefox").strip().lower() or "firefox"
        debug = env.get("DEBUG", "False").strip().lower() in {"true", "1", "yes", "on"}
        raw_pages = env.get("PAGES")
        if raw_pages is not None and raw_pages.strip():
            pages = _parse_pages(raw_pages, default=DEFAULT_PAGES)
        else:
            pages = DEFAULT_PAGES
        return cls(
            username=username,
            password=password,
            browser=browser,
            debug=debug,
            pages=pages,
        )

    def require_credentials(self) -> None:
        if not self.username or not self.password:
            raise ValueError("Missing DOCUMENTO or CONTRASENA environment variables")
