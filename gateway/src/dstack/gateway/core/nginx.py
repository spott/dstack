import importlib.resources
import logging
import subprocess
import tempfile
from asyncio import Lock
from pathlib import Path
from typing import Annotated, Dict, Literal, Union

import jinja2
from pydantic import BaseModel, Field

from dstack.gateway.common import run_async
from dstack.gateway.errors import GatewayError

CONFIGS_DIR = Path("/etc/nginx/sites-enabled")
GATEWAY_PORT = 8000
logger = logging.getLogger(__name__)


class SiteConfig(BaseModel):
    type: str
    domain: str

    def render(self) -> str:
        template = importlib.resources.read_text(
            "dstack.gateway.resources.nginx", f"{self.type}.jinja2"
        )
        return jinja2.Template(template).render(
            **self.model_dump(),
            gateway_port=GATEWAY_PORT,
        )


class ServiceConfig(SiteConfig):
    type: Literal["service"] = "service"
    project: str
    service_id: str
    auth: bool
    servers: Dict[str, str] = {}


class EntrypointConfig(SiteConfig):
    type: Literal["entrypoint"] = "entrypoint"
    proxy_path: str


class Nginx(BaseModel):
    """
    Nginx keeps track of registered domains, updates nginx config and issues SSL certificates.
    Its internal state could be serialized to a file and restored from it using pydantic.
    """

    configs: Dict[
        str, Annotated[Union[ServiceConfig, EntrypointConfig], Field(discriminator="type")]
    ] = {}
    _lock: Lock = Lock()

    async def register_service(self, project: str, service_id: str, domain: str, auth: bool):
        config_name = self.get_config_name(domain)
        conf = ServiceConfig(
            project=project,
            service_id=service_id,
            domain=domain,
            auth=auth,
        )

        async with self._lock:
            if config_name in self.configs:
                raise GatewayError(f"Domain {domain} is already registered")

            logger.debug("Registering service domain %s", domain)

            await run_async(self.run_certbot, domain)
            await run_async(self.write_conf, conf.render(), config_name)
            self.configs[config_name] = conf

        logger.info("Service domain %s is registered now", domain)

    async def register_entrypoint(self, domain: str, prefix: str):
        config_name = self.get_config_name(domain)
        conf = EntrypointConfig(
            domain=domain,
            proxy_path=prefix,
        )

        async with self._lock:
            if config_name in self.configs:
                raise GatewayError(f"Domain {domain} is already registered")

            logger.debug("Registering entrypoint domain %s", domain)

            await run_async(self.run_certbot, domain)
            await run_async(self.write_conf, conf.render(), config_name)
            self.configs[config_name] = conf

        logger.info("Entrypoint domain %s is registered now", domain)

    async def unregister_domain(self, domain: str):
        config_name = self.get_config_name(domain)

        async with self._lock:
            if config_name not in self.configs:
                raise GatewayError("Domain is not registered")

            logger.debug("Unregistering domain %s", domain)

            await run_async(sudo_rm, CONFIGS_DIR / config_name)
            await run_async(self.reload)
            self.configs.pop(config_name)

        logger.info("Domain %s is unregistered now", domain)

    async def add_upstream(self, domain: str, server: str, replica_id: str):
        config_name = self.get_config_name(domain)

        async with self._lock:
            if config_name not in self.configs:
                raise GatewayError(f"Domain {domain} is not registered")

            logger.debug("Adding upstream %s to domain %s", server, domain)

            conf = self.configs[config_name].model_copy(deep=True)
            conf.servers[replica_id] = server
            await run_async(self.write_conf, conf.render(), config_name)
            self.configs[config_name] = conf

        logger.debug("Upstream %s is added to domain %s", server, domain)

    async def remove_upstream(self, domain: str, replica_id: str):
        config_name = self.get_config_name(domain)

        async with self._lock:
            if config_name not in self.configs:
                raise GatewayError(f"Domain {domain} is not registered")
            if replica_id not in self.configs[config_name].servers:
                raise GatewayError(f"Upstream {replica_id} is not registered")

            logger.debug("Removing upstream %s from domain %s", replica_id, domain)

            conf = self.configs[config_name].model_copy(deep=True)
            conf.servers.pop(replica_id)
            await run_async(self.write_conf, conf.render(), config_name)
            self.configs[config_name] = conf

        logger.debug("Upstream %s is removed from domain %s", replica_id, domain)

    @staticmethod
    def reload():
        cmd = ["sudo", "systemctl", "reload", "nginx.service"]
        r = subprocess.run(cmd)
        if r.returncode != 0:
            raise GatewayError("Failed to reload nginx")

    @classmethod
    def write_conf(cls, conf: str, conf_name: str):
        """Update config and reload nginx. Rollback changes on error."""
        conf_path = CONFIGS_DIR / conf_name
        old_conf = conf_path.read_text() if conf_path.exists() else None

        sudo_write(conf_path, conf)
        try:
            cls.reload()
        except GatewayError:
            # rollback changes
            if old_conf is not None:
                sudo_write(conf_path, old_conf)
            else:
                sudo_rm(conf_path)
            raise

    @staticmethod
    def run_certbot(domain: str):
        logger.info("Running certbot for %s", domain)
        cmd = ["sudo", "certbot", "certonly"]
        cmd += ["--non-interactive", "--agree-tos", "--register-unsafely-without-email"]
        cmd += ["--nginx", "--domain", domain]
        r = subprocess.run(cmd, capture_output=True)
        if r.returncode != 0:
            raise GatewayError(f"Certbot failed:\n{r.stderr.decode()}")

    @staticmethod
    def get_config_name(domain: str) -> str:
        return f"443-{domain}.conf"


def sudo_write(path: Path, content: str):
    with tempfile.NamedTemporaryFile("w") as temp:
        temp.write(content)
        temp.flush()
        temp.seek(0)
        r = subprocess.run(["sudo", "cp", "-p", temp.name, path])
        if r.returncode != 0:
            raise GatewayError("Failed to copy file as sudo")


def sudo_rm(path: Path):
    r = subprocess.run(["sudo", "rm", path])
    if r.returncode != 0:
        raise GatewayError("Failed to remove file as sudo")
