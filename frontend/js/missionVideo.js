import {
    MISSION_VIDEOS,
    DEFAULT_VIDEO,
    SUCCESS_VIDEO,
    FAIL_VIDEO,
    ASSASSIN_SUCCESS_VIDEO,
    ASSASSIN_FAILED_VIDEO,
    VIDEO_BASE_PATH,
} from './videoManifest.js';

const ROLE_TO_TOKEN = {
    merlin: 'Merlin',
    percival: 'Percival',
    loyal_servant: 'Loyal',
    morgana: 'Morcana',
    assassin: 'Assassin',
    minion: 'Minion',
    mordred: 'Mordred',
    oberon: 'Oberon',
};

const CANONICAL_ORDER = ['Merlin', 'Percival', 'Loyal', 'Morcana', 'Assassin', 'Minion', 'Mordred', 'Oberon'];

const GOOD_TOKENS = new Set(['Merlin', 'Percival', 'Loyal']);
const EVIL_TOKENS = new Set(['Morcana', 'Assassin', 'Minion', 'Mordred', 'Oberon']);
const ALL_TOKENS = new Set([...GOOD_TOKENS, ...EVIL_TOKENS]);

let lastPlayedMission = null;

// 按任务轮次缓存结果，避免投票早于过场视频完成时被 playMissionVideo 重置丢失
const pendingMissionResults = new Map();
let missionResult = undefined;
let executionEnded = false;
let resultPlaying = false;
let waitingPollTimer = null;

function teamToTokens(teamNames, players) {
    const roles = teamNames
        .map(name => players.find(p => p.name === name)?.role)
        .filter(Boolean);

    const tokenCounts = {};
    for (const role of roles) {
        const token = ROLE_TO_TOKEN[role];
        if (token) {
            tokenCounts[token] = (tokenCounts[token] || 0) + 1;
        }
    }

    const tokens = [];
    for (const token of CANONICAL_ORDER) {
        const count = tokenCounts[token] || 0;
        for (let i = 0; i < count; i++) {
            tokens.push(token);
        }
    }
    return tokens;
}

function parseVideoTokens(filename) {
    const base = filename.replace(/\.mp4$/, '');
    return base.split('_').filter(part => ALL_TOKENS.has(part));
}

function countSides(tokens) {
    return {
        total: tokens.length,
        good: tokens.filter(t => GOOD_TOKENS.has(t)).length,
        evil: tokens.filter(t => EVIL_TOKENS.has(t)).length,
    };
}

function countMultiset(tokens) {
    const counts = {};
    for (const token of tokens) {
        counts[token] = (counts[token] || 0) + 1;
    }
    return counts;
}

function multisetOverlap(a, b) {
    const countsA = countMultiset(a);
    const countsB = countMultiset(b);
    let overlap = 0;
    for (const [token, count] of Object.entries(countsB)) {
        overlap += Math.min(count, countsA[token] || 0);
    }
    return overlap;
}

function pickBestCandidate(candidates, teamTokens) {
    let best = [];
    let bestOverlap = -1;

    for (const filename of candidates) {
        const videoTokens = parseVideoTokens(filename);
        const overlap = multisetOverlap(teamTokens, videoTokens);
        if (overlap > bestOverlap) {
            bestOverlap = overlap;
            best = [filename];
        } else if (overlap === bestOverlap) {
            best.push(filename);
        }
    }

    return best[Math.floor(Math.random() * best.length)];
}

export function resolveMissionVideo(teamNames, players) {
    const teamTokens = teamToTokens(teamNames, players);
    const teamSides = countSides(teamTokens);
    const exactName = teamTokens.join('_') + '.mp4';

    if (MISSION_VIDEOS.includes(exactName)) {
        return { filename: exactName, matchLevel: 'exact' };
    }

    const structuralCandidates = MISSION_VIDEOS.filter(filename => {
        const sides = countSides(parseVideoTokens(filename));
        return sides.total === teamSides.total
            && sides.good === teamSides.good
            && sides.evil === teamSides.evil;
    });

    if (structuralCandidates.length > 0) {
        return {
            filename: pickBestCandidate(structuralCandidates, teamTokens),
            matchLevel: 'structural',
        };
    }

    const countCandidates = MISSION_VIDEOS.filter(filename => {
        return parseVideoTokens(filename).length === teamSides.total;
    });

    if (countCandidates.length > 0) {
        return {
            filename: countCandidates[Math.floor(Math.random() * countCandidates.length)],
            matchLevel: 'count',
        };
    }

    return { filename: DEFAULT_VIDEO, matchLevel: 'default' };
}

function clearWaitingPoll() {
    if (waitingPollTimer) {
        clearInterval(waitingPollTimer);
        waitingPollTimer = null;
    }
}

function showWaiting() {
    const waiting = document.getElementById('missionVideoWaiting');
    const video = document.getElementById('missionVideo');
    const overlay = document.getElementById('missionVideoOverlay');
    if (overlay) overlay.style.display = 'flex';
    if (video) video.style.display = 'none';
    if (waiting) waiting.style.display = 'flex';
    startWaitingFallback();
}

function hideWaiting() {
    clearWaitingPoll();
    const waiting = document.getElementById('missionVideoWaiting');
    const video = document.getElementById('missionVideo');
    if (waiting) waiting.style.display = 'none';
    if (video) video.style.display = '';
}

function hideOverlay() {
    const overlay = document.getElementById('missionVideoOverlay');
    const video = document.getElementById('missionVideo');
    if (!overlay || !video) return;

    clearWaitingPoll();
    video.pause();
    video.removeAttribute('src');
    video.load();
    video.style.display = '';
    hideWaiting();
    overlay.style.display = 'none';
}

