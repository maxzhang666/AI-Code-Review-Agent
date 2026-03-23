from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.deps import get_db, get_request_id
from app.core.logging import get_logger
from app.llm import llm_router
from app.llm.types import LLMRequest
from app.models import GitLabConfig, LLMProvider
from app.models.project import Project
from app.schemas.llm import (
    FetchModelsRequest,
    FetchModelsResponse,
    GitLabConfigCreate,
    GitLabConfigResponse,
    GitLabConfigUpdate,
    LLMConfigLegacyResponse,
    LLMProviderCreate,
    LLMProviderResponse,
    LLMProviderUpdate,
    TestLLMConnectionRequest,
    TestLLMConnectionResponse,
)

router = APIRouter()


def _provider_to_legacy(provider: LLMProvider) -> LLMConfigLegacyResponse:
    config_data = provider.config_data if isinstance(provider.config_data, dict) else {}
    max_tokens_raw = config_data.get("max_tokens", 20480)
    try:
        max_tokens = int(max_tokens_raw)
    except (TypeError, ValueError):
        max_tokens = 20480
    if max_tokens <= 0:
        max_tokens = 20480
    return LLMConfigLegacyResponse(
        id=provider.id,
        provider=provider.name,
        model=str(config_data.get("model") or ""),
        max_tokens=max_tokens,
        api_key=str(config_data.get("api_key") or ""),
        api_base=(str(config_data["api_base"]) if config_data.get("api_base") else None),
        is_active=provider.is_active,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
    )


async def _get_provider_or_404(provider_id: int, db: AsyncSession) -> LLMProvider:
    provider = await db.get(LLMProvider, provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="LLM provider not found.")
    return provider


async def _get_gitlab_config_or_404(config_id: int, db: AsyncSession) -> GitLabConfig:
    config = await db.get(GitLabConfig, config_id)
    if config is None:
        raise HTTPException(status_code=404, detail="GitLab config not found.")
    return config


def _extract_model_ids(body: Any) -> list[str]:
    models: list[str] = []
    if isinstance(body, dict):
        data = body.get("data", [])
        if isinstance(data, list):
            models = sorted(str(item["id"]) for item in data if isinstance(item, dict) and "id" in item)
    if not models and isinstance(body, list):
        models = sorted(str(item["id"]) for item in body if isinstance(item, dict) and "id" in item)
    return models


@router.get("/llm-configs/")
async def list_llm_configs(
    page: int = Query(default=1, ge=1),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    settings = get_settings()
    page_size = settings.PAGE_SIZE
    offset = (page - 1) * page_size

    count = len((await db.execute(select(LLMProvider.id))).all())
    providers = (
        await db.execute(
            select(LLMProvider)
            .order_by(LLMProvider.created_at.desc(), LLMProvider.id.desc())
            .offset(offset)
            .limit(page_size)
        )
    ).scalars().all()

    project_counts = dict(
        (await db.execute(
            select(Project.default_llm_provider_id, func.count(Project.id))
            .where(Project.default_llm_provider_id.isnot(None))
            .group_by(Project.default_llm_provider_id)
        )).all()
    )

    results = []
    for p in providers:
        resp = LLMProviderResponse.model_validate(p, from_attributes=True)
        resp.project_count = project_counts.get(p.id, 0)
        results.append(resp)

    return {"count": count, "results": results}


@router.post("/llm-configs/", response_model=LLMProviderResponse)
async def create_llm_config(
    payload: LLMProviderCreate,
    db: AsyncSession = Depends(get_db),
) -> LLMProviderResponse:
    provider = LLMProvider(
        name=payload.name,
        protocol=payload.protocol,
        is_active=payload.is_active,
        is_default=payload.is_default,
        config_data=payload.config_data,
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return LLMProviderResponse.model_validate(provider, from_attributes=True)


@router.get("/llm-configs/active/", response_model=LLMConfigLegacyResponse)
async def get_active_llm_config(db: AsyncSession = Depends(get_db)) -> LLMConfigLegacyResponse:
    provider = (
        await db.execute(
            select(LLMProvider)
            .where(LLMProvider.is_default.is_(True), LLMProvider.is_active.is_(True))
            .limit(1)
        )
    ).scalars().first()
    if provider is None:
        provider = (
            await db.execute(
                select(LLMProvider)
                .where(LLMProvider.is_active.is_(True))
                .order_by(LLMProvider.id.asc())
                .limit(1)
            )
        ).scalars().first()
    if provider is None:
        raise HTTPException(status_code=404, detail="No active LLM config found.")
    return _provider_to_legacy(provider)


@router.post("/llm-configs/{provider_id}/activate/")
async def activate_llm_config(
    provider_id: int,
    db: AsyncSession = Depends(get_db),
    request_id: str | None = Depends(get_request_id),
) -> dict[str, Any]:
    provider = await _get_provider_or_404(provider_id, db)
    if not provider.is_active:
        raise HTTPException(status_code=400, detail="Cannot set an inactive provider as default.")
    providers = (await db.execute(select(LLMProvider))).scalars().all()
    for item in providers:
        item.is_default = item.id == provider.id
    await db.commit()
    logger = get_logger(__name__, request_id)
    logger.info("llm_config_set_default", provider_id=provider_id)
    return {"code": 200, "message": "LLM config set as default", "id": provider_id}


@router.get("/llm-configs/{provider_id}/", response_model=LLMProviderResponse)
async def get_llm_config(provider_id: int, db: AsyncSession = Depends(get_db)) -> LLMProviderResponse:
    provider = await _get_provider_or_404(provider_id, db)
    return LLMProviderResponse.model_validate(provider, from_attributes=True)


@router.put("/llm-configs/{provider_id}/", response_model=LLMProviderResponse)
async def put_llm_config(
    provider_id: int,
    payload: LLMProviderCreate,
    db: AsyncSession = Depends(get_db),
) -> LLMProviderResponse:
    provider = await _get_provider_or_404(provider_id, db)
    provider.name = payload.name
    provider.protocol = payload.protocol
    provider.is_active = payload.is_active
    provider.is_default = payload.is_default
    provider.config_data = payload.config_data
    await db.commit()
    await db.refresh(provider)
    return LLMProviderResponse.model_validate(provider, from_attributes=True)


@router.patch("/llm-configs/{provider_id}/", response_model=LLMProviderResponse)
async def patch_llm_config(
    provider_id: int,
    payload: LLMProviderUpdate,
    db: AsyncSession = Depends(get_db),
) -> LLMProviderResponse:
    provider = await _get_provider_or_404(provider_id, db)
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(provider, field, value)
    await db.commit()
    await db.refresh(provider)
    return LLMProviderResponse.model_validate(provider, from_attributes=True)


@router.delete("/llm-configs/{provider_id}/")
async def delete_llm_config(provider_id: int, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    provider = await _get_provider_or_404(provider_id, db)
    ref_count = (
        await db.execute(
            select(func.count(Project.id))
            .where(Project.default_llm_provider_id == provider_id)
        )
    ).scalar() or 0
    if ref_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"该供应商正被 {ref_count} 个项目引用，无法删除",
        )
    await db.delete(provider)
    await db.commit()
    return {"code": 200, "message": "LLM config deleted"}


@router.post("/llm-configs/fetch-models/", response_model=FetchModelsResponse)
async def fetch_models(payload: FetchModelsRequest) -> FetchModelsResponse:
    logger = get_logger(__name__)
    api_base = payload.api_base.rstrip("/")
    url = f"{api_base}/models"

    headers: dict[str, str] = {}
    if payload.api_key:
        headers["Authorization"] = f"Bearer {payload.api_key}"

    logger.debug("fetch_models_request", url=url, has_key=bool(payload.api_key))

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            body = resp.json()
    except httpx.TimeoutException:
        logger.warning("fetch_models_timeout", url=url)
        raise HTTPException(status_code=504, detail="请求超时，请检查 API 地址是否可达")
    except httpx.ConnectError as e:
        logger.warning("fetch_models_connect_error", url=url, error=str(e))
        raise HTTPException(status_code=502, detail="无法连接到 API 服务，请检查 API Base URL")
    except httpx.HTTPStatusError as e:
        detail_body = ""
        try:
            detail_body = e.response.text[:200]
        except Exception:
            pass
        logger.warning(
            "fetch_models_http_error", url=url,
            status=e.response.status_code, body=detail_body,
        )
        raise HTTPException(
            status_code=502,
            detail=f"API 返回错误 {e.response.status_code}: {detail_body}" if detail_body else f"API 返回错误: {e.response.status_code}",
        )
    except Exception as e:
        logger.error("fetch_models_unexpected_error", url=url, error=str(e))
        raise HTTPException(status_code=502, detail=f"请求失败: {e}")

    models = _extract_model_ids(body)

    logger.info("fetch_models_success", url=url, model_count=len(models))
    return FetchModelsResponse(models=models)


@router.post("/llm-configs/test-connection/", response_model=TestLLMConnectionResponse)
async def test_llm_connection(
    payload: TestLLMConnectionRequest,
    request_id: str | None = Depends(get_request_id),
) -> TestLLMConnectionResponse:
    logger = get_logger(__name__, request_id)
    protocol = str(payload.protocol or "").strip()
    config_data = payload.config_data if isinstance(payload.config_data, dict) else {}

    provider = LLMProvider(
        name="__connection_test__",
        protocol=protocol,
        is_active=True,
        config_data=config_data,
    )
    ok, message = await llm_router.validate_provider(provider)
    if not ok:
        logger.warning("llm_connection_test_failed", protocol=protocol, error_message=message)
        return TestLLMConnectionResponse(
            success=False,
            message=message or "连接测试失败",
            details={"protocol": protocol},
        )

    max_tokens = 256
    try:
        configured_max_tokens = int(config_data.get("max_tokens", max_tokens))
        if configured_max_tokens > 0:
            max_tokens = min(configured_max_tokens, 1024)
    except (TypeError, ValueError):
        pass

    request = LLMRequest(
        prompt="请只回复: CONNECTION_OK",
        system_message="你是连通性测试助手。只输出纯文本 CONNECTION_OK，不要额外内容。",
        temperature=0,
        max_tokens=max_tokens,
    )

    logger.info("llm_connection_test_started", protocol=protocol)
    try:
        response = await llm_router.review(provider, request)
    except TimeoutError:
        logger.warning("llm_connection_test_timeout", protocol=protocol)
        return TestLLMConnectionResponse(
            success=False,
            message="连接超时，请检查网络连通性或提高超时时间",
            details={"protocol": protocol},
        )
    except Exception as e:
        logger.warning("llm_connection_test_request_failed", protocol=protocol, error=str(e))
        return TestLLMConnectionResponse(
            success=False,
            message=f"模型调用失败: {e}",
            details={"protocol": protocol},
        )

    content = str(response.content or "").strip()
    logger.info(
        "llm_connection_test_succeeded",
        protocol=protocol,
        model=response.model,
        content_length=len(content),
        duration_ms=response.duration_ms,
    )
    return TestLLMConnectionResponse(
        success=True,
        message="连接测试通过，模型有响应" if content else "连接测试通过，但模型未返回文本内容",
        details={
            "protocol": protocol,
            "model": response.model,
            "duration_ms": response.duration_ms,
            "content": content,
            "content_length": len(content),
            "usage": response.usage or {},
            "raw_response": response.raw_response or {},
        },
    )


@router.get("/gitlab-configs/")
async def list_gitlab_configs(
    page: int = Query(default=1, ge=1),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    settings = get_settings()
    page_size = settings.PAGE_SIZE
    offset = (page - 1) * page_size

    count = len((await db.execute(select(GitLabConfig.id))).all())
    configs = (
        await db.execute(
            select(GitLabConfig)
            .order_by(GitLabConfig.updated_at.desc())
            .offset(offset)
            .limit(page_size)
        )
    ).scalars().all()
    return {"count": count, "results": [GitLabConfigResponse.model_validate(item, from_attributes=True) for item in configs]}


@router.post("/gitlab-configs/", response_model=GitLabConfigResponse)
async def create_gitlab_config(
    payload: GitLabConfigCreate,
    db: AsyncSession = Depends(get_db),
) -> GitLabConfigResponse:
    config = GitLabConfig(
        server_url=payload.server_url,
        private_token=payload.private_token,
        is_active=True,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return GitLabConfigResponse.model_validate(config, from_attributes=True)


@router.get("/gitlab-configs/active/", response_model=GitLabConfigResponse)
async def get_active_gitlab_config(db: AsyncSession = Depends(get_db)) -> GitLabConfigResponse:
    config = (
        await db.execute(
            select(GitLabConfig)
            .where(GitLabConfig.is_active.is_(True))
            .order_by(GitLabConfig.updated_at.desc())
            .limit(1)
        )
    ).scalars().first()
    if config is None:
        raise HTTPException(status_code=404, detail="No active GitLab config found.")
    return GitLabConfigResponse.model_validate(config, from_attributes=True)


@router.post("/gitlab-configs/{config_id}/activate/")
async def activate_gitlab_config(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    request_id: str | None = Depends(get_request_id),
) -> dict[str, Any]:
    config = await _get_gitlab_config_or_404(config_id, db)
    configs = (await db.execute(select(GitLabConfig))).scalars().all()
    for item in configs:
        item.is_active = item.id == config.id
    await db.commit()
    logger = get_logger(__name__, request_id)
    logger.info("gitlab_config_activated", config_id=config_id)
    return {"code": 200, "message": "GitLab config activated", "id": config_id}


@router.get("/gitlab-configs/{config_id}/", response_model=GitLabConfigResponse)
async def get_gitlab_config(config_id: int, db: AsyncSession = Depends(get_db)) -> GitLabConfigResponse:
    config = await _get_gitlab_config_or_404(config_id, db)
    return GitLabConfigResponse.model_validate(config, from_attributes=True)


@router.put("/gitlab-configs/{config_id}/", response_model=GitLabConfigResponse)
async def put_gitlab_config(
    config_id: int,
    payload: GitLabConfigCreate,
    db: AsyncSession = Depends(get_db),
) -> GitLabConfigResponse:
    config = await _get_gitlab_config_or_404(config_id, db)
    config.server_url = payload.server_url
    config.private_token = payload.private_token
    await db.commit()
    await db.refresh(config)
    return GitLabConfigResponse.model_validate(config, from_attributes=True)


@router.patch("/gitlab-configs/{config_id}/", response_model=GitLabConfigResponse)
async def patch_gitlab_config(
    config_id: int,
    payload: GitLabConfigUpdate,
    db: AsyncSession = Depends(get_db),
) -> GitLabConfigResponse:
    config = await _get_gitlab_config_or_404(config_id, db)
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)
    await db.commit()
    await db.refresh(config)
    return GitLabConfigResponse.model_validate(config, from_attributes=True)


@router.delete("/gitlab-configs/{config_id}/")
async def delete_gitlab_config(config_id: int, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    config = await _get_gitlab_config_or_404(config_id, db)
    await db.delete(config)
    await db.commit()
    return {"code": 200, "message": "GitLab config deleted"}
