"""
智能点餐助手主程序 FastAPI 接口
1.定义FastAPI应用实例
2.提供三个主要接口：
2.1 POST /chat - 智能对话接口
2.2 POST /delivery - 配送查询接口
2.3 GET /menu/list - 菜品列表接口
"""


import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel  
from typing import List,Optional    
from tools.amap_tool import PathInputMode
import logging
logging.basicConfig(level=logging.INFO)
logger=logging.getLogger(__name__)
 

app=FastAPI(title="智能点餐助手的API接口",description="智能点餐应用主要暴露三个接口分别为智能对话接口、配送查询接口、菜品列表接口")



@app.get("/")
def  read_root():
    """测试项目根路径访问是否可用"""
    return {"hello":"world"}



@app.get("/healthy")
def  healthy():
    """测试项目请求路径访问是否可用"""
    return {"message":"请求路径访问健康"}





class DeliveryRequest(BaseModel):
    ###配送查询请求###
    address: str # 地址
    travel_mode: PathInputMode # 出行方式

class ChatRequest(BaseModel):
    ###智能对话请求###
    query: str # 输入查询
     





# 定义数据模型
# 菜品列表展示
class MenuListResponse(BaseModel):
    """菜品列表响应"""
    success: bool   # 有数据：True 没数据False
    menu_items: List[dict] # 菜品列表
    count: int # 菜品数
    message: str # 响应消息提示



#配送响应数据模型

class DeliveryResponse(BaseModel):

    ###配送查询响应####
    success: bool # 有数据：True 没数据False
    in_range: bool # 是否在配送范围
    distance: float # 距离（公里）
    formatted_address: str # 格式化地址
    duration: float # 时间（秒）

    message: str # 响应消息提示
    travel_mode: PathInputMode # 出行方式
    input_address: str # 输入地址


class ChatResponse(BaseModel):
    ###智能对话响应###
    success: bool # 有数据：True 没数据False
    query: str # 输入查询
    response: Optional[str] = None # 响应内容
    menu_ids: Optional[List[str]] = None # 推荐的菜品 ID（与向量检索一致，字符串）
    recommendation: Optional[str] = None # 推荐正文（与 agent 返回字段 recommendation 一致）


class DeliveryRequest(BaseModel):
    input_address: str # 输入地址
    travel_mode: PathInputMode # 出行方式   



@app.get("/menu/list", response_model=MenuListResponse)
async def menu_list_endpoint():
    """菜品列表区域展示"""

    # 1.调用service
    from  service.diancan_service import get_menu

    # 2.调用方法
    menu_items=get_menu()


    # 3.封装结果返回
    if  not  menu_items:
        return MenuListResponse(
            success=False,
            menu_items=[],
            count=0,
            message="暂无菜品列表可用"
        )

    return MenuListResponse(
        success=True,
        menu_items=menu_items,
        count=len(menu_items),
        message=f"成功查询到{len(menu_items)}道菜品信息"
    )



@app.post("/delivery", response_model=DeliveryResponse)
async def delivery_endpoint(request: DeliveryRequest):
    try:
        from service.diancan_service import check_delivery_range

        result = check_delivery_range(request.input_address, request.travel_mode)

        # 业务失败（地理编码/路径规划等返回 success: False）
        if result.get("success") is False:
            return DeliveryResponse(
                success=False,
                in_range=False,
                distance=0,
                formatted_address=request.input_address,
                duration=0.0,
                message=result.get("message") or "配送范围查询失败",
                travel_mode=request.travel_mode,
                input_address=request.input_address,
            )
        return DeliveryResponse(
            success=True,
            in_range=result.get("in_range"),
            distance=result.get("distance"),
            formatted_address=result.get("formatted_address"),
            duration=float(result.get("duration") or 0),
            message=result.get("message"),
            travel_mode=request.travel_mode,
            input_address=request.input_address,
        )
    except Exception as e:
        logger.error(f"配送查询接口异常: {e}")
        return DeliveryResponse(
            success=False,
            in_range=False,
            distance=0,
            formatted_address=request.input_address,
            duration=0.0,
            message=f"查询配送范围失败: {e}",
            travel_mode=request.travel_mode,
            input_address=request.input_address,
        )


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:    
        from service.diancan_service import smart_chat

        result = smart_chat(request.query)

        if isinstance(result, dict) and "recommendation" in result and "menu_ids" in result:
            return ChatResponse(
                success=True,
                query=request.query,
                recommendation=result.get("recommendation"),
                menu_ids=result.get("menu_ids"),
            )
        # 普通文本响应
        return ChatResponse(
            success=True,
            query=request.query,
            response=str(result)           
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"智能对话接口异常: {e}"
            )


@app.post("/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """智能对话 SSE：意图路由后开始流式输出正文（Embedding 可走缓存）。"""
    def generate():
        from service.diancan_service import iter_chat_sse_events

        try:
            for ev in iter_chat_sse_events(request.query):
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )