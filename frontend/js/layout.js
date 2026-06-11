// 布局偏好：auto | desktop | mobile（轻量，仅切换 #app.mobile-ui）

const STORAGE_KEY = 'avalon_layout_pref';
const MOBILE_MQ = window.matchMedia('(max-width: 768px)');
/** 与 .game-table::before 内框 inset(10px) 对齐，避免牌桌压线 */
const INNER_BORDER_INSET = 20;

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
        requestAnimationFrame(() => fitTableScale());
    } else {
        resetMobileTableScale();
        requestAnimationFrame(() => fitTableScale());
    }
}

function getGameTableInnerBounds(gameTable) {
    const style = getComputedStyle(gameTable);
    const padX = parseFloat(style.paddingLeft) + parseFloat(style.paddingRight);
    const padY = parseFloat(style.paddingTop) + parseFloat(style.paddingBottom);
    return {
        width: gameTable.clientWidth - padX - INNER_BORDER_INSET,
        height: gameTable.clientHeight - padY - INNER_BORDER_INSET,
    };
}

/**
 * 按 .game-table 内边框区域等比缩放牌桌（含玩家卡片）。
 * 电脑版：可放大（大屏）或缩小（小窗），始终保持在装饰边框内。
 * 手机版：仅缩小，原点靠上。
 */
export function fitTableScale() {
    const gameTable = document.querySelector('.game-table');
    const container = document.getElementById('playersContainer');
    if (!gameTable || !container) return;

    container.style.transform = 'none';
    container.style.marginBottom = '0';
    container.style.transformOrigin = '';

    const inner = getGameTableInnerBounds(gameTable);
    const neededW = container.offsetWidth;
    const neededH = container.offsetHeight;
    if (neededW <= 0 || neededH <= 0 || inner.width <= 0 || inner.height <= 0) return;

    let scale = Math.min(inner.width / neededW, inner.height / neededH);

    if (isMobileLayout()) {
        scale = Math.min(1, scale);
    } else {
        const MIN_DESKTOP_SCALE = 0.3;
        const MAX_DESKTOP_SCALE = 1.5;
        scale = Math.max(MIN_DESKTOP_SCALE, Math.min(MAX_DESKTOP_SCALE, scale));
    }

    if (Math.abs(scale - 1) < 0.005) {
        window.dispatchEvent(new CustomEvent('table-layout-fitted'));
        return;
    }

    if (isMobileLayout()) {
        container.style.transformOrigin = 'top center';
        container.style.transform = `scale(${scale})`;
        container.style.marginBottom = `${-(neededH * (1 - scale))}px`;
    } else {
        container.style.transformOrigin = 'center center';
        container.style.transform = `scale(${scale})`;
    }

    window.dispatchEvent(new CustomEvent('table-layout-fitted'));
}

/** @deprecated 使用 fitTableScale */
export function fitMobileTableScale() {
    fitTableScale();
}

export function resetMobileTableScale() {
    const container = document.getElementById('playersContainer');
    if (!container) return;
    container.style.transform = '';
    container.style.marginBottom = '';
    container.style.transformOrigin = '';
}

let resizeTimer = null;
window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => fitTableScale(), 150);
});

function syncMenuActiveState() {
    document.querySelectorAll('[data-layout-pref]').forEach((btn) => {
        btn.classList.toggle('is-active', btn.dataset.layoutPref === preference);
    });
}
