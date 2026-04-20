"""
智能点餐助手主程序
LangChain中Agent组件的作用:根据自然语言选择工具，调用工具。
该程序构建了一个包含工具选择功能的LLM系统(相当于LangChain中的Agent角色)，能够：
1. 自动选择合适的工具（常规咨询、菜品推荐、配送范围检查）
2. 调用相应工具并返回结果
3. 提供自然、友好的对话体验
"""
from pathlib import Path
import sys

# 将项目根目录加入路径，便于直接 python agent/assistant.py 运行
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import json
import logging
import time
from typing import Dict, Any
from tools.llm_tool import call_llm
from agent.mcp import general_inquiry, menu_inquiry, delivery_check_tool
from json.decoder import JSONDecodeError
import logging
logger = logging.getLogger(__name__)        

class SmartRestaurantAssistant:
    """智能点餐助手"""

    # 本质上未来需要封装的工具的名字就是函数的名字和工具对象(函数对象)
    def __init__(self):
        self.tools = {
            "general_inquiry": general_inquiry,
            "menu_inquiry": menu_inquiry,
            "delivery_check_tool": delivery_check_tool
        }


        self.instructions = """你是一个智能餐厅助手的意图分析器。
        请分析用户问题意图，并且选择最合适的工具来处理：

        工具说明：
        1. general_inquiry: 处理餐厅常规咨询（营业时间、地址、电话、优惠活动、预约等）
        2. menu_inquiry: 处理智能菜品推荐和咨询（推荐菜品、介绍菜品、询问菜品信息、点餐等）
        3. delivery_check_tool: 处理配送范围检查（查询某个地址是否在配送范围内、能否送达等）

        你必须严格按照以下JSON格式返回，不要包含任何其他文字：
        {
            "tool_name": "工具名称",
             "format_query": "处理后的用户问题"
        }

        正确示例：
        用户："你们几点营业？" -> {"tool_name": "general_inquiry", "format_query": "营业时间"}
        用户："推荐川菜系列的菜品" -> {"tool_name": "menu_inquiry", "format_query": "推荐川菜"}
        用户："能送到武汉大学吗？" -> {"tool_name": "delivery_check_tool", "format_query": "武汉大学"}

        重要规则：
        - 只返回纯JSON，不要有任何额外字符和解释
        - 确保JSON格式完全正确
        - tool_name必须是以下之一：general_inquiry, menu_inquiry, delivery_check_tool
        - format_query要简洁明了地概括用户问题

        记住：如果你错误的选择工具，系统将会出现崩溃。"""


        self.max_retry_times = 3 #最大重试次数
        self.retry_delay = 2 #最大重试间隔



    def _clean_llm_response(self, llm_response_content:str) -> str:
        ###清洗LLM的字符串内容###
        #1. 处理markdown格式的json字符串

        if llm_response_content.startswith("```json"):
            llm_response_content=llm_response_content[7:]
        if llm_response_content.endswith("```"):
            llm_response_content=llm_response_content[:-3]

        #2. 处理json的有效嵌套
        start_index = llm_response_content.find("{")  #左边找到第一个
        end_index = llm_response_content.rfind("}")

        #3.获取有效的json
        if start_index !=-1 and end_index !=-1 and start_index < end_index:
            llm_response_content= llm_response_content[start_index:end_index+1]
            return llm_response_content

        raise ValueError(f"Invalid JSON response: {llm_response_content}")




    def intent_analysis(self, user_query: str, last_error: str)->Dict[str, Any]:

        instructions = self.instructions
        #1.是否有错误
        if last_error:
            instructions += f"\n上次意图分析失败: {last_error}\n 请根据上次意图分析失败的原因，修正意图分析的错误，并返回正确的意图分析结果Json格式。"


        llm_response_str =  call_llm(user_query, self.instructions)
        clean_llm_response_str = self._clean_llm_response(llm_response_str)

        #反序列化llm_response_str为字典
        llm_response_dict = json.loads(clean_llm_response_str)

        return llm_response_dict


    def _fallback_llm_response(self, user_query:str) -> Dict[str, Any]:

        logging.info("基于关键词列表[手动封装工具结构信息]的规则进行降级机制兜底")
        #1. 关键词列表--菜品推荐
        ###
        # 简单（性能高） --->>复杂(性能低) --->>返回工具结构信息
        # 1.列表匹配
        # 2.正则匹配
        # 3.语义相似(嵌入模型： 语义在空间的距离 夹角)
        # 4.LLM相似性匹配(文本模型)
        # 5.经典的机器学系算法(BF算法 ITF算法 ) -->刚需数据标注，泛化能力弱
        ###

        delivery_keywords = ["配送", "送餐", "外卖", "快递", "快递费", "快递费多少", "快递费怎么算", "快递费怎么收", "快递费怎么计算", "快递费怎么收取", "快递费怎么计算", "快递费怎么收取"]

        menu_keywords = ["菜单", "菜品", "菜谱", "菜肴", "菜系", "菜系推荐", "菜系介绍", "菜系推荐", "菜系介绍", "菜系推荐", "菜系介绍","点餐","推荐","介绍","询问","信息","点餐"]

        if any(keyword in user_query for keyword in delivery_keywords):
            return {"tool_name": "delivery_check_tool", "format_query": user_query}
        elif any(keyword in user_query for keyword in menu_keywords):
            return {"tool_name": "menu_inquiry", "format_query": user_query}
        else:
            return {"tool_name": "general_inquiry", "format_query": user_query}


    def analyse_intent_with_retry(self, query: str) -> Dict[str, str]:
        logger.info(f"分析用户意图: {query}")

        last_error = None
        for retry in range(self.max_retry_times):
            try:
                logger.info(f"意图分析第 {retry + 1} 次尝试")
                result = self.intent_analysis(query, last_error)
                logger.info(f"意图分析成功: {result}")
                return result
            except(JSONDecodeError, ValueError) as e:
                last_error = str(e)
                logger.warning(f"第 {retry + 1} 次尝试失败: {last_error}")

                if retry < self.max_retry_times - 1:
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"经过 {self.max_retry_times} 次重试后仍然失败，使用兜底方案")
            
            #
            return self._fallback_llm_response(query)



    def execute_tool(self, tool_name:str,tool_param:str) -> Dict[str, Any] | str:
        """
        Execute the tool with the given tool name and parameters
        """
        try:
            tool_obj = self.tools[tool_name]
            if tool_obj is None:
                raise ValueError(f"Invalid tool name: {tool_name}")

            if tool_name == "general_inquiry":
                tool_result = tool_obj.invoke(
                    {"query": tool_param, "context": ""}
                )
            elif tool_name == "menu_inquiry":
                tool_result = tool_obj.invoke(
                    {"query": tool_param, "context": ""}
                )
            elif tool_name == "delivery_check_tool":
                tool_result = tool_obj.invoke({"address": tool_param, "travel_mode": "2"})
            else:
                raise ValueError(f"Invalid tool name: {tool_name}")

            return tool_result
        except Exception as e:
            raise RuntimeError(f"Tool execution failed: {str(e)}")
   



    ###
    ### LangChain中Agent组件中的invoke方法
    ### 作用：  1.找工具 2.调用工具 
    ### 本质就是Agent和外部应用之间的交互

    def invoke(self, user_query:str):
        
        # match tools with user query
        structured_tool = self.analyse_intent_with_retry(user_query)
        tool_name = structured_tool['tool_name']
        tool_param = structured_tool['format_query']




        
        tool_result = self.execute_tool(tool_name, tool_param)
        return tool_result


def chat_with_assistant(user_query: str):
    """
    智能对话助手
    """

    try:
        # 1. 实例化小助手
        assistant = SmartRestaurantAssistant()
        # 2. 调用小助手的方法
        assistant_response = assistant.invoke(user_query)
        print(f"Assistant Response: {assistant_response}")
        return assistant_response
    except Exception as e:
        print(f"Assistant Error: {str(e)}")
        return {"error": str(e)}


if __name__ == "__main__":

    pass
    # user_query = "你们餐厅的联系电话是多少"
    # assistant_response = chat_with_assistant(user_query)
    # print(f"Assistant Response: {assistant_response}")

    
    # user_query = "推荐鲁菜"
    # assistant_response = chat_with_assistant(user_query)
    # print(f"Assistant Response: {assistant_response}")

    # user_query = "南充五中在你们的配送范围内吗？"
    # assistant_response = chat_with_assistant(user_query)
    # print(f"Assistant Response: {assistant_response}")