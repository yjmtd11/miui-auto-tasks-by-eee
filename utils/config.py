"""配置文件"""
import os
import platform
from hashlib import md5
from json import JSONDecodeError
from pathlib import Path
from typing import Dict, List, Optional, Union

import orjson
import yaml  # pylint: disable=wrong-import-order
from pydantic import BaseModel, ValidationError, field_validator  # pylint: disable=no-name-in-module

from .logger import log

ROOT_PATH = Path(__file__).parent.parent.absolute()

DATA_PATH = ROOT_PATH / "data"
"""数据保存目录"""

CONFIG_TYPE = "json" if os.path.isfile(DATA_PATH / "config.json") else "yaml"
"""数据文件类型"""

CONFIG_PATH = DATA_PATH / f"config.{CONFIG_TYPE}" if os.getenv("MIUITASK_CONFIG_PATH") is None else Path(
    os.getenv("MIUITASK_CONFIG_PATH"))
"""数据文件默认路径"""

os.makedirs(DATA_PATH, exist_ok=True)


def md5_crypto(passwd: str) -> str:
    """MD5加密"""
    return md5(passwd.encode('utf8')).hexdigest().upper()


def cookies_to_dict(cookies: str):
    """将cookies字符串转换为字典"""
    cookies_dict = {}
    if not cookies or "=" not in cookies:
        return cookies_dict
    for cookie in cookies.split(';'):
        key, value = cookie.strip().split('=', 1)
        cookies_dict[key] = value
    return cookies_dict


def get_platform() -> str:
    """获取当前运行平台"""
    if os.path.exists('/.dockerenv'):
        if os.environ.get('QL_DIR') and os.environ.get('QL_BRANCH'):
            return "qinglong"
        return "docker"
    return platform.system().lower()


class Account(BaseModel):
    """账号处理器"""
    uid: str = "100000"
    password: str = ""
    cookies: Union[dict, str] = {}
    login_user_agent: str = ""
    user_agent: str = 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/116.0.0.0 Safari/537.36'
    device: str = ""
    device_model: str = ""
    CheckIn: bool = False
    BrowseUserPage: bool = False
    BrowsePost: bool = False
    BrowseVideoPost: bool = False
    ThumbUp: bool = False
    BrowseSpecialPage: bool = False
    BoardFollow: bool = False
    CarrotPull: bool = False
    WxSign: bool = False

    @field_validator("password")
    @classmethod
    def _password(cls, value: Optional[str]):
        if len(value) == 32:
            return value
        return md5_crypto(value)

    @field_validator("cookies")
    @classmethod
    def _cookies(cls, value: Union[dict, str]):
        if isinstance(value, str):
            return cookies_to_dict(value)
        return value


class OnePush(BaseModel):
    """推送配置"""
    notifier: Union[str, bool] = ""
    params: Dict = {
        "title": "",
        "markdown": False,
        "token": "",
        "userid": ""
    }


class Ttocr(BaseModel):
    """ttorc参数设置"""
    app_key: str = ""
    createTask_url: str = ""
    createTask_data: Dict = {}
    getTaskResult_url: str = ""


class Preference(BaseModel):
    """偏好设置"""
    geetest_url: str = ""
    geetest_params: Dict = {}
    geetest_data: Dict = {}
    twocaptcha_api_key: str = ""
    twocaptcha_userAgent: str = ""
    ttocr: Ttocr = Ttocr()


class Config(BaseModel):
    """插件数据"""
    preference: Preference = Preference()
    accounts: List[Account] = [Account()]
    ONEPUSH: OnePush = OnePush()


class ConfigManager:
    """配置管理器"""
    data_obj = Config()
    platform = get_platform()

    @classmethod
    def load_config(cls):
        """加载插件数据文件"""
        if os.path.exists(DATA_PATH) and os.path.isfile(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, 'r', encoding="utf-8") as file:
                    if CONFIG_TYPE == "json":
                        data = orjson.loads(file.read())
                    else:
                        data = yaml.safe_load(file)
                new_model = Config.model_validate(data)
                for attr in new_model.model_fields:
                    setattr(cls.data_obj, attr, getattr(new_model, attr))
                cls.write_plugin_data()  # 同步配置
            except (ValidationError, JSONDecodeError):
                log.exception(f"读取数据文件失败，请检查数据文件 {CONFIG_PATH} 格式是否正确")
                raise
            except Exception:
                log.exception(f"读取数据文件失败，请检查数据文件 {CONFIG_PATH} 是否存在且有权限读写")
                raise
        else:
            try:
                os.makedirs(DATA_PATH, exist_ok=True)
                cls.write_plugin_data()
            except (AttributeError, TypeError, ValueError, PermissionError):
                log.exception(f"创建数据文件失败，请检查是否有权限读写 {CONFIG_PATH}")
                raise
            log.info(f"数据文件 {CONFIG_PATH} 不存在，已创建默认数据文件。")

    @classmethod
    def write_plugin_data(cls, data: Config = None):
        """
        写入插件数据文件
        :param data: 配置对象，默认为当前配置
        """
        try:
            write_data = data if data else cls.data_obj
            if CONFIG_TYPE == "json":
                str_data = orjson.dumps(
                    write_data.model_dump(),
                    option=orjson.OPT_PASSTHROUGH_DATETIME | orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_INDENT_2
                )
                with open(CONFIG_PATH, "wb") as file:
                    file.write(str_data)
            else:
                str_data = yaml.dump(
                    write_data.model_dump(),
                    indent=4,
                    allow_unicode=True,
                    sort_keys=False
                )
                with open(CONFIG_PATH, "w", encoding="utf-8") as file:
                    file.write(str_data)
            return True
        except (AttributeError, TypeError, ValueError, OSError) as e:
            log.exception(f"数据写入失败: {str(e)}")
            return False


ConfigManager.load_config()