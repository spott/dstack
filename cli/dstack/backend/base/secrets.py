from abc import ABC, abstractmethod
from typing import List, Optional

from dstack.backend.base.storage import Storage
from dstack.core.secret import Secret


class SecretsManager(ABC):
    def __init__(self, repo_id: str):
        self.repo_id = repo_id

    @abstractmethod
    def get_secret(self, secret_name: str) -> Optional[Secret]:
        pass

    @abstractmethod
    def add_secret(self, secret: Secret):
        pass

    @abstractmethod
    def update_secret(self, secret: Secret):
        pass

    @abstractmethod
    def delete_secret(self, secret_name: str):
        pass

    @abstractmethod
    def get_credentials(self) -> Optional[str]:
        pass

    @abstractmethod
    def add_credentials(self, data: str):
        pass

    @abstractmethod
    def update_credentials(self, data: str):
        pass


def list_secret_names(storage: Storage, repo_id: str) -> List[str]:
    secret_head_prefix = _get_secret_heads_keys_prefix(repo_id)
    secret_heads_keys = storage.list_objects(secret_head_prefix)
    secret_names = []
    for secret_head_key in secret_heads_keys:
        secret_name = secret_head_key[len(secret_head_prefix) :]
        secret_names.append(secret_name)
    return secret_names


def get_secret(
    secrets_manager: SecretsManager,
    secret_name: str,
) -> Optional[Secret]:
    return secrets_manager.get_secret(secret_name)


def add_secret(
    storage: Storage,
    secrets_manager: SecretsManager,
    secret: Secret,
):
    secrets_manager.add_secret(secret)
    storage.put_object(
        key=_get_secret_head_key(secrets_manager.repo_id, secret.secret_name),
        content="",
    )


def update_secret(
    storage: Storage,
    secrets_manager: SecretsManager,
    secret: Secret,
):
    secrets_manager.update_secret(secret)
    storage.put_object(
        key=_get_secret_head_key(secrets_manager.repo_id, secret.secret_name),
        content="",
    )


def delete_secret(
    storage: Storage,
    secrets_manager: SecretsManager,
    secret_name: str,
):
    secrets_manager.delete_secret(secret_name)
    storage.delete_object(_get_secret_head_key(secrets_manager.repo_id, secret_name))


def _get_secret_heads_dir(repo_id: str) -> str:
    return f"secrets/{repo_id}/"


def _get_secret_heads_keys_prefix(repo_id: str) -> str:
    prefix = _get_secret_heads_dir(repo_id)
    key = f"{prefix}l;"
    return key


def _get_secret_head_key(repo_id: str, secret_name: str) -> str:
    prefix = _get_secret_heads_dir(repo_id)
    key = f"{prefix}l;{secret_name}"
    return key
