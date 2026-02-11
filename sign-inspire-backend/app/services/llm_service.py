import os
from dotenv import load_dotenv
load_dotenv() #

from langchain_google_genai import ChatGoogleGenerativeAI # <-- 换成这个
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from app.schemas.rule import RuleCreate

# 1. 初始化 Gemini
# model="gemini-2.5-flash" 是目前性价比最高的，速度极快
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    # 如果你在国内，可能需要配置代理，或者确保你的终端开启了全局代理
    # transport="rest", 
)

parser = PydanticOutputParser(pydantic_object=RuleCreate)

async def parse_rule_with_langchain(text: str, store_id: str) -> RuleCreate:
    system_prompt = """
    你是一个专业的数字标牌调度助手。
    请将用户的自然语言需求转换为结构化的 JSON 规则。
    
    当前门店 ID: {store_id}
    
    要求：
    1. 严格遵守输出格式。
    2. 如果用户没有指定 'action' (动作)，默认设为 'switch_playlist'。
    3. 如果用户没有指定 'conditions' (条件)，请根据语境推断。
    
    {format_instructions}
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "{text}")
    ]).partial(format_instructions=parser.get_format_instructions())

    chain = prompt | llm | parser
    
    print(f"🧠 [Gemini] 正在解析: {text}")
    try:
        result = await chain.ainvoke({"text": text, "store_id": store_id})
        return result
    except Exception as e:
        # Gemini 有时候对 JSON 格式不仅十分严格，我们可以捕获错误看详情
        print(f"Gemini 解析错误: {e}")
        raise e