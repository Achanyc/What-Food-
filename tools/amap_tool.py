"""
高德地图工具模块

该模块提供高德地图的API调用功能，
用于获取地图上的地点信息、路线规划等
"""

from gc import get_referents
from typing import Dict,Any,Optional,Literal
import requests
from requests.adapters import HTTPAdapter
from dotenv import load_dotenv
from pathlib import Path
from urllib3 import Retry
from dataclasses import dataclass
import json
import logging
import os
load_dotenv()


PathInputMode=Literal["1", "2", "3"]
PathMode=Literal["walking","electrobike","driving"]

class PathModeConverter:
    @staticmethod
    def to_mode(path_mode_input: PathInputMode) -> PathMode:
        mapping: Dict[PathInputMode, PathMode] = {
            "1": "walking",
            "2": "electrobike",
            "3": "driving",
        }
        try:
            return mapping[path_mode_input]
        except KeyError:
            raise ValueError(f"Invalid path_mode_input: {path_mode_input}. Supported modes are {list(mapping.keys())}")
   


@dataclass #快速地对对象做操作赋值
class AmapConfig:
    AMAP_API_KEY:str=os.getenv("AMAP_API_KEY")
    MERCHANT_LONGITUDE:str=os.getenv("MERCHANT_LONGITUDE")
    MERCHANT_LATITUDE:str=os.getenv("MERCHANT_LATITUDE")
    DELIVERY_RADIUS:int=(int)(os.getenv("DELIVERY_RADIUS"))
    DEFAULT_PATH_MODE=os.getenv("DEFAULT_PATH_MODE")

    def __post_init__(self):
        ###自动调用###
        if self.AMAP_API_KEY is None:
            raise ValueError("AMAP_API_KEY is not set")


        

#创建配置实例
amap_config = AmapConfig()




def create_session_with_retry():

    #1.构建session
    session=requests.Session() 

    #2.构建重试规则
    retry_rule = Retry(
        total = 3,#(总共重试3次, 不包含第一次)
        backoff_factor = 1,#(重试间隔时间:0.5秒) 退避因子 backoff_factor=1, (backoff_factor)*(2^retries-1) 重试时间：1s,2s,4s,8s,16s   
        status_forcelist = [429,500,502,503,504,505],#(429,500,502,503,504,505状态码时重试)
   
    )  

    #3.构建HTTPAdapter
    adapter = HTTPAdapter(max_retries=retry_rule)

    #4.挂载HTTPAdapter到session
    session.mount('https://',adapter)
    session.mount('http://',adapter)
    return session





