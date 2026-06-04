// 语音/TTS 功能
import state from './state.js';

export async function loadTTSModule() {
    try {
        const module = await import('../tts.js');
        state.tts = module.tts;
        console.log('语音合成模块已加载');

        if (state.players.length > 0) {
            setTimeout(() => {
                preconfigureAIVoices();
            }, 1000);
        }
    } catch (error) {
        console.error('加载语音合成模块失败:', error);
    }
}

export function preconfigureAIVoices() {
    if (!state.tts || !state.players || state.players.length === 0) return;

    const aiPlayers = state.players.filter(p => p.is_ai);
    if (aiPlayers.length > 0) {
        state.tts.preconfigureAIVoices(aiPlayers);
        console.log(`已预配置 ${aiPlayers.length} 个AI玩家的语音`);
    }
}

export function initializeVoiceControl() {
    if (!('speechSynthesis' in window)) {
        console.warn('浏览器不支持语音合成，无法使用语音功能');
        return;
    }

    const controlPanel = document.createElement('div');
    controlPanel.id = 'voiceControlPanel';
    controlPanel.className = 'voice-control-panel';
    controlPanel.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: rgba(0, 0, 0, 0.7);
        color: white;
        padding: 15px;
        border-radius: 10px;
        z-index: 1000;
        display: flex;
        flex-direction: column;
        gap: 10px;
        max-width: 300px;
    `;

    const title = document.createElement('h3');
    title.textContent = '语音设置';
    title.style.margin = '0 0 10px 0';
    title.style.fontSize = '16px';
    controlPanel.appendChild(title);

    const enableContainer = document.createElement('div');
    enableContainer.style.display = 'flex';
    enableContainer.style.alignItems = 'center';
    enableContainer.style.justifyContent = 'space-between';

    const enableLabel = document.createElement('label');
    enableLabel.textContent = '启用AI语音';
    enableContainer.appendChild(enableLabel);

    const enableSwitch = document.createElement('input');
    enableSwitch.type = 'checkbox';
    enableSwitch.id = 'voiceEnableSwitch';
    enableSwitch.checked = true;
    enableContainer.appendChild(enableSwitch);

    controlPanel.appendChild(enableContainer);

    const globalParamsContainer = document.createElement('div');
    globalParamsContainer.className = 'global-params';

    const params = [
        { id: 'voiceRateControl', label: '语速', min: '0.5', max: '2', step: '0.1', value: '1', valueId: 'voiceRateValue' },
        { id: 'voicePitchControl', label: '音调', min: '0.5', max: '2', step: '0.1', value: '1', valueId: 'voicePitchValue' },
        { id: 'voiceVolumeControl', label: '音量', min: '0', max: '1', step: '0.1', value: '1', valueId: 'voiceVolumeValue' }
    ];

    params.forEach(param => {
        const container = document.createElement('div');
        container.style.display = 'flex';
        container.style.alignItems = 'center';
        container.style.justifyContent = 'space-between';

        const label = document.createElement('label');
        label.textContent = param.label;
        label.htmlFor = param.id;
        container.appendChild(label);

        const control = document.createElement('input');
        control.type = 'range';
        control.id = param.id;
        control.min = param.min;
        control.max = param.max;
        control.step = param.step;
        control.value = param.value;
        control.style.width = '100px';
        container.appendChild(control);

        const valueSpan = document.createElement('span');
        valueSpan.id = param.valueId;
        valueSpan.textContent = param.value;
        valueSpan.style.minWidth = '30px';
        container.appendChild(valueSpan);

        control.addEventListener('input', function() {
            valueSpan.textContent = this.value;
        });

        globalParamsContainer.appendChild(container);
    });

    controlPanel.appendChild(globalParamsContainer);

    const testButton = document.createElement('button');
    testButton.textContent = '测试语音';
    testButton.onclick = testVoice;
    controlPanel.appendChild(testButton);

    enableSwitch.addEventListener('change', function() {
        if (state.tts) {
            state.tts.enable(this.checked);
            console.log(`语音合成已${this.checked ? '启用' : '禁用'}`);
        }
    });
}

export function testVoice() {
    console.log('测试语音功能调用');
    console.log('tts 对象:', state.tts);

    if (!('speechSynthesis' in window)) {
        console.error('window.speechSynthesis 不存在');
        alert('您的浏览器不支持Web Speech API，无法使用语音合成功能');
        return;
    }

    if (!state.tts) {
        console.error('tts 实例未加载');
        alert('语音合成模块未加载成功，请刷新页面重试');
        return;
    }

    const status = state.tts.getStatus();
    console.log('语音合成状态:', status);

    if (!status.supported) {
        console.error('tts.getStatus().supported 返回 false');
        alert('语音合成功能不被支持，请刷新页面重试或使用其他浏览器');
        return;
    }

    const rate = parseFloat(document.getElementById('voiceRateControl')?.value || '1');
    const pitch = parseFloat(document.getElementById('voicePitchControl')?.value || '1');
    const volume = parseFloat(document.getElementById('voiceVolumeControl')?.value || '1');

    state.tts.configureVoice('测试语音', null, pitch, rate, volume);
    state.tts.speak('这是一段测试语音，您可以通过上方的滑块调整语速、音调和音量。', '测试语音');

    // 动态导入 chat 模块避免循环依赖
    import('./chat.js').then(({ addChatMessage }) => {
        addChatMessage('测试语音', '这是一段测试语音，您可以通过上方的滑块调整语速、音调和音量。', 'system');
    });
}
