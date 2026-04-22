"""
llm_tool模块

该模块提供了通用的llm调用
将llm调用进行封装,在后续调用时只需调用call_llm即可

"""


import os
from typing import Iterator

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()





def call_llm(query:str, system_prompt:str)->str:
    """
    调用llm
    args:
        query:用户的问题
        system_prompt:系统提示词
    return:
        response:自然语言的回答
    """

    #1. 获取模型的信息

    api_key=os.getenv("DASHSCOPE_API_KEY")
    api_base=os.getenv("DASHSCOPE_API_BASE")
    model_name=os.getenv("LLM_MODE")

    if not api_key or not api_base or not model_name:
        raise ValueError("DASHSCOPE_API_KEY, DASHSCOPE_API_BASE, LLM_MODE 环境变量未设置")

    #2. 定义模型实例
    # 该方法不能服务国内大模型(deepseek除外)
    #llm = init_chat_model(model="", model_provider = "", api_key=api_key, api_base=api_base)

    # 该方法可以支持国内大模型
    llm = ChatOpenAI(model_name=model_name, openai_api_key=api_key, openai_api_base=api_base)


    ###  role: AI/Human/System
    #    ChatPromptTemplate或者PromptTemplate 对象 有且只有两种方式（调用from_messages()方法和实例化ChatPromptTemplate）来构建提示词
    #    from_messages()方法: 接受一个包含BaseMessage对象的列表,每个对象代表一条消息
    #    from_template()方法: 接受一个字符串模板,并使用字符串格式化语法将模板中的变量替换为实际值
    # 
    ### 
    #3. 构建提示词
    prompt = ChatPromptTemplate.from_messages([
        ("system", "{system_instruction}"),
        ("human", "{query}")
    ])
    #prompt_value = prompt.from_template(system_instruction = "AI专家", query = "AI好就业吗?")

    #定义链 (chain) 通过LCEL语法构建 "chain = prompt | llm "
    chain = prompt | llm

    #执行链
    response = chain.invoke({"system_instruction": system_prompt, "query": query})

    return response.content


def stream_llm(query: str, system_prompt: str) -> Iterator[str]:
    """
    流式调用 LLM，按文本片段 yield（用于 SSE）。
    """
    api_key = os.getenv("DASHSCOPE_API_KEY")
    api_base = os.getenv("DASHSCOPE_API_BASE")
    model_name = os.getenv("LLM_MODE")

    if not api_key or not api_base or not model_name:
        raise ValueError("DASHSCOPE_API_KEY, DASHSCOPE_API_BASE, LLM_MODE 环境变量未设置")

    llm = ChatOpenAI(
        model_name=model_name,
        openai_api_key=api_key,
        openai_api_base=api_base,
        streaming=True,
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", "{system_instruction}"),
        ("human", "{query}")
    ])

    chain = prompt | llm

    for chunk in chain.stream({"system_instruction": system_prompt, "query": query}):
        piece = getattr(chunk, "content", None) or ""
        if piece:
            yield piece


if __name__ == "__main__":
    response = call_llm(query="AI好就业吗?", system_prompt="AI就业分析市场专家，用真实数据客观回答用户询问的就业问题")
    print(response)





