"""
智能点餐助手 服务类封装

封装三个核心功能：
- smart_chat: 调用 assistant.py 中的 chat_with_assistant 函数
- delivery_check: 调用 check_delivery_range 函数 获取配送范围展示
- get_menu: 调用 get_menu_items_list 函数 获取菜品区域数据的展示
- iter_chat_sse_events: 流式对话（SSE），意图路由后按 token 推送 LLM 输出
"""

from typing import Any, Dict, Iterator

from tools.amap_tool import PathInputMode

def  get_menu():
    """获取菜品区域数据的展示"""
    from  tools.db_tool import  get_menu_items
    return get_menu_items()



def check_delivery_range(address: str, travel_mode: PathInputMode):

    from tools.amap_tool import __check_delivery_range
    return __check_delivery_range(address, travel_mode)



def smart_chat(user_query: str):
    ####### 对话接口 #######

    from   agent.assistant import chat_with_assistant

    return chat_with_assistant(user_query)


def iter_chat_sse_events(user_query: str) -> Iterator[Dict[str, Any]]:
    """
    生成 SSE 事件字典序列。

    事件类型：
    - route: 意图路由结果
    - meta:  menu_ids（菜品推荐场景）
    - start: 开始生成（mode: text | recommendation | delivery）
    - delta: 正文增量片段
    - done: 结束（可带 menu_ids）
    - error: 异常信息
    """
    from agent.assistant import SmartRestaurantAssistant
    from agent.mcp import delivery_check_tool, load_prompt_template
    from tools.llm_tool import stream_llm
    from tools.menu_context_display import sanitize_menu_contents_for_prompt
    from tools.pinecone_tool import search_menu_data_with_id

    assistant = SmartRestaurantAssistant()
    structured = assistant.analyse_intent_with_retry(user_query)
    tool_name = structured.get("tool_name")
    tool_param = structured.get("format_query") or user_query

    if not tool_name:
        yield {"type": "error", "message": "意图分析未返回 tool_name"}
        return

    yield {"type": "route", "tool": tool_name, "format_query": tool_param}

    if tool_name == "general_inquiry":
        template = load_prompt_template("general_inquiry")
        full_query = (
            f"用户问题: {tool_param}\n\n "
            f",请基于以上检索到的信息，回答用户提出的相关问题"
        )
        yield {"type": "start", "mode": "text"}
        try:
            for chunk in stream_llm(full_query, template):
                yield {"type": "delta", "content": chunk}
            yield {"type": "done", "success": True, "query": user_query}
        except Exception as e:
            yield {"type": "error", "message": str(e)}

    elif tool_name == "menu_inquiry":
        prompt_template = load_prompt_template("menu_inquiry")
        similar_results = search_menu_data_with_id(tool_param)

        menu_ids = []
        if isinstance(similar_results, dict):
            menu_ids = similar_results.get("ids") or []

        yield {"type": "meta", "menu_ids": menu_ids}

        if isinstance(similar_results, dict) and similar_results.get("contents"):
            display_lines = sanitize_menu_contents_for_prompt(similar_results["contents"])
            menu_contents_context = "\n".join(f" -{item}" for item in display_lines)
            full_query = (
                f"当前从向量数据库中检索到的菜品信息:\n{menu_contents_context} \n\n"
                f"用户问题: \n{tool_param} \n\n "
                f",请基于以上检索到的信息，回答用户提出的相关问题"
            )
        else:
            full_query = (
                f"暂无相关菜品信息,用户问题: {tool_param} \n\n "
                f",请基于一般的菜品信息，回答用户提出的相关问题"
            )

        yield {"type": "start", "mode": "recommendation"}
        try:
            for chunk in stream_llm(full_query, prompt_template):
                yield {"type": "delta", "content": chunk}
            yield {
                "type": "done",
                "success": True,
                "query": user_query,
                "menu_ids": menu_ids,
            }
        except Exception as e:
            yield {"type": "error", "message": str(e)}

    elif tool_name == "delivery_check_tool":
        yield {"type": "start", "mode": "delivery"}
        try:
            text = delivery_check_tool.invoke(
                {"address": tool_param, "travel_mode": "2"}
            )
            yield {"type": "delta", "content": str(text)}
            yield {"type": "done", "success": True, "query": user_query}
        except Exception as e:
            yield {"type": "error", "message": str(e)}

    else:
        yield {"type": "error", "message": f"未知工具: {tool_name}"}