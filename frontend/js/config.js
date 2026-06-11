// 从后端加载可由 .env 配置的客户端参数
import state from './state.js';

export async function loadClientConfig() {
    try {
        const response = await fetch(`${state.API_BASE}/client-config`);
        if (!response.ok) return;

        const config = await response.json();
        if (config.speech_gap_ms != null) {
            state.speechGapMs = config.speech_gap_ms;
            window.__avalonSpeechGapMs = config.speech_gap_ms;
        }
    } catch (error) {
        console.warn('加载客户端配置失败，使用默认值', error);
    }
}
