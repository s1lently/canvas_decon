"""
主入口文件：获取 Canvas 登录 Cookie
用法：python main.py
"""
from login import getCookie
import json
import config

def main():
    """
    主执行函数：
    - 从 account_info.json 读取凭据和密钥数据
    - 调用getCookie模块来获取登录cookies
    - 将获取到的cookies打印到控制台并保存
    """
    print("正在读取配置文件...")
    with open(config.ACCOUNT_INFO_FILE, 'r') as f:
        cfg = json.load(f)

    account = cfg['account']
    password = cfg['password']
    otp_keys_data = cfg['otp_keys']

    print("正在开始获取Cookie...")
    cookies = getCookie.get_cookies(account, password, otp_keys_data)

    if cookies:
        print("\n成功获取Cookies:")
        print(json.dumps(cookies, indent=4))

        with open(config.COOKIES_FILE, 'w') as f:
            json.dump(cookies, f, indent=4)
        print(f"\nCookies已保存到 {config.COOKIES_FILE}")
    else:
        print("\n获取Cookie失败。请查看上面的错误日志。")

if __name__ == "__main__":
    main()
