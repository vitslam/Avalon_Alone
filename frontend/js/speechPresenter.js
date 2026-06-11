// 发言展示队列：气泡、呼吸灯与 TTS 同步，避免后端预取导致 UI 抢跑
import state from './state.js';
import { whenTtsReady, unlockSpeechAudio } from './voice.js';
import {
    updateCurrentSpeaker,
    showPlayerSpeaking,
    showCurrentSpeakerIndicator,
    hideSpeechPresentation,
} from './table.js';

const queue = [];
let presenting = false;
let currentSpeaker = null;
let advanceTimer = null;

function estimateSpeechDurationMs(message) {
    if (!message) return 2000;
    const seconds = 0.8 + message.length * 0.18;
    return Math.max(2.0, seconds) * 1000;
}

function shouldPlayTts(isAi) {
    if (!isAi || !state.tts) return false;
    const status = state.tts.getStatus();
    return status.supported && status.enabled;
}

function finishCurrentSpeech(onDone) {
    setTimeout(() => {
        presenting = false;
        onDone();
    }, state.speechGapMs);
}

function processNext() {
    if (presenting || queue.length === 0) return;

    presenting = true;
    const { speaker, message, is_ai } = queue.shift();
    currentSpeaker = speaker;

    showCurrentSpeakerIndicator(speaker);
    updateCurrentSpeaker(speaker);
    showPlayerSpeaking(speaker, message);

    const durationMs = estimateSpeechDurationMs(message);

    const advance = () => {
        if (advanceTimer) {
            clearTimeout(advanceTimer);
            advanceTimer = null;
        }
        // 仅收起气泡/推进展示队列，不 stop TTS——语音由 tts.js 内部队列串行播完
        hideSpeechPresentation(speaker);
        currentSpeaker = null;
        finishCurrentSpeech(processNext);
    };

    whenTtsReady.then(() => {
        unlockSpeechAudio();

        // 气泡节奏与后端 ai_speak 估算时长对齐；TTS 独立播放，不阻塞队列（避免 iOS onend 卡死）
        if (shouldPlayTts(is_ai)) {
            state.tts.speak(message, speaker);
        }

        advanceTimer = setTimeout(advance, durationMs);
    });
}

export function enqueuePlayerSpeech(speakingData) {
    queue.push(speakingData);
    processNext();
}

export function clearSpeechQueue() {
    queue.length = 0;
    presenting = false;
    if (advanceTimer) {
        clearTimeout(advanceTimer);
        advanceTimer = null;
    }
    if (currentSpeaker) {
        hideSpeechPresentation(currentSpeaker);
        currentSpeaker = null;
    }
    if (state.tts) {
        state.tts.stop();
    }
}

/** Safari 切后台时 TTS 可能永不触发 onend，仅解除 presenting 锁，保留队列待回前台续播 */
export function pauseForBackground() {
    if (advanceTimer) {
        clearTimeout(advanceTimer);
        advanceTimer = null;
    }
    if (state.tts) {
        state.tts.stop();
    }

    if (!presenting) {
        return;
    }

    if (currentSpeaker) {
        hideSpeechPresentation(currentSpeaker);
        currentSpeaker = null;
    }

    presenting = false;
}

export function resumeSpeechQueue() {
    processNext();
}
