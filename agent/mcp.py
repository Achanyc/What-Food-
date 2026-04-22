"""
实现LangChain中各个工具的定义（定义三个工具、工具一：实现常规问题的对话回答 工具二：实现菜品查询问题对话 工具三：实现距离范围配送问题对话）
"""

from ast import main
from tools.menu_context_display import sanitize_menu_contents_for_prompt
from tools.pinecone_tool import search_menu_data_with_id
from langchain_core.tools import tool,ToolException
from tools.llm_tool import call_llm
from tools.amap_tool import get_delivery_range, PathInputMode


from typing import Dict, Any
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_prompt_template(prompt_name: str)->str:
    
    try:
        current_file_path = os.path.abspath(__file__)
        print(current_file_path)  
        current_dir = os.path.dirname(current_file_path)
        project_root = os.path.dirname(current_dir)


        prompt_path = os.path.join(project_root, "prompts", f"{prompt_name}.txt")

        with open(prompt_path, "r", encoding="utf-8") as file:
            return file.read().strip()  
    except Exception as e:
        logging.error(f"加载提示词模版失败: {str(e)}")
        return "无法加载提示词模版，请根据用户提问，直接提供帮助"




@tool
def general_inquiry(query: str, context: str) -> str:
    """
        常规问询工具

        处理用户的一般性问题，包括但不限于：
        - 餐厅介绍和服务信息
        - 营业时间和联系方式
        - 优惠活动和会员服务
        - 其他非菜品相关的咨询

        Args:
            query: 用户的问询内容
            context: 可选的上下文信息，用于提供更精准的回复

        Returns:
            str: 针对用户问询的智能回复

        Raises:
            ToolException: 当处理查询时发生错误
        """


    try:
        # 1. 加载提示词模版
        template=load_prompt_template("general_inquiry")
        


        # TODO: 后续扩展context的获取方式，从记忆组件中读取QA
        #context = "这里是上下文信息"
        # 2. 处理输入问题
        full_query=  f"当前提供的上下文:{context} \n\n 用户问题: {query}\n\n ,请基于以上检索到的信息，回答用户提出的相关问题"  if   context else f"用户问题: {query}\n\n ,请基于以上检索到的信息，回答用户提出的相关问题"

        # 3. 调用LLM模型
        response = call_llm(full_query, template)

        # TODO:将QA写入到记忆组件

        return  response


    except Exception as e:
        raise ToolException(f"常规问询处理失败: {str(e)}")




@tool
def menu_inquiry(query: str, context: str) -> str:
    """菜单与菜品推荐问询工具。根据用户问题检索并推荐相关菜品。"""

    try:
        prompt_template = load_prompt_template("menu_inquiry")

        # 1. 利用文本嵌入模型，从向量数据库中检索菜品信息
        similar_results = search_menu_data_with_id(query)
        if similar_results and similar_results['contents']:
            display_lines = sanitize_menu_contents_for_prompt(similar_results["contents"])
            menu_contents_context = "\n".join(f" -{item}" for item in display_lines)
            full_query = f"当前从向量数据库中检索到的菜品信息:\n{menu_contents_context} \n\n 用户问题: \n{query} \n\n ,请基于以上检索到的信息，回答用户提出的相关问题"
        else:
            full_query = f"暂无相关菜品信息,用户问题: {query} \n\n ,请基于一般的菜品信息，回答用户提出的相关问题"

        # 利用文本模型对向量数据库中检索到的菜品再做一次总结、提取和过滤。最终推荐和你问题最相似的菜品
        llm_response = call_llm(full_query, prompt_template)

        return {
            "recommendation": llm_response,
            "menu_ids": similar_results['ids'] if similar_results and 'ids' in similar_results else [] #使用正则表达式提取similar_results菜品ID
        }
    except Exception as e:
        raise ToolException(f"菜单问询处理失败: {str(e)}")



@tool
def delivery_check_tool(address: str, travel_mode: PathInputMode) -> str:
    """
    配送范围查询工具
    
    处理用户提出的配送范围查询问题，包括但不限于：
    - 查询用户地址的配送范围
    - 查询用户地址的配送时间
    - 查询用户地址的配送费用
    """
    try:
        delivery_range = get_delivery_range(address, travel_mode)

        if delivery_range['success']:
            status_text = "可以配送" if delivery_range["in_range"] else "超出范围"

            response_text = f"""
            配送信息查询结果：
            配送地址：{delivery_range['formatted_address']}
            配送距离：{delivery_range['distance']}公里(骑行距离))
            配送状态: {status_text}
            """.strip()
        else:
            response_text = f"配送范围查询失败：{delivery_range.get('message', '未知错误')}"
        return response_text
    except Exception as e:
        raise ToolException(f"配送范围查询处理失败: {str(e)}")





if __name__ == "__main__":
    print(general_inquiry("我想吃一份宫保鸡丁", ""))
    print(menu_inquiry("我想吃一份宫保鸡丁", ""))




