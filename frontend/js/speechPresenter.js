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

    const advance = () => {
        hideSpeechPresentation(speaker);
        currentSpeaker = null;
        finishCurrentSpeech(processNext);
    };

    let advanced = false;
    const advanceOnce = () => {
        if (advanced) return;
        advanced = true;
        if (advanceTimer) {
            clearTimeout(advanceTimer);
            advanceTimer = null;
        }
        advance();
    };

    whenTtsReady.then(() => {
        unlockSpeechAudio();

        if (shouldPlayTts(is_ai)) {
            // 气泡随 TTS 播完再消失；估算时长×2 作 iOS onend 不可靠时的兜底
            const fallbackMs = estimateSpeechDurationMs(message) * 2;
            advanceTimer = setTimeout(advanceOnce, fallbackMs);
            state.tts.speak(message, speaker, advanceOnce);
        } else {
            advanceTimer = setTimeout(advanceOnce, estimateSpeechDurationMs(message));
        }
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
