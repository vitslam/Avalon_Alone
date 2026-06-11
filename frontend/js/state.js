// 共享可变状态
const state = {
    gameState: null,
    players: [],
    websocket: null,
    tts: null,
    API_BASE: `${window.location.protocol}//${window.location.host}`,
    teamVoteDisplay: null,
    speechGapMs: 300,
};

export default state;
