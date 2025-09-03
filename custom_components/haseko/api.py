from __future__ import annotations

from typing import Any, Dict

import aiohttp

BASE_URL = "https://api.aseko.cloud"


class AsekoApi:
    def __init__(self, session: aiohttp.ClientSession, api_key: str, client_name: str, client_version: str) -> None:
        self._session = session
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "X-Client-Name": client_name,
            "X-Client-Version": client_version,
        }

    async def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        url = f"{BASE_URL}{path}"
        async with self._session.request(method, url, headers=self._headers, **kwargs) as resp:
            if resp.status >= 400:
                try:
                    data = await resp.json()
                except Exception:
                    txt = await resp.text()
                    raise RuntimeError(f"HTTP {resp.status}: {txt}")
                code = data.get("error", {}).get("code") or data.get("code")
                msg = data.get("error", {}).get("message") or data.get("message") or str(data)
                raise RuntimeError(f"HTTP {resp.status}: {code or ''} {msg or ''}".strip())
            return await resp.json()

    async def auth_check(self) -> Dict[str, Any]:
        return await self._request("GET", "/api/v1/auth/check")

    async def list_units(self, page: int = 1, limit: int = 100) -> Dict[str, Any]:
        params = {"page": page, "limit": limit}
        return await self._request("GET", "/api/v1/paired-units", params=params)

    async def get_unit(self, serial: str) -> Dict[str, Any]:
        return await self._request("GET", f"/api/v1/paired-units/{serial}")
