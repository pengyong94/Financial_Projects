import redis
import configparser
import os
from utils.logger import info_logger, filter as trace_filter  # 重命名 filter 导入


config = configparser.ConfigParser()
config.read('config.ini')
# 获取 OSS 配置
user_name = config.get('REDIS', 'user_name')
host = config.get('REDIS', 'host')
port = config.get('REDIS', 'port')
password = config.get('REDIS', 'password')

def redis_connection():
    try:
        # 创建Redis连接对象
        r = redis.Redis(
            host=host,
            port=port,
            username=user_name,  
            password=password,
            decode_responses=True
        )
        
        # 发送PING命令测试连接
        response = r.ping()
        if response:
            info_logger.info("Redis连接成功，服务正常响应 PONG")
            return r
        else:
            info_logger.error("连接异常，未能收到有效响应")
            
    except redis.ConnectionError as e:
        info_logger.error(f"连接失败，错误详情：{str(e)}")
    except redis.AuthenticationError as e:
        info_logger.error(f"认证失败，请检查密码：{str(e)}")
    except Exception as e:
        info_logger.error(f"未知错误：{str(e)}")
    



# 执行测试
# redis_connection()

