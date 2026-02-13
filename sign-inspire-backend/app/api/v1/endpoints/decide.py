"""
AI 驱动广告牌推荐 - 决策接口
"""
import asyncio
from typing import Optional
from fastapi import APIRouter, HTTPException

from app.schemas.decide import DecideRequest, DecideResponse, UserRule
from app.services.context_service import get_current_context
from app.services.inventory_service import fetch_available_ads, get_ad_by_id
from app.services.decide_service import run_ai_decide
from app.services.device_push_service import push_content_to_device

router = APIRouter(tags=["decide"])


@router.post("/decide", response_model=DecideResponse)
async def decide(req: DecideRequest):
    """
    AI 决策接口：根据 location_id 与用户自然语言规则，选择最合适的广告。

    流程：
    1. 并行获取：环境上下文（天气 API）+ 广告库存
    2. 构造 Prompt 发送给 LLM
    3. LLM 返回 selected_ad_id 与 reason
    4. 若传入 device_id，则自动向设备推送内容
    """
    try:
        # 并行调用 Task 1（环境）和 Task 2（广告）
        context_task = asyncio.create_task(get_current_context(req.location_id))
        ads = fetch_available_ads(None)
        context = await context_task

        if not context:
            raise HTTPException(status_code=400, detail=f"无法解析 location_id: {req.location_id}")

        if not ads:
            raise HTTPException(status_code=500, detail="广告库存为空")

        # AI 决策
        result = await run_ai_decide(context, ads, req.user_rule)
        if not result:
            raise HTTPException(status_code=500, detail="AI 决策失败")

        # 获取完整广告素材（不传 db 避免 generator throw 问题）
        ad_content = get_ad_by_id(result.selected_ad_id, None)

        # 若请求了推送，执行推送到设备
        push_success = None
        if req.device_id and ad_content:
            push_success = push_content_to_device(req.device_id, ad_content)

        return DecideResponse(
            selected_ad_id=result.selected_ad_id,
            reason=result.reason,
            ad_content=ad_content,
            push_success=push_success,
        )
    except HTTPException:
        raise
    except Exception as e:
        err_msg = f"{type(e).__name__}: {str(e)[:200]}"
        raise HTTPException(status_code=500, detail=err_msg)
