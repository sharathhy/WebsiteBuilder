from fastapi import APIRouter

from leadforge.core.deps import AdminUser, CurrentUser
from leadforge.schemas.targets import TargetsConfig
from leadforge.services.targets import load_targets, save_targets

router = APIRouter(prefix="/config/targets", tags=["config"])


@router.get("", response_model=TargetsConfig)
async def get_targets(_: CurrentUser) -> TargetsConfig:
    return load_targets()


@router.put("", response_model=TargetsConfig)
async def put_targets(body: TargetsConfig, _: AdminUser) -> TargetsConfig:
    save_targets(body)
    return load_targets()
