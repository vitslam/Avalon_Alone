from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import asyncio
from .game import AvalonGame
from .player import Player, AIPlayer, God
from .ai_controller import AIController

app = FastAPI(title="Avalon Alone API", version="1.0.0")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局游戏实例
game_instance = None
ai_controller = None
websocket_connections = []

# Pydantic模型
class PlayerConfig(BaseModel):
    name: str
    is_ai: bool = False
    ai_engine: Optional[str] = "gpt-3.5"

class TeamSelection(BaseModel):
    selected_players: List[str]

class Vote(BaseModel):
    player_name: str
    vote: str

class Assassination(BaseModel):
    target_name: str

class GameConfig(BaseModel):
    players: List[PlayerConfig]

@app.get("/")
async def root():
    """根路径"""
    return {"message": "Avalon Alone API", "version": "1.0.0"}

@app.post("/game/start")
async def start_game(config: GameConfig):
    """开始新游戏"""
    global game_instance, ai_controller
    
    if len(config.players) < 5 or len(config.players) > 10:
        raise HTTPException(status_code=400, detail="玩家数量必须在5-10人之间")
    
    # 创建玩家列表
    players = []
    for player_config in config.players:
        if player_config.is_ai:
            player = AIPlayer(player_config.name, player_config.ai_engine)
        else:
            player = Player(player_config.name)
        players.append(player)
    
    # 创建上帝和游戏实例
    god = God()
    game_instance = AvalonGame(players, god)
    
    # 创建AI控制器，传递WebSocket通知函数
    ai_controller = AIController(game_instance, notify_all_connections)
    
    # 开始游戏
    result = game_instance.start_game()
    
    # 通知所有WebSocket连接
    await notify_all_connections("game_started", result)
    
    # 如果全是AI玩家，启动自动游戏
    ai_players_count = sum(1 for p in players if p.is_ai)
    if ai_players_count == len(players):
        print("检测到全AI游戏，启动自动游戏模式")
        asyncio.create_task(start_auto_game())
    
    return result

async def start_auto_game():
    """启动自动游戏"""
    global ai_controller
    if ai_controller:
        await ai_controller.start_auto_play()

@app.get("/game/state")
async def get_game_state():
    """获取游戏状态"""
    if not game_instance:
        raise HTTPException(status_code=404, detail="游戏未开始")
    
    state = game_instance.get_game_state()
    
    # 添加AI控制器状态
    if ai_controller:
        state['ai_controller'] = ai_controller.get_ai_status()
    
    return state

@app.get("/game/mission-config")
async def get_mission_config():
    """获取当前任务配置"""
    if not game_instance:
        raise HTTPException(status_code=404, detail="游戏未开始")
    
    return game_instance.get_mission_config()

@app.get("/game/available-players")
async def get_available_players():
    """获取可选择的玩家列表"""
    if not game_instance:
        raise HTTPException(status_code=404, detail="游戏未开始")
    
    return {
        "available_players": game_instance.get_available_players(),
        "mission_players": game_instance.get_mission_players()
    }

@app.post("/game/select-team")
async def select_team(selection: TeamSelection):
    """选择任务队伍"""
    if not game_instance:
        raise HTTPException(status_code=404, detail="游戏未开始")
    
    result = game_instance.select_team(selection.selected_players)
    
    if 'error' in result:
        raise HTTPException(status_code=400, detail=result['error'])
    
    # 通知所有WebSocket连接
    await notify_all_connections("team_selected", result)
    
    return result

@app.post("/game/vote-team")
async def vote_team(vote: Vote):
    """队伍投票"""
    if not game_instance:
        raise HTTPException(status_code=404, detail="游戏未开始")
    
    result = game_instance.vote_team(vote.player_name, vote.vote)
    
    if 'error' in result:
        raise HTTPException(status_code=400, detail=result['error'])
    
    # 通知所有WebSocket连接
    await notify_all_connections("team_vote_recorded", result)
    
    return result

@app.post("/game/vote-mission")
async def vote_mission(vote: Vote):
    """任务投票"""
    if not game_instance:
        raise HTTPException(status_code=404, detail="游戏未开始")
    
    result = game_instance.vote_mission(vote.player_name, vote.vote)
    
    if 'error' in result:
        raise HTTPException(status_code=400, detail=result['error'])
    
    # 通知所有WebSocket连接
    await notify_all_connections("mission_vote_recorded", result)
    
    return result

@app.post("/game/assassinate")
async def assassinate(assassination: Assassination):
    """刺客刺杀"""
    if not game_instance:
        raise HTTPException(status_code=404, detail="游戏未开始")
    
    result = game_instance.assassinate(assassination.target_name)
    
    if 'error' in result:
        raise HTTPException(status_code=400, detail=result['error'])
    
    # 通知所有WebSocket连接
    await notify_all_connections("assassination_result", result)
    
    return result

@app.get("/game/roles")
async def get_roles():
    """获取角色信息"""
    from .constants import ROLES
    return {"roles": ROLES}

@app.get("/game/phases")
async def get_phases():
    """获取游戏阶段信息"""
    from .constants import GAME_PHASES
    return {"phases": GAME_PHASES}

@app.post("/game/reset")
async def reset_game():
    """重置游戏"""
    global game_instance, ai_controller
    
    # 停止AI控制器
    if ai_controller:
        ai_controller.stop_auto_play()
        ai_controller = None
    
    game_instance = None
    
    # 通知所有WebSocket连接
    await notify_all_connections("game_reset", {"status": "reset"})
    
    return {"status": "reset"}

@app.get("/game/ai-status")
async def get_ai_status():
    """获取AI控制器状态"""
    if not ai_controller:
        return {"is_running": False, "ai_players_count": 0}
    
    return ai_controller.get_ai_status()

@app.post("/game/ai-control")
async def control_ai(action: str):
    """控制AI控制器"""
    global ai_controller
    
    if action == "start" and ai_controller:
        asyncio.create_task(ai_controller.start_auto_play())
        return {"status": "ai_started"}
    elif action == "stop" and ai_controller:
        ai_controller.stop_auto_play()
        return {"status": "ai_stopped"}
    else:
        raise HTTPException(status_code=400, detail="无效的AI控制操作")

# WebSocket连接管理
async def notify_all_connections(event: str, data: Dict[str, Any]):
    """通知所有WebSocket连接"""
    message = {
        "event": event,
        "data": data,
        "timestamp": asyncio.get_event_loop().time()
    }
    
    for connection in websocket_connections:
        try:
            await connection.send_text(json.dumps(message))
        except:
            # 连接可能已断开，忽略错误
            pass

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点，用于实时游戏状态更新"""
    await websocket.accept()
    websocket_connections.append(websocket)
    
    try:
        # 发送当前游戏状态
        if game_instance:
            await websocket.send_text(json.dumps({
                "event": "current_state",
                "data": game_instance.get_game_state()
            }))
        
        # 保持连接直到客户端断开
        while True:
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        websocket_connections.remove(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)

# 健康检查
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy", 
        "game_active": game_instance is not None,
        "ai_controller_active": ai_controller is not None and ai_controller.is_running
    } 