function tryAdvanceMissionVideoFlow() {
    if (resultPlaying || lastPlayedMission == null) return;

    if (missionResult === undefined) {
        const pending = pendingMissionResults.get(lastPlayedMission);
        if (pending !== undefined) {
            missionResult = pending;
        }
    }

    if (executionEnded && missionResult !== undefined) {
        playResultVideo();
    }
}

async function pollMissionResultFromState() {
    if (missionResult !== undefined || lastPlayedMission == null) return;

    const pending = pendingMissionResults.get(lastPlayedMission);
    if (pending !== undefined) {
        setMissionResult(pending, lastPlayedMission);
        return;
    }

    try {
        const { fetchCurrentGameState } = await import('./websocket.js');
        await fetchCurrentGameState();
        const state = (await import('./state.js')).default;
        const match = state.gameState?.mission_results?.find(
            (result) => result.mission === lastPlayedMission,
        );
        if (match && typeof match.success === 'boolean') {
            setMissionResult(match.success, lastPlayedMission);
        }
    } catch (err) {
        console.warn('轮询任务结果失败:', err);
    }
}

function startWaitingFallback() {
    if (waitingPollTimer || missionResult !== undefined) return;

    let attempts = 0;
    waitingPollTimer = setInterval(async () => {
        if (missionResult !== undefined || !executionEnded) {
            clearWaitingPoll();
            return;
        }

        attempts += 1;
        await pollMissionResultFromState();

        if (missionResult !== undefined) {
            clearWaitingPoll();
            return;
        }

        if (attempts >= 30) {
            console.warn('任务结果等待超时，关闭过场层');
            clearWaitingPoll();
            hideOverlay();
        }
    }, 500);
}

export function stopMissionVideo() {
    lastPlayedMission = null;
    missionResult = undefined;
    executionEnded = false;
    resultPlaying = false;
    pendingMissionResults.clear();
    clearWaitingPoll();
    hideOverlay();
}

function playFile(name, onEnded, allowFallback = false) {
    const overlay = document.getElementById('missionVideoOverlay');
    const video = document.getElementById('missionVideo');
    if (!overlay || !video) return;

    hideWaiting();
    let usedFallback = false;

    const tryPlay = (file, withSound = true) => {
        video.src = `${VIDEO_BASE_PATH}/${file}`;
        overlay.style.display = 'flex';
        video.muted = !withSound;
        video.volume = 1;

        const playPromise = video.play();
        if (!playPromise || typeof playPromise.catch !== 'function') return;

        playPromise.catch(err => {
            if (withSound) {
                console.warn('有声自动播放被拦截，降级为静音:', err.message);
                tryPlay(file, false);
                return;
            }
            console.warn('视频播放失败:', err);
            if (onEnded) onEnded();
        });
    };

    video.onended = onEnded;
    video.onerror = () => {
        if (allowFallback && !usedFallback && name !== DEFAULT_VIDEO) {
            usedFallback = true;
            console.warn(`视频加载失败，使用默认: ${name}`);
            tryPlay(DEFAULT_VIDEO);
        } else if (onEnded) {
            onEnded();
        }
    };

    tryPlay(name);
}

function playResultVideo() {
    if (resultPlaying || missionResult === undefined) return;
    resultPlaying = true;
    clearWaitingPoll();
    const file = missionResult ? SUCCESS_VIDEO : FAIL_VIDEO;
    const missionNumber = lastPlayedMission;
    console.log(`任务结果视频: ${file}`);
    playFile(file, () => {
        if (missionNumber != null) {
            pendingMissionResults.delete(missionNumber);
        }
        hideOverlay();
    });
}

function onExecutionEnded() {
    executionEnded = true;
    tryAdvanceMissionVideoFlow();
    if (missionResult === undefined) {
        showWaiting();
    }
}

export function setMissionResult(success, missionNumber) {
    if (missionNumber == null) {
        console.warn('setMissionResult: 缺少 mission_number，忽略');
        return;
    }

    pendingMissionResults.set(missionNumber, success);
    tryAdvanceMissionVideoFlow();
}

export function playAssassinationVideo(assassinSucceeded, onEnded) {
    const file = assassinSucceeded ? ASSASSIN_SUCCESS_VIDEO : ASSASSIN_FAILED_VIDEO;
    console.log(`刺杀结果视频: ${file}`);
    playFile(file, () => {
        hideOverlay();
        if (onEnded) onEnded();
    });
}

export function playMissionVideo(teamNames, players, missionNumber) {
    if (!teamNames?.length || !players?.length || missionNumber == null) return;
    if (lastPlayedMission === missionNumber && executionEnded && missionResult === undefined) {
        tryAdvanceMissionVideoFlow();
        return;
    }
    if (lastPlayedMission === missionNumber && !executionEnded) return;

    const overlay = document.getElementById('missionVideoOverlay');
    const video = document.getElementById('missionVideo');
    if (!overlay || !video) return;

    const { filename, matchLevel } = resolveMissionVideo(teamNames, players);
    console.log(`任务过场视频 [${matchLevel}]: ${filename} (第${missionNumber}轮)`);

    lastPlayedMission = missionNumber;
    missionResult = undefined;
    executionEnded = false;
    resultPlaying = false;
    clearWaitingPoll();

    playFile(filename, onExecutionEnded, true);
    tryAdvanceMissionVideoFlow();
}
