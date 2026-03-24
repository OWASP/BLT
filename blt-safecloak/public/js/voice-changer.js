/**
 * BLT-SafeCloak — voice-changer.js
 * Real-time voice effects using the Web Audio API.
 * Processes the microphone stream through an effect chain and exposes
 * a processed MediaStream that can be fed into WebRTC peer connections.
 *
 * Audio graph
 * -----------
 *   rawStream → sourceNode → inputGainNode → [effect chain] → destinationNode
 *                                                                     ↓
 *                                                          monitorSourceNode
 *                                                                     ↓
 *                                                          monitorGain → audioCtx.destination
 */

const VoiceChanger = (() => {
  let audioCtx = null;
  let sourceNode = null;
  let inputGainNode = null;      /* mic input level control */
  let destinationNode = null;
  let monitorGain = null;        /* speaker output for "hear yourself" */
  let monitorSourceNode = null;  /* re-routes processed stream to speakers */
  let activeOscillator = null;   /* robot mode oscillator — needs explicit stop */

  let currentMode = "normal";
  let processedStream = null;

  /* User preferences — preserved across destroy/init cycles */
  let monitorEnabled = false;
  let monitorVolume = 0.5;
  let micGain = 1.0;
  let effectIntensity = 0.5; /* 0 = subtle, 1 = maximum; scales every effect chain */

  const MODES = {
    normal:   { label: "Normal",    icon: "fa-microphone",     description: "No voice effect applied" },
    deep:     { label: "Deep",      icon: "fa-down-long",      description: "Lower, deeper voice tone" },
    chipmunk: { label: "Chipmunk",  icon: "fa-up-long",        description: "Higher-pitched squeaky voice" },
    robot:    { label: "Robot",     icon: "fa-robot",          description: "Robotic ring-modulation effect" },
    echo:     { label: "Echo",      icon: "fa-wave-square",    description: "Reverb and echo effect" },
    voice1:   { label: "Telephone", icon: "fa-phone",          description: "Classic telephone / walkie-talkie" },
    voice2:   { label: "Alien",     icon: "fa-user-astronaut", description: "Otherworldly alien voice" },
    voice3:   { label: "Monster",   icon: "fa-skull",          description: "Deep monster voice with tremolo" },
  };

  /* ── Helpers ── */

  /** Linear interpolate between a and b at position t (0–1). */
  function lerp(a, b, t) {
    return a + (b - a) * t;
  }

  function makeDistortionCurve(amount) {
    const n = 512;
    const curve = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      const x = (i * 2) / n - 1;
      curve[i] = ((Math.PI + amount) * x) / (Math.PI + amount * Math.abs(x));
    }
    return curve;
  }

  /**
   * Stop any running oscillator from a previous robot chain, then
   * disconnect both sourceNode and inputGainNode so the old effect
   * chain is fully torn down before a new one is wired up.
   */
  function disconnectSource() {
    if (activeOscillator) {
      try {
        activeOscillator.stop();
      } catch {
        /* ignore — already stopped */
      }
      try {
        activeOscillator.disconnect();
      } catch {
        /* ignore */
      }
      activeOscillator = null;
    }
    if (inputGainNode) {
      try {
        inputGainNode.disconnect();
      } catch {
        /* ignore */
      }
    }
    if (sourceNode) {
      try {
        sourceNode.disconnect();
      } catch {
        /* ignore */
      }
    }
  }

  /* ── Effect chains ── */

  function buildChain(mode) {
    disconnectSource();
    /* monitorGain is not checked here — it is wired once in init() and does not
     * participate in the effect chain itself; it reads from destinationNode.stream
     * and routes to audioCtx.destination independently. */
    if (!audioCtx || !sourceNode || !inputGainNode || !destinationNode) return;

    /* Always reconnect: sourceNode → inputGainNode */
    sourceNode.connect(inputGainNode);

    /* t = effectIntensity (0–1) used to scale every effect parameter */
    const t = effectIntensity;

    switch (mode) {
      case "deep": {
        /* Boost bass, attenuate treble → deeper sounding voice */
        const lowShelf = audioCtx.createBiquadFilter();
        lowShelf.type = "lowshelf";
        lowShelf.frequency.value = 250;
        lowShelf.gain.value = lerp(3, 18, t);

        const highShelf = audioCtx.createBiquadFilter();
        highShelf.type = "highshelf";
        highShelf.frequency.value = 2000;
        highShelf.gain.value = lerp(-3, -16, t);

        const gain = audioCtx.createGain();
        gain.gain.value = 1.1;

        inputGainNode.connect(lowShelf);
        lowShelf.connect(highShelf);
        highShelf.connect(gain);
        gain.connect(destinationNode);
        break;
      }

      case "chipmunk": {
        /* Attenuate bass, boost upper-mid/treble → thin, squeaky voice */
        const lowShelf = audioCtx.createBiquadFilter();
        lowShelf.type = "lowshelf";
        lowShelf.frequency.value = 400;
        lowShelf.gain.value = lerp(-4, -14, t);

        const highpass = audioCtx.createBiquadFilter();
        highpass.type = "highpass";
        highpass.frequency.value = 600;
        highpass.Q.value = 0.7;

        const peaking = audioCtx.createBiquadFilter();
        peaking.type = "peaking";
        peaking.frequency.value = 3200;
        peaking.gain.value = lerp(3, 14, t);
        peaking.Q.value = 1;

        inputGainNode.connect(lowShelf);
        lowShelf.connect(highpass);
        highpass.connect(peaking);
        peaking.connect(destinationNode);
        break;
      }

      case "robot": {
        /* Ring modulation: multiply source by a low-frequency oscillator */
        const oscillator = audioCtx.createOscillator();
        oscillator.type = "square";
        oscillator.frequency.value = lerp(30, 100, t);

        /* The oscillator drives the gain of a GainNode that the source passes through */
        const ringGain = audioCtx.createGain();
        ringGain.gain.value = 0; /* oscillator will modulate this */

        oscillator.connect(ringGain.gain);
        oscillator.start();
        activeOscillator = oscillator; /* tracked so it can be stopped on next buildChain */

        const waveshaper = audioCtx.createWaveShaper();
        waveshaper.curve = makeDistortionCurve(lerp(30, 150, t));
        waveshaper.oversample = "4x";

        const bandpass = audioCtx.createBiquadFilter();
        bandpass.type = "bandpass";
        bandpass.frequency.value = 1400;
        bandpass.Q.value = 0.6;

        const gainOut = audioCtx.createGain();
        gainOut.gain.value = 1.4;

        inputGainNode.connect(ringGain);
        ringGain.connect(waveshaper);
        waveshaper.connect(bandpass);
        bandpass.connect(gainOut);
        gainOut.connect(destinationNode);
        break;
      }

      case "echo": {
        /* Short delay with feedback loop mixed with the dry signal */
        const delay = audioCtx.createDelay(1.0);
        delay.delayTime.value = lerp(0.1, 0.38, t);

        const feedback = audioCtx.createGain();
        feedback.gain.value = lerp(0.2, 0.55, t);

        const dryGain = audioCtx.createGain();
        dryGain.gain.value = 0.8;

        const wetGain = audioCtx.createGain();
        wetGain.gain.value = lerp(0.3, 0.7, t);

        /* Dry path */
        inputGainNode.connect(dryGain);
        dryGain.connect(destinationNode);

        /* Wet path with feedback */
        inputGainNode.connect(delay);
        delay.connect(feedback);
        feedback.connect(delay);
        delay.connect(wetGain);
        wetGain.connect(destinationNode);
        break;
      }

      case "voice1": {
        /* Telephone: narrow phone bandwidth (HP+LP) + tube-style distortion */
        const highpass = audioCtx.createBiquadFilter();
        highpass.type = "highpass";
        highpass.frequency.value = lerp(150, 500, t);
        highpass.Q.value = 0.9;

        const lowpass = audioCtx.createBiquadFilter();
        lowpass.type = "lowpass";
        lowpass.frequency.value = lerp(5000, 2200, t);
        lowpass.Q.value = 0.9;

        const waveshaper = audioCtx.createWaveShaper();
        waveshaper.curve = makeDistortionCurve(lerp(10, 90, t));
        waveshaper.oversample = "2x";

        const gainOut = audioCtx.createGain();
        gainOut.gain.value = 1.2;

        inputGainNode.connect(highpass);
        highpass.connect(lowpass);
        lowpass.connect(waveshaper);
        waveshaper.connect(gainOut);
        gainOut.connect(destinationNode);
        break;
      }

      case "voice2": {
        /* Alien: ring modulation at a mid frequency + comb-filter via short delay */
        const oscillator = audioCtx.createOscillator();
        oscillator.type = "sine";
        oscillator.frequency.value = lerp(60, 200, t);

        const ringGain = audioCtx.createGain();
        ringGain.gain.value = 0;
        oscillator.connect(ringGain.gain);
        oscillator.start();
        activeOscillator = oscillator;

        /* Comb filter via short feedback delay */
        const combDelay = audioCtx.createDelay(0.05);
        combDelay.delayTime.value = lerp(0.003, 0.015, t);
        const combFeedback = audioCtx.createGain();
        combFeedback.gain.value = lerp(0.35, 0.65, t);

        const dryGain = audioCtx.createGain();
        dryGain.gain.value = 0.6;
        const wetGain = audioCtx.createGain();
        wetGain.gain.value = lerp(0.4, 0.9, t);

        inputGainNode.connect(dryGain);
        dryGain.connect(destinationNode);

        inputGainNode.connect(ringGain);
        ringGain.connect(combDelay);
        combDelay.connect(combFeedback);
        combFeedback.connect(combDelay);
        combDelay.connect(wetGain);
        wetGain.connect(destinationNode);
        break;
      }

      case "voice3": {
        /* Monster: strong low-shelf boost + tremolo + heavy distortion */
        const lowShelf = audioCtx.createBiquadFilter();
        lowShelf.type = "lowshelf";
        lowShelf.frequency.value = 300;
        lowShelf.gain.value = lerp(8, 20, t);

        const highShelf = audioCtx.createBiquadFilter();
        highShelf.type = "highshelf";
        highShelf.frequency.value = 1500;
        highShelf.gain.value = lerp(-6, -18, t);

        /* Tremolo via LFO modulating a gain node */
        const tremoloGain = audioCtx.createGain();
        tremoloGain.gain.value = 0.7;
        const tremolo = audioCtx.createOscillator();
        tremolo.type = "sine";
        tremolo.frequency.value = lerp(3, 10, t);
        const tremoloDepth = audioCtx.createGain();
        tremoloDepth.gain.value = lerp(0.15, 0.5, t);
        tremolo.connect(tremoloDepth);
        tremoloDepth.connect(tremoloGain.gain);
        tremolo.start();
        activeOscillator = tremolo;

        const waveshaper = audioCtx.createWaveShaper();
        waveshaper.curve = makeDistortionCurve(lerp(80, 280, t));
        waveshaper.oversample = "4x";

        const gainOut = audioCtx.createGain();
        gainOut.gain.value = lerp(0.9, 1.4, t);

        inputGainNode.connect(lowShelf);
        lowShelf.connect(highShelf);
        highShelf.connect(tremoloGain);
        tremoloGain.connect(waveshaper);
        waveshaper.connect(gainOut);
        gainOut.connect(destinationNode);
        break;
      }

      default: /* normal — direct passthrough */
        inputGainNode.connect(destinationNode);
    }
  }

  /* ── Public API ── */

  /**
   * Initialise the voice changer with a raw microphone MediaStream.
   * Returns a MediaStream containing only the processed audio track
   * that can be combined with a video track for WebRTC transmission.
   *
   * Safe to call multiple times — tears down any previous context first.
   */
  function init(rawStream) {
    /* Tear down any existing audio context and nodes before reinitialising */
    destroy();

    let newAudioCtx = null;
    try {
      newAudioCtx = new (window.AudioContext || window.webkitAudioContext)();

      const newSourceNode = newAudioCtx.createMediaStreamSource(rawStream);
      const newInputGainNode = newAudioCtx.createGain();
      newInputGainNode.gain.value = micGain;

      const newDestinationNode = newAudioCtx.createMediaStreamDestination();

      /* Monitor path: processed stream → speakers */
      const newMonitorGain = newAudioCtx.createGain();
      newMonitorGain.gain.value = monitorEnabled ? monitorVolume : 0;
      newMonitorGain.connect(newAudioCtx.destination);

      /* Only assign module-level state after all nodes are created successfully */
      audioCtx = newAudioCtx;
      sourceNode = newSourceNode;
      inputGainNode = newInputGainNode;
      destinationNode = newDestinationNode;
      monitorGain = newMonitorGain;

      buildChain(currentMode);
      processedStream = destinationNode.stream;

      /* Route processed audio back to speakers for the monitor feature.
       * monitorGain.gain = 0 keeps it silent until the user enables monitoring. */
      monitorSourceNode = audioCtx.createMediaStreamSource(processedStream);
      monitorSourceNode.connect(monitorGain);
    } catch {
      /* Clean up any partially-created AudioContext before falling back */
      if (newAudioCtx) {
        try {
          newAudioCtx.close();
        } catch {
          /* ignore */
        }
      }
      audioCtx = null;
      sourceNode = null;
      inputGainNode = null;
      destinationNode = null;
      monitorGain = null;
      monitorSourceNode = null;

      /* Web Audio API unavailable — return an audio-only stream as fallback */
      const audioTracks =
        typeof rawStream.getAudioTracks === "function" ? rawStream.getAudioTracks() : [];
      processedStream = new MediaStream(audioTracks);
    }
    return processedStream;
  }

  /** Switch the active voice effect at any time (even during an active call). */
  function setMode(mode) {
    if (!MODES[mode]) return;
    currentMode = mode;
    buildChain(mode);
  }

  /**
   * Toggle the "hear yourself" monitor on or off.
   * Returns the new enabled state.
   */
  function toggleMonitor() {
    monitorEnabled = !monitorEnabled;
    if (monitorGain) {
      monitorGain.gain.value = monitorEnabled ? monitorVolume : 0;
    }
    return monitorEnabled;
  }

  /**
   * Set monitor speaker volume (0–1).
   * Takes effect immediately when the monitor is enabled.
   */
  function setMonitorVolume(v) {
    monitorVolume = Math.max(0, Math.min(1, Number(v)));
    if (monitorGain && monitorEnabled) {
      monitorGain.gain.value = monitorVolume;
    }
    return monitorVolume;
  }

  /**
   * Set microphone input gain (0–2).
   * A value of 1.0 is unity gain; 2.0 doubles the signal level.
   */
  function setMicGain(v) {
    micGain = Math.max(0, Math.min(2, Number(v)));
    if (inputGainNode) {
      inputGainNode.gain.value = micGain;
    }
    return micGain;
  }

  /**
   * Set the intensity of the current effect chain (0–1).
   * 0 = subtle / 1 = maximum. Rebuilds the active chain immediately.
   */
  function setEffectIntensity(v) {
    effectIntensity = Math.max(0, Math.min(1, Number(v)));
    buildChain(currentMode);
    return effectIntensity;
  }

  function getMode() {
    return currentMode;
  }

  function getModes() {
    return MODES;
  }

  function getProcessedStream() {
    return processedStream;
  }

  function getMonitorEnabled() {
    return monitorEnabled;
  }

  function getMonitorVolume() {
    return monitorVolume;
  }

  function getMicGain() {
    return micGain;
  }

  function getEffectIntensity() {
    return effectIntensity;
  }

  /** Release all audio resources. */
  function destroy() {
    if (activeOscillator) {
      try {
        activeOscillator.stop();
      } catch {
        /* ignore — may already be stopped */
      }
      try {
        activeOscillator.disconnect();
      } catch {
        /* ignore */
      }
      activeOscillator = null;
    }
    if (monitorSourceNode) {
      try {
        monitorSourceNode.disconnect();
      } catch {
        /* ignore */
      }
      monitorSourceNode = null;
    }
    if (sourceNode) {
      try {
        sourceNode.disconnect();
      } catch {
        /* ignore */
      }
      sourceNode = null;
    }
    if (audioCtx) {
      audioCtx.close();
      audioCtx = null;
    }
    inputGainNode = null;
    destinationNode = null;
    monitorGain = null;
    processedStream = null;
    currentMode = "normal";
    /* monitorEnabled is intentionally reset to false on destroy — silently
     * re-enabling mic monitoring on the next init() without user action
     * would be surprising and potentially undesirable.
     * monitorVolume and micGain are user preferences preserved across destroy/init. */
    monitorEnabled = false;
  }

  return {
    init,
    setMode,
    getMode,
    getModes,
    getProcessedStream,
    destroy,
    toggleMonitor,
    setMonitorVolume,
    setMicGain,
    setEffectIntensity,
    getMonitorEnabled,
    getMonitorVolume,
    getMicGain,
    getEffectIntensity,
  };
})();

