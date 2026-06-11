// 布局偏好：auto | desktop | mobile（轻量，仅切换 #app.mobile-ui）

const STORAGE_KEY = 'avalon_layout_pref';
const MOBILE_MQ = window.matchMedia('(max-width: 768px)');

let preference = 'auto';
const changeListeners = [];

export function initLayout() {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === 'auto' || saved === 'desktop' || saved === 'mobile') {
        preference = saved;
    }
    MOBILE_MQ.addEventListener('change', applyLayout);
    applyLayout();
}

export function getLayoutPreference() {
    return preference;
}

export function isMobileLayout() {
    if (preference === 'mobile') return true;
    if (preference === 'desktop') return false;
    return MOBILE_MQ.matches;
}

export function setLayoutPreference(pref) {
    if (pref !== 'auto' && pref !== 'desktop' && pref !== 'mobile') return;
    preference = pref;
    localStorage.setItem(STORAGE_KEY, pref);
    applyLayout();
}

export function onLayoutChange(listener) {
    changeListeners.push(listener);
}

export function bindLayoutMenu() {
    document.querySelectorAll('[data-layout-pref]').forEach((btn) => {
        btn.addEventListener('click', () => {
            setLayoutPreference(btn.dataset.layoutPref);
        });
    });
    syncMenuActiveState();
}

function applyLayout() {
    const app = document.getElementById('app');
    if (!app) return;

    const mobile = isMobileLayout();
    app.classList.toggle('mobile-ui', mobile);
    app.dataset.layoutPref = preference;
    syncMenuActiveState();
    changeListeners.forEach((fn) => fn(mobile));

    if (mobile) {
        requestAnimationFrame(() => fitMobileTableScale());
    } else {
        resetMobileTableScale();
    }
}

/** 按 game-table 可用高度等比缩小牌桌区域，避免上下溢出屏幕 */
export function fitMobileTableScale() {
    if (!isMobileLayout()) {
        resetMobileTableScale();
        return;
    }

    const gameTable = document.querySelector('.game-table');
    const container = document.getElementById('playersContainer');
    if (!gameTable || !container) return;

    container.style.transform = 'none';
    container.style.marginBottom = '0';

    const available = gameTable.clientHeight - 12;
    const needed = container.offsetHeight;
    if (available <= 0 || needed <= 0) return;

    const scale = Math.min(1, available / needed);
    if (scale >= 0.995) return;

    container.style.transformOrigin = 'top center';
    container.style.transform = `scale(${scale})`;
    container.style.marginBottom = `${-(needed * (1 - scale))}px`;
}

export function resetMobileTableScale() {
    const container = document.getElementById('playersContainer');
    if (!container) return;
    container.style.transform = '';
    container.style.marginBottom = '';
}

let resizeTimer = null;
window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => fitMobileTableScale(), 150);
});

function syncMenuActiveState() {
    document.querySelectorAll('[data-layout-pref]').forEach((btn) => {
        btn.classList.toggle('is-active', btn.dataset.layoutPref === preference);
    });
}
