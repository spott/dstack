from typing import List, Optional

from pydantic import parse_obj_as

import dstack._internal.server.schemas.pools as schemas_pools
from dstack._internal.core.models.pools import Instance, Pool
from dstack._internal.core.models.profiles import Profile
from dstack._internal.core.models.resources import ResourcesSpec
from dstack._internal.server.schemas.runs import AddRemoteInstanceRequest
from dstack.api.server._group import APIClientGroup


class PoolAPIClient(APIClientGroup):  # type: ignore[misc]
    def list(self, project_name: str) -> List[Pool]:
        resp = self._request(f"/api/project/{project_name}/pool/list")
        result: List[Pool] = parse_obj_as(List[Pool], resp.json())  # type: ignore[operator]
        return result

    def delete(self, project_name: str, pool_name: str, force: bool) -> None:
        body = schemas_pools.DeletePoolRequest(name=pool_name, force=force)
        self._request(f"/api/project/{project_name}/pool/delete", body=body.json())

    def create(self, project_name: str, pool_name: str) -> None:
        body = schemas_pools.CreatePoolRequest(name=pool_name)
        self._request(f"/api/project/{project_name}/pool/remove", body=body.json())

    def show(self, project_name: str, pool_name: str) -> List[Instance]:
        body = schemas_pools.ShowPoolRequest(name=pool_name)
        resp = self._request(f"/api/project/{project_name}/pool/show", body=body.json())
        result: List[Instance] = parse_obj_as(List[Instance], resp.json())  # type: ignore[operator]
        return result

    def remove(self, project_name: str, pool_name: str, instance_name: str) -> None:
        body = schemas_pools.RemoveInstanceRequest(
            pool_name=pool_name, instance_name=instance_name
        )
        self._request(f"/api/project/{project_name}/pool/remove", body=body.json())

    def set_default(self, project_name: str, pool_name: str) -> bool:
        body = schemas_pools.SetDefaultPoolRequest(pool_name=pool_name)
        result = self._request(f"/api/project/{project_name}/pool/set-default", body=body.json())
        return bool(result.json())

    def add_remote(
        self,
        project_name: str,
        resources: ResourcesSpec,
        profile: Profile,
        instance_name: Optional[str],
        host: str,
        port: str,
    ) -> bool:
        body = AddRemoteInstanceRequest(
            profile=profile,
            instance_name=instance_name,
            host=host,
            port=port,
            resources=resources,
        )
        result = self._request(f"/api/project/{project_name}/pool/add_remote", body=body.json())
        return bool(result.json())
