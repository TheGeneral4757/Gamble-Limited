/**
 * Gamble Limited - Main JavaScript
 * Global functionality, balance management, and sound effects
 */

// ==================== Sound Effects System ====================

class SoundManager {
    constructor() {
        this.enabled = true;
        this.volume = 0.5;
        this.sounds = {};
        this.audioContext = null;

        // Initialize Web Audio API on first user interaction
        document.addEventListener('click', () => this.initAudioContext(), { once: true });
    }

    initAudioContext() {
        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }
    }

    // Generate sounds programmatically (no external files needed)
    async generateTone(frequency, duration, type = 'sine', volumeMultiplier = 1) {
        if (!this.enabled || !this.audioContext) return;

        try {
            const oscillator = this.audioContext.createOscillator();
            const gainNode = this.audioContext.createGain();

            oscillator.connect(gainNode);
            gainNode.connect(this.audioContext.destination);

            oscillator.frequency.value = frequency;
            oscillator.type = type;

            gainNode.gain.setValueAtTime(this.volume * volumeMultiplier, this.audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + duration);

            oscillator.start(this.audioContext.currentTime);
            oscillator.stop(this.audioContext.currentTime + duration);
        } catch (e) {
            console.log('Sound error:', e);
        }
    }

    // Specific sound effects
    spin() {
        // Slot machine spinning sound - rapid clicks
        for (let i = 0; i < 10; i++) {
            setTimeout(() => this.generateTone(200 + Math.random() * 100, 0.05, 'square', 0.3), i * 50);
        }
    }

    reelStop() {
        this.generateTone(300, 0.1, 'square', 0.5);
    }

    win() {
        // Ascending happy tones
        const notes = [523, 659, 784, 1047];
        notes.forEach((freq, i) => {
            setTimeout(() => this.generateTone(freq, 0.15, 'sine', 0.6), i * 100);
        });
    }

    bigWin() {
        // Jackpot fanfare
        const notes = [523, 659, 784, 880, 1047, 1319, 1568];
        notes.forEach((freq, i) => {
            setTimeout(() => this.generateTone(freq, 0.2, 'sine', 0.7), i * 80);
        });
    }

    lose() {
        // Descending sad tones
        this.generateTone(300, 0.3, 'sawtooth', 0.3);
        setTimeout(() => this.generateTone(200, 0.4, 'sawtooth', 0.2), 150);
    }

    cardDeal() {
        this.generateTone(800, 0.05, 'square', 0.4);
    }

    cardFlip() {
        setTimeout(() => this.generateTone(600, 0.08, 'square', 0.3), 0);
        setTimeout(() => this.generateTone(900, 0.08, 'square', 0.3), 50);
    }

    coinFlip() {
        // Metallic coin sound
        for (let i = 0; i < 8; i++) {
            setTimeout(() => this.generateTone(1000 + Math.random() * 500, 0.05, 'triangle', 0.4), i * 100);
        }
    }

    wheelSpin() {
        // Roulette wheel spinning
        for (let i = 0; i < 20; i++) {
            setTimeout(() => this.generateTone(150 + i * 5, 0.08, 'square', 0.2), i * 100);
        }
    }

    ballDrop() {
        // Plinko ball bouncing
        this.generateTone(600, 0.05, 'triangle', 0.4);
    }

    ballLand() {
        this.generateTone(200, 0.2, 'sine', 0.5);
    }

    click() {
        this.generateTone(800, 0.03, 'square', 0.3);
    }

    coin() {
        // Coin collect sound
        this.generateTone(1200, 0.1, 'sine', 0.4);
        setTimeout(() => this.generateTone(1600, 0.1, 'sine', 0.3), 50);
    }

    error() {
        this.generateTone(200, 0.3, 'sawtooth', 0.4);
    }

    ding() {
        this.generateTone(880, 0.15, 'sine', 0.5);
    }

    toggle() {
        this.enabled = !this.enabled;
        return this.enabled;
    }

    setVolume(vol) {
        this.volume = Math.max(0, Math.min(1, vol));
    }
}

// Global sound manager instance
const soundManager = new SoundManager();

// Convenience function for playing sounds
function playSound(soundName) {
    if (soundManager[soundName]) {
        soundManager[soundName]();
    }
}

// ==================== Balance Management ====================

async function fetchBalance() {
    try {
        const response = await fetch('/api/economy/balance');
        if (!response.ok) throw new Error('Failed to fetch balance');

        const data = await response.json();
        updateBalanceDisplay(data);

        // Set user ID cookie if not present
        if (data.user_id && !getCookie('user_id')) {
            document.cookie = `user_id=${data.user_id};path=/;max-age=31536000`;
        }

        return data;
    } catch (error) {
        console.error('Balance fetch error:', error);
        return null;
    }
}

