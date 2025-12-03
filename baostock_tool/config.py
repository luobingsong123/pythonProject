import configparser
import os


config_path = os.path.join("./config/config.ini")
if not os.path.exists(config_path):
    raise FileNotFoundError(f"配置文件 {config_path} 未找到！")
config = configparser.ConfigParser()
config.read(config_path, encoding="utf-8")

def get_db_config():
    return {
        "host": config.get("database", "host"),
        "port": config.getint("database", "port"),
        "user": config.get("database", "username"),
        "password": config.get("database", "password"),
        "database": config.get("database", "database"),
        "charset": "utf8mb4"
    }

def get_log_config():
    return {
            "log_level": config.get("logging", "level"),
            "log_dir": config.get("logging", "log_dir"),
    }

def get_web_config():
    return {
        "host": config.get("webserver", "host"),
        "port": config.get("webserver", "port"),
    }


if __name__ == "__main__":
    print(get_db_config())
    print(get_log_config())
    print(get_web_config())