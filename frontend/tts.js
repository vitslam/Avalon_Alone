/**
 * 文本转语音模块
 * 用于让AI玩家发言时能够发出声音
 */

class TextToSpeech {
    constructor() {
        // 检查浏览器是否支持Web Speech API
        this.speechSynthesis = window.speechSynthesis;
        this.isSupported = 'speechSynthesis' in window;
        this.enabled = this.isSupported; // 默认启用
        this.voices = [];
        this.defaultVoice = null;
        this.voiceMap = {}; // 存储每个AI玩家对应的语音配置
        this.utteranceQueue = []; // 语音队列
        this.currentUtterance = null;
        this.speaking = false;
        this._lastAiPlayers = null; // 语音列表异步加载后重新分配音色
        
        if (this.isSupported) {
            // 初始化语音列表
            this.initVoices();
            
            // 监听语音加载事件
            window.speechSynthesis.onvoiceschanged = () => {
                this.initVoices();
                if (this._lastAiPlayers?.length) {
                    this._applyAIVoiceAssignments(this._lastAiPlayers);
                }
            };
        } else {
            console.warn('浏览器不支持Web Speech API，无法使用语音合成功能');
        }
    }

    // 初始化语音列表
    initVoices() {
        this.voices = this.speechSynthesis.getVoices();
        
        // 尝试选择中文语音作为默认语音
        this.defaultVoice = this.voices.find(voice => 
            voice.lang.includes('zh-CN') || voice.lang.includes('zh')
        ) || this.voices[0];
        
        console.log('可用语音列表:', this.voices.map(v => ({name: v.name, lang: v.lang})));
        console.log('默认语音:', this.defaultVoice ? {name: this.defaultVoice.name, lang: this.defaultVoice.lang} : '无');
    }

    _isMaleVoice(voice) {
        const name = voice.name.toLowerCase();
        return /kangkang|yunxi|yunyang|li-mu|male|男|david|george|daniel|yunjian|yunfeng/.test(name);
    }

    _isFemaleVoice(voice) {
        const name = voice.name.toLowerCase();
        return /huihui|yaoyao|ting-ting|sin-ji|xiaoxiao|xiaoyi|mei-jia|female|女|karen|samantha|tingting/.test(name);
    }

    // 构建可用音色池：优先中文，去重，男女声交替排列以增加差异感
    _buildVoicePool() {
        const seen = new Set();
        const zhVoices = [];
        for (const voice of this.voices) {
            if (!/zh/i.test(voice.lang)) continue;
            const key = voice.voiceURI || voice.name;
            if (seen.has(key)) continue;
            seen.add(key);
            zhVoices.push(voice);
        }

        const male = zhVoices.filter(v => this._isMaleVoice(v));
        const female = zhVoices.filter(v => this._isFemaleVoice(v));
        const neutral = zhVoices.filter(v => !this._isMaleVoice(v) && !this._isFemaleVoice(v));

        const pool = [];
        let mi = 0;
        let fi = 0;
        let ni = 0;
        const total = zhVoices.length;
        while (pool.length < total) {
            if (fi < female.length) pool.push(female[fi++]);
            if (mi < male.length) pool.push(male[mi++]);
            if (ni < neutral.length) pool.push(neutral[ni++]);
            if (fi >= female.length && mi >= male.length && ni >= neutral.length) break;
        }

        if (pool.length === 0 && this.defaultVoice) {
            pool.push(this.defaultVoice);
        }

        return pool;
    }

    // 为特定AI玩家配置语音（voiceName 可为名称字符串或 SpeechSynthesisVoice 对象）
    configureVoice(playerName, voiceName = null, pitch = 1, rate = 1, volume = 1) {
        if (!this.isSupported) return;
        
        let voice = null;
        if (voiceName && typeof voiceName === 'object' && voiceName.name) {
            voice = voiceName;
        } else if (voiceName) {
            voice = this.voices.find(v => v.name === voiceName || v.name.includes(voiceName));
        }
        
        voice = voice || this.defaultVoice;
        
        this.voiceMap[playerName] = {
            voice: voice,
            pitch: pitch,
            rate: rate,
            volume: volume
        };
        
        console.log(`已为玩家 ${playerName} 配置语音:`, {name: voice?.name, pitch, rate, volume});
    }

    // 播放文本语音
    speak(text, playerName = 'AI') {
        if (!this.isSupported || !this.enabled || !text) {
            console.log(`语音播放被跳过: 支持=${this.isSupported}, 启用=${this.enabled}, 文本=${!!text}`);
            return;
        }
        
        // 将语音请求添加到队列
        this.utteranceQueue.push({ text, playerName });
        console.log(`添加语音到队列 (${playerName})，当前队列长度: ${this.utteranceQueue.length}`);
        
        // 如果当前没有正在播放的语音，开始处理队列
        if (!this.speaking) {
            this._processQueue();
        }
    }
    
