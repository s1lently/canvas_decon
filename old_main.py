import getCookie
import json

def main():
    """
    主执行函数：
    - 从 account_info.json 读取凭据和密钥数据
    - 调用getCookie模块来获取登录cookies
    - 将获取到的cookies打印到控制台
    """
    print("正在读取配置文件...")
    with open('account_info.json', 'r') as f:
        config = json.load(f)
    
    account = config['account']
    password = config['password']
    otp_keys_data = config['otp_keys'] # Read the key data directly

    print("正在开始获取Cookie...")
    cookies = getCookie.get_cookies(account, password, otp_keys_data)
    
    if cookies:
        print("\n成功获取Cookies:")
        print(json.dumps(cookies, indent=4))
        
        with open('cookies.json', 'w') as f:
            json.dump(cookies, f, indent=4)
        print("\nCookies也已保存到 cookies.json")
    else:
        print("\n获取Cookie失败。请查看上面的错误日志。")

if __name__ == "__main__":
    main()
