/**
 * BLT-SafeCloak — voice-changer.js
 * Real-time voice effects using the Web Audio API.
 * Processes the microphone stream through an effect chain and exposes
 * a processed MediaStream that can be fed into WebRTC peer connections.
 */

const VoiceChanger = (() => {
  let audioCtx = null;
  let sourceNode = null;
  let destinationNode = null;
  let currentMode = "normal";
  let processedStream = null;

  const MODES = {
    normal: {
      label: "Normal",
      icon: "fa-microphone",
      description: "No voice effect applied",
    },
    deep: {
      label: "Deep",
      icon: "fa-down-long",
      description: "Lower, deeper voice tone",
    },
    chipmunk: {
      label: "Chipmunk",
      icon: "fa-up-long",
      description: "Higher-pitched squeaky voice",
    },
    robot: {
      label: "Robot",
      icon: "fa-robot",
      description: "Robotic ring-modulation effect",
    },
    echo: {
      label: "Echo",
      icon: "fa-wave-square",
      description: "Reverb and echo effect",
    },
  };

  /* ── Helpers ── */

  function makeDistortionCurve(amount) {
    const n = 512;
    const curve = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      const x = (i * 2) / n - 1;
      curve[i] = ((Math.PI + amount) * x) / (Math.PI + amount * Math.abs(x));
    }
    return curve;
  }

  function disconnectSource() {
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
    if (!audioCtx || !sourceNode || !destinationNode) return;

    switch (mode) {
      case "deep": {
        /* Boost bass, attenuate treble → deeper sounding voice */
        const lowShelf = audioCtx.createBiquadFilter();
        lowShelf.type = "lowshelf";
        lowShelf.frequency.value = 250;
        lowShelf.gain.value = 9;

        const highShelf = audioCtx.createBiquadFilter();
        highShelf.type = "highshelf";
        highShelf.frequency.value = 2000;
        highShelf.gain.value = -8;

        const gain = audioCtx.createGain();
        gain.gain.value = 1.1;

        sourceNode.connect(lowShelf);
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
        lowShelf.gain.value = -10;

        const highpass = audioCtx.createBiquadFilter();
        highpass.type = "highpass";
        highpass.frequency.value = 600;
        highpass.Q.value = 0.7;

        const peaking = audioCtx.createBiquadFilter();
        peaking.type = "peaking";
        peaking.frequency.value = 3200;
        peaking.gain.value = 8;
        peaking.Q.value = 1;

        sourceNode.connect(lowShelf);
        lowShelf.connect(highpass);
        highpass.connect(peaking);
        peaking.connect(destinationNode);
        break;
      }

      case "robot": {
        /* Ring modulation: multiply source by a low-frequency oscillator */
        const oscillator = audioCtx.createOscillator();
        oscillator.type = "square";
        oscillator.frequency.value = 60;

        /* The oscillator drives the gain of a GainNode that the source passes through */
        const ringGain = audioCtx.createGain();
        ringGain.gain.value = 0; /* oscillator will modulate this */

        oscillator.connect(ringGain.gain);
        oscillator.start();

        const waveshaper = audioCtx.createWaveShaper();
        waveshaper.curve = makeDistortionCurve(80);
        waveshaper.oversample = "4x";

        const bandpass = audioCtx.createBiquadFilter();
        bandpass.type = "bandpass";
        bandpass.frequency.value = 1400;
        bandpass.Q.value = 0.6;

        const gainOut = audioCtx.createGain();
        gainOut.gain.value = 1.4;

        sourceNode.connect(ringGain);
        ringGain.connect(waveshaper);
        waveshaper.connect(bandpass);
        bandpass.connect(gainOut);
        gainOut.connect(destinationNode);
        break;
      }

      case "echo": {
        /* Short delay with feedback loop mixed with the dry signal */
        const delay = audioCtx.createDelay(1.0);
        delay.delayTime.value = 0.22;

        const feedback = audioCtx.createGain();
        feedback.gain.value = 0.38;

        const dryGain = audioCtx.createGain();
        dryGain.gain.value = 0.8;

        const wetGain = audioCtx.createGain();
        wetGain.gain.value = 0.55;

        /* Dry path */
        sourceNode.connect(dryGain);
        dryGain.connect(destinationNode);

        /* Wet path with feedback */
        sourceNode.connect(delay);
        delay.connect(feedback);
        feedback.connect(delay);
        delay.connect(wetGain);
        wetGain.connect(destinationNode);
        break;
      }

      default: /* normal — direct passthrough */
        sourceNode.connect(destinationNode);
    }
  }

  /* ── Public API ── */

  /**
   * Initialise the voice changer with a raw microphone MediaStream.
   * Returns a new MediaStream that contains only the processed audio track
   * and can be combined with a video track for WebRTC transmission.
   */
  function init(rawStream) {
    try {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      sourceNode = audioCtx.createMediaStreamSource(rawStream);
      destinationNode = audioCtx.createMediaStreamDestination();
      buildChain(currentMode);
      processedStream = destinationNode.stream;
    } catch {
      /* Web Audio API unavailable — fall back to raw stream */
      processedStream = rawStream;
    }
    return processedStream;
  }

  /** Switch the active voice effect at any time (even during an active call). */
  function setMode(mode) {
    if (!MODES[mode]) return;
    currentMode = mode;
    buildChain(mode);
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

  /** Release all audio resources. */
  function destroy() {
    disconnectSource();
    if (audioCtx) {
      audioCtx.close();
      audioCtx = null;
    }
    sourceNode = null;
    destinationNode = null;
    processedStream = null;
    currentMode = "normal";
  }

  return { init, setMode, getMode, getModes, getProcessedStream, destroy };
})();
