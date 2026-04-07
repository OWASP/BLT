/**
 * BLT-SafeCloak — voice-changer.js
 * Real-time voice effects using the Web Audio API.
 * Processes the microphone stream through an effect chain and exposes
 * a processed MediaStream that can be fed into WebRTC peer connections.
 *
 * Audio graph
 * -----------
 *   rawStream → sourceNode → inputGainNode → [effect segments in series] → destinationNode
 *                                                                                  ↓
 *                                                                       monitorSourceNode
 *                                                                                  ↓
 *                                                                       monitorGain → audioCtx.destination
 *
 * Effect segments (dry/wet per-effect):
 *   prevNode ─── dryGain (1−level) ──────────────────────────→ mergerNode
 *            └── wetPath: effectIn → [nodes] → effectOut → wetGain (level) ─┘
 *
 * Multiple effects are chained in series. At level=0 an effect is bypassed
 * entirely (only the dry signal passes through to the next stage).
 */

const VoiceChanger = (() => {
  let audioCtx = null;
  let sourceNode = null;
  let inputGainNode = null; /* mic input level control */
  let destinationNode = null;
  let monitorGain = null; /* speaker output for "hear yourself" */
  let monitorSourceNode = null; /* re-routes processed stream to speakers */
  let activeOscillators = []; /* all running oscillators — need explicit stop on rebuild */

  /** Per-effect intensity levels (0 = bypassed, 1 = full effect). */
  let effectLevels = { deep: 0, chipmunk: 0, robot: 0, echo: 0, voice1: 0, voice2: 0, voice3: 0 };

  /* Backward-compat state for setMode / getMode / setEffectIntensity / getEffectIntensity */
  let _primaryMode = "normal";
  let _globalIntensity = 0.5;

  /* User preferences — preserved across destroy/init cycles */
  let monitorEnabled = false;
  let monitorVolume = 0.5;
  let micGain = 1.0;

  let processedStream = null;

  const MODES = {
    normal: { label: "Normal", icon: "fa-microphone", description: "No voice effect applied" },
    deep: { label: "Deep", icon: "fa-down-long", description: "Lower, deeper voice tone" },
    chipmunk: {
      label: "Chipmunk",
      icon: "fa-up-long",
      description: "Higher-pitched squeaky voice",
    },
    robot: { label: "Robot", icon: "fa-robot", description: "Robotic ring-modulation effect" },
    echo: { label: "Echo", icon: "fa-wave-square", description: "Reverb and echo effect" },
    voice1: {
      label: "Telephone",
      icon: "fa-phone",
      description: "Classic telephone / walkie-talkie",
    },
    voice2: { label: "Alien", icon: "fa-user-astronaut", description: "Otherworldly alien voice" },
    voice3: { label: "Monster", icon: "fa-skull", description: "Deep monster voice with tremolo" },
  };

  /** The order in which active effects are applied in series. */
  const EFFECT_ORDER = ["deep", "chipmunk", "robot", "echo", "voice1", "voice2", "voice3"];

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
   * Stop all running oscillators, then disconnect sourceNode and inputGainNode
   * so the old effect chain is fully torn down before a new one is wired up.
   */
  function disconnectSource() {
    activeOscillators.forEach((osc) => {
      try {
        osc.stop();
      } catch {
        /* already stopped */
      }
      try {
        osc.disconnect();
      } catch {
        /* ignore */
      }
    });
    activeOscillators = [];

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

  /* ── Effect node builders ── */

  /**
   * Build the pure-wet audio nodes for one effect mode.
   * Returns { inputNode, outputNode } — the caller is responsible for connecting
   * prevNode → inputNode and outputNode → wetGainNode.
   * @param {string} mode - effect key
   * @param {number} t    - effect level (0–1), used to scale parameters
   */
  function buildEffectNodes(mode, t) {
    switch (mode) {
      case "deep": {
        /* Boost bass, attenuate treble — scaled with t for smoother intensity blending */
        const lowShelf = audioCtx.createBiquadFilter();
        lowShelf.type = "lowshelf";
        lowShelf.frequency.value = 250;
        lowShelf.gain.value = lerp(3, 18, t);

        const highShelf = audioCtx.createBiquadFilter();
        highShelf.type = "highshelf";
        highShelf.frequency.value = 2000;
        highShelf.gain.value = lerp(-3, -16, t);

        lowShelf.connect(highShelf);
        return { inputNode: lowShelf, outputNode: highShelf };
      }

      case "chipmunk": {
        /* Attenuate bass, boost upper-mid/treble — scaled with t */
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

        lowShelf.connect(highpass);
        highpass.connect(peaking);
        return { inputNode: lowShelf, outputNode: peaking };
      }

      case "robot": {
        const oscillator = audioCtx.createOscillator();
        oscillator.type = "square";
        oscillator.frequency.value = lerp(30, 100, t);

        const ringGain = audioCtx.createGain();
        ringGain.gain.value = 0;
        oscillator.connect(ringGain.gain);
        oscillator.start();
        activeOscillators.push(oscillator);

        const waveshaper = audioCtx.createWaveShaper();
        waveshaper.curve = makeDistortionCurve(lerp(30, 150, t));
        waveshaper.oversample = "4x";

        const bandpass = audioCtx.createBiquadFilter();
        bandpass.type = "bandpass";
        bandpass.frequency.value = 1400;
        bandpass.Q.value = 0.6;

        ringGain.connect(waveshaper);
        waveshaper.connect(bandpass);
        return { inputNode: ringGain, outputNode: bandpass };
      }

      case "echo": {
        const delay = audioCtx.createDelay(1.0);
        delay.delayTime.value = lerp(0.1, 0.38, t);

        const feedback = audioCtx.createGain();
        feedback.gain.value = lerp(0.2, 0.55, t);

        delay.connect(feedback);
        feedback.connect(delay);
        /* The delay node acts as both input and output; the feedback loop is internal. */
        return { inputNode: delay, outputNode: delay };
      }

      case "voice1": {
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

        highpass.connect(lowpass);
        lowpass.connect(waveshaper);
        return { inputNode: highpass, outputNode: waveshaper };
      }

      case "voice2": {
        const oscillator = audioCtx.createOscillator();
        oscillator.type = "sine";
        oscillator.frequency.value = lerp(60, 200, t);

        const ringGain = audioCtx.createGain();
        ringGain.gain.value = 0;
        oscillator.connect(ringGain.gain);
        oscillator.start();
        activeOscillators.push(oscillator);

        const combDelay = audioCtx.createDelay(0.05);
        combDelay.delayTime.value = lerp(0.003, 0.015, t);
        const combFeedback = audioCtx.createGain();
        combFeedback.gain.value = lerp(0.35, 0.65, t);

        ringGain.connect(combDelay);
        combDelay.connect(combFeedback);
        combFeedback.connect(combDelay);
        return { inputNode: ringGain, outputNode: combDelay };
      }

      case "voice3": {
        const lowShelf = audioCtx.createBiquadFilter();
        lowShelf.type = "lowshelf";
        lowShelf.frequency.value = 300;
        lowShelf.gain.value = lerp(8, 20, t);

        const highShelf = audioCtx.createBiquadFilter();
        highShelf.type = "highshelf";
        highShelf.frequency.value = 1500;
        highShelf.gain.value = lerp(-6, -18, t);

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
        activeOscillators.push(tremolo);

        const waveshaper = audioCtx.createWaveShaper();
        waveshaper.curve = makeDistortionCurve(lerp(80, 280, t));
        waveshaper.oversample = "4x";

        lowShelf.connect(highShelf);
        highShelf.connect(tremoloGain);
        tremoloGain.connect(waveshaper);
        return { inputNode: lowShelf, outputNode: waveshaper };
      }

      default: {
        /* Passthrough — should not normally be called for 'normal' */
        const pass = audioCtx.createGain();
        return { inputNode: pass, outputNode: pass };
      }
    }
  }

  /**
   * Build a single dry/wet effect segment for one mode at the given level.
   * @param {string} mode      - effect key
   * @param {number} level     - 0–1 (0 = fully bypassed, 1 = 100% wet)
   * @param {AudioNode} prevNode - the node that feeds into this segment
   * @returns {AudioNode} - the merger/output node to use as input for the next segment
   */
  function buildEffectSegment(mode, level, prevNode) {
    const merger = audioCtx.createGain();

    /* Dry path (1 − level) */
    const dryGain = audioCtx.createGain();
    dryGain.gain.value = Math.max(0, 1 - level);
    prevNode.connect(dryGain);
    dryGain.connect(merger);

    /* Wet path (level) */
    const { inputNode, outputNode } = buildEffectNodes(mode, level);
    const wetGain = audioCtx.createGain();
    wetGain.gain.value = level;
    prevNode.connect(inputNode);
    outputNode.connect(wetGain);
    wetGain.connect(merger);

    return merger;
  }

  /**
   * Tear down the current chain and rebuild it from effectLevels.
   * Active effects (level > 0) are applied in EFFECT_ORDER as dry/wet segments in series.
   * When all levels are 0 the signal passes through unchanged (normal mode).
   */
  function buildCombinedChain() {
    disconnectSource();
    if (!audioCtx || !sourceNode || !inputGainNode || !destinationNode) return;

    sourceNode.connect(inputGainNode);

    const activeEffects = EFFECT_ORDER.filter((m) => effectLevels[m] > 0);

    if (activeEffects.length === 0) {
      /* No effects active — plain passthrough */
      inputGainNode.connect(destinationNode);
      return;
    }

    let prevNode = inputGainNode;
    for (const mode of activeEffects) {
      prevNode = buildEffectSegment(mode, effectLevels[mode], prevNode);
    }
    prevNode.connect(destinationNode);
  }

  /* ── Public API ── */

  /**
   * Initialise the voice changer with a raw microphone MediaStream.
   * Returns a MediaStream containing only the processed audio track.
   * Safe to call multiple times — tears down any previous context first.
   */
  function init(rawStream) {
    destroy();

    let newAudioCtx = null;
    try {
      newAudioCtx = new (window.AudioContext || window.webkitAudioContext)();

      const newSourceNode = newAudioCtx.createMediaStreamSource(rawStream);
      const newInputGainNode = newAudioCtx.createGain();
      newInputGainNode.gain.value = micGain;

      const newDestinationNode = newAudioCtx.createMediaStreamDestination();

      const newMonitorGain = newAudioCtx.createGain();
      newMonitorGain.gain.value = monitorEnabled ? monitorVolume : 0;
      newMonitorGain.connect(newAudioCtx.destination);

      /* Assign module-level state only after all nodes are created successfully */
      audioCtx = newAudioCtx;
      sourceNode = newSourceNode;
      inputGainNode = newInputGainNode;
      destinationNode = newDestinationNode;
      monitorGain = newMonitorGain;

      buildCombinedChain();
      processedStream = destinationNode.stream;

      monitorSourceNode = audioCtx.createMediaStreamSource(processedStream);
      monitorSourceNode.connect(monitorGain);
    } catch {
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

  /* ── Combined-effects API ── */

  /**
   * Set the intensity level of a single effect (0 = off / bypass, 1 = full effect).
   * Multiple effects can be active simultaneously.
   * Rebuilds the chain immediately.
   */
  function setEffectLevel(mode, level) {
    if (!effectLevels.hasOwnProperty(mode)) return 0;
    effectLevels[mode] = Math.max(0, Math.min(1, Number(level)));
    buildCombinedChain();
    return effectLevels[mode];
  }

  /** Return a shallow copy of the current effectLevels map. */
  function getEffectLevels() {
    return { ...effectLevels };
  }

  /**
   * Toggle a single effect on (at _globalIntensity) or off (0).
   * Returns the new level.
   */
  function toggleEffect(mode) {
    if (!effectLevels.hasOwnProperty(mode)) return 0;
    const newLevel = effectLevels[mode] > 0 ? 0 : _globalIntensity;
    effectLevels[mode] = newLevel;
    buildCombinedChain();
    return newLevel;
  }

  /* ── Backward-compatible single-mode API ── */

  /**
   * Set a single exclusive voice effect, clearing all others.
   * Backward-compatible with older call sites and tests.
   */
  function setMode(mode) {
    if (!MODES[mode]) return;
    _primaryMode = mode;
    /* Exclusive: clear all effect levels */
    EFFECT_ORDER.forEach((m) => {
      effectLevels[m] = 0;
    });
    if (mode !== "normal") {
      effectLevels[mode] = _globalIntensity;
    }
    buildCombinedChain();
  }

  /** Return the primary mode set via setMode() (backward compat). */
  function getMode() {
    return _primaryMode;
  }

  /**
   * Set the global intensity applied when toggling effects on.
   * Also updates the primary mode's level if set via setMode().
   * Backward-compatible with the single-intensity API.
   */
  function setEffectIntensity(v) {
    _globalIntensity = Math.max(0, Math.min(1, Number(v)));
    if (_primaryMode !== "normal" && effectLevels.hasOwnProperty(_primaryMode)) {
      effectLevels[_primaryMode] = _globalIntensity;
      buildCombinedChain();
    }
    return _globalIntensity;
  }

  function getEffectIntensity() {
    return _globalIntensity;
  }

  /* ── Monitor API ── */

  function toggleMonitor() {
    monitorEnabled = !monitorEnabled;
    if (monitorGain) {
      monitorGain.gain.value = monitorEnabled ? monitorVolume : 0;
    }
    return monitorEnabled;
  }

  function setMonitorVolume(v) {
    monitorVolume = Math.max(0, Math.min(1, Number(v)));
    if (monitorGain && monitorEnabled) {
      monitorGain.gain.value = monitorVolume;
    }
    return monitorVolume;
  }

  function setMicGain(v) {
    micGain = Math.max(0, Math.min(2, Number(v)));
    if (inputGainNode) {
      inputGainNode.gain.value = micGain;
    }
    return micGain;
  }

  /* ── Getters ── */

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

  /** Release all audio resources. */
  function destroy() {
    activeOscillators.forEach((osc) => {
      try {
        osc.stop();
      } catch {
        /* may already be stopped */
      }
      try {
        osc.disconnect();
      } catch {
        /* ignore */
      }
    });
    activeOscillators = [];

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

    /* Reset effect state */
    EFFECT_ORDER.forEach((m) => {
      effectLevels[m] = 0;
    });
    _primaryMode = "normal";

    /* monitorEnabled intentionally reset — silently re-enabling without user action is surprising */
    monitorEnabled = false;
    /* monitorVolume, micGain, _globalIntensity are user preferences preserved across destroy/init */
  }

  return {
    init,
    destroy,
    /* Combined-effects API */
    setEffectLevel,
    getEffectLevels,
    toggleEffect,
    /* Backward-compat single-mode API */
    setMode,
    getMode,
    getModes,
    setEffectIntensity,
    getEffectIntensity,
    /* Monitor / mic API */
    toggleMonitor,
    setMonitorVolume,
    setMicGain,
    /* Getters */
    getProcessedStream,
    getMonitorEnabled,
    getMonitorVolume,
    getMicGain,
  };
})();
