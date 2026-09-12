from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from src.case_radar.providers.base import ProviderAuthExpired, ProviderUnavailable
from src.case_radar.providers.x import XLoggedInProvider


class TwikitSessionClient:
    """Thin lazy wrapper that exposes Twikit replies through the generic X adapter contract."""

    def __init__(self, session_file: str, *, client: Any | None = None) -> None:
        self.session_file = session_file
        self._client = client

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        try:
            twikit = importlib.import_module("twikit")
            client = twikit.Client(language="en-US")
            client.load_cookies(self.session_file)
            self._client = client
            return client
        except ImportError as exc:
            raise ProviderUnavailable("Adapter X logged-in não instalado") from exc
        except Exception as exc:
            raise ProviderAuthExpired("Sessão X inválida ou expirada") from exc

    def search_tweet(self, query: str, product: str):
        return self._ensure_client().search_tweet(query, product)

    def get_tweet_by_id(self, tweet_id: str):
        return self._ensure_client().get_tweet_by_id(tweet_id)

    async def get_tweet_replies(self, tweet_id: str):
        tweet = await self._ensure_client().get_tweet_by_id(tweet_id)
        replies = getattr(tweet, "replies", None)
        return list(replies or [])


class TwikitXLoggedInProvider(XLoggedInProvider):
    """Default logged-in X provider backed by a user-supplied Twikit cookie file."""

    def __init__(self, session_file: str | None = None, *, client: Any | None = None) -> None:
        super().__init__(session_file=session_file, client=None)
        self._injected_client = client

    def is_available(self) -> bool:
        if self._injected_client is not None:
            return True
        if not self.session_file or not Path(self.session_file).is_file():
            return False
        try:
            importlib.import_module("twikit")
            return True
        except ImportError:
            return False

    def _load_client(self):
        if self.client is not None:
            self._refresh_social_capabilities(self.client)
            return self.client
        if self._injected_client is not None:
            self.client = TwikitSessionClient(self.session_file, client=self._injected_client)
            self._refresh_social_capabilities(self.client)
            return self.client
        if not self.session_file or not Path(self.session_file).is_file():
            raise ProviderUnavailable("Sessão X não configurada", provider=self.name)
        self.client = TwikitSessionClient(self.session_file)
        self._refresh_social_capabilities(self.client)
        return self.client
