"""
阿瓦隆 Alone 配置文件
"""

import os
from typing import Dict, Any

# 服务器配置
SERVER_CONFIG = {
    'host': os.getenv('AVALON_HOST', '0.0.0.0'),
    'port': int(os.getenv('AVALON_PORT', 8000)),
    'debug': os.getenv('AVALON_DEBUG', 'true').lower() == 'true',
    'reload': os.getenv('AVALON_RELOAD', 'true').lower() == 'true'
}

# 游戏配置
GAME_CONFIG = {
    'min_players': 5,
    'max_players': 10,
    'default_ai_engine': 'gpt-3.5',
    'available_ai_engines': ['gpt-3.5', 'gpt-4', 'claude'],
    'max_failed_team_votes': 5,
    'missions_to_win': 3
}

# AI 配置
AI_CONFIG = {
    'gpt-3.5': {
        'name': 'GPT-3.5',
        'description': 'OpenAI GPT-3.5 模型',
        'api_key_env': 'OPENAI_API_KEY'
    },
    'gpt-4': {
        'name': 'GPT-4',
        'description': 'OpenAI GPT-4 模型',
        'api_key_env': 'OPENAI_API_KEY'
    },
    'claude': {
        'name': 'Claude',
        'description': 'Anthropic Claude 模型',
        'api_key_env': 'ANTHROPIC_API_KEY'
    }
}

# 前端配置
FRONTEND_CONFIG = {
    'websocket_url': os.getenv('AVALON_WS_URL', 'ws://localhost:8000/ws'),
    'api_base_url': os.getenv('AVALON_API_URL', 'http://localhost:8000'),
    'auto_reconnect': True,
    'reconnect_interval': 5000  # 毫秒
}

# 日志配置
LOGGING_CONFIG = {
    'level': os.getenv('AVALON_LOG_LEVEL', 'INFO'),
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': os.getenv('AVALON_LOG_FILE', 'avalon.log')
}

# 安全配置
SECURITY_CONFIG = {
    'cors_origins': ['*'],  # 生产环境应该限制具体域名
    'cors_credentials': True,
    'cors_methods': ['*'],
    'cors_headers': ['*']
}

def get_config() -> Dict[str, Any]:
    """获取完整配置"""
    return {
        'server': SERVER_CONFIG,
        'game': GAME_CONFIG,
        'ai': AI_CONFIG,
        'frontend': FRONTEND_CONFIG,
        'logging': LOGGING_CONFIG,
        'security': SECURITY_CONFIG
    }

def validate_config() -> bool:
    """验证配置"""
    try:
        # 验证服务器配置
        assert SERVER_CONFIG['port'] > 0 and SERVER_CONFIG['port'] < 65536
        
        # 验证游戏配置
        assert GAME_CONFIG['min_players'] <= GAME_CONFIG['max_players']
        assert GAME_CONFIG['missions_to_win'] > 0
        
        # 验证 AI 配置
        for engine in GAME_CONFIG['available_ai_engines']:
            assert engine in AI_CONFIG
        
        return True
    except AssertionError:
        return False

if __name__ == "__main__":
    # 打印配置信息
    config = get_config()
    print("阿瓦隆 Alone 配置:")
    for section, settings in config.items():
        print(f"\n[{section.upper()}]")
        for key, value in settings.items():
            print(f"  {key}: {value}")
    
    # 验证配置
    if validate_config():
        print("\n✅ 配置验证通过")
    else:
        print("\n❌ 配置验证失败") 