function updateBalanceDisplay(balance) {
    const cashEl = document.getElementById('cash-balance');
    const creditsEl = document.getElementById('credits-balance');

    if (cashEl && balance.cash !== undefined) {
        const oldValue = parseFloat(cashEl.textContent) || 0;
        cashEl.textContent = formatNumber(balance.cash);

        // Animate on change
        if (balance.cash > oldValue) {
            cashEl.parentElement.classList.add('balance-up');
            setTimeout(() => cashEl.parentElement.classList.remove('balance-up'), 500);
        } else if (balance.cash < oldValue) {
            cashEl.parentElement.classList.add('balance-down');
            setTimeout(() => cashEl.parentElement.classList.remove('balance-down'), 500);
        }
    }
    if (creditsEl && balance.credits !== undefined) {
        const oldValue = parseFloat(creditsEl.textContent) || 0;
        creditsEl.textContent = formatNumber(balance.credits);

        if (balance.credits > oldValue) {
            creditsEl.parentElement.classList.add('balance-up');
            setTimeout(() => creditsEl.parentElement.classList.remove('balance-up'), 500);
        } else if (balance.credits < oldValue) {
            creditsEl.parentElement.classList.add('balance-down');
            setTimeout(() => creditsEl.parentElement.classList.remove('balance-down'), 500);
        }
    }
}

// Global function for game pages to update balance
function updateBalance(balance) {
    updateBalanceDisplay(balance);
}

// ==================== Utility Functions ====================

function formatNumber(num) {
    return parseFloat(num).toFixed(2);
}

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}

// ==================== Toast Notifications ====================

function showToast(message, type = 'info') {
    // Remove existing toasts
    document.querySelectorAll('.toast').forEach(t => t.remove());

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    // Animate in
    setTimeout(() => toast.classList.add('show'), 10);

    // Remove after delay
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ==================== API Helpers ====================

async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method,
        headers: {}
    };

    if (data) {
        options.headers['Content-Type'] = 'application/json';
        options.body = JSON.stringify(data);
    }

    const response = await fetch(endpoint, options);
    const result = await response.json();

    if (!response.ok) {
        throw new Error(result.detail || 'API error');
    }

    return result;
}

// ==================== Initialization ====================

document.addEventListener('DOMContentLoaded', function () {
    // Fetch balance on page load
    fetchBalance();

    // Refresh balance periodically
    setInterval(fetchBalance, 30000);

    // Add loading animation style
    const style = document.createElement('style');
    style.textContent = `
        .toast {
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 15px 25px;
            border-radius: 8px;
            color: white;
            font-weight: 600;
            opacity: 0;
            transform: translateY(20px);
            transition: all 0.3s ease;
            z-index: 10000;
        }
        .toast.show {
            opacity: 1;
            transform: translateY(0);
        }
        .toast-info { background: linear-gradient(135deg, #00f2ff, #7000ff); }
        .toast-success { background: linear-gradient(135deg, #00ff88, #00cc66); }
        .toast-error { background: linear-gradient(135deg, #ff5555, #ff0055); }
        .toast-warning { background: linear-gradient(135deg, #ffaa00, #ff6600); }
        
        .balance-up {
            animation: pulse-green 0.5s ease;
        }
        .balance-down {
            animation: pulse-red 0.5s ease;
        }
        @keyframes pulse-green {
            0%, 100% { color: #00ff88; }
            50% { color: #00ff00; transform: scale(1.1); }
        }
        @keyframes pulse-red {
            0%, 100% { }
            50% { color: #ff5555; transform: scale(0.95); }
        }
    `;
    document.head.appendChild(style);

    // Add sound toggle to header
    const header = document.querySelector('.main-header nav');
    if (header) {
        const soundBtn = document.createElement('button');
        soundBtn.className = 'sound-toggle';
        soundBtn.innerHTML = '🔊';
        soundBtn.title = 'Toggle Sound';
        soundBtn.style.cssText = 'background: none; border: none; font-size: 1.2rem; cursor: pointer; margin-left: 15px;';
        soundBtn.onclick = () => {
            const enabled = soundManager.toggle();
            soundBtn.innerHTML = enabled ? '🔊' : '🔇';
            if (enabled) playSound('ding');
        };
        header.appendChild(soundBtn);
    }

    console.log('🎰 Gamble Limited Platform Loaded');
    console.log('🔊 Sound effects enabled - click anywhere to activate');
});
