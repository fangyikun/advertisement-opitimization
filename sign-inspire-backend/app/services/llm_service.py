import os
from dotenv import load_dotenv
load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from app.schemas.rule import RuleCreate
from app.services.vocabulary_service import (
    get_weather_mappings,
    get_action_mappings,
    ensure_action_mapping,
    ensure_weather_mapping,
)

# 1. 初始化 Gemini
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
)

parser = PydanticOutputParser(pydantic_object=RuleCreate)


def _parse_with_vocab(text: str, db=None):
    """
    使用动态词汇表解析规则（优先路径）
    若词汇表中存在匹配则直接返回；遇到新词则自动创建并写入词汇表
    """
    from app.schemas.rule import RuleCreate, Condition, Action

    weather_map = get_weather_mappings(db)
    action_map = get_action_mappings(db)

    # 按关键词长度降序匹配
    condition_value = None
    for kw in sorted(weather_map.keys(), key=len, reverse=True):
        if kw in text:
            condition_value = kw  # 保持中文用于规则展示
            break

    target_id = None
    for kw in sorted(action_map.keys(), key=len, reverse=True):
        if kw in text:
            target_id = action_map[kw]
            break

    # 新词：自动创建
    if target_id is None:
        extracted = _extract_action_with_llm(text)
        if extracted:
            target_id = ensure_action_mapping(extracted, db)
        else:
            # LLM 失败时（如配额用尽）：从文本中移除天气关键词，剩余部分作为动作
            remainder = text.strip()
            if condition_value:
                remainder = remainder.replace(condition_value, "", 1).strip()
            remainder = remainder.replace("  ", " ").strip()
            if remainder and len(remainder) >= 2:
                target_id = ensure_action_mapping(remainder, db)
                print(f"   [Fallback] LLM 不可用，从文本提取动作: '{remainder}' -> {target_id}")
            else:
                target_id = "coffee_ad"

    if condition_value is None:
        extracted_weather = _extract_weather_with_llm(text)
        if extracted_weather:
            condition_value = extracted_weather
            ensure_weather_mapping(extracted_weather, db)
        else:
            condition_value = "多云"

    rule_name = text.strip()[:50]
    print(f"🔧 [Vocab Parser] 解析规则: {text}")
    print(f"   天气条件: {condition_value}")
    print(f"   播放内容: {target_id}")

    return RuleCreate(
        name=rule_name,
        priority=1,
        conditions=[Condition(type="weather", operator="==", value=condition_value)],
        action=Action(type="switch_playlist", target_id=target_id),
    )


def _extract_action_with_llm(text: str) -> str:
    """使用 LLM 提取用户想要的广告/产品类型（仅在新词时调用）"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你从用户输入中提取「想要播放的广告或产品类型」。只返回提取的词，如：咖啡、防晒霜、雨衣、冰激凌。不要解释，不要句号。无法确定时返回「未知」。"),
        ("user", "{text}"),
    ])
    try:
        chain = prompt | llm
        result = chain.invoke({"text": text})
        content = (result.content or "").strip()
        if content and content != "未知":
            return content
    except Exception as e:
        print(f"⚠️ [LLM] 提取动作失败: {e}")
    return ""


def _extract_weather_with_llm(text: str) -> str:
    """使用 LLM 提取用户指定的天气条件（仅在新词时调用）"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你从用户输入中提取「天气条件」。只返回一个词，如：晴天、多云、雨天、雪天、雾天。不要解释。无法确定时返回空。"),
        ("user", "{text}"),
    ])
    try:
        chain = prompt | llm
        result = chain.invoke({"text": text})
        content = (result.content or "").strip()
        if content:
            return content
    except Exception as e:
        print(f"⚠️ [LLM] 提取天气失败: {e}")
    return ""


async def parse_rule_with_langchain(text: str, store_id: str, db=None) -> RuleCreate:
    """
    解析自然语言规则。
    优先使用动态词汇表（含自动创建新词），复杂输入或词汇无法覆盖时再调用完整 Gemini 解析。
    """
    # 1. 优先使用词汇表解析（支持新词自动创建）
    try:
        return _parse_with_vocab(text, db)
    except Exception as e:
        print(f"⚠️ [Vocab] 词汇解析异常，尝试 Gemini: {e}")

    # 2. 降级：使用 Gemini 完整解析
    return await _parse_rule_with_gemini_full(text, store_id, db)


async def _parse_rule_with_gemini_full(text: str, store_id: str, db=None) -> RuleCreate:
    """Gemini 完整规则解析（原有逻辑）"""
    system_prompt = """
    你是一个专业的数字标牌调度助手。
    请将用户的自然语言需求转换为结构化的 JSON 规则。

    当前门店 ID: {store_id}

    要求：
    1. 严格遵守输出格式。
    2. 如果用户没有指定 'action' (动作)，默认设为 'switch_playlist'。
    3. 如果用户没有指定 'conditions' (条件)，请根据语境推断。
    4. target_id 使用英文和下划线，如：coffee_ad、sunscreen_ad、yuyi_ad（雨衣广告）

    {format_instructions}
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "{text}")
    ]).partial(format_instructions=parser.get_format_instructions())

    chain = prompt | llm | parser

    print(f"🧠 [Gemini] 正在解析（复杂输入）: {text}")
    try:
        result = await chain.ainvoke({"text": text, "store_id": store_id})
        # 若 Gemini 返回了新的 target_id，可顺手写入词汇表（可选）
        if result.action and result.action.target_id:
            from app.services.vocabulary_service import add_mapping
            add_mapping("action", text[:30], result.action.target_id, db)
        return result
    except Exception as e:
        error_msg = str(e)
        if "RESOURCE_EXHAUSTED" in error_msg or "429" in error_msg or "quota" in error_msg.lower():
            print("⚠️ Gemini API 配额已用完，使用词汇解析")
            return _parse_with_vocab(text, db)
        print(f"⚠️ Gemini 解析错误，使用词汇解析: {e}")
        return _parse_with_vocab(text, db)
