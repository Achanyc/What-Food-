"""
Pinecone向量数据库工具模块

该模块提供Pinecone向量数据库的连接和操作功能，
用于存储和查询菜品信息的向量化数据，支持语义搜索
"""

from ast import match_case
import  os
import sys
from token import tok_name
import dashscope
from  dotenv import load_dotenv
from  typing import List,Dict,Any
from pinecone import Pinecone
from pinecone import ServerlessSpec
from http import HTTPStatus

from tools.embedding_cache import get_embedding_cache


load_dotenv()


import  logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class   PineconeVectorDB:
    """PineCone向量数据库的操作"""

    def  __init__(self):
        self.pinecone_api_key=os.getenv("PINECONE_API_KEY","pcsk_2ZXjeu_6CJdYmKmDaLHXvchuHUQEPXWt7SFzD9fhX9onTVbjeBm19bf7unAbMXN7ZjtjDd")
        self.dashscope_api_key=os.getenv("DASHSCOPE_API_KEY","sk-2d152263bea641c9b9fa4ddebe8f2ce7")
        self.pinecone_env=os.getenv("PINECONE_ENV","us-east-1")

        # 配置索引名字、嵌入模型名字、嵌入模型的维度
        self.index_name="restaurant-menu-item-index"
        self.embedding_model="text-embedding-v4"
        self.dimension=1536   

        # 配置pinecone客户端对象以及索引对象
        self.pc=None
        self.index=None


    def  initialize_connection(self)->bool:
        """初始化PineCone向量数据库的客户端对象以及索引对象"""
        try:
            # 1.判断pinecone_api_key 是否赋值成功
            if  not self.pinecone_api_key:
                logger.error("pinecone api_key  not found!")
                return False

            # 2.初始化客户端对象
            self.pc = Pinecone(api_key=self.pinecone_api_key)

            # 3.初始化索引对象

            #没有索引时创建
            if not self.pc.has_index(self.index_name):
                self.pc.create_index(
                    name=self.index_name,
                    vector_type="dense", 
                                        #dense 向量类型： 以 Embedding 模型完成“语义压缩”：将对象转化为高维空间的坐标；空间映射：用cosine距离来计算相似度。判断苹果相近水果的维度，也靠近手机的维度
                                        #sparse 稀疏向量则是更加死板严格地包含关键字， 通常可以和dense一起混合检索提高召回质量
                # 3.2 设置向量维度
                   dimension=self.dimension,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws",
                                        region=self.pinecone_env)
                )

           #  4. 获取并赋值
           # 有索引时直接给pc客户端赋值
            self.index=self.pc.Index(self.index_name)
            logger.info("初始化向量数据库PineCone客户端以及索引对象成功")
            return  True
        except Exception as e:
            logger.error(f"初始化向量数据库PineCone客户端以及索引对象失败:{e}")
            return  False



    def  clear_index_vectors(self)->bool:
        """清空指定索引下的向量数据【不是删除索引，索引结构保留，向量数据删除】"""

        try:
            if  not self.index and  not self.initialize_connection():
                logger.error("索引不存在")
                return False

            # 判断索引下是否已经有向量数据。如果有向量数据，直接删除向量数据  如果没有向量数据，不用在删除
            vector_status=self.index.describe_index_stats()
            count=vector_status['total_vector_count']
            if  count==0:
                logger.info("该索引下不存在任何向量数据")
                return  True
            self.index.delete(delete_all=True)

            logger.info("成功删除索引下所有的向量数据")

            return  True
        except Exception as e:
            logger.error(f"删除索引下的向量数据失败:{e}")
            return  False


    def  _embedding_content(self,content:str)->List[float] or None:
        """对文本进行向量化
        args:content:要向量的文本
        :return:文本向量后的结果。[0.1111,0.23,...]
        """
        try:
            # 1.判断dashscope_api_key
            if  not self.dashscope_api_key:
                logger.error("dashscope api_key  not found!")
                return None

            cache = get_embedding_cache()
            cached = cache.get(content, self.embedding_model, self.dimension)
            if cached is not None:
                logger.debug("embedding cache hit (len=%s)", len(cached))
                return cached

            # 2.发送请求
            resp = dashscope.TextEmbedding.call(
                api_key=self.dashscope_api_key,
                model=self.embedding_model,
                input=content,
                dimension=self.dimension,  # 指定向量维度（仅 text-embedding-v3及 text-embedding-v4支持该参数）
            )

            # 3.解析响应结果，提取要的向量列表值
            if resp.status_code == HTTPStatus.OK:
                logger.debug("文本向量化成功（已写入缓存）")
                vec = resp.get('output').get('embeddings')[0].get('embedding')
                if vec and len(vec) == self.dimension:
                    cache.put(content, self.embedding_model, self.dimension, vec)
                return vec
            else:
                # dashscope 的返回对象通常包含：status_code / code / message / request_id 等信息
                status_code = getattr(resp, "status_code", None)
                code = getattr(resp, "code", None)
                message = getattr(resp, "message", None)
                request_id = getattr(resp, "request_id", None)
                logger.error(
                    f"发送文本嵌入模型请求处理失败 status_code={status_code} code={code} message={message} request_id={request_id}"
                )
                return None
        except Exception as e:
            logger.error(f"发送文本嵌入模型请求处理失败,原因:{e}")
            return None


    def _validate_datasource(self,validation_content:str)->bool:
        """校验数据源"""

        # 1.校验是否有
        if  not validation_content:
            logger.error("数据源不存在")
            return False

        # 2.校验是否能用
        validate_result_str=("当前无可用的菜品信息","查询菜品信息失败")

        # 3.判断最终结果
        return  not validation_content.startswith(validate_result_str)


    def  _splite_content(self,splite_content:str)->List[str]:
        """切割加载到的菜品信息"""
        try:

            # 1.定义文本切分器（递归的文本切分器）
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            text_spliter=RecursiveCharacterTextSplitter(chunk_size=100,chunk_overlap=0,separators=["\n"],length_function=len)

            # 2.切割
            docs=text_spliter.create_documents([splite_content])

            # 3.处理切后的文档列表
            clearn_docs=[]
            for  doc  in docs:
                # a) 提取的文档对象的内容
                page_content=doc.page_content
                # b) 提取的文档对象的内容做一个小清洗
                # 数据清洗通过去掉每一块字符串两端的空白符来完成
                clearn_content = page_content.strip()
                clearn_docs.append(clearn_content)
         
            print(f"菜品信息切割后的块个数：{len(clearn_docs)}")
            return clearn_docs
        except Exception as e:
            logger.error(f"文本切割失败:{e}")
            return []

    def upsert_menu_data(self, menu_data: str = None, batch_size: int = 30, clear_existing: bool = True) -> bool:
        """
        将文本向量存储到PineCone向量数据库
        args1:菜品信息
        args2:批量插入向量数据库中的阈值大小
        args3:是否要清空之前索引下的向量数据。
        """

        try:
           if  not menu_data:
               # 兼容两种启动方式：
               # 1) python tools/pinecone_tool.py  -> sys.path[0] 是 tools/
               # 2) python -m tools.pinecone_tool  -> 正常包导入
               try:
                   from .db_tool import get_all_menu_items  # type: ignore
               except Exception:
                   try:
                       from tools.db_tool import get_all_menu_items  # type: ignore
                   except Exception:
                       from db_tool import get_all_menu_items  # type: ignore
               # 0. 清除现有数据
               if clear_existing:
                   self.clear_index_vectors()
               # 1.从数据库查
               menu_item_str=get_all_menu_items()

               # 2.校验数据源
               if  not self._validate_datasource(menu_item_str):
                   logger.error("校验数据源失败,不能进行向量")
                   return False

               # 3.对加载到的数据切分
               embedding_chunks=self._splite_content(menu_item_str)
               if  not  embedding_chunks:
                   logger.error("切片失败，不能进行向量")
                   return  False


               # 4.对切分后的chunk进行向量操作
               batch=[]
               for  line_num,chunk in enumerate(embedding_chunks,1):
                   # a) 对chunk进行向量操作
                   vectors_content=self._embedding_content(chunk)
                   # b) 判断向量结果
                   if not vectors_content or  len(vectors_content)!=self.dimension:
                       logger.error("向量值不存在或者维度不匹配")
                       return False

                   # c) 判断索引对象
                   if not self.index and not self.initialize_connection():
                       logger.error("索引不存在")
                       return False

                   # d) 准备一些元数据
                   menu_medata={
                       "content": chunk,   # 原始文本
                       "line_number": line_num,
                       "dish_id":f"菜品ID:{line_num}", # 真正应该利用正则表达式提取菜品ID
                       "type": "menu_item"
                   }
                   # e) 准备向量数据的唯一标识(假设充当)
                   unique_vector_id=str(line_num)

                   batch.append((unique_vector_id,vectors_content,menu_medata))


                   # f) 将文本向量的结果插入到向量数据库中
                   if len(batch)>=batch_size:
                       # 可以插入
                       self.index.upsert(vectors=batch)
                       batch=[] # 清空

               if batch:
                   self.index.upsert(vectors=batch)
               logger.info("切分之后的文本内容成功存储到向量数据库中...")
               return  True

           else:
               logger.info("处理文本数据")
               logger.info("向量化文本数据")
               logger.info("向量结果存储到向量数据库")
               return   False

        except Exception as e:
            logger.error(f"同步数据到向量数据库失败{e}")
            return  False





    def search_similar_menu_data(self, query:str, top_k:int = 2) -> List[Dict[str,Any]]:
        ###相似性检索###

        try:
        #确保索引存在
            if not self.index and not self.initialize_connection():
                logger.error("索引不存在")
                return False


        #将问题向量化
            query_vector=self._embedding_content(query)
          
                
        #判断向量是否存在或者有效
            if not query_vector or len(query_vector)!=self.dimension:
                logger.error("向量值不存在或者维度不匹配")
                return False

        #执行语义搜索
            similar_results= self.index.query(
                vector=query_vector,
                top_k=top_k,
                include_metadata=True,
            )

        #提取相似结果
            matches_results=similar_results.get('matches')
            if not matches_results:
                logger.info("没有找到相似的菜品信息")
                return []





                

        #处理相似结果
            finall_results_list=[]
            for item in matches_results:
                match_item = {
                    'id':item.get('id'),
                    'score':item.get('score'),
                    'content':item.get('metadata').get('content'),
                    'line_number':item.get('metadata').get('line_number')
                }
                finall_results_list.append(match_item)
            logger.info(f"相似性检索成功，找到{len(finall_results_list)}条相似的菜品信息")
            return finall_results_list

        except Exception as e:
            logger.error(f"相似性检索失败{e}")
            return  []    




# 定义全局实例
pinecone_db=PineconeVectorDB()


#暴露定义全局同步数据库的方法
def pinconeInput(menu_data:str=None,clear_existing:bool=True)->bool:
    """
    同步菜品信息到PineCone向量数据库
    args1:menu_data:菜品信息
    args2:clear_existing:是否要清空之前索引下的向量数据。
    return:True:成功，False:失败
    
    
    
    """

    try:
        return pinecone_db.upsert_menu_data(menu_data=menu_data,clear_existing=clear_existing)
    except Exception as e:
        logger.error(f"同步菜品信息到PineCone向量数据库失败{e}")
        return False



#暴露定义全局查询数据库的方法

def search_menu_data(query:str,top_k:int=2)->List[Dict[str,Any]]:
    """
    查询菜品信息
    args1:query:查询条件
    args2:top_k:返回结果的条数
    return:True:成功，False:失败
    """
    match_results= pinecone_db.search_similar_menu_data(query=query,top_k=top_k)
    if not match_results:
        logger.error("没有找到相似的菜品信息")
        return []
    return [item.get('content') for item in match_results]




#前端展示用
def search_menu_data_with_id(query:str,top_k:int=2)->[Dict[str,Any]]:

    """
    查询菜品信息
    args1:query:查询条件
    args2:top_k:返回结果的条数
    return:True:成功，False:失败
    """
    match_results= pinecone_db.search_similar_menu_data(query=query,top_k=top_k)
    if not match_results:
            logger.error("没有找到相似的菜品信息")
            return []
    
    dishes = []
    for item in match_results:
        content = item.get('content')
        import re
        match = re.match(r'菜品ID:(\d+)',content)
        if match:
            dish_id = match.group(1)
            print(dish_id)
        else:
            dish_id=item['id']
        dishes.append(dish_id)
    return  {
     "contents":  [item.get('content') for item in match_results] , 
     "ids":  dishes,   
     "scores":  [item.get('score') for item in match_results]  
    }




if __name__ == "__main__":

    # Windows 控制台可能默认使用 gbk，打印包含 '¥' 等字符会报 UnicodeEncodeError
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # py3.7+
    except Exception:
        pass

    #  print("\n1.测试pinecone客户端和索引的创建")
    #  pinecone_db.initialize_connection()

    # #print("\n2.上传菜品信息到向量数据库")

    # #pinecone_db.upsert_menu_data(menu_data=None,batch_size=10)

    #  pinecone_db.upsert_menu_data(menu_data=None,batch_size=10,clear_existing=True)

    # print("\n3.菜品相似度检索")
    # matches_results = pinecone_db.search_similar_menu_data(query="我想吃鱼",top_k=2) 
    # #本质上能够根据语义召回信息，是用到了嵌入模型text-embedding-v4的能力。
    # for match in matches_results:
    #     print(match)

    # print("\n5.菜品相似度检索")
    # matches_results = search_menu_data(query="我想吃蒜香排骨",top_k=3)
    # for match in matches_results:
    #     print(match)


    print("\n6.菜品相似度检索")
    matches_results = search_menu_data_with_id(query="我想吃蒜香排骨",top_k=3)
    
    print(matches_results)





















































































