// 共享可变状态
const state = {
    gameState: null,
    players: [],
    selectedPlayers: [],
    websocket: null,
    currentPlayer: null,
    tts: null,
    API_BASE: 'http://localhost:8234'
};

export default state;
