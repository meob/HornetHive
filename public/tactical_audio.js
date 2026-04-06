/**
 * HORNET HIVE - Tactical Audio Engine (Web Audio API)
 * Procedural sound generation for C4I Dashboard.
 * No external files required.
 */

const TacticalAudio = (() => {
    let audioCtx = null;

    const init = () => {
        if (!audioCtx) {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
    };

    const createOscillator = (freq, type = 'sine', duration = 0.5, volume = 0.1) => {
        init();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();

        osc.type = type;
        osc.frequency.setValueAtTime(freq, audioCtx.currentTime);

        gain.gain.setValueAtTime(volume, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + duration);

        osc.connect(gain);
        gain.connect(audioCtx.destination);

        return { osc, gain };
    };

    return {
        // --- SOUND PROFILES ---

        // 🚨 MAYDAY: Repeating high-pitched alarm
        playMayday: () => {
            init();
            const now = audioCtx.currentTime;
            const { osc, gain } = createOscillator(880, 'square', 0.8, 0.05);
            osc.frequency.alternate = true;
            
            // Pulse effect
            osc.frequency.setValueAtTime(880, now);
            osc.frequency.setValueAtTime(660, now + 0.2);
            osc.frequency.setValueAtTime(880, now + 0.4);
            osc.frequency.setValueAtTime(660, now + 0.6);

            osc.start(now);
            osc.stop(now + 0.8);
        },

        // 🎯 DETECTION: Sharp lock-on sound
        playDetection: () => {
            init();
            const now = audioCtx.currentTime;
            const { osc, gain } = createOscillator(1200, 'sawtooth', 0.3, 0.08);
            
            osc.frequency.exponentialRampToValueAtTime(440, now + 0.3);
            
            osc.start(now);
            osc.stop(now + 0.3);
        },

        // ✅ MISSION SUCCESS: Ascending positive tone
        playSuccess: () => {
            init();
            const now = audioCtx.currentTime;
            [440, 554.37, 659.25, 880].forEach((freq, i) => {
                const { osc, gain } = createOscillator(freq, 'sine', 0.4, 0.1);
                osc.start(now + (i * 0.1));
                osc.stop(now + (i * 0.1) + 0.4);
            });
        },

        // 🛡️ WRA (STRIKE): Low frequency confirmation
        playWRA: () => {
            init();
            const now = audioCtx.currentTime;
            const { osc, gain } = createOscillator(110, 'sine', 1.0, 0.15);
            
            osc.frequency.setValueAtTime(110, now);
            osc.frequency.linearRampToValueAtTime(150, now + 0.5);
            osc.frequency.linearRampToValueAtTime(110, now + 1.0);

            osc.start(now);
            osc.stop(now + 1.0);
        },

        // 📡 RADAR PING: Classic sonar sound
        playRadarPing: () => {
            init();
            const now = audioCtx.currentTime;
            const { osc, gain } = createOscillator(1760, 'sine', 0.4, 0.03);
            
            gain.gain.setValueAtTime(0.03, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.4);

            osc.start(now);
            osc.stop(now + 0.4);
        },

        // Helper to unlock audio on first interaction
        unlock: () => {
            if (audioCtx && audioCtx.state === 'suspended') {
                audioCtx.resume();
            }
        }
    };
})();

// Export for browser
window.TacticalAudio = TacticalAudio;
