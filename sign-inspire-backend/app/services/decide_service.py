"""
AI 决策引擎：根据环境上下文、用户规则与广告库，由 LLM 选择最合适的广告
"""
from typing import Optional, List

from app.schemas.decide import AdAsset, EnvironmentContext, UserRule


class DecideResult:
    """决策结果"""
    def __init__(self, selected_ad_id: str, reason: str):
        self.selected_ad_id = selected_ad_id
        self.reason = reason


async def run_ai_decide(
    context: EnvironmentContext,
    ads: List[AdAsset],
    user_rule: UserRule,
) -> Optional[DecideResult]:
    """
    将「当前天气」「可用广告列表」「用户自然语言规则」组合成 Prompt 发送给 LLM。

    LLM 任务：
    1. 分析用户规则
    2. 结合当前环境匹配最合适的 ad_id
    3. 输出 JSON：{"selected_ad_id": "xxx", "reason": "因为..."}
    """
    if not ads:
        return None

    # 构建广告列表描述（供 LLM 理解）
    ads_desc = []
    for a in ads:
        tags_str = ", ".join(a.tags) if a.tags else ""
        desc = a.description or ""
        ads_desc.append(f"- id={a.id}, tags=[{tags_str}], description={desc}")

    prompt = f"""你是一个数字标牌广告推荐助手。根据当前环境与用户规则，从以下广告库中选择最合适的一个。

## 当前环境
- 地点: {context.location}
- 天气: {context.weather_condition}
- 温度: {context.temperature}°C
- 当地时间: {context.local_time.strftime("%Y-%m-%d %H:%M")}

## 用户规则（自然语言）
{user_rule.natural_language_instruction}

## 可用广告列表
{chr(10).join(ads_desc)}

## 要求
1. 严格分析用户规则，结合当前天气、温度、时间。
2. 从上述列表中选出最匹配的广告 id。
3. 若无法完全匹配，选最接近的。
4. 必须输出 JSON 格式，不要其他内容：
{{"selected_ad_id": "xxx", "reason": "选择理由（中文）"}}

示例：{{"selected_ad_id": "hot_drink_ad", "reason": "因为现在阿德莱德下雨且气温低，符合用户规定的'热咖啡'策略"}}
"""

    try:
        from app.services.llm_service import _get_llm
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import JsonOutputParser
        from pydantic import BaseModel, Field

        class LLMOutput(BaseModel):
            selected_ad_id: str = Field(description="选中的广告 ID")
            reason: str = Field(description="选择理由")

        llm = _get_llm()
        parser = JsonOutputParser(pydantic_object=LLMOutput)

        prompt_template = ChatPromptTemplate.from_messages([
            ("system", "你输出严格的 JSON，不要 markdown 代码块。"),
            ("user", "{prompt}"),
        ])

        chain = prompt_template | llm | parser
        result = await chain.ainvoke({"prompt": prompt})

        if isinstance(result, dict):
            ad_id = result.get("selected_ad_id", "")
            reason = result.get("reason", "")
        else:
            ad_id = getattr(result, "selected_ad_id", "")
            reason = getattr(result, "reason", "")

        if not ad_id:
            # 回退：选第一个
            ad_id = ads[0].id
            reason = "无法解析 LLM 输出，使用默认广告"

        # 验证 ad_id 是否在列表中
        valid_ids = {a.id for a in ads}
        if ad_id not in valid_ids:
            # 找最相似的（简单按前缀）
            for a in ads:
                if ad_id in a.id or a.id in ad_id:
                    ad_id = a.id
                    break
            else:
                ad_id = ads[0].id
                reason = f"LLM 返回的 ID 不在列表中，使用 {ad_id}"

        return DecideResult(selected_ad_id=ad_id, reason=reason or "AI 推荐")

    except Exception as e:
        try:
            print(f"[Decide] LLM fail: {e}")
        except UnicodeEncodeError:
            pass
        # 回退：选第一个
        return DecideResult(selected_ad_id=ads[0].id, reason=f"LLM  fallback: {str(e)}")