    // 处理语音队列
    _processQueue() {
        if (this.utteranceQueue.length === 0) {
            return;
        }
        
        // 获取队列中的第一个语音请求
        const request = this.utteranceQueue.shift();
        const { text, playerName } = request;
        
        // 获取该玩家的语音配置
        const config = this.voiceMap[playerName] || {
            voice: this.defaultVoice,
            pitch: 1,
            rate: 1,
            volume: 1
        };
        
        // 创建语音实例
        const utterance = new SpeechSynthesisUtterance(text);
        
        // 设置语音参数
        if (config.voice) {
            utterance.voice = config.voice;
        }
        utterance.pitch = config.pitch;
        utterance.rate = config.rate;
        utterance.volume = config.volume;
        utterance.lang = utterance.voice ? utterance.voice.lang : 'zh-CN';
        
        // 添加事件监听
        utterance.onstart = () => {
            console.log(`开始播放语音 (${playerName}):`, text);
            this.speaking = true;
            this.currentUtterance = utterance;
            
            // 当语音开始播放时，立即通知后端准备下一个玩家的发言
            // 只有当前队列中还有下一个发言者时才通知
            if (this.utteranceQueue.length === 0 && typeof window.onVoiceStart === 'function') {
                console.log(`通知后端准备下一个玩家发言: ${playerName}`);
                window.onVoiceStart(playerName, utterance.text);
            }
        };
        
        utterance.onend = (event) => {
            console.log(`语音播放完成 (${playerName}):`, utterance.text);
            this.speaking = false;
            this.currentUtterance = null;
            
            // 通知后端语音播放完成
            if (typeof window.onVoiceEnd === 'function') {
                console.log(`通知后端语音播放完成: ${playerName}`);
                window.onVoiceEnd(playerName, utterance.text);
            }
            
            // 处理下一个语音请求
            if (this.utteranceQueue.length > 0) {
                setTimeout(() => this._processQueue(), 300); // 短暂延迟，让玩家能区分不同发言
            }
        };
        
        utterance.onerror = (event) => {
            console.error(`语音播放错误 (${playerName}):`, event.error);
            this.speaking = false;
            this.currentUtterance = null;
            
            // 处理下一个语音请求
            if (this.utteranceQueue.length > 0) {
                setTimeout(() => this._processQueue(), 300);
            }
        };
        
        // 播放语音
        this.speechSynthesis.speak(utterance);
    }

    // 停止正在播放的语音
    stop() {
        if (!this.isSupported) return;
        this.speechSynthesis.cancel();
        this.speaking = false;
        this.currentUtterance = null;
        this.utteranceQueue = [];
        console.log('语音已停止，队列已清空');
    }

    // 是否正在播放语音
    isSpeaking() {
        if (!this.isSupported) return false;
        return this.speaking;
    }

    _applyAIVoiceAssignments(aiPlayers) {
        const voicePool = this._buildVoicePool();
        const pitchPresets = [
            { pitch: 0.75, rate: 1.05, volume: 1.0 },
            { pitch: 1.25, rate: 1.1, volume: 0.95 },
            { pitch: 0.9, rate: 0.95, volume: 1.0 },
            { pitch: 1.1, rate: 1.15, volume: 0.9 },
            { pitch: 0.8, rate: 1.0, volume: 1.0 },
            { pitch: 1.35, rate: 1.2, volume: 0.9 },
            { pitch: 0.7, rate: 1.05, volume: 0.95 },
            { pitch: 1.0, rate: 1.05, volume: 1.0 },
        ];

        const uniqueVoices = voicePool.length;
        console.log(`音色池: ${uniqueVoices} 个`, voicePool.map(v => v.name));

        aiPlayers.forEach((player, index) => {
            const voice = voicePool[index % voicePool.length];
            const preset = pitchPresets[index % pitchPresets.length];
            // 音色足够时保持接近原生参数，不足时用音调/语速拉开差异
            const useNativeParams = uniqueVoices >= aiPlayers.length;
            const pitch = useNativeParams ? 1.0 : preset.pitch;
            const rate = useNativeParams ? 1.05 : preset.rate;
            const volume = useNativeParams ? 1.0 : preset.volume;
            this.configureVoice(player.name, voice, pitch, rate, volume);
        });
    }

    // 预配置多个AI玩家的语音
    preconfigureAIVoices(aiPlayers) {
        if (!this.isSupported) return;
        this._lastAiPlayers = aiPlayers;
        this._applyAIVoiceAssignments(aiPlayers);
    }

    // 启用/禁用语音合成功能
    enable(enabled) {
        this.enabled = enabled;
        if (!enabled) {
            this.stop();
        }
        return this.enabled;
    }

    // 获取当前状态
    getStatus() {
        return {
            supported: this.isSupported,
            enabled: this.enabled,
            speaking: this.isSpeaking(),
            voicesCount: this.voices.length,
            configuredPlayers: Object.keys(this.voiceMap).length
        };
    }
}

// 创建TextToSpeech实例并导出
const tts = new TextToSpeech();
export { tts };