#!/usr/bin/env python3
"""
测试重构后的项目结构
"""
import sys
import os

def test_config():
    """测试 config 模块"""
    print("Testing config module...")
    import config
    assert hasattr(config, 'COOKIES_FILE')
    assert hasattr(config, 'ACCOUNT_INFO_FILE')
    assert hasattr(config, 'GEMINI_API_KEY')
    assert hasattr(config, 'CANVAS_BASE_URL')
    assert config.ROOT_DIR.endswith('niubiaaaa')
    print("✓ Config module OK")

def test_login_module():
    """测试 login 模块"""
    print("\nTesting login module...")
    from login import getCookie, getTotp
    assert hasattr(getCookie, 'get_cookies')
    assert hasattr(getTotp, 'generate_token')
    print("✓ Login module OK")

def test_func_modules():
    """测试 func 模块"""
    print("\nTesting func modules...")
    modules = [
        'getCourses', 'getHomework', 'getQuiz',
        'getAss', 'getSyll', 'getHTML', 'html2md',
        'getAPI', 'gCO', 'stQz'
    ]

    for module_name in modules:
        try:
            exec(f"from func import {module_name}")
            print(f"  ✓ {module_name}")
        except ImportError as e:
            print(f"  ✗ {module_name}: {e}")
            return False

    print("✓ All func modules OK")
    return True

def test_paths():
    """测试路径配置"""
    print("\nTesting path configurations...")
    import config
    from func import getHomework, getQuiz

    # Check getHomework paths
    assert getHomework.COOKIES_FILE == config.COOKIES_FILE
    assert getHomework.OUTPUT_DIR == config.OUTPUT_DIR
    assert getHomework.GEMINI_API_KEY == config.GEMINI_API_KEY
    print("  ✓ getHomework paths")

    # Check getQuiz paths
    assert getQuiz.COOKIES_FILE == config.COOKIES_FILE
    assert getQuiz.GEMINI_API_KEY == config.GEMINI_API_KEY
    print("  ✓ getQuiz paths")

    print("✓ Path configurations OK")

def main():
    print("=" * 50)
    print("项目结构测试")
    print("=" * 50)

    try:
        test_config()
        test_login_module()
        test_func_modules()
        test_paths()

        print("\n" + "=" * 50)
        print("✓ 所有测试通过!")
        print("=" * 50)
        return 0
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
