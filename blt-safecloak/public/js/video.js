/**
 * BLT-SafeCloak — video.js
 * Secure video chat using WebRTC (via PeerJS) with consent recording
 */

const VideoChat = (() => {
  let peer = null;
  let localStream = null;
  let voiceStream = null; /* localStream video + processed audio for WebRTC */
  const activeCalls = new Map(); // peerId -> MediaConnection
  const activeDataConns = new Map(); // peerId -> DataConnection
  let audioContext = null;
  let analyser = null;
  let voiceAnimFrame = null;
  let micMuted = true;
  let camOff = true;
  let consentGiven = false;
  let screenSharing = false;
  let initialMediaPreferences = { mic: true, cam: true };
  const VOICE_PREFS_STORAGE_KEY = "blt-safecloak-voice-preferences";
  const DISPLAY_NAME_STORAGE_KEY = "blt-safecloak-display-name";
  const PROFILE_BROADCAST_THROTTLE_MS = 220;
  const SPEAKING_THRESHOLD = 28;
  const SPEAKING_HOLD_MS = 260;

  const peerProfiles = new Map(); // peerId -> { name, initials, micMuted, camOff }
  const remoteSpeakingMonitors = new Map(); // peerId -> { analyser, data, source, activeUntil }
  let speakingLoopFrame = null;
  let speakingAudioContext = null;
  let localSpeakingUntil = 0;
  const lastProfileBroadcastAt = new Map(); // peerId -> timestamp

  const state = {
    peerId: null,
    connected: false,
    sessionId: null,
    sessionKey: null,
    displayName: "You",
    displayInitials: "YU",
  };

  /* ── DOM helpers ── */
  const $ = (id) => document.getElementById(id);

  function updateStatus(text, type = "muted") {
    const el = $("connection-status");
    if (!el) return;
    el.textContent = text;
    el.className = `text-${type}`;
  }

  function setDotStatus(status) {
    const dot = $("status-dot");
    if (dot) dot.className = `status-dot ${status}`;
  }

  function normalizeDisplayName(value) {
    return (value || "").trim().replace(/\s+/g, " ").slice(0, 40);
  }

  function makeInitials(name) {
    const words = normalizeDisplayName(name).split(" ").filter(Boolean);
    if (words.length >= 2) {
      return `${words[0][0] || ""}${words[1][0] || ""}`.toUpperCase();
    }
    const first = words[0] || "";
    return first.slice(0, 2).toUpperCase() || "NA";
  }

  function resolveDisplayName() {
    const params = new URLSearchParams(window.location.search);
    const fromUrl = normalizeDisplayName(params.get("name"));
    if (fromUrl) {
      try {
        window.sessionStorage.setItem(DISPLAY_NAME_STORAGE_KEY, fromUrl);
      } catch {
        /* ignore storage failures */
      }
      return fromUrl;
    }

    try {
      const fromStorage = normalizeDisplayName(window.sessionStorage.getItem(DISPLAY_NAME_STORAGE_KEY));
      if (fromStorage) return fromStorage;
    } catch {
      /* ignore storage failures */
    }

    return "Guest";
  }

  function getProfileForPeer(peerId) {
    if (peerId === state.peerId || peerId === "local") {
      return {
        name: state.displayName,
        initials: state.displayInitials,
        micMuted: isLocalMicMutedState(),
        camOff: isLocalCamOffState(),
      };
    }
    const profile = peerProfiles.get(peerId);
    if (profile) return profile;
    return {
      name: peerId,
      initials: makeInitials(peerId),
      micMuted: false,
      camOff: false,
    };
  }

  function getDisplayLabel(peerId) {
    if (peerId === state.peerId || peerId === "local") return "You";
    return getProfileForPeer(peerId).name || peerId;
  }

  function getSelfProfilePayload() {
    return {
      type: "profile",
      id: state.peerId,
      name: state.displayName,
      initials: state.displayInitials,
      micMuted: isLocalMicMutedState(),
      camOff: screenSharing ? false : isLocalCamOffState(),
    };
  }

  function isLocalMicMutedState() {
    const hasAudioTrack = Boolean(localStream && localStream.getAudioTracks().length);
    return !hasAudioTrack || micMuted;
  }

  function isLocalCamOffState() {
    if (screenSharing) return false;
    const hasVideoTrack = Boolean(localStream && localStream.getVideoTracks().length);
    return !hasVideoTrack || camOff;
  }

  function setAvatarVisibility(avatarEl, visible) {
    if (!avatarEl) return;
    avatarEl.classList.toggle("hidden", !visible);
    avatarEl.style.display = visible ? "flex" : "none";
  }

  function getTileElements(peerId) {
    const isLocal = peerId === "local" || peerId === state.peerId;
    const wrapper = isLocal ? $("wrapper-local") : $(`wrapper-${peerId}`);
    if (!wrapper) return null;

    return {
      wrapper,
      dot: wrapper.querySelector(".status-dot"),
      video: wrapper.querySelector("video"),
      avatar: wrapper.querySelector(".video-avatar"),
      avatarInitials: wrapper.querySelector(".video-avatar-initials"),
      avatarName: wrapper.querySelector(".video-avatar-name"),
      speaking: wrapper.querySelector(".video-speaking-indicator"),
      stateMic:
        wrapper.querySelector('[data-state="mic"]') || (isLocal ? $("state-icon-local-mic") : null),
      stateCam:
        wrapper.querySelector('[data-state="cam"]') || (isLocal ? $("state-icon-local-cam") : null),
      labelName:
        wrapper.querySelector('[data-role="label-name"]') || (isLocal ? $("label-local-name") : null),
    };
  }

  function setTileStateIcon(iconEl, kind, isOff) {
    if (!iconEl) return;
    iconEl.classList.toggle("off", Boolean(isOff));
    if (kind === "mic") {
      iconEl.innerHTML = isOff
        ? '<i class="fa-solid fa-microphone-slash" aria-hidden="true"></i>'
        : '<i class="fa-solid fa-microphone" aria-hidden="true"></i>';
      return;
    }
    if (kind === "cam") {
      iconEl.innerHTML = isOff
        ? '<i class="fa-solid fa-video-slash" aria-hidden="true"></i>'
        : '<i class="fa-solid fa-video" aria-hidden="true"></i>';
    }
  }

  function setTileSpeakingIndicator(peerId, active) {
    const tile = getTileElements(peerId);
    if (!tile || !tile.speaking) return;
    tile.speaking.classList.toggle("active", Boolean(active));
  }

  function ensureRemoteTile(peerId) {
    const existing = getTileElements(peerId);
    if (existing) return existing;

    const profile = getProfileForPeer(peerId);
    const videoWrapper = document.createElement("div");
    videoWrapper.className = "video-wrapper rounded-xl bg-gray-900";
    videoWrapper.id = `wrapper-${peerId}`;

    const videoEl = document.createElement("video");
    videoEl.autoplay = true;
    videoEl.playsInline = true;
    videoEl.setAttribute("aria-label", `Participant ${profile.name} video`);
    videoWrapper.appendChild(videoEl);

    const avatar = document.createElement("div");
    avatar.className = "video-avatar hidden";
    avatar.style.display = "none";
    avatar.setAttribute("aria-hidden", "true");

    const avatarInitials = document.createElement("div");
    avatarInitials.className = "video-avatar-initials";
    avatarInitials.textContent = profile.initials;

    const avatarName = document.createElement("div");
    avatarName.className = "video-avatar-name";
    avatarName.textContent = profile.name;

    avatar.appendChild(avatarInitials);
    avatar.appendChild(avatarName);
    videoWrapper.appendChild(avatar);

    const speaking = document.createElement("div");
    speaking.className = "video-speaking-indicator";
    speaking.setAttribute("aria-hidden", "true");
    speaking.innerHTML = '<i class="fa-solid fa-volume-high" aria-hidden="true"></i>';
    videoWrapper.appendChild(speaking);

    const stateIcons = document.createElement("div");
    stateIcons.className = "video-state-icons";
    stateIcons.setAttribute("aria-hidden", "true");

    const micIcon = document.createElement("span");
    micIcon.className = "video-state-icon";
    micIcon.dataset.state = "mic";
    micIcon.innerHTML = '<i class="fa-solid fa-microphone" aria-hidden="true"></i>';

    const camIcon = document.createElement("span");
    camIcon.className = "video-state-icon";
    camIcon.dataset.state = "cam";
    camIcon.innerHTML = '<i class="fa-solid fa-video" aria-hidden="true"></i>';

    stateIcons.appendChild(micIcon);
    stateIcons.appendChild(camIcon);
    videoWrapper.appendChild(stateIcons);

    const label = document.createElement("div");
    label.className =
      "video-label rounded-md bg-black/65 px-2 py-1 text-xs text-white flex items-center gap-2";
    label.id = `label-${peerId}`;

    const labelDot = document.createElement("span");
    labelDot.className = "status-dot connecting";
    labelDot.setAttribute("aria-hidden", "true");
    labelDot.id = `dot-${peerId}`;

    const labelText = document.createElement("span");
    labelText.className = "max-w-[145px] truncate font-semibold";
    labelText.dataset.role = "label-name";
    labelText.textContent = profile.name;

    label.appendChild(labelDot);
    label.appendChild(labelText);
    videoWrapper.appendChild(label);

    const videoGrid = $("video-grid");
    if (videoGrid) {
      videoGrid.appendChild(videoWrapper);
    }

    return getTileElements(peerId);
  }

  function updateTilePresentation(peerId) {
    const tile = getTileElements(peerId);
    if (!tile) return;

    const isLocal = peerId === "local" || peerId === state.peerId;
    const profile = getProfileForPeer(peerId);
    const displayName = isLocal ? state.displayName : profile.name;
    const initials = profile.initials || makeInitials(displayName);
    const micIsMuted = isLocal ? isLocalMicMutedState() : Boolean(profile.micMuted);
    const cameraIsOff = isLocal ? isLocalCamOffState() : Boolean(profile.camOff);

    if (tile.dot) {
      tile.dot.className = `status-dot ${isLocal || activeCalls.has(peerId) ? "online" : "connecting"}`;
    }
    if (tile.labelName) {
      tile.labelName.textContent = isLocal ? "You" : displayName;
      tile.labelName.title = displayName;
    }
    if (tile.video) {
      tile.video.setAttribute("aria-label", isLocal ? "Your video" : `Participant ${displayName} video`);
    }
    if (tile.avatarInitials) {
      tile.avatarInitials.textContent = initials;
    }
    if (tile.avatarName) {
      tile.avatarName.textContent = displayName;
    }

    setAvatarVisibility(tile.avatar, cameraIsOff);
    setTileStateIcon(tile.stateMic, "mic", micIsMuted);
    setTileStateIcon(tile.stateCam, "cam", cameraIsOff);

    if (micIsMuted) {
      setTileSpeakingIndicator(peerId, false);
    }
  }

  function updateLocalTilePresentation() {
    updateTilePresentation("local");
  }

  function ensureSpeakingAudioContext() {
    if (speakingAudioContext) return speakingAudioContext;
    try {
      speakingAudioContext = new (window.AudioContext || window.webkitAudioContext)();
      return speakingAudioContext;
    } catch {
      return null;
    }
  }

  function stopRemoteSpeakingMonitor(peerId) {
    const monitor = remoteSpeakingMonitors.get(peerId);
    if (!monitor) return;
    try {
      monitor.source.disconnect();
    } catch {
      /* ignore disconnect failures */
    }
    remoteSpeakingMonitors.delete(peerId);
    setTileSpeakingIndicator(peerId, false);
  }

  function stopAllRemoteSpeakingMonitors() {
    Array.from(remoteSpeakingMonitors.keys()).forEach((peerId) => stopRemoteSpeakingMonitor(peerId));
    if (speakingLoopFrame) {
      cancelAnimationFrame(speakingLoopFrame);
      speakingLoopFrame = null;
    }
  }

  function runSpeakingLoop() {
    if (speakingLoopFrame) return;

    const step = () => {
      const now = performance.now();

      remoteSpeakingMonitors.forEach((monitor, peerId) => {
        try {
          monitor.analyser.getByteFrequencyData(monitor.data);
          const sum = monitor.data.reduce((acc, value) => acc + value, 0);
          const avg = monitor.data.length ? sum / monitor.data.length : 0;
          if (avg >= SPEAKING_THRESHOLD) {
            monitor.activeUntil = now + SPEAKING_HOLD_MS;
          }
          const profile = getProfileForPeer(peerId);
          const speakingNow = monitor.activeUntil > now && !Boolean(profile.micMuted);
          setTileSpeakingIndicator(peerId, speakingNow);
        } catch {
          stopRemoteSpeakingMonitor(peerId);
        }
      });

      if (remoteSpeakingMonitors.size === 0) {
        speakingLoopFrame = null;
        return;
      }
      speakingLoopFrame = requestAnimationFrame(step);
    };

    speakingLoopFrame = requestAnimationFrame(step);
  }

  function attachRemoteSpeakingMonitor(peerId, stream) {
    stopRemoteSpeakingMonitor(peerId);
    if (!stream || !stream.getAudioTracks || stream.getAudioTracks().length === 0) {
      return;
    }

    const ctx = ensureSpeakingAudioContext();
    if (!ctx) return;
    if (ctx.state === "suspended") {
      ctx.resume().catch(() => {});
    }

    try {
      const source = ctx.createMediaStreamSource(stream);
      const analyserNode = ctx.createAnalyser();
      analyserNode.fftSize = 256;
      source.connect(analyserNode);
      remoteSpeakingMonitors.set(peerId, {
        analyser: analyserNode,
        data: new Uint8Array(analyserNode.frequencyBinCount),
        source,
        activeUntil: 0,
      });
      runSpeakingLoop();
    } catch {
      /* audio monitor not available for this stream */
    }
  }

  function upsertRemoteProfile(peerId, payload) {
    if (!peerId || peerId === state.peerId) return;

    const prev = peerProfiles.get(peerId) || {
      name: peerId,
      initials: makeInitials(peerId),
      micMuted: false,
      camOff: false,
    };
    const normalizedName = normalizeDisplayName(payload && payload.name);

    const profile = {
      name: normalizedName || prev.name,
      initials: makeInitials(normalizedName || prev.name),
      micMuted:
        payload && typeof payload.micMuted === "boolean" ? payload.micMuted : Boolean(prev.micMuted),
      camOff: payload && typeof payload.camOff === "boolean" ? payload.camOff : Boolean(prev.camOff),
    };

    peerProfiles.set(peerId, profile);
    updateTilePresentation(peerId);
    updateParticipantsList();
  }

  function sendProfileTo(peerId, force = false) {
    const conn = activeDataConns.get(peerId);
    if (!conn || !conn.open || !state.peerId) return;

    const now = Date.now();
    const lastAt = lastProfileBroadcastAt.get(peerId) || 0;
    if (!force && now - lastAt < PROFILE_BROADCAST_THROTTLE_MS) {
      return;
    }

    conn.send(getSelfProfilePayload());
    lastProfileBroadcastAt.set(peerId, now);
  }

  function broadcastProfile(force = false) {
    activeDataConns.forEach((_conn, peerId) => {
      sendProfileTo(peerId, force);
    });
  }

  function ensureDataConn(remotePeerId) {
    if (!peer || !remotePeerId || remotePeerId === state.peerId) {
      return null;
    }

    const existing = activeDataConns.get(remotePeerId);
    if (existing) {
      return existing;
    }

    const conn = peer.connect(remotePeerId);
    setupDataConn(conn);
    return conn;
  }

  /* ── Browser detection ── */
  function detectBrowser() {
    const ua = navigator.userAgent;
    if (/Edg\//.test(ua)) return "edge";
    if (/OPR\/|Opera/.test(ua)) return "opera";
    if (/Chrome\//.test(ua)) return "chrome";
    if (/Firefox\//.test(ua)) return "firefox";
    if (/Safari\//.test(ua) && !/Chrome\/|Chromium\//.test(ua)) return "safari";
    return "other";
  }

  function getCameraInstructions(browser) {
    const steps = {
      chrome: `<strong>Google Chrome:</strong><ol style="margin:0.5rem 0 0 1.25rem;display:flex;flex-direction:column;gap:0.3rem">
        <li>Click the <strong>camera blocked</strong> icon (🔒 or 📷) in the address bar.</li>
        <li>Select <strong>Always allow</strong> for the camera and microphone, then click <strong>Done</strong>.</li>
        <li>Or go to <strong>Settings → Privacy and security → Site settings → Camera</strong> and allow this site.</li>
        <li>Reload the page and click <em>Try Again</em>.</li></ol>`,
      edge: `<strong>Microsoft Edge:</strong><ol style="margin:0.5rem 0 0 1.25rem;display:flex;flex-direction:column;gap:0.3rem">
        <li>Click the <strong>camera blocked</strong> icon (🔒 or 📷) in the address bar.</li>
        <li>Set Camera and Microphone permissions to <strong>Allow</strong>, then click <strong>Save</strong>.</li>
        <li>Or go to <strong>Settings → Cookies and site permissions → Camera</strong> and add this site to the allow list.</li>
        <li>Reload the page and click <em>Try Again</em>.</li></ol>`,
      firefox: `<strong>Mozilla Firefox:</strong><ol style="margin:0.5rem 0 0 1.25rem;display:flex;flex-direction:column;gap:0.3rem">
        <li>Click the <strong>camera blocked</strong> icon (🎥 with a slash) in the address bar.</li>
        <li>Click <strong>Blocked Temporarily</strong> or <strong>Blocked</strong> next to Camera and Microphone and choose <strong>Allow</strong>.</li>
        <li>Or go to <strong>about:preferences#privacy</strong> → Permissions → Camera → Settings, and allow this site.</li>
        <li>Reload the page and click <em>Try Again</em>.</li></ol>`,
      safari: `<strong>Safari:</strong><ol style="margin:0.5rem 0 0 1.25rem;display:flex;flex-direction:column;gap:0.3rem">
        <li>In the menu bar, go to <strong>Safari → Settings for This Website</strong> (or <strong>Preferences → Websites → Camera</strong>).</li>
        <li>Set Camera and Microphone to <strong>Allow</strong>.</li>
        <li>Reload the page and click <em>Try Again</em>.</li></ol>`,
      opera: `<strong>Opera:</strong><ol style="margin:0.5rem 0 0 1.25rem;display:flex;flex-direction:column;gap:0.3rem">
        <li>Click the <strong>camera blocked</strong> icon (🔒 or 📷) in the address bar.</li>
        <li>Select <strong>Always allow</strong> for the camera and microphone, then click <strong>Done</strong>.</li>
        <li>Or go to <strong>Settings → Privacy &amp; security → Site settings → Camera</strong> and allow this site.</li>
        <li>Reload the page and click <em>Try Again</em>.</li></ol>`,
      other: `<strong>Your browser:</strong><ol style="margin:0.5rem 0 0 1.25rem;display:flex;flex-direction:column;gap:0.3rem">
        <li>Look for a <strong>camera or lock icon</strong> in the address bar and click it.</li>
        <li>Set Camera and Microphone permissions to <strong>Allow</strong>.</li>
        <li>Check your browser's <strong>site settings / permissions</strong> page and ensure this site is not blocked.</li>
        <li>Reload the page and click <em>Try Again</em>.</li></ol>`,
    };
    return steps[browser] || steps.other;
  }

  function showCameraDenied() {
    const denied = $("camera-denied");
    const instructions = $("camera-denied-instructions");
    const mainGrid = $("main-grid");
    const permAlert = $("perm-alert");
    const callControls = $("call-controls");
    if (instructions) instructions.innerHTML = getCameraInstructions(detectBrowser());
    if (denied) denied.style.display = "flex";
    if (mainGrid) mainGrid.style.display = "none";
    if (permAlert) permAlert.style.display = "none";
    if (callControls) callControls.style.display = "none";
    const retryBtn = $("btn-camera-retry");
    if (retryBtn) retryBtn.addEventListener("click", () => location.reload());
  }

  /* ── Media ── */
  async function attachStream(stream) {
    const localVideo = $("local-video");
    if (localVideo) {
      localVideo.srcObject = stream;
      localVideo.muted = true;
    }

    /* Build a separate stream for WebRTC: original video + voice-changed audio */
    if (typeof VoiceChanger !== "undefined") {
      const processedAudio = VoiceChanger.init(stream);
      const videoTrack = stream.getVideoTracks()[0];
      const audioTrack = processedAudio.getAudioTracks()[0];
      const tracks = [videoTrack, audioTrack].filter(Boolean);
      voiceStream = tracks.length ? new MediaStream(tracks) : stream;
    } else {
      voiceStream = stream;
    }

    startVoiceMeter(stream);
    updateLocalTilePresentation();
    broadcastProfile(true);
  }

  function syncControlButtons() {
    const hasAudioTrack = Boolean(localStream && localStream.getAudioTracks().length);
    const hasVideoTrack = Boolean(localStream && localStream.getVideoTracks().length);

    const micBtn = $("btn-mic");
    if (micBtn) {
      if (!hasAudioTrack) {
        micBtn.innerHTML = '<i class="fa-solid fa-microphone-slash" aria-hidden="true"></i>';
        micBtn.title = "Microphone not available";
        micBtn.disabled = true;
        micBtn.classList.add("opacity-50", "cursor-not-allowed");
      } else {
        micBtn.innerHTML = micMuted
          ? '<i class="fa-solid fa-microphone-slash" aria-hidden="true"></i>'
          : '<i class="fa-solid fa-microphone" aria-hidden="true"></i>';
        micBtn.title = micMuted ? "Unmute mic" : "Mute mic";
        micBtn.disabled = false;
        micBtn.classList.remove("opacity-50", "cursor-not-allowed");
      }
      micBtn.setAttribute("aria-pressed", micMuted ? "true" : "false");
      micBtn.classList.toggle("active", micMuted);
    }

    const camBtn = $("btn-cam");
    if (camBtn) {
      if (!hasVideoTrack) {
        camBtn.innerHTML = '<i class="fa-solid fa-video-slash" aria-hidden="true"></i>';
        camBtn.title = "Camera not available";
        camBtn.disabled = true;
        camBtn.classList.add("opacity-50", "cursor-not-allowed");
      } else {
        camBtn.innerHTML = camOff
          ? '<i class="fa-solid fa-video-slash" aria-hidden="true"></i>'
          : '<i class="fa-solid fa-video" aria-hidden="true"></i>';
        camBtn.title = camOff ? "Enable camera" : "Disable camera";
        camBtn.disabled = false;
        camBtn.classList.remove("opacity-50", "cursor-not-allowed");
      }
      camBtn.setAttribute("aria-pressed", camOff ? "true" : "false");
      camBtn.classList.toggle("active", camOff);
    }
  }

  function applyInitialMediaPreferences() {
    if (!localStream) return;

    const hasAudioTrack = localStream.getAudioTracks().length > 0;
    const hasVideoTrack = localStream.getVideoTracks().length > 0;

    micMuted = hasAudioTrack ? !initialMediaPreferences.mic : false;
    camOff = hasVideoTrack ? !initialMediaPreferences.cam : false;

    if (hasAudioTrack) {
      localStream.getAudioTracks().forEach((track) => (track.enabled = !micMuted));
    }
    if (hasVideoTrack) {
      localStream.getVideoTracks().forEach((track) => (track.enabled = !camOff));
    }

    syncControlButtons();
    updateLocalTilePresentation();
    broadcastProfile(true);
  }

  let mediaPromise = null;

  async function startLocalMedia() {
    if (mediaPromise) return mediaPromise;
    mediaPromise = (async () => {
      // 1. Try full video + audio
      try {
        localStream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: true,
        });
        await attachStream(localStream);
        applyInitialMediaPreferences();
        return true;
      } catch (err) {
        if (
          err.name === "NotAllowedError" ||
          err.name === "PermissionDeniedError" ||
          err.name === "SecurityError"
        ) {
          showCameraDenied();
          return false;
        }

        if (err.name === "NotReadableError" || err.name === "TrackStartError") {
          showToast(
            "Camera or microphone is already in use by another application. Please close it and reload.",
            "error"
          );
          return false;
        }

        // For NotFoundError / DevicesNotFoundError try partial fallbacks below.
        if (err.name !== "NotFoundError" && err.name !== "DevicesNotFoundError") {
          showToast("Could not access camera/microphone: " + err.message, "error");
          return false;
        }
      }

      // 2. No combined device found — try audio-only
      try {
        localStream = await navigator.mediaDevices.getUserMedia({
          video: false,
          audio: true,
        });
        await attachStream(localStream);
        applyInitialMediaPreferences();
        showToast("No camera found — joining with audio only", "warning");
        return true;
      } catch (audioErr) {
        if (
          audioErr.name === "NotAllowedError" ||
          audioErr.name === "PermissionDeniedError" ||
          audioErr.name === "SecurityError"
        ) {
          showCameraDenied();
          return false;
        }
        if (
          audioErr.name !== "NotFoundError" &&
          audioErr.name !== "DevicesNotFoundError"
        ) {
          showToast("Could not access microphone: " + audioErr.message, "error");
          return false;
        }
      }

      // 3. No microphone either — try video-only
      try {
        localStream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: false,
        });
        await attachStream(localStream);
        applyInitialMediaPreferences();
        showToast("No microphone found — joining with video only", "warning");
        return true;
      } catch (videoErr) {
        if (
          videoErr.name === "NotAllowedError" ||
          videoErr.name === "PermissionDeniedError" ||
          videoErr.name === "SecurityError"
        ) {
          showCameraDenied();
          return false;
        }
        if (
          videoErr.name === "NotReadableError" ||
          videoErr.name === "TrackStartError"
        ) {
          showToast(
            "Camera is already in use by another application. Please close it and reload.",
            "error"
          );
          return false;
        }
        if (
          videoErr.name !== "NotFoundError" &&
          videoErr.name !== "DevicesNotFoundError"
        ) {
          showToast("Could not access camera: " + videoErr.message, "error");
          return false;
        }
      }

      // 4. No devices at all
      showToast(
        "No camera or microphone found. Please connect a device and try reloading the page.",
        "error"
      );
      return false;
    })();

    const result = await mediaPromise;
    if (!result) mediaPromise = null; // Allow retry if it failed
    return result;
  }

  function startVoiceMeter(stream) {
    try {
      if (voiceAnimFrame) {
        cancelAnimationFrame(voiceAnimFrame);
        voiceAnimFrame = null;
      }
      if (audioContext) {
        audioContext.close().catch(() => {});
      }
      audioContext = new (window.AudioContext || window.webkitAudioContext)();
      analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      const src = audioContext.createMediaStreamSource(stream);
      src.connect(analyser);
      animateVoiceMeter();
    } catch {
      /* audio context not available */
    }
  }

  function animateVoiceMeter() {
    const bars = document.querySelectorAll(".voice-bar");
    if (!analyser) return;
    const data = new Uint8Array(analyser.frequencyBinCount);
    function frame() {
      analyser.getByteFrequencyData(data);

      if (bars.length) {
        const slice = Math.floor(data.length / bars.length);
        bars.forEach((bar, i) => {
          const avg = data.slice(i * slice, (i + 1) * slice).reduce((a, b) => a + b, 0) / slice;
          bar.style.height = `${Math.max(4, (avg / 255) * 24)}px`;
        });
      }

      const now = performance.now();
      const sum = data.reduce((acc, value) => acc + value, 0);
      const avg = data.length ? sum / data.length : 0;
      if (avg >= SPEAKING_THRESHOLD) {
        localSpeakingUntil = now + SPEAKING_HOLD_MS;
      }
      setTileSpeakingIndicator("local", localSpeakingUntil > now && !isLocalMicMutedState());

      voiceAnimFrame = requestAnimationFrame(frame);
    }
    frame();
  }

  /* ── PeerJS setup ── */
  async function initPeer() {
    if (typeof Peer === "undefined") {
      showToast("PeerJS not loaded", "error");
      return;
    }
    state.peerId = Crypto.randomId(6);
    state.sessionKey = await Crypto.generateKey();
    state.sessionId = state.peerId;

    peer = new Peer(
      state.peerId,
      Object.assign(
        {
          host: "0.peerjs.com",
          port: 443,
          secure: true,
          path: "/",
          debug: 0,
        },
        window.__PEERJS_CONFIG__ || {}
      )
    );

    peer.on("open", (id) => {
      $("my-peer-id") && ($("my-peer-id").textContent = id);
      updateStatus("Ready — share your Room ID", "secondary");
      setDotStatus("online");
      updateLocalTilePresentation();
      showToast("Connected to signaling server", "success");
      // Auto-connect if a room ID was passed in the URL
      const params = new URLSearchParams(window.location.search);
      const joinId = params.get("room");
      if (joinId && joinId !== state.peerId) {
        const remoteInput = $("remote-id");
        if (remoteInput) {
          remoteInput.value = joinId;
        }
        callPeer(joinId);
      }
    });

    peer.on("call", async (incomingCall) => {
      if (activeCalls.has(incomingCall.peer)) {
        incomingCall.close();
        return;
      }
      if (!consentGiven) {
        const ok = await askConsent(incomingCall.peer);
        if (!ok) {
          incomingCall.close();
          return;
        }
      }
      activeCalls.set(incomingCall.peer, incomingCall);
      updateParticipantsList();
<<<<<<< HEAD
      incomingCall.answer(voiceStream || localStream);
=======

      if (!localStream) {
        micMuted = false;
        camOff = false;
        const ok = await startLocalMedia();
        if (!ok) {
          incomingCall.close();
          return;
        }
      }

      incomingCall.answer(localStream);
>>>>>>> 747222e (Delayed Media Permissions)
      handleCallStream(incomingCall);
      ensureDataConn(incomingCall.peer);
      sendPeerListTo(incomingCall.peer);
    });

    peer.on("connection", (conn) => {
      setupDataConn(conn);
    });

    peer.on("error", (err) => {
      updateStatus("Error: " + err.message, "danger");
      setDotStatus("offline");
      showToast("Connection error: " + err.type, "error");
    });

    peer.on("disconnected", () => {
      updateStatus("Disconnected", "warning");
      setDotStatus("offline");
    });
  }

  function updateParticipantsList() {
    const listEl = $("participants-list");
    const countEl = $("participant-count");
    if (countEl) {
      countEl.textContent = `${activeCalls.size} connected`;
    }
    if (!listEl) return;
    listEl.innerHTML = "";
    if (activeCalls.size === 0) {
      const empty = document.createElement("p");
      empty.className = "text-sm text-gray-500 text-center py-2";
      empty.textContent = "No participants connected";
      listEl.appendChild(empty);
      return;
    }
    activeCalls.forEach((_call, peerId) => {
      const item = document.createElement("div");
      item.className = "flex items-center justify-between gap-2 py-1 text-sm";

      const nameSpan = document.createElement("span");
      nameSpan.className = "flex min-w-0 items-center gap-2";

      const dot = document.createElement("span");
      dot.className = "status-dot online";
      dot.setAttribute("aria-hidden", "true");

      const textWrap = document.createElement("span");
      textWrap.className = "flex min-w-0 flex-col";

      const nameLabel = document.createElement("span");
      nameLabel.className = "truncate font-semibold text-gray-900";
      nameLabel.title = getDisplayLabel(peerId);
      nameLabel.textContent = getDisplayLabel(peerId);

      const idLabel = document.createElement("span");
      idLabel.className = "truncate font-mono text-[11px] text-gray-500";
      idLabel.title = peerId;
      idLabel.textContent = peerId;

      nameSpan.appendChild(dot);
      textWrap.appendChild(nameLabel);
      textWrap.appendChild(idLabel);
      nameSpan.appendChild(textWrap);

      const disconnectBtn = document.createElement("button");
      disconnectBtn.className = "control-btn";
      disconnectBtn.style.cssText = "width:32px;height:32px;font-size:0.75rem";
      disconnectBtn.title = `Disconnect ${getDisplayLabel(peerId)}`;
      disconnectBtn.setAttribute("aria-label", `Disconnect ${getDisplayLabel(peerId)}`);
      disconnectBtn.innerHTML = '<i class="fa-solid fa-phone-slash" aria-hidden="true"></i>';
      disconnectBtn.addEventListener("click", () => VideoChat.disconnectPeer(peerId));

      item.appendChild(nameSpan);
      item.appendChild(disconnectBtn);
      listEl.appendChild(item);
    });
  }

  function handleCallStream(call) {
    const remotePeerId = call.peer;
    const tile = ensureRemoteTile(remotePeerId);
    const videoEl = tile ? tile.video : null;
    updateTilePresentation(remotePeerId);

    call.on("stream", (remoteStream) => {
      if (videoEl) {
        videoEl.srcObject = remoteStream;
      }
      attachRemoteSpeakingMonitor(remotePeerId, remoteStream);
      updateTilePresentation(remotePeerId);
      state.connected = true;
      const count = activeCalls.size;
      updateStatus(
        `🔒 Encrypted call active (${count} participant${count !== 1 ? "s" : ""})`,
        "success"
      );
      setDotStatus("online");
<<<<<<< HEAD
=======
      if ($("call-controls")) {
        $("call-controls").classList.remove("hidden");
        $("btn-noise") && $("btn-noise").classList.remove("hidden");
        $("btn-screen") && $("btn-screen").classList.remove("hidden");
        $("btn-end") && $("btn-end").classList.remove("hidden");
      }
>>>>>>> 747222e (Delayed Media Permissions)
      updateParticipantsList();
      sendProfileTo(remotePeerId, true);
    });

    call.on("close", () => {
      activeCalls.delete(remotePeerId);
      const dataConn = activeDataConns.get(remotePeerId);
      if (dataConn) {
        try {
          dataConn.close();
        } catch {
          /* ignore close failures */
        }
      }
      stopRemoteSpeakingMonitor(remotePeerId);
      peerProfiles.delete(remotePeerId);
      lastProfileBroadcastAt.delete(remotePeerId);
      const wrapper = $(`wrapper-${remotePeerId}`);
      if (wrapper) wrapper.remove();
      if (activeCalls.size === 0) {
        state.connected = false;
        updateStatus("Call ended", "muted");
        setDotStatus("offline");
<<<<<<< HEAD
=======
        if ($("call-controls")) {
          $("btn-noise") && $("btn-noise").classList.add("hidden");
          $("btn-screen") && $("btn-screen").classList.add("hidden");
          $("btn-end") && $("btn-end").classList.add("hidden");
        }
>>>>>>> 747222e (Delayed Media Permissions)
      } else {
        const count = activeCalls.size;
        updateStatus(
          `🔒 Encrypted call active (${count} participant${count !== 1 ? "s" : ""})`,
          "success"
        );
      }
      updateParticipantsList();
    });

    call.on("error", (err) => {
      updateTilePresentation(remotePeerId);
      showToast("Call error: " + err.message, "error");
    });
  }

  /* ── Full-mesh helpers ── */
  function setupDataConn(conn) {
    if (!conn || !conn.peer) return;
    activeDataConns.set(conn.peer, conn);

    conn.on("open", () => {
      sendProfileTo(conn.peer, true);
    });

    conn.on("data", (data) => {
      if (data && data.type === "peers" && Array.isArray(data.ids)) {
        data.ids.forEach((id) => {
          const peerId = typeof id === "string" ? id.trim() : "";
          if (peerId && peerId !== state.peerId && !activeCalls.has(peerId)) {
            callPeer(peerId);
          }
        });
        return;
      }

      if (data && data.type === "profile") {
        const incomingPeerId =
          typeof data.id === "string" && data.id.trim() ? data.id.trim() : conn.peer;
        if (incomingPeerId === conn.peer) {
          upsertRemoteProfile(conn.peer, data);
        }
      }
    });

    const cleanup = () => {
      if (activeDataConns.get(conn.peer) === conn) {
        activeDataConns.delete(conn.peer);
      }
      lastProfileBroadcastAt.delete(conn.peer);
    };
    conn.on("close", cleanup);
    conn.on("error", cleanup);
  }

  function sendPeerListTo(remotePeerId) {
    const peerList = Array.from(activeCalls.keys()).filter((id) => id !== remotePeerId);
    if (peerList.length === 0) return;
    const conn = ensureDataConn(remotePeerId);
    if (!conn) return;

    const payload = { type: "peers", ids: peerList };
    const sendPayload = () => {
      if (conn.open) conn.send(payload);
    };
    if (conn.open) {
      sendPayload();
    } else {
      conn.on("open", sendPayload);
    }

    sendProfileTo(remotePeerId, true);
  }

  /* ── Input validation ── */
  function isValidRoomId(roomId) {
    if (!roomId || typeof roomId !== "string") return false;
    // Match the same character set used by Crypto.randomId(): uppercase A-Z (except I,O) + digits 2-9
    return /^[ABCDEFGHJKLMNPQRSTUVWXYZ23456789]{6}$/.test(roomId.trim());
  }

  async function callPeer(remotePeerId) {
    if (!peer) {
      showToast("Not connected to server", "error");
      return;
    }
    if (!localStream) {
      // If joining a call directly, enable both by default
      micMuted = false;
      camOff = false;
      const ok = await startLocalMedia();
      if (!ok) return;
    }
    if (!remotePeerId) {
      showToast("Enter a Room ID to call", "warning");
      return;
    }

    // Ensure remotePeerId is a string before trimming (defensive against network data)
    if (typeof remotePeerId !== "string") {
      showToast("Invalid Room ID format", "error");
      return;
    }

    // Normalize the peer ID by trimming whitespace
    remotePeerId = remotePeerId.trim();

    if (!remotePeerId) {
      showToast("Enter a Room ID to call", "warning");
      return;
    }

    if (!isValidRoomId(remotePeerId)) {
      showToast(
        "Room ID must be exactly 6 characters using only uppercase letters (A-Z except I,O) and digits (2-9)",
        "error"
      );
      return;
    }
    if (remotePeerId === state.peerId) {
      showToast("You cannot call yourself", "warning");
      return;
    }
    if (activeCalls.has(remotePeerId)) {
      showToast("Already connected to this participant", "warning");
      return;
    }

    if (!consentGiven) {
      const ok = await askConsent("the remote participant");
      if (!ok) return;
    }

    updateStatus("Calling…", "warning");
    setDotStatus("connecting");
    const call = peer.call(remotePeerId, voiceStream || localStream);
    activeCalls.set(remotePeerId, call);
    updateParticipantsList();
    handleCallStream(call);
    ensureDataConn(remotePeerId);
  }

  /* ── Controls ── */
  async function toggleMic() {
    micMuted = !micMuted;
    if (!localStream) {
      const ok = await startLocalMedia();
      if (!ok) {
        micMuted = true; // reset state
        return;
      }
    } else {
      localStream.getAudioTracks().forEach((t) => (t.enabled = !micMuted));
    }

    syncControlButtons();
    updateLocalTilePresentation();
    broadcastProfile(true);
    showToast(micMuted ? "Microphone muted" : "Microphone unmuted", "info");
  }

  async function toggleCamera() {
    camOff = !camOff;
    if (!localStream) {
      const ok = await startLocalMedia();
      if (!ok) {
        camOff = true; // reset state
        return;
      }
    } else {
      localStream.getVideoTracks().forEach((t) => (t.enabled = !camOff));
    }

    syncControlButtons();
    updateLocalTilePresentation();
    broadcastProfile(true);
    showToast(camOff ? "Camera disabled" : "Camera enabled", "info");
  }

  function disconnectPeer(peerId) {
    const call = activeCalls.get(peerId);
    if (call) {
      call.close();
    }
  }

  function endCall() {
    activeCalls.forEach((call) => call.close());
    activeCalls.clear();
    activeDataConns.forEach((conn) => conn.close());
    activeDataConns.clear();
    lastProfileBroadcastAt.clear();
    peerProfiles.clear();
    stopAllRemoteSpeakingMonitors();
    localSpeakingUntil = 0;
    setTileSpeakingIndicator("local", false);
    state.connected = false;
    updateStatus("Call ended", "muted");
    setDotStatus("offline");
    const videoGrid = $("video-grid");
    if (videoGrid) {
      videoGrid.querySelectorAll(".video-wrapper:not(:first-child)").forEach((w) => w.remove());
    }
    updateLocalTilePresentation();
    if ($("call-controls")) {
      $("btn-noise") && $("btn-noise").classList.add("hidden");
      $("btn-screen") && $("btn-screen").classList.add("hidden");
      $("btn-end") && $("btn-end").classList.add("hidden");
    }
    updateParticipantsList();
    showToast("Call ended", "info");
    // Record consent end
    ConsentManager &&
      ConsentManager.record({
        type: "recorded",
        name: "Call session ended",
        details: `Session ID: ${state.sessionId} — ended at ${new Date().toISOString()}`,
      });
  }

  function hangup() {
    endCall();
    if (peer) {
      peer.disconnect();
      peer.destroy();
      peer = null;
    }
    if (localStream) {
      localStream.getTracks().forEach((t) => t.stop());
      localStream = null;
    }
    voiceStream = null;
    if (voiceAnimFrame) {
      cancelAnimationFrame(voiceAnimFrame);
      voiceAnimFrame = null;
    }
    if (audioContext) {
      audioContext.close().catch(() => {});
      audioContext = null;
    }
    stopAllRemoteSpeakingMonitors();
    if (speakingAudioContext) {
      speakingAudioContext.close().catch(() => {});
      speakingAudioContext = null;
    }
    localSpeakingUntil = 0;
    setTileSpeakingIndicator("local", false);
    if (typeof VoiceChanger !== "undefined") VoiceChanger.destroy();
    /* Reset monitor button state */
    const monitorBtn = $("btn-monitor");
    if (monitorBtn) {
      monitorBtn.classList.remove("active");
      monitorBtn.setAttribute("aria-pressed", "false");
    }
    /* Reset voice mode buttons to normal, clear all per-effect slider rows */
    document.querySelectorAll("[data-voice-mode]").forEach((btn) => {
      const isNormal = btn.dataset.voiceMode === "normal";
      btn.classList.toggle("active", isNormal);
      btn.setAttribute("aria-pressed", String(isNormal));
    });
    const effectSlidersContainer = document.getElementById("effect-sliders-container");
    if (effectSlidersContainer) effectSlidersContainer.innerHTML = "";
    updateLocalTilePresentation();
    setDotStatus("offline");
    updateStatus("Disconnected", "muted");
    showToast("Session ended and media released", "success");
  }

  /* ── Voice changer ── */

  /** Push current processed stream track to all active calls. */
  function _replaceVoiceTrack() {
    if (typeof VoiceChanger === "undefined") return;
    const newTrack =
      VoiceChanger.getProcessedStream() && VoiceChanger.getProcessedStream().getAudioTracks()[0];
    if (!newTrack) return;
    activeCalls.forEach((call) => {
      if (call.peerConnection) {
        const sender = call.peerConnection
          .getSenders()
          .find((s) => s.track && s.track.kind === "audio");
        if (sender) sender.replaceTrack(newTrack);
      }
    });
  }

  /** Update the fill gradient of a range input to reflect its current value. */
  function _syncSliderFill(el) {
    if (!el) return;
    const min = parseFloat(el.min) || 0;
    const max = parseFloat(el.max) || 100;
    const pct = (((parseFloat(el.value) || 0) - min) / (max - min)) * 100;
    el.style.background = `linear-gradient(to right, #e10101 ${pct}%, #e5e7eb ${pct}%)`;
  }

  function _readStoredVoicePreferences() {
    try {
      const raw = window.sessionStorage.getItem(VOICE_PREFS_STORAGE_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      return parsed && typeof parsed === "object" ? parsed : null;
    } catch {
      return null;
    }
  }

  function _applyStoredVoicePreferences() {
    if (typeof VoiceChanger === "undefined") return;

    const saved = _readStoredVoicePreferences();
    if (!saved) return;

    const savedLevels =
      saved.effectLevels && typeof saved.effectLevels === "object" ? saved.effectLevels : {};
    const currentLevels = VoiceChanger.getEffectLevels();
    Object.keys(currentLevels).forEach((mode) => {
      const raw = Number(savedLevels[mode]);
      const value = Number.isFinite(raw) ? Math.max(0, Math.min(1, raw)) : 0;
      VoiceChanger.setEffectLevel(mode, value);
    });

    if (Number.isFinite(Number(saved.monitorVolume))) {
      VoiceChanger.setMonitorVolume(Math.max(0, Math.min(1, Number(saved.monitorVolume))));
    }
    if (Number.isFinite(Number(saved.micGain))) {
      VoiceChanger.setMicGain(Math.max(0, Math.min(2, Number(saved.micGain))));
    }

    if (VoiceChanger.getMonitorEnabled()) {
      VoiceChanger.toggleMonitor();
    }

    const monitorSlider = $("slider-monitor-volume");
    const monitorLabel = $("label-monitor-volume");
    if (monitorSlider && monitorLabel) {
      const value = Math.round(VoiceChanger.getMonitorVolume() * 100);
      monitorSlider.value = String(value);
      monitorLabel.textContent = `${value}%`;
      _syncSliderFill(monitorSlider);
    }

    const micGainSlider = $("slider-mic-gain");
    const micGainLabel = $("label-mic-gain");
    if (micGainSlider && micGainLabel) {
      const value = Math.round(VoiceChanger.getMicGain() * 100);
      micGainSlider.value = String(value);
      micGainLabel.textContent = `${value}%`;
      _syncSliderFill(micGainSlider);
    }

    const effectSlidersContainer = document.getElementById("effect-sliders-container");
    if (effectSlidersContainer) {
      effectSlidersContainer.innerHTML = "";
    }

    const levels = VoiceChanger.getEffectLevels();
    Object.entries(levels).forEach(([mode, level]) => {
      const isOn = level > 0;
      const btn = document.querySelector(`[data-voice-mode="${mode}"]`);
      if (btn) {
        btn.classList.toggle("active", isOn);
        btn.setAttribute("aria-pressed", String(isOn));
      }
      if (isOn) {
        _addEffectSliderRow(mode, level);
      }
    });

    _syncNormalChip();
    const monitorBtn = $("btn-monitor");
    if (monitorBtn) {
      monitorBtn.classList.remove("active");
      monitorBtn.setAttribute("aria-pressed", "false");
    }
    _replaceVoiceTrack();
  }

  /** Update the Normal chip state based on whether any effects are active. */
  function _syncNormalChip() {
    const levels = typeof VoiceChanger !== "undefined" ? VoiceChanger.getEffectLevels() : {};
    const anyActive = Object.values(levels).some((v) => v > 0);
    const normalBtn = document.querySelector('[data-voice-mode="normal"]');
    if (normalBtn) {
      normalBtn.classList.toggle("active", !anyActive);
      normalBtn.setAttribute("aria-pressed", String(!anyActive));
    }
  }

  /**
   * Dynamically create and append an effect-level slider row to #effect-sliders-container.
   * @param {string} mode  - effect key
   * @param {number} level - initial level 0–1
   */
  function _addEffectSliderRow(mode, level) {
    const container = document.getElementById("effect-sliders-container");
    if (!container) return;
    if (container.querySelector(`[data-effect-slider="${mode}"]`)) return; /* already exists */

    const modes = typeof VoiceChanger !== "undefined" ? VoiceChanger.getModes() : {};
    const modeInfo = modes[mode] || { label: mode, icon: "fa-music" };
    const initialPct = Math.round(level * 100);

    const row = document.createElement("div");
    row.className = "flex items-center gap-2 mt-1.5";
    row.setAttribute("data-effect-slider", mode);

    /* Label */
    const lbl = document.createElement("span");
    lbl.className = "flex-none text-[11px] font-semibold text-gray-500 flex items-center gap-1";
    lbl.style.minWidth = "4.5rem";
    lbl.innerHTML = `<i class="fa-solid ${modeInfo.icon} text-[10px]" aria-hidden="true"></i>${modeInfo.label}`;
    row.appendChild(lbl);

    /* Slider */
    const slider = document.createElement("input");
    slider.type = "range";
    slider.className = "voice-slider flex-1 min-w-0";
    slider.min = "0";
    slider.max = "100";
    slider.step = "1";
    slider.value = String(initialPct);
    slider.setAttribute("aria-label", `${modeInfo.label} effect level`);
    /* Sync fill on creation */
    slider.style.background = `linear-gradient(to right, #e10101 ${initialPct}%, #e5e7eb ${initialPct}%)`;
    row.appendChild(slider);

    /* Value label */
    const valLbl = document.createElement("span");
    valLbl.className = "flex-none w-7 text-right text-[11px] font-semibold text-primary";
    valLbl.textContent = `${initialPct}%`;
    row.appendChild(valLbl);

    /* Bind input event */
    slider.addEventListener("input", () => {
      const v = parseInt(slider.value, 10);
      valLbl.textContent = `${v}%`;
      _syncSliderFill(slider);
      setVoiceLevel(mode, v / 100);
    });

    container.appendChild(row);
  }

  /** Remove the effect-level slider row for a mode (if present). */
  function _removeEffectSliderRow(mode) {
    const container = document.getElementById("effect-sliders-container");
    if (!container) return;
    const row = container.querySelector(`[data-effect-slider="${mode}"]`);
    if (row) row.remove();
  }

  /**
   * Set the "Normal" mode — clears all active effects and removes all slider rows.
   * Called by the Normal chip button.
   */
  function setVoiceMode(mode) {
    if (typeof VoiceChanger === "undefined") return;

    if (mode === "normal") {
      const levels = VoiceChanger.getEffectLevels();
      Object.keys(levels).forEach((m) => VoiceChanger.setEffectLevel(m, 0));
      _replaceVoiceTrack();

      /* Clear all per-effect slider rows */
      const container = document.getElementById("effect-sliders-container");
      if (container) container.innerHTML = "";

      /* Update chip states */
      document.querySelectorAll("[data-voice-mode]").forEach((btn) => {
        const isNormal = btn.dataset.voiceMode === "normal";
        btn.classList.toggle("active", isNormal);
        btn.setAttribute("aria-pressed", String(isNormal));
      });

      showToast("Voice effect: Normal", "info");
    } else {
      /* Backward-compat path (used by tests / old callers) */
      VoiceChanger.setMode(mode);
      _replaceVoiceTrack();

      /* Show single slider row for this mode */
      const container = document.getElementById("effect-sliders-container");
      if (container) container.innerHTML = "";
      const level = VoiceChanger.getEffectLevels()[mode] || 0;
      if (level > 0) _addEffectSliderRow(mode, level);

      document.querySelectorAll("[data-voice-mode]").forEach((btn) => {
        const isActive = btn.dataset.voiceMode === mode;
        btn.classList.toggle("active", isActive);
        btn.setAttribute("aria-pressed", String(isActive));
      });

      const modeName = VoiceChanger.getModes()[mode] ? VoiceChanger.getModes()[mode].label : mode;
      showToast(`Voice effect: ${modeName}`, "info");
    }
  }

  /**
   * Toggle a single voice effect on/off independently of other effects.
   * Called by non-Normal chip buttons for combined-effects mode.
   */
  function toggleEffectMode(mode) {
    if (typeof VoiceChanger === "undefined") return;

    const newLevel = VoiceChanger.toggleEffect(mode);
    _replaceVoiceTrack();

    /* Update this chip's active state */
    const btn = document.querySelector(`[data-voice-mode="${mode}"]`);
    if (btn) {
      btn.classList.toggle("active", newLevel > 0);
      btn.setAttribute("aria-pressed", String(newLevel > 0));
    }

    /* Show or remove the effect's slider row */
    if (newLevel > 0) {
      _addEffectSliderRow(mode, newLevel);
    } else {
      _removeEffectSliderRow(mode);
    }

    _syncNormalChip();

    const modeInfo = VoiceChanger.getModes()[mode];
    const modeName = modeInfo ? modeInfo.label : mode;
    showToast(newLevel > 0 ? `Effect added: ${modeName}` : `Effect removed: ${modeName}`, "info");
  }

  /**
   * Update the level of a single active effect (called from per-effect sliders).
   * If level reaches 0 the effect is removed and the slider row is destroyed.
   */
  function setVoiceLevel(mode, level) {
    if (typeof VoiceChanger === "undefined") return;

    VoiceChanger.setEffectLevel(mode, level);
    _replaceVoiceTrack();

    const on = level > 0;
    const btn = document.querySelector(`[data-voice-mode="${mode}"]`);
    if (btn) {
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-pressed", String(on));
    }

    if (!on) {
      /* Effect fully removed — destroy its slider row */
      _removeEffectSliderRow(mode);
    }

    _syncNormalChip();
  }

  function toggleVoiceEffectsPanel() {
    const panel = $("voice-effects-panel");
    const btn = $("btn-voice-changer");
    if (!panel) return;
    const isHidden = panel.classList.toggle("hidden");
    if (btn) btn.setAttribute("aria-expanded", isHidden ? "false" : "true");
  }

  /** Toggle the "Hear Yourself" monitor on/off and sync the UI button state. */
  function toggleMonitor() {
    if (typeof VoiceChanger === "undefined") return;
    VoiceChanger.toggleMonitor();
    const on = VoiceChanger.getMonitorEnabled();
    const btn = $("btn-monitor");
    if (btn) {
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-pressed", String(on));
    }
  }

  /* ── Noise suppression hint ── */
  async function toggleNoiseSuppression() {
    if (!localStream) return;
    const audioTrack = localStream.getAudioTracks()[0];
    if (!audioTrack) return;
    try {
      const settings = audioTrack.getSettings();
      const current = settings.noiseSuppression;
      await audioTrack.applyConstraints({
        noiseSuppression: !current,
        echoCancellation: true,
        autoGainControl: true,
      });
      showToast(`Noise suppression ${!current ? "enabled" : "disabled"}`, "success");
      const btn = $("btn-noise");
      if (btn) btn.classList.toggle("active", !current);
    } catch {
      showToast("Noise suppression not supported on this device", "warning");
    }
  }

  /* ── Consent gate ── */
  function askConsent(callerName) {
    return new Promise((resolve) => {
      const overlay = document.createElement("div");
      overlay.className = "modal-overlay";
      overlay.style.display = "flex";
      overlay.innerHTML = `
        <div class="modal" style="max-width:440px">
          <h3 style="display:flex;align-items:center;gap:0.5rem"><i class="fa-solid fa-shield-halved" aria-hidden="true"></i>Recording Consent Required</h3>
          <p>This call may be recorded for AI notes and security purposes. Do you consent to participate in this secure call with <strong>${callerName}</strong>?</p>
          <div class="alert alert-info" style="margin-bottom:1rem">
            <i class="fa-solid fa-circle-info" aria-hidden="true"></i>
            <span>Consent is cryptographically timestamped and stored locally. You can withdraw at any time.</span>
          </div>
          <div style="display:flex;gap:0.75rem;justify-content:flex-end">
            <button class="btn btn-secondary" id="consent-deny">Decline</button>
            <button class="btn btn-primary" id="consent-allow">I Consent</button>
          </div>
        </div>
      `;
      document.body.appendChild(overlay);

      overlay.querySelector("#consent-allow").onclick = () => {
        consentGiven = true;
        overlay.remove();
        ConsentManager &&
          ConsentManager.record({
            type: "given",
            name: `Consent given for call with ${callerName}`,
            details: `Session ID: ${state.sessionId}`,
          });
        resolve(true);
      };
      overlay.querySelector("#consent-deny").onclick = () => {
        overlay.remove();
        resolve(false);
      };
    });
  }

  /* ── Share link ── */
  function copyRoomId() {
    if (!state.peerId) {
      showToast("Room not ready yet — please wait", "warning");
      return;
    }
    copyToClipboard(state.peerId, "Room ID");
  }

  function copyRoomLink() {
    if (!state.peerId) {
      showToast("Room not ready yet — please wait", "warning");
      return;
    }
    const url = `${window.location.origin}/video-chat?room=${encodeURIComponent(state.peerId)}`;
    copyToClipboard(url, "Room link");
  }

  /* ── Screen share ── */
  async function shareScreen() {
    try {
      const screenStream = await navigator.mediaDevices.getDisplayMedia({ video: true });
      const screenTrack = screenStream.getVideoTracks()[0];
      for (const call of activeCalls.values()) {
        if (call.peerConnection) {
          const sender = call.peerConnection
            .getSenders()
            .find((s) => s.track && s.track.kind === "video");
          if (sender) await sender.replaceTrack(screenTrack);
        }
      }
      const localVideo = $("local-video");
      if (localVideo) localVideo.srcObject = screenStream;
      showToast("Screen sharing started", "success");
      screenSharing = true;
      $("btn-screen") && $("btn-screen").classList.add("active");
      updateLocalTilePresentation();
      broadcastProfile(true);
      screenTrack.onended = () => {
        if (screenSharing) stopScreenShare();
      };
    } catch (err) {
      if (err.name !== "NotAllowedError") showToast("Screen share error: " + err.message, "error");
    }
  }

  function stopScreenShare() {
    if (!localStream) return;
    const videoTrack = localStream.getVideoTracks()[0];
    if (videoTrack && activeCalls.size > 0) {
      for (const call of activeCalls.values()) {
        const sender =
          call.peerConnection &&
          call.peerConnection.getSenders().find((s) => s.track && s.track.kind === "video");
        if (sender) sender.replaceTrack(videoTrack);
      }
    }
    const localVideo = $("local-video");
    if (localVideo) {
      localVideo.srcObject = localStream;
    }
    $("btn-screen") && $("btn-screen").classList.remove("active");
    screenSharing = false;
    updateLocalTilePresentation();
    broadcastProfile(true);
    showToast("Screen sharing stopped", "info");
  }

  function readInitialMediaPreferencesFromUrl() {
    const params = new URLSearchParams(window.location.search);
    const mic = params.get("mic");
    const cam = params.get("cam");

    if (mic === "off" || mic === "on") {
      initialMediaPreferences.mic = mic === "on";
    }
    if (cam === "off" || cam === "on") {
      initialMediaPreferences.cam = cam === "on";
    }

    if (params.get("prejoin") === "1") {
      params.delete("prejoin");
      params.delete("mic");
      params.delete("cam");
      params.delete("name");
      const query = params.toString();
      const cleanUrl = window.location.pathname + (query ? "?" + query : "");
      window.history.replaceState({}, "", cleanUrl);
    }
  }

  /* ── Init ── */
    state.displayName = resolveDisplayName();
    state.displayInitials = makeInitials(state.displayName);

    readInitialMediaPreferencesFromUrl();
    updateLocalTilePresentation();
    
    // We try to start media immediately if we have preferences from the lobby
    const ok = await startLocalMedia();
    if (ok) {
      updateLocalTilePresentation();
      _applyStoredVoicePreferences();
    }
    
    // Always init peer regardless of success of startLocalMedia (can join without media)
    await initPeer();
    return true;

  return {
    init,
    callPeer,
    disconnectPeer,
    toggleMic,
    toggleCamera,
    endCall,
    hangup,
    toggleNoiseSuppression,
    setVoiceMode,
    toggleEffectMode,
    setVoiceLevel,
    toggleVoiceEffectsPanel,
    toggleMonitor,
    shareScreen,
    stopScreenShare,
    copyRoomId,
    copyRoomLink,
    state,
  };
})();
