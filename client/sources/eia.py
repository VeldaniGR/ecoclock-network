"""EIA (U.S. Energy Information Administration) API client. Resolves the API key from (in order):
    1. ECOCLOCK_EIA_KEY environment variable
    2. ~/.config/ecoclock/eia.key file (single line, no newline)
  Free tier: 5_000 calls/month. Each call here consumes one credit on the server."""
from __future__ import annotations
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

EIA_BASE_URL = "https://api.eia.gov/v2"
DEFAULT_TIMEOUT = 30.0
KEY_FILE = Path.home() / ".config" / "ecoclock" / "eia.key"


class EIAError(RuntimeError):
	"""Raised when an EIA call fails for a known reason."""


def _load_api_key() -> str:
	"""Resolve the EIA API key from env or config file."""
	env_key = os.environ.get("ECOCLOCK_EIA_KEY", "").strip()
	if env_key:
		return env_key

	if not KEY_FILE.exists():
		raise EIAError(
			f"EIA API key not found. Set ECOCLOCK_EIA_KEY or create {KEY_FILE}"
		)

	raw = KEY_FILE.read_text(encoding="utf-8").strip()
	if not raw:
		raise EIAError(f"EIA API key file {KEY_FILE} is empty")
	return raw


@dataclass
class EIAClient:
	"""Thin wrapper around the EIA v2 API."""

	api_key: str
	base_url: str = EIA_BASE_URL
	timeout: float = DEFAULT_TIMEOUT

	@classmethod
	def from_env(cls) -> "EIAClient":
		return cls(api_key=_load_api_key())

	def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
		url = f"{self.base_url}{path}"
		query = {"api_key": self.api_key}
		if params:
			query.update(params)

		try:
			response = httpx.get(url, params=query, timeout=self.timeout)
		except httpx.HTTPError as exc:
			raise EIAError(f"EIA request failed: {exc}") from exc

		if response.status_code != 200:
			raise EIAError(
				f"EIA returned {response.status_code}: {response.text[:200]}"
			)

		return response.json()

	def fetch_co2_by_sector(
		self, sector: str, frequency: str = "annual"
	) -> list[dict[str, Any]]:
		"""Fetch CO2 emissions for a given sector.
		sector examples: 'electric-power', 'transportation', 'industrial',
		'residential', 'commercial', 'total'"""

		path = f"/co2/emissions/by-sector/{sector}/"
		params = {"frequency": frequency, "data[]": "value"}
		payload = self._get(path, params)
		return payload.get("response", {}).get("data", [])

	def health_check(self) -> bool:
		"""Return True if the API key is valid and the service responds."""
		try:
			self._get("/", params={"length": 1})
			return True
		except EIAError:
			return False
