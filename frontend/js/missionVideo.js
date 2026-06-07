import { MISSION_VIDEOS, DEFAULT_VIDEO, VIDEO_BASE_PATH } from './videoManifest.js';

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

    return { filename: DEFAULT_VIDEO, matchLevel: 'default' };
}

function hideOverlay() {
    const overlay = document.getElementById('missionVideoOverlay');
    const video = document.getElementById('missionVideo');
    if (!overlay || !video) return;

    video.pause();
    video.removeAttribute('src');
    video.load();
    overlay.style.display = 'none';
}

export function stopMissionVideo() {
    lastPlayedMission = null;
    hideOverlay();
}

export function playMissionVideo(teamNames, players, missionNumber) {
    if (!teamNames?.length || !players?.length) return;
    if (lastPlayedMission === missionNumber) return;

    const overlay = document.getElementById('missionVideoOverlay');
    const video = document.getElementById('missionVideo');
    if (!overlay || !video) return;

    const { filename, matchLevel } = resolveMissionVideo(teamNames, players);
    console.log(`任务过场视频 [${matchLevel}]: ${filename}`);

    lastPlayedMission = missionNumber;

    let usedFallback = false;

    const tryPlay = (name, withSound = true) => {
        video.src = `${VIDEO_BASE_PATH}/${name}`;
        overlay.style.display = 'flex';
        video.muted = !withSound;
        video.volume = 1;

        const playPromise = video.play();
        if (!playPromise || typeof playPromise.catch !== 'function') return;

        playPromise.catch(err => {
            if (withSound) {
                console.warn('有声自动播放被拦截，降级为静音:', err.message);
                tryPlay(name, false);
                return;
            }
            console.warn('视频播放失败:', err);
            hideOverlay();
        });
    };

    video.onended = hideOverlay;
    video.onerror = () => {
        if (!usedFallback && filename !== DEFAULT_VIDEO) {
            usedFallback = true;
            console.warn(`视频加载失败，使用默认: ${filename}`);
            tryPlay(DEFAULT_VIDEO);
        } else {
            hideOverlay();
        }
    };

    tryPlay(filename);
}
