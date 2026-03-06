"""Secure local token storage for Readwise API tokens."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import orjson
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

DEFAULT_STORE_DIR = Path.home() / ".readwise-reader"
DEFAULT_STORE_PATH = DEFAULT_STORE_DIR / "tokens.enc"
DEFAULT_KEY_PATH = DEFAULT_STORE_DIR / ".key"


class TokenStore:
    """Encrypted local storage for sensitive tokens.

    Uses Fernet symmetric encryption. The encryption key is stored
    in a separate file with restricted permissions.
    """

    def __init__(
        self,
        store_path: Path | None = None,
        key_path: Path | None = None,
    ) -> None:
        self.store_path = store_path or DEFAULT_STORE_PATH
        self.key_path = key_path or DEFAULT_KEY_PATH
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._fernet = Fernet(self._load_or_create_key())

    def _load_or_create_key(self) -> bytes:
        """Load or generate the encryption key."""
        if self.key_path.exists():
            return self.key_path.read_bytes().strip()
        key = Fernet.generate_key()
        self.key_path.write_bytes(key)
        os.chmod(self.key_path, 0o600)
        logger.info("Generated new encryption key at %s", self.key_path)
        return key

    def _load_store(self) -> dict[str, str]:
        """Load and decrypt the token store."""
        if not self.store_path.exists():
            return {}
        encrypted = self.store_path.read_bytes()
        decrypted = self._fernet.decrypt(encrypted)
        return orjson.loads(decrypted)

    def _save_store(self, data: dict[str, str]) -> None:
        """Encrypt and save the token store."""
        serialized = orjson.dumps(data)
        encrypted = self._fernet.encrypt(serialized)
        self.store_path.write_bytes(encrypted)
        os.chmod(self.store_path, 0o600)

    def get_readwise_token(self) -> str | None:
        """Get the stored Readwise API token."""
        store = self._load_store()
        return store.get("readwise_token")

    def set_readwise_token(self, token: str) -> None:
        """Store the Readwise API token."""
        store = self._load_store()
        store["readwise_token"] = token
        self._save_store(store)
        logger.info("Readwise API token stored")

    def has_readwise_token(self) -> bool:
        """Check if a Readwise token is stored."""
        return self.get_readwise_token() is not None

    def delete_readwise_token(self) -> None:
        """Remove the stored Readwise token."""
        store = self._load_store()
        store.pop("readwise_token", None)
        self._save_store(store)