def safe_requests(base_url:str,params:dict)->Optional[Dict]:
    #安全的HTTP请求，处理重试和SSL降级

    #HTTPS（加密）协议请求：1. 需要证书验证SSL证书,有可能过期或者错误。需要处理SSL降级为HTTP请求。2. HTTPS协议的网络连接没建立或者网络连接超时。3. Json反序列化失败。
    #1.获取session对象
    session = create_session_with_retry()
    try:
       

        #2.发送请求
        response = session.get(url=base_url, params=params, timeout=10)
        response.raise_for_status()  #遇到[400，600]之间的状态码抛出异常
        res = response.json()  #将网络传输字节反序列化成字典对象。  字节--->对象 反序列化方便应用程序处理  (对象--->字节 序列化方便网络传输)

        return res
    except requests.exceptions.SSLError as e:
       try:
            http_request_url = base_url.replace('https://', 'http://')
            response = session.get(url=http_request_url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()

       except requests.exceptions.RequestException as e:
        raise requests.exceptions.RequestException(f"HTTP请求失败: {e}")
   
    except requests.exceptions.RequestException as e:
        raise requests.exceptions.RequestException(f"HTTP请求失败: {e}")
    except json.decoder.JSONDecodeError as e:
        logging. error(f"JSON解析失败: {e}")
        raise json.decoder.JSONDecodeError(f"反序列化失败: {e}")





def geo_code_by_address(address:str)->Dict[str,Any]:
  """
  根据地址获取高德地图的编码
  args:address:地址
  return:Dict[str,Any]:返回结果

  """
  

  try:
      #1.构建请求的URL
    request_url = "https://restapi.amap.com/v3/geocode/geo"

    #2.构建请求的para
    params = {
        "address": address,
        "key": amap_config.AMAP_API_KEY
    }

    #3.发送请求
    response = safe_requests(request_url,params)

    #4.解析结果: 失败
    # 高德返回的 status 是字符串 "1" 表示成功，用 != 1 会与整数比较失败导致误判
    if str(response.get("status")) != "1":
        return{
            "success": False,
            "message": response.get("info"),
        }
    
    #5.解析结果: 成功

    geocodes = response.get("geocodes")[0]

    return{
        "success": True,
        "location": geocodes.get("location"),
        "formatted_address": geocodes.get("formatted_address"),
    }

  #4.解析结果
  except Exception as e:
    logging.error(f"获取高德地图编码失败: {e}")
    raise Exception(f"获取高德地图编码失败: {e}")


def calculate_distance(origin_location:str,destination_location:str,path_mode_input:PathInputMode or None)->Dict[str,Any]:
  """
  计算两个地点之间的距离
  args:origin:起点
  args:destination:终点
  return:Dict[str,Any]:返回结果
  """

  try:
    if amap_config.AMAP_API_KEY is None:
      raise ValueError("AMAP_API_KEY is not set")

    path_endpoint = {
      "walking": "https://restapi.amap.com/v5/direction/walking",
      "electrobike": "https://restapi.amap.com/v5/direction/electrobike",
      "driving": "https://restapi.amap.com/v5/direction/driving"
    }

    inner_mode = PathModeConverter.to_mode(path_mode_input)

    params = {
      "key": amap_config.AMAP_API_KEY,
      "origin": origin_location, #106.129670,30.957616
      "destination": destination_location, #106.083042,30.797312
    }
    if inner_mode == "driving":
      params["show_fields"] = "cost"

    request_url = path_endpoint[inner_mode]
    response = safe_requests(request_url, params)
    if str(response.get("status")) != "1":
      return {
        "success": False,
        "message": response.get("info"),
      }

    #print(response)

    path = response.get("route", {}).get("paths", [{}])[0]
    if inner_mode == "driving" or inner_mode == "walking":
      duration = path.get("cost", {}).get("duration")
    else:
      duration = path.get("duration")

    return {
      "success": True,
      "distance": int(path.get("distance") or 0),
      "duration": duration,
    }
  except Exception as e:
    logging.error(f"计算两个地点之间的距离失败: {e}")
    raise Exception(f"计算两个地点之间的距离失败: {e}")



def __check_delivery_range(address:str,path_mode_input:PathInputMode = None)->Dict[str,Any]:
  """
  检查地址是否在配送范围内
  args:address:地址
  return:Dict[str,Any]:返回结果
  """
  
  # 获取终点的坐标
  geocode_result = geo_code_by_address(address)
  if not geocode_result.get("success"):
    return {
      "success": False,
      "message": geocode_result.get("message"),
    }

  # 获取起点的坐标
  original_location = f"{amap_config.MERCHANT_LONGITUDE},{amap_config.MERCHANT_LATITUDE}"
  calculate_distance_result = calculate_distance(
    original_location,
    geocode_result["location"],
     path_mode_input=path_mode_input or amap_config.DEFAULT_PATH_MODE
  )

  if not calculate_distance_result.get("success"):
    return {
      "success": False,
      "message": calculate_distance_result.get("message"),
    }

  # 两点之间的距离、时间、是否在配送范围、格式化地址等信息
  distance_m = calculate_distance_result.get("distance")
  distance_km = round((distance_m or 0) / 1000, 2)  # 保留两位小数
  in_range = distance_m  <= amap_config.DELIVERY_RADIUS
  duration = calculate_distance_result.get("duration")
  return{
    "success": True,
    "in_range": in_range,
    "distance": distance_km,
    "duration": int(duration),
    "formatted_address": geocode_result.get("formatted_address"),
    "message": (
        f"配送范围查询成功，距离为{distance_km}公里\n"
        f"时间为{duration}分钟\n"
        f"地址为{geocode_result.get('formatted_address')}\n"
        f"是否在配送范围之内: {'是' if in_range else '否'}"
    )
  }

get_delivery_range = __check_delivery_range


if __name__ == "__main__":

    pass
    # geocode_result1 = geo_code_by_address("南充阳光中心城")#{'success': True, 'location': '106.129670,30.957616', 'formatted_address': '四川省南充市顺庆区芦溪镇'}
    # print(geocode_result1.get("location"))

    # geocode_result2 = geo_code_by_address("南充泰和尚渡") #{'success': True, 'location': '106.083042,30.797312', 'formatted_address': '四川省南充市顺庆区北湖公园'}
    # print(geocode_result2.get("location"))



    # print(calculate_distance(geocode_result1["location"],geocode_result2["location"],"2"))

    pass

    test_address = "南充阳光中心城"
    walk_result = __check_delivery_range(test_address, "2")  # "0" 步行
    if not walk_result.get("success"):
        print(f"步行模式失败：{walk_result.get('message')}")
        raise SystemExit(1)
    walk_distance = walk_result.get("distance")
    walk_duration = walk_result.get("duration")
    walk_in_range = walk_result.get("in_range")

    walk_minutes = int(walk_duration) // 60
    walk_seconds = int(walk_duration - walk_minutes) % 60


    print(
        f"步行模式：距离为 {walk_distance} 公里，"
        f"时间为 {walk_minutes} 分 {walk_seconds} 秒，"
        f"是否在配送范围：{'是' if walk_in_range else '否'}"
    )



    # 对不同的测试地址和配送方式（1-步行，2-电动车，3-驾车）循环测试配送范围
    test_addresses = [
        "南充阳光中心城",
        "南充泰和尚渡",
        "南充王府"
    ]
    mode_names = {
        "1": "步行",
        "2": "电动车",
        "3": "驾车"
    }
    for addr in test_addresses:
        print(f"测试地址：{addr}")
        for mode in ["1", "2", "3"]:
            result = __check_delivery_range(addr, mode)
            km = result.get("distance")
            duration = result.get("duration")
            in_range = result.get("in_range")
            if duration is not None:
                minutes = int(duration) // 60
                seconds = int(duration) % 60
            else:
                minutes = seconds = 0

            print(
                f"{mode_names[mode]}模式：距离为 {km} 公里，"
                f"时间为 {minutes} 分 {seconds} 秒，"
                f"是否在配送范围：{'是' if in_range else '否'}"
            )
        print("-" * 40)
  
  
