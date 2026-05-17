import json

import redis.asyncio as redis


REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0


# 创建redis的连接对象
redis_client = redis.Redis(
    host=REDIS_HOST,  # redis服务地址
    port=REDIS_PORT,  # redis端口号
    db=REDIS_DB,     # redis数据库编号，默认为0
    decode_responses=True  # 返回结果为字符串类型，默认为字节类型
)

# 设置  和  读取（字符串 和 列表或字典）"[{}]"
# 读取：字符串
async def get_cache(key:str):
    """
    获取redis数据
    :param key:
    :return:
    """
    try:

        return await redis_client.get(key)
    except Exception as e:
        print(f"获取缓存失败：{e}")
        return  None

# 读取：列表或字典
async def get_json_cache(key:str):
    """
    获取redis数据
    :param key:
    :return:
    """
    try:

       data = await redis_client.get(key)
       if data:
           return json.loads(data)  #序列化
    except Exception as e:
        print(f"获取缓存失败：{e}")
        return  None


# 设置缓存
async def set_cache(key:str, value:str, expire:int=3600):
    """
    设置redis数据
    :param key:
    :param value:
    :param expire:过期时间
    :return:
    """
    try:
        if isinstance(value, (dict, list)):
            #转字符串再存
            value = json.dumps(value,ensure_ascii=False)
        await redis_client.setex(key, expire, value)
        return True
    except Exception as e:
        print(f"设置缓存失败：{e}")
        return False
