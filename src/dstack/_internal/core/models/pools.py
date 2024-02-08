import datetime
from typing import Optional

from pydantic import BaseModel

from dstack._internal.core.models.backends.base import BackendType
from dstack._internal.core.models.instances import InstanceType
from dstack._internal.core.models.runs import InstanceStatus, JobStatus


class Pool(BaseModel):  # type: ignore[misc]
    name: str
    default: bool
    created_at: datetime.datetime
    total_instances: int
    available_instances: int


class Instance(BaseModel):  # type: ignore[misc]
    backend: BackendType
    instance_type: InstanceType
    instance_id: str  # TODO: rename to name
    job_name: Optional[str] = None
    job_status: Optional[JobStatus] = None
    hostname: str
    status: InstanceStatus
    price: float
