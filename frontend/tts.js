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
        
        if (this.isSupported) {
            // 初始化语音列表
            this.initVoices();
            
            // 监听语音加载事件
            window.speechSynthesis.onvoiceschanged = () => {
                this.initVoices();
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

    // 为特定AI玩家配置语音
    configureVoice(playerName, voiceName = null, pitch = 1, rate = 1, volume = 1) {
        if (!this.isSupported) return;
        
        // 查找指定名称的语音
        let voice = null;
        if (voiceName) {
            voice = this.voices.find(v => v.name === voiceName || v.name.includes(voiceName));
        }
        
        // 如果没有找到指定的语音或没有提供语音名称，则使用默认语音
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
        
        // 获取该玩家的语音配置
        const config = this.voiceMap[playerName] || {
            voice: this.defaultVoice,
            pitch: 1,
            rate: 1,
            volume: 1
        };
        
        // 取消当前可能正在播放的语音
        this.speechSynthesis.cancel();
        
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
        };
        
        utterance.onend = () => {
            console.log(`语音播放结束 (${playerName})`);
        };
        
        utterance.onerror = (event) => {
            console.error(`语音播放错误 (${playerName}):`, event.error);
        };
        
        // 播放语音
        this.speechSynthesis.speak(utterance);
    }

    // 停止正在播放的语音
    stop() {
        if (!this.isSupported) return;
        this.speechSynthesis.cancel();
    }

    // 是否正在播放语音
    isSpeaking() {
        if (!this.isSupported) return false;
        return this.speechSynthesis.speaking;
    }

    // 预配置多个AI玩家的语音
    preconfigureAIVoices(aiPlayers) {
        if (!this.isSupported) return;
        
        // 预定义一些语音参数组合，为不同AI玩家分配不同的声音特性
        const voiceConfigurations = [
            {pitch: 1.2, rate: 0.9, volume: 1.0},  // 高音调，慢速
            {pitch: 0.8, rate: 1.1, volume: 0.9},  // 低音调，快速
            {pitch: 1.0, rate: 1.0, volume: 1.0},  // 正常音调，正常速度
            {pitch: 0.9, rate: 0.8, volume: 0.95}, // 低音调，慢速
            {pitch: 1.3, rate: 1.2, volume: 0.9}   // 高音调，快速
        ];
        
        aiPlayers.forEach((player, index) => {
            // 循环使用预定义的语音配置
            const config = voiceConfigurations[index % voiceConfigurations.length];
            this.configureVoice(player.name, null, config.pitch, config.rate, config.volume);
        });
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

// 创建全局实例
export const tts = new TextToSpeech();

export default TextToSpeech;