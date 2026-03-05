"""
QuestDB HTTP REST API 客户端

用于连接和操作QuestDB时序数据库
"""

import requests
import pandas as pd
import json
from typing import Optional
from utils.logger_utils import setup_logger
import config

logger = setup_logger(
    logger_name=__name__,
    log_level=config.get_log_config()["log_level"],
    log_dir=config.get_log_config()["log_dir"]
)


class QuestDBClient:
    """QuestDB HTTP REST API 客户端"""

    def __init__(self, host: str = 'localhost', port: int = 9000, user: str = '', password: str = ''):
        """
        初始化QuestDB客户端

        Args:
            host: QuestDB服务器地址
            port: QuestDB HTTP端口
            user: 用户名（可选）
            password: 密码（可选）
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.base_url = f"http://{host}:{port}"

    def test_connection(self) -> bool:
        """
        测试 QuestDB 连接

        Returns:
            bool: 连接是否成功
        """
        try:
            url = f"{self.base_url}/exec"
            params = {'query': 'SELECT 1'}
            auth = (self.user, self.password) if self.user else None
            response = requests.get(url, params=params, auth=auth, timeout=10)
            if response.status_code == 200:
                logger.info(f"QuestDB 连接测试成功: {self.host}:{self.port}")
                return True
            else:
                logger.error(f"QuestDB 连接测试失败: HTTP {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"QuestDB 连接测试失败: {e}")
            return False

    def query(self, sql: str, timeout: int = 300) -> pd.DataFrame:
        """
        执行SQL查询并返回DataFrame

        Args:
            sql: SQL语句
            timeout: 超时时间（秒），默认5分钟

        Returns:
            DataFrame: 查询结果

        Raises:
            Exception: 查询失败时抛出异常
        """
        auth = None
        if self.user:
            auth = (self.user, self.password)

        url = f"{self.base_url}/exec"
        params = {'query': sql, 'df': 'true'}

        logger.debug(f"QuestDB查询: {sql[:200]}...")

        try:
            response = requests.get(url, params=params, auth=auth, timeout=timeout)

            if response.status_code == 200:
                content = response.text.strip()
                if not content or content == 'null':
                    return pd.DataFrame()

                try:
                    json_data = json.loads(content)
                    if 'error' in json_data:
                        raise Exception(f"QuestDB SQL执行错误: {json_data.get('error')}")
                    if 'columns' in json_data and 'dataset' in json_data:
                        df = pd.DataFrame(json_data['dataset'], columns=[c['name'] for c in json_data['columns']])
                        logger.debug(f"QuestDB查询返回 {len(df)} 行")
                        return df
                except json.JSONDecodeError:
                    pass

                logger.debug(f"QuestDB原始返回: {content[:500]}...")

                try:
                    df = pd.read_json(content, orient='records')
                except Exception as parse_err:
                    logger.error(f"JSON解析失败: {parse_err}")
                    logger.error(f"原始内容: {content[:1000]}")
                    raise

                logger.debug(f"QuestDB查询返回 {len(df)} 行")
                return df
            else:
                raise Exception(f"QuestDB查询失败: HTTP {response.status_code}, {response.text}")
        except requests.exceptions.Timeout:
            raise Exception(f"QuestDB查询超时（超过{timeout}秒）: 查询数据量可能过大，请减少查询股票数量或分批查询")
        except requests.exceptions.RequestException as e:
            raise Exception(f"QuestDB连接失败: {e}")

    def execute(self, sql: str, timeout: int = 120) -> None:
        """
        执行SQL语句（用于INSERT等操作）

        Args:
            sql: SQL语句
            timeout: 超时时间（秒）

        Raises:
            Exception: 执行失败时抛出异常
        """
        auth = None
        if self.user:
            auth = (self.user, self.password)

        url = f"{self.base_url}/exec"
        data = sql.encode('utf-8')

        try:
            response = requests.post(url, data=data, auth=auth, timeout=timeout,
                                     headers={'Content-Type': 'text/plain'})

            if response.status_code != 200:
                raise Exception(f"QuestDB执行失败: HTTP {response.status_code}, {response.text}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"QuestDB连接失败: {e}")


def create_questdb_client() -> QuestDBClient:
    """
    创建QuestDB客户端实例（从配置文件读取）

    Returns:
        QuestDBClient: QuestDB客户端实例
    """
    questdb_config = config.get_questdb_config()
    return QuestDBClient(
        host=questdb_config['host'],
        port=questdb_config['port'],
        user=questdb_config['user'],
        password=questdb_config['password']
    )
