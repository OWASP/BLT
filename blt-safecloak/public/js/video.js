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
  let localHandRaised = false;
  let inviteAutoJoinAttempted = false;
  let inviteAutoJoinRoomId = "";
  let initialMediaPreferences = { mic: false, cam: false };
  const MEDIA_PREFS_STORAGE_KEY = "blt-safecloak-media-preferences";
  const VOICE_PREFS_STORAGE_KEY = "blt-safecloak-voice-preferences";
  const DISPLAY_NAME_STORAGE_KEY = "blt-safecloak-display-name";
  const ROOM_ID_STORAGE_KEY = "blt-safecloak-room-id";
  const PROFILE_BROADCAST_THROTTLE_MS = 220;
  const SPEAKING_THRESHOLD = 28;
  const SPEAKING_HOLD_MS = 260;
  const MAX_VIDEO_PARTICIPANTS = 5;
  const FULL_VIDEO_MODE_HINT = "Full video chat mode active for rooms with up to 5 participants.";
  const WALKIE_MODE_HINT = "Walkie-talkie mode active: audio-only with push-to-talk floor control.";

  const peerProfiles = new Map(); // peerId -> { name, initials, micMuted, camOff, handRaised }
  const remoteSpeakingMonitors = new Map(); // peerId -> { analyser, data, source, activeUntil }
  const mutedPeers = new Set(); // peerId -> locally muted audio
  let speakingLoopFrame = null;
  let speakingAudioContext = null;
  let localSpeakingUntil = 0;
  const lastProfileBroadcastAt = new Map(); // peerId -> timestamp
  let navigationInProgress = false;
  let isEndingCall = false;
  let walkieTalkieMode = false;
  let walkieFloorHolder = null;
  let wasMicMutedBeforeWalkie = true;
  let wasCamOffBeforeWalkie = true;
  let reconnectAttempts = 0;
  const MAX_RECONNECT_ATTEMPTS = 3;
  const RECONNECT_BASE_DELAY_MS = 1000;

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

  function updateStatus(iconClass, text, type = "muted") {
    const el = $("connection-status");
    if (!el) return;
    el.innerHTML = "";
    if (iconClass) {
      const icon = document.createElement("i");
      icon.className = iconClass + " mr-1";
      icon.setAttribute("aria-hidden", "true");
      el.appendChild(icon);
    }
    const textNode = document.createTextNode(text);
    el.appendChild(textNode);
    el.className = `text-${type}`;
  }

  function navigateToHome() {
    if (navigationInProgress) return;
    navigationInProgress = true;
    try {
      window.location.assign("/");
    } catch {
      window.location.href = "/";
    }
  }

  function setStatusIcon(status) {
    const icon = $("status-icon");
    if (!icon) return;
    if (status === "online") {
      icon.className = "fa-solid fa-circle text-green-500";
    } else if (status === "offline") {
      icon.className = "fa-solid fa-circle text-gray-400";
    } else if (status === "connecting") {
      icon.className = "fa-solid fa-circle text-amber-500 fa-fade";
    }
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
      const fromStorage = normalizeDisplayName(
        window.sessionStorage.getItem(DISPLAY_NAME_STORAGE_KEY)
      );
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
        handRaised: localHandRaised,
      };
    }
    const profile = peerProfiles.get(peerId);
    if (profile) return profile;
    return {
      name: peerId,
      initials: makeInitials(peerId),
      micMuted: false,
      camOff: false,
      handRaised: false,
    };
  }

  function getDisplayLabel(peerId) {
    if (peerId === state.peerId || peerId === "local") return "You";
    return getProfileForPeer(peerId).name || peerId;
  }

  function normalizeRoomId(value) {
    return (value || "").trim().toUpperCase();
  }

  function getInviteRoomIdFromUrl() {
    const params = new URLSearchParams(window.location.search);
    return normalizeRoomId(params.get("room"));
  }

  function getStoredOwnRoomId() {
    try {
      return normalizeRoomId(window.sessionStorage.getItem(ROOM_ID_STORAGE_KEY));
    } catch {
      return "";
    }
  }

  function persistOwnRoomId(roomId) {
    const normalizedRoomId = normalizeRoomId(roomId);
    if (!isValidRoomId(normalizedRoomId)) return;
    try {
      window.sessionStorage.setItem(ROOM_ID_STORAGE_KEY, normalizedRoomId);
    } catch {
      /* ignore storage failures */
    }
  }

  function shouldReuseInviteRoomAsPeerId(inviteRoomId) {
    const normalizedInviteRoomId = normalizeRoomId(inviteRoomId);
    if (!isValidRoomId(normalizedInviteRoomId)) return false;
    if (normalizedInviteRoomId !== getStoredOwnRoomId()) return false;
    const navEntries =
      typeof performance !== "undefined" && performance.getEntriesByType
        ? performance.getEntriesByType("navigation")
        : [];
    return Boolean(navEntries.length && navEntries[0] && navEntries[0].type === "reload");
  }

  function ensureRoomIdInUrl(roomId) {
    const normalizedRoomId = normalizeRoomId(roomId);
    if (!isValidRoomId(normalizedRoomId)) return;
    try {
      const url = new URL(window.location.href);
      if (url.searchParams.get("room")) return;
      url.searchParams.set("room", normalizedRoomId);
      window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
    } catch {
      /* ignore URL update failures */
    }
  }

  function populateRemoteIdInput(roomId) {
    const remoteInput = $("remote-id");
    if (remoteInput) {
      remoteInput.value = roomId;
    }
  }

  function getParticipantTotal() {
    const isPeerReady = Boolean(peer && peer.open && state.peerId);
    const localVisible = isPeerReady || activeCalls.size > 0;
    return activeCalls.size + (localVisible ? 1 : 0);
  }

  function sendDataToAll(payload) {
    activeDataConns.forEach((conn) => {
      if (conn && conn.open) {
        conn.send(payload);
      }
    });
  }

  async function releaseWalkieFloor() {
    if (!walkieTalkieMode || walkieFloorHolder !== state.peerId) return;
    walkieFloorHolder = null;
    if (localStream) {
      localStream.getAudioTracks().forEach((track) => {
        track.enabled = false;
      });
    }
    micMuted = true;
    syncControlButtons();
    updateLocalTilePresentation();
    broadcastProfile(true);
    sendDataToAll({ type: "floor", action: "release", id: state.peerId });
  }

  async function claimWalkieFloor() {
    if (!walkieTalkieMode) return false;
    if (walkieFloorHolder && walkieFloorHolder !== state.peerId) {
      showToast(`Cannot speak: ${getDisplayLabel(walkieFloorHolder)} is currently talking`, "info");
      return false;
    }

    const ok = await startLocalMedia({ audio: true, video: false });
    if (!ok || !localStream) return false;

    walkieFloorHolder = state.peerId;
    localStream.getAudioTracks().forEach((track) => {
      track.enabled = true;
    });
    micMuted = false;
    const localAudio = localStream.getAudioTracks()[0];
    if (localAudio) {
      await updateTracksInCalls(localAudio, "audio");
      if (typeof VoiceChanger !== "undefined" && voiceStream) {
        _replaceVoiceTrack();
      }
    }
    syncControlButtons();
    updateLocalTilePresentation();
    broadcastProfile(true);
    sendDataToAll({ type: "floor", action: "claim", id: state.peerId });
    return true;
  }

  function getSelfProfilePayload() {
    return {
      type: "profile",
      id: state.peerId,
      name: state.displayName,
      initials: state.displayInitials,
      micMuted: isLocalMicMutedState(),
      camOff: screenSharing ? false : isLocalCamOffState(),
      handRaised: localHandRaised,
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
        wrapper.querySelector('[data-role="label-name"]') ||
        (isLocal ? $("label-local-name") : null),
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
    videoEl.muted = mutedPeers.has(peerId);
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
      tile.video.setAttribute(
        "aria-label",
        isLocal ? "Your video" : `Participant ${displayName} video`
      );
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
    Array.from(remoteSpeakingMonitors.keys()).forEach((peerId) =>
      stopRemoteSpeakingMonitor(peerId)
    );
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
      handRaised: false,
    };
    const normalizedName = normalizeDisplayName(payload && payload.name);

    const profile = {
      name: normalizedName || prev.name,
      initials: makeInitials(normalizedName || prev.name),
      micMuted:
        payload && typeof payload.micMuted === "boolean"
          ? payload.micMuted
          : Boolean(prev.micMuted),
      camOff:
        payload && typeof payload.camOff === "boolean" ? payload.camOff : Boolean(prev.camOff),
      handRaised:
        payload && typeof payload.handRaised === "boolean"
          ? payload.handRaised
          : Boolean(prev.handRaised),
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
        <li>Click the <strong>camera/lock</strong> icon in the address bar.</li>
        <li>Select <strong>Always allow</strong> for the camera and microphone, then click <strong>Done</strong>.</li>
        <li>Or go to <strong>Settings → Privacy and security → Site settings → Camera</strong> and allow this site.</li>
        <li>Reload the page and click <em>Try Again</em>.</li></ol>`,
      edge: `<strong>Microsoft Edge:</strong><ol style="margin:0.5rem 0 0 1.25rem;display:flex;flex-direction:column;gap:0.3rem">
        <li>Click the <strong>camera/lock</strong> icon in the address bar.</li>
        <li>Set Camera and Microphone permissions to <strong>Allow</strong>, then click <strong>Save</strong>.</li>
        <li>Or go to <strong>Settings → Cookies and site permissions → Camera</strong> and add this site to the allow list.</li>
        <li>Reload the page and click <em>Try Again</em>.</li></ol>`,
      firefox: `<strong>Mozilla Firefox:</strong><ol style="margin:0.5rem 0 0 1.25rem;display:flex;flex-direction:column;gap:0.3rem">
        <li>Click the <strong>permissions icon</strong> (camera icon with a slash) in the address bar.</li>
        <li>Click <strong>Blocked Temporarily</strong> or <strong>Blocked</strong> next to Camera and Microphone and choose <strong>Allow</strong>.</li>
        <li>Or go to <strong>about:preferences#privacy</strong> → Permissions → Camera → Settings, and allow this site.</li>
        <li>Reload the page and click <em>Try Again</em>.</li></ol>`,
      safari: `<strong>Safari:</strong><ol style="margin:0.5rem 0 0 1.25rem;display:flex;flex-direction:column;gap:0.3rem">
        <li>In the menu bar, go to <strong>Safari → Settings for This Website</strong> (or <strong>Preferences → Websites → Camera</strong>).</li>
        <li>Set Camera and Microphone to <strong>Allow</strong>.</li>
        <li>Reload the page and click <em>Try Again</em>.</li></ol>`,
      opera: `<strong>Opera:</strong><ol style="margin:0.5rem 0 0 1.25rem;display:flex;flex-direction:column;gap:0.3rem">
        <li>Click the <strong>camera/lock</strong> icon in the address bar.</li>
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
      _applyStoredVoicePreferences();
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
      // Disable only when the device is genuinely unavailable: user wants mic on
      // but there is no track. When micMuted=true the track was intentionally
      // stopped — keep the button enabled so the user can re-enable.
      const micUnavailable = !hasAudioTrack && !micMuted;
      if (micUnavailable) {
        micBtn.innerHTML = '<i class="fa-solid fa-microphone-slash" aria-hidden="true"></i>';
        micBtn.title = micMuted ? "Unmute mic" : "Mute mic";
        micBtn.disabled = false;
        micBtn.classList.remove("opacity-50", "cursor-not-allowed");
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
      // Same logic: disable only when user wants cam on but no track exists.
      const camUnavailable = !hasVideoTrack && !camOff;
      if (camUnavailable) {
        camBtn.innerHTML = '<i class="fa-solid fa-video-slash" aria-hidden="true"></i>';
        camBtn.title = camOff ? "Enable camera" : "Disable camera";
        camBtn.disabled = false;
        camBtn.classList.remove("opacity-50", "cursor-not-allowed");
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

    const pushToTalkBtn = $("btn-push-to-talk");
    if (pushToTalkBtn) {
      const isSpeaking = walkieTalkieMode && walkieFloorHolder === state.peerId && !micMuted;
      pushToTalkBtn.classList.toggle("hidden", !walkieTalkieMode);
      pushToTalkBtn.classList.toggle("active", isSpeaking);
      pushToTalkBtn.setAttribute("aria-pressed", isSpeaking ? "true" : "false");
      pushToTalkBtn.disabled = !walkieTalkieMode;
    }
  }

  async function setWalkieTalkieMode(enabled) {
    if (walkieTalkieMode === enabled) return;
    if (!enabled) {
      await releaseWalkieFloor();
    }
    walkieTalkieMode = enabled;
    const addParticipantCard = $("add-participant-card");
    const participantModeHint = $("participant-mode-hint");
    const inviteRoomId = getInviteRoomIdFromUrl();
    const shouldHideAddParticipant = isValidRoomId(inviteRoomId) && inviteRoomId !== state.peerId;

    if (enabled) {
      wasMicMutedBeforeWalkie = micMuted;
      wasCamOffBeforeWalkie = camOff;
      walkieFloorHolder = null;
      camOff = true;
      micMuted = true;
      if (localStream) {
        localStream.getVideoTracks().forEach((track) => {
          track.stop();
          localStream.removeTrack(track);
        });
        localStream.getAudioTracks().forEach((track) => {
          track.enabled = false;
        });
      }
      await updateTracksInCalls(null, "video");
      if (addParticipantCard) addParticipantCard.style.display = "none";
      if (participantModeHint) {
        participantModeHint.textContent = WALKIE_MODE_HINT;
      }
      showToast("Walkie-talkie mode enabled for large room", "info");
    } else {
      walkieFloorHolder = null;
      micMuted = wasMicMutedBeforeWalkie;
      camOff = wasCamOffBeforeWalkie;
      if (!camOff) {
        await startLocalMedia({ video: true, audio: false });
      }
      if (!micMuted) {
        await startLocalMedia({ audio: true, video: false });
      }
      if (addParticipantCard)
        addParticipantCard.style.display = shouldHideAddParticipant ? "none" : "";
      if (participantModeHint) {
        participantModeHint.textContent = FULL_VIDEO_MODE_HINT;
      }
      showToast("Full video mode restored", "success");
    }

    syncControlButtons();
    updateLocalTilePresentation();
    updateParticipantsList();
    broadcastProfile(true);
  }

  async function onPushToTalkStart() {
    if (!walkieTalkieMode) return;
    await claimWalkieFloor();
  }

  async function onPushToTalkEnd() {
    if (!walkieTalkieMode) return;
    await releaseWalkieFloor();
  }

  function evaluateCommunicationMode() {
    const totalParticipants = getParticipantTotal();
    const shouldEnableWalkie = totalParticipants > MAX_VIDEO_PARTICIPANTS;
    if (walkieTalkieMode !== shouldEnableWalkie) {
      void setWalkieTalkieMode(shouldEnableWalkie);
    }
  }

  function applyInitialMediaPreferences() {
    micMuted = !initialMediaPreferences.mic;
    camOff = !initialMediaPreferences.cam;

    if (!localStream) {
      syncControlButtons();
      updateLocalTilePresentation();
      return;
    }

    const hasAudioTrack = localStream.getAudioTracks().length > 0;
    const hasVideoTrack = localStream.getVideoTracks().length > 0;

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

  // Per-kind in-flight acquisition guards — prevents double getUserMedia for
  // the same track kind when toggle is called rapidly.
  const _mediaPromise = { audio: null, video: null };

  async function ensureLocalStream() {
    if (!localStream) {
      localStream = new MediaStream();
      attachStream(localStream);
    }
    return localStream;
  }

  async function startLocalMedia(constraints = { video: true, audio: true }) {
    // Return an in-flight promise if the requested track kind is already being acquired.
    if (constraints.audio && _mediaPromise.audio) return _mediaPromise.audio;
    if (constraints.video && _mediaPromise.video) return _mediaPromise.video;

    const run = (async () => {
      try {
        const ls = await ensureLocalStream();
        const request = {
          audio: !!constraints.audio && ls.getAudioTracks().length === 0,
          video: !!constraints.video && ls.getVideoTracks().length === 0,
        };
        if (!request.audio && !request.video) return true;

        const stream = await navigator.mediaDevices.getUserMedia(request);

        if (constraints.audio && stream.getAudioTracks().length > 0) {
          stream.getAudioTracks().forEach((t) => {
            t.enabled = !micMuted;
            ls.addTrack(t);
          });

          let freshAudio = ls.getAudioTracks()[ls.getAudioTracks().length - 1];
          if (typeof VoiceChanger !== "undefined") {
            const processedAudio = VoiceChanger.init(ls);
            freshAudio = processedAudio.getAudioTracks()[0] || freshAudio;

            const videoTrack = ls.getVideoTracks()[0];
            const tracks = [videoTrack, freshAudio].filter(Boolean);
            voiceStream = tracks.length ? new MediaStream(tracks) : ls;
          }

          // Replace track in all active calls with the fresh audio track.
          await updateTracksInCalls(freshAudio, "audio");
          startVoiceMeter(ls);
        }
        if (constraints.video && stream.getVideoTracks().length > 0) {
          stream.getVideoTracks().forEach((t) => {
            t.enabled = !camOff;
            ls.addTrack(t);
          });
          const freshVideo = ls.getVideoTracks()[ls.getVideoTracks().length - 1];

          if (voiceStream && voiceStream !== ls) {
            const freshAudio = voiceStream.getAudioTracks()[0];
            voiceStream = new MediaStream([freshVideo, freshAudio].filter(Boolean));
          } else {
            voiceStream = ls;
          }

          // Replace track in all active calls with the fresh video track.
          await updateTracksInCalls(freshVideo, "video");
          const localVideo = $("local-video");
          if (localVideo) localVideo.srcObject = ls;
        }
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
        showToast("Access error: " + err.message, "error");
        return false;
      } finally {
        if (constraints.audio) _mediaPromise.audio = null;
        if (constraints.video) _mediaPromise.video = null;
      }
    })();

    if (constraints.audio) _mediaPromise.audio = run;
    if (constraints.video) _mediaPromise.video = run;

    return run;
  }

  function startVoiceMeter(stream) {
    if (audioContext || stream.getAudioTracks().length === 0) return;
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
    const inviteRoomId = getInviteRoomIdFromUrl();
    state.peerId = shouldReuseInviteRoomAsPeerId(inviteRoomId) ? inviteRoomId : Crypto.randomId(6);
    persistOwnRoomId(state.peerId);
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
      reconnectAttempts = 0;
      $("my-peer-id") && ($("my-peer-id").textContent = id);
      persistOwnRoomId(id);
      ensureRoomIdInUrl(id);
      updateStatus("fa-solid fa-share-nodes", "Ready — share your Room ID", "secondary");
      setStatusIcon("online");
      updateLocalTilePresentation();
      updateParticipantsList();
      showToast("Connected to signaling server", "success");
      const inviteRoomId = inviteAutoJoinRoomId || getInviteRoomIdFromUrl();
      // Skip auto-join when this tab is the host for the room ID in the URL.
      if (!inviteRoomId || inviteRoomId === id) {
        return;
      }

      if (!isValidRoomId(inviteRoomId)) {
        showToast("Invite link contains an invalid Room ID", "warning");
        return;
      }

      populateRemoteIdInput(inviteRoomId);
      void autoJoinFromInvite(inviteRoomId).catch(() => {
        showToast("Unable to auto-join from invite link", "error");
      });
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

      const mediaOk = await startLocalMedia();
      if (!mediaOk) {
        incomingCall.close();
        return;
      }

      activeCalls.set(incomingCall.peer, incomingCall);
      updateParticipantsList();

      incomingCall.answer(voiceStream || localStream);
      handleCallStream(incomingCall);
      ensureDataConn(incomingCall.peer);
      sendPeerListTo(incomingCall.peer);
    });

    peer.on("connection", (conn) => {
      setupDataConn(conn);
    });

    peer.on("error", (err) => {
      updateStatus("fa-solid fa-circle-exclamation", "Error: " + err.message, "danger");
      setStatusIcon("offline");
      showToast("Connection error: " + err.type, "error");
    });

    peer.on("disconnected", () => {
      if (peer.destroyed || isEndingCall) {
        updateStatus("fa-solid fa-plug-circle-xmark", "Disconnected", "warning");
        setStatusIcon("offline");
        return;
      }
      if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttempts++;
        const delay = RECONNECT_BASE_DELAY_MS * Math.pow(2, reconnectAttempts - 1);
        updateStatus("fa-solid fa-arrows-rotate fa-spin", `Reconnecting (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})…`, "warning");
        setStatusIcon("offline");
        const currentPeer = peer;
        setTimeout(() => {
          if (currentPeer === peer && !isEndingCall && !currentPeer.destroyed && !currentPeer.open) {
            currentPeer.reconnect();
          }
        }, delay);
      } else {
        updateStatus("fa-solid fa-plug-circle-xmark", "Disconnected — could not reconnect", "danger");
        setStatusIcon("offline");
        showToast("Lost connection to signaling server. Please rejoin.", "error");
      }
    });
  }

  function updateParticipantsList() {
    const listEl = $("participants-list");
    const countEl = $("participant-count");
    const isPeerReady = Boolean(peer && peer.open && state.peerId);
    const localVisible = isPeerReady || activeCalls.size > 0;
    const participantTotal = getParticipantTotal();
    if (countEl) {
      countEl.textContent = `${participantTotal} in room`;
    }
    const participantModeHint = $("participant-mode-hint");
    if (participantModeHint) {
      participantModeHint.textContent =
        participantTotal > MAX_VIDEO_PARTICIPANTS ? WALKIE_MODE_HINT : FULL_VIDEO_MODE_HINT;
    }
    if (!listEl) return;
    listEl.innerHTML = "";
    evaluateCommunicationMode();

    if (!isPeerReady && activeCalls.size === 0) {
      const empty = document.createElement("p");
      empty.className = "text-sm text-gray-500 text-center py-2";
      empty.textContent = "No participants connected";
      listEl.appendChild(empty);
      return;
    }

    const localItem = document.createElement("div");
    localItem.className = "flex items-center justify-between gap-2 py-1 text-sm";

    const localNameSpan = document.createElement("span");
    localNameSpan.className = "flex min-w-0 items-center gap-2";

    const localDot = document.createElement("i");
    localDot.className = "fa-solid fa-circle text-green-500 text-[10px]";
    localDot.setAttribute("aria-hidden", "true");

    const localTextWrap = document.createElement("span");
    localTextWrap.className = "flex min-w-0 flex-col";

    const localNameLabel = document.createElement("span");
    localNameLabel.className = "truncate font-semibold text-gray-900 flex items-center gap-1.5";
    localNameLabel.title = state.displayName;

    const localNameText = document.createElement("span");
    localNameText.className = "truncate";
    localNameText.textContent = `${state.displayName} (You)`;
    localNameLabel.appendChild(localNameText);

    if (localHandRaised) {
      const hand = document.createElement("span");
      hand.textContent = "✋";
      hand.className = "leading-none";
      hand.setAttribute("role", "img");
      hand.setAttribute("aria-label", "Hand raised");
      hand.title = "Hand raised";
      localNameLabel.appendChild(hand);
    }

    const localIdLabel = document.createElement("span");
    localIdLabel.className = "truncate font-mono text-[11px] text-gray-500";
    localIdLabel.title = state.peerId || "Not connected";
    localIdLabel.textContent = state.peerId || "Not connected";

    localNameSpan.appendChild(localDot);
    localTextWrap.appendChild(localNameLabel);
    localTextWrap.appendChild(localIdLabel);
    localNameSpan.appendChild(localTextWrap);

    localItem.appendChild(localNameSpan);
    listEl.appendChild(localItem);

    activeCalls.forEach((_call, peerId) => {
      const item = document.createElement("div");
      item.className = "flex items-center justify-between gap-2 py-1 text-sm";

      const nameSpan = document.createElement("span");
      nameSpan.className = "flex min-w-0 items-center gap-2";

      const dot = document.createElement("i");
      dot.className = "fa-solid fa-circle text-green-500 text-[10px]";
      dot.setAttribute("aria-hidden", "true");

      const textWrap = document.createElement("span");
      textWrap.className = "flex min-w-0 flex-col";

      const nameLabel = document.createElement("span");
      nameLabel.className = "truncate font-semibold text-gray-900 flex items-center gap-1.5";
      nameLabel.title = getDisplayLabel(peerId);

      const nameText = document.createElement("span");
      nameText.className = "truncate";
      nameText.textContent = getDisplayLabel(peerId);
      nameLabel.appendChild(nameText);

      const remoteProfile = getProfileForPeer(peerId);
      if (remoteProfile.handRaised) {
        const remoteHand = document.createElement("span");
        remoteHand.textContent = "✋";
        remoteHand.className = "leading-none";
        remoteHand.setAttribute("role", "img");
        remoteHand.setAttribute("aria-label", "Hand raised");
        remoteHand.title = "Hand raised";
        nameLabel.appendChild(remoteHand);
      }

      const idLabel = document.createElement("span");
      idLabel.className = "truncate font-mono text-[11px] text-gray-500";
      idLabel.title = peerId;
      idLabel.textContent = peerId;

      nameSpan.appendChild(dot);
      textWrap.appendChild(nameLabel);
      textWrap.appendChild(idLabel);
      nameSpan.appendChild(textWrap);

      const muteBtn = document.createElement("button");
      const isMuted = mutedPeers.has(peerId);
      muteBtn.className = "control-btn participant-mute-btn";
      muteBtn.style.cssText = "width:32px;height:32px;font-size:0.75rem";
      muteBtn.title = isMuted ? `Unmute ${getDisplayLabel(peerId)}` : `Mute ${getDisplayLabel(peerId)}`;
      muteBtn.setAttribute("aria-label", muteBtn.title);
      muteBtn.setAttribute("aria-pressed", String(isMuted));
      muteBtn.innerHTML = isMuted ? '<i class="fa-solid fa-microphone-slash" aria-hidden="true"></i>' : '<i class="fa-solid fa-microphone" aria-hidden="true"></i>';
      muteBtn.addEventListener("click", () => {
        if (typeof window.toggleParticipantMute === "function") {
          window.toggleParticipantMute(peerId);
        } else {
          togglePeerAudioMute(peerId);
        }
      });

      const disconnectBtn = document.createElement("button");
      disconnectBtn.className = "control-btn";
      disconnectBtn.style.cssText = "width:32px;height:32px;font-size:0.75rem";
      disconnectBtn.title = `Disconnect ${getDisplayLabel(peerId)}`;
      disconnectBtn.setAttribute("aria-label", `Disconnect ${getDisplayLabel(peerId)}`);
      disconnectBtn.innerHTML = '<i class="fa-solid fa-phone-slash" aria-hidden="true"></i>';
      disconnectBtn.addEventListener("click", () => VideoChat.disconnectPeer(peerId));

      const actionsSpan = document.createElement("span");
      actionsSpan.className = "flex items-center gap-1.5";
      actionsSpan.appendChild(muteBtn);
      actionsSpan.appendChild(disconnectBtn);

      item.appendChild(nameSpan);
      item.appendChild(actionsSpan);
      listEl.appendChild(item);
    });
  }

  function syncRaiseHandButton() {
    const handBtn = $("btn-hand");
    if (!handBtn) return;
    handBtn.classList.toggle("active", localHandRaised);
    handBtn.setAttribute("aria-pressed", localHandRaised ? "true" : "false");
    handBtn.title = localHandRaised ? "Lower hand" : "Raise hand";
  }

  function toggleRaiseHand() {
    localHandRaised = !localHandRaised;
    syncRaiseHandButton();
    updateParticipantsList();
    broadcastProfile(true);
    showToast(localHandRaised ? "Hand raised" : "Hand lowered", "info");
  }

  function handleCallStream(call) {
    const remotePeerId = call.peer;
    // Persist sender references here to ensure replaceTrack works even if s.track is switched to null later
    call.sendersByKind = {};
    const pc = call.peerConnection;
    if (pc && typeof pc.getTransceivers === "function") {
      pc.getTransceivers().forEach((tr) => {
        if (tr.sender && tr.receiver && tr.receiver.track) {
          call.sendersByKind[tr.receiver.track.kind] = tr.sender;
        }
      });
    } else if (pc) {
      // Fallback for browsers without full transceiver support
      pc.getSenders().forEach((s) => {
        if (s.track) call.sendersByKind[s.track.kind] = s;
      });
    }

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
        "fa-solid fa-lock text-primary",
        `Encrypted call active (${count} participant${count !== 1 ? "s" : ""})`,
        "success"
      );
      setStatusIcon("online");
      if ($("call-controls")) {
        $("call-controls").classList.remove("hidden");
        $("btn-noise") && $("btn-noise").classList.remove("hidden");
        $("btn-screen") && $("btn-screen").classList.remove("hidden");
        $("btn-end") && $("btn-end").classList.remove("hidden");
      }
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
        // Only show remote-disconnect UI if this is not a local teardown
        if (!isEndingCall) {
          updateStatus("fa-solid fa-phone-slash", "Call ended", "muted");
          setStatusIcon("offline");
          if ($("call-controls")) {
            $("btn-noise") && $("btn-noise").classList.add("hidden");
            $("btn-screen") && $("btn-screen").classList.add("hidden");
            $("btn-end") && $("btn-end").classList.remove("hidden");
          }
          showToast("Participant disconnected. Use End Call to return home.", "info");
        }
      } else {
        const count = activeCalls.size;
        updateStatus(
          "fa-solid fa-lock text-primary",
          `Encrypted call active (${count} participant${count !== 1 ? "s" : ""})`,
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
        return;
      }

      if (data && data.type === "floor") {
        const floorPeerId = typeof data.id === "string" ? data.id.trim() : "";
        if (!floorPeerId) return;
        if (floorPeerId !== conn.peer) return;
        if (data.action === "claim") {
          walkieFloorHolder = floorPeerId;
          if (floorPeerId !== state.peerId) {
            micMuted = true;
            if (localStream) {
              localStream.getAudioTracks().forEach((track) => {
                track.enabled = false;
              });
            }
          }
          syncControlButtons();
          updateLocalTilePresentation();
          broadcastProfile(true);
          return;
        }
        if (data.action === "release" && walkieFloorHolder === floorPeerId) {
          walkieFloorHolder = null;
          syncControlButtons();
          return;
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
    return /^[ABCDEFGHJKLMNPQRSTUVWXYZ23456789]{6}$/.test(roomId);
  }

  async function autoJoinFromInvite(roomId) {
    const normalizedRoomId = normalizeRoomId(roomId);
    if (!normalizedRoomId || !isValidRoomId(normalizedRoomId)) {
      return false;
    }

    populateRemoteIdInput(normalizedRoomId);

    if (!peer || !state.peerId) {
      inviteAutoJoinRoomId = normalizedRoomId;
      return false;
    }

    if (normalizedRoomId === state.peerId) {
      showToast("Invite link points to your own Room ID", "warning");
      return false;
    }

    if (activeCalls.has(normalizedRoomId)) {
      inviteAutoJoinAttempted = true;
      inviteAutoJoinRoomId = normalizedRoomId;
      return true;
    }

    if (inviteAutoJoinAttempted && inviteAutoJoinRoomId === normalizedRoomId) {
      return false;
    }

    inviteAutoJoinAttempted = true;
    inviteAutoJoinRoomId = normalizedRoomId;
    showToast("Joining room from invite link...", "info");
    await callPeer(normalizedRoomId);
    return true;
  }

  async function callPeer(remotePeerId) {
    if (!peer) {
      showToast("Not connected to server", "error");
      return false;
    }
    if (!remotePeerId) {
      showToast("Enter a Room ID to call", "warning");
      return false;
    }

    // Ensure remotePeerId is a string before trimming
    if (typeof remotePeerId !== "string") {
      showToast("Invalid Room ID format", "error");
      return false;
    }

    // Normalize the peer ID to avoid whitespace/case mismatches
    remotePeerId = normalizeRoomId(remotePeerId);

    if (!isValidRoomId(remotePeerId)) {
      showToast(
        "Room ID must be exactly 6 characters using only uppercase letters (A-Z except I,O) and digits (2-9)",
        "error"
      );
      return false;
    }
    if (remotePeerId === state.peerId) {
      showToast("You cannot call yourself", "warning");
      return false;
    }
    if (activeCalls.has(remotePeerId)) {
      showToast("Already connected to this participant", "warning");
      return false;
    }

    if (!consentGiven) {
      const ok = await askConsent("the remote participant");
      if (!ok) return false;
    }

    const ok = await startLocalMedia();
    if (!ok) return false;

    updateStatus("fa-solid fa-spinner fa-spin", "Calling...", "warning");
    setStatusIcon("connecting");
    const call = peer.call(remotePeerId, voiceStream || localStream);
    activeCalls.set(remotePeerId, call);
    updateParticipantsList();
    handleCallStream(call);
    ensureDataConn(remotePeerId);
    return true;
  }

  /* ── Controls ── */
  async function updateTracksInCalls(newTrack, kind) {
    for (const call of activeCalls.values()) {
      // 1. Check saved senders first (robust against null tracks after mute).
      let sender = call.sendersByKind ? call.sendersByKind[kind] : null;

      // 2. Fallback: scan transceivers by kind — also matches senders whose
      //    current track may be null (e.g. after a prior replaceTrack(null)).
      if (!sender) {
        const pc = call.peerConnection;
        if (!pc) continue;
        if (typeof pc.getTransceivers === "function") {
          const tr = pc
            .getTransceivers()
            .find((t) => t.receiver && t.receiver.track && t.receiver.track.kind === kind);
          sender = tr ? tr.sender : null;
        }
        if (!sender) {
          sender = pc.getSenders().find((s) => s.track && s.track.kind === kind);
        }
        if (sender && call.sendersByKind) call.sendersByKind[kind] = sender;
      }

      if (sender) {
        try {
          await sender.replaceTrack(newTrack);
          // Keep the cache fresh so subsequent toggles find the correct sender.
          if (call.sendersByKind) call.sendersByKind[kind] = sender;
        } catch (err) {
          console.warn(
            `[VideoChat] replaceTrack failed for kind=${kind} on peer=${call.peer}:`,
            err
          );
        }
      }
    }
  }

  function updateMediaButtons() {
    const micBtn = $("btn-mic");
    if (micBtn) {
      micBtn.innerHTML = micMuted
        ? '<i class="fa-solid fa-microphone-slash" aria-hidden="true"></i>'
        : '<i class="fa-solid fa-microphone" aria-hidden="true"></i>';
      micBtn.title = micMuted ? "Unmute mic" : "Mute mic";
      micBtn.classList.toggle("active", micMuted);
      micBtn.setAttribute("aria-pressed", micMuted ? "true" : "false");
    }
    const camBtn = $("btn-cam");
    if (camBtn) {
      camBtn.innerHTML = camOff
        ? '<i class="fa-solid fa-video-slash" aria-hidden="true"></i>'
        : '<i class="fa-solid fa-video" aria-hidden="true"></i>';
      camBtn.title = camOff ? "Enable camera" : "Disable camera";
      camBtn.classList.toggle("active", camOff);
      camBtn.setAttribute("aria-pressed", camOff ? "true" : "false");
    }
  }

  /* ── Initial Permission Helper ── */
  async function checkInitialPermissions() {
    if (!navigator.permissions || !navigator.permissions.query) return;
    try {
      // Check camera & mic state without requesting them
      const camStatus = await navigator.permissions.query({ name: "camera" });
      const micStatus = await navigator.permissions.query({ name: "microphone" });

      const updateHint = () => {
        const isBlocked = camStatus.state === "denied" || micStatus.state === "denied";
        const hint = $("permission-hint");
        if (hint) {
          if (isBlocked) hint.classList.remove("hidden");
          else hint.classList.add("hidden");
        }
      };

      updateHint();
      camStatus.onchange = updateHint;
      micStatus.onchange = updateHint;
    } catch (e) {
      console.warn("Permissions API not supported for media:", e);
    }
  }

  async function toggleMic() {
    if (walkieTalkieMode) {
      showToast("Microphone toggle is disabled. Use the Push-to-Talk button instead.", "info");
      return;
    }
    micMuted = !micMuted;
    updateMediaButtons(); // Update instantly for zero delay UI
    if (!localStream || localStream.getAudioTracks().length === 0) {
      if (!micMuted) {
        const ok = await startLocalMedia({ audio: true, video: false });
        if (!ok) {
          micMuted = true;
          updateMediaButtons();
          return;
        }
      }
    } else {
      if (micMuted) {
        // Turning OFF: stop hardware and remove track so next unmute re-acquires.
        localStream.getAudioTracks().forEach((t) => {
          t.stop();
          localStream.removeTrack(t);
        });
        await updateTracksInCalls(null, "audio");
      } else {
        // Turning ON: re-enable any still-present (but disabled) track first.
        // This handles the initial-load case where tracks were acquired with
        // enabled=false. Only call startLocalMedia when there is truly no track.
        const existing = localStream.getAudioTracks();
        if (existing.length > 0) {
          existing.forEach((t) => (t.enabled = true));
          await updateTracksInCalls(existing[existing.length - 1], "audio");
          if (typeof VoiceChanger !== "undefined" && voiceStream) {
            _replaceVoiceTrack();
          }
        } else {
          const ok = await startLocalMedia({ audio: true, video: false });
          if (ok) {
            if (typeof VoiceChanger !== "undefined" && voiceStream) {
              _replaceVoiceTrack();
            }
          } else {
            micMuted = true;
            updateMediaButtons();
          }
        }
      }
    }

    syncControlButtons();
    updateLocalTilePresentation();
    broadcastProfile(true);
    showToast(micMuted ? "Microphone muted" : "Microphone unmuted", "info");
  }

  async function toggleCamera() {
    if (walkieTalkieMode) {
      showToast("Camera is disabled in walkie-talkie mode", "info");
      return;
    }
    camOff = !camOff;
    updateMediaButtons(); // Update instantly
    if (!localStream || localStream.getVideoTracks().length === 0) {
      if (!camOff) {
        const ok = await startLocalMedia({ video: true, audio: false });
        if (!ok) {
          camOff = true;
          updateMediaButtons();
          return;
        }
      }
    } else {
      if (camOff) {
        // Turning OFF: stop hardware and remove track so next enable re-acquires.
        localStream.getVideoTracks().forEach((t) => {
          t.stop();
          localStream.removeTrack(t);
        });
        await updateTracksInCalls(null, "video");
      } else {
        // Turning ON: re-enable any still-present (but disabled) track first.
        // This handles the initial-load case where tracks were acquired with
        // enabled=false. Only call startLocalMedia when there is truly no track.
        const existing = localStream.getVideoTracks();
        if (existing.length > 0) {
          existing.forEach((t) => (t.enabled = true));
          await updateTracksInCalls(existing[existing.length - 1], "video");
          const localVideo = $("local-video");
          if (localVideo) localVideo.srcObject = localStream;
        } else {
          const ok = await startLocalMedia({ video: true, audio: false });
          if (!ok) {
            camOff = true;
            updateMediaButtons();
          }
        }
      }
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

  function togglePeerAudioMute(peerId) {
    if (mutedPeers.has(peerId)) {
      mutedPeers.delete(peerId);
    } else {
      mutedPeers.add(peerId);
    }
    
    const tile = getTileElements(peerId);
    if (tile && tile.video) {
        tile.video.muted = mutedPeers.has(peerId);
    }
    
    updateParticipantsList();
  }

  async function endCall(options = {}) {
    const { keepEndControlVisible = false } = options;
    isEndingCall = true;

    activeCalls.forEach((call) => {
      try {
        call.close();
      } catch {
        /* ignore close failures */
      }
    });
    activeCalls.clear();
    activeDataConns.forEach((conn) => {
      try {
        conn.close();
      } catch {
        /* ignore close failures */
      }
    });
    activeDataConns.clear();
    // Yield to allow any microtasks/event handlers triggered by close() to run while
    // isEndingCall is still true and connections are known to be closing.
    await Promise.resolve();
    lastProfileBroadcastAt.clear();
    peerProfiles.clear();
    stopAllRemoteSpeakingMonitors();
    localSpeakingUntil = 0;
    setTileSpeakingIndicator("local", false);
    localHandRaised = false;
    walkieFloorHolder = null;
    walkieTalkieMode = false;
    syncRaiseHandButton();
    state.connected = false;
    updateStatus("fa-solid fa-phone-slash", "Call ended", "muted");
    setStatusIcon("offline");
    const videoGrid = $("video-grid");
    if (videoGrid) {
      videoGrid.querySelectorAll(".video-wrapper:not(:first-child)").forEach((w) => w.remove());
    }
    updateLocalTilePresentation();
    if ($("call-controls")) {
      $("btn-noise") && $("btn-noise").classList.add("hidden");
      $("btn-screen") && $("btn-screen").classList.add("hidden");
      if (keepEndControlVisible) {
        $("btn-end") && $("btn-end").classList.remove("hidden");
      } else {
        $("btn-end") && $("btn-end").classList.add("hidden");
      }
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
    isEndingCall = false;
  }

  async function hangup(options = {}) {
    const { navigateHome = true } = options;

    await endCall();
    if (peer) {
      try {
        peer.disconnect();
      } catch {
        /* ignore disconnect failures */
      }
      try {
        peer.destroy();
      } catch {
        /* ignore destroy failures */
      }
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
      try {
        await audioContext.close();
      } catch {
        /* ignore close failures */
      }
      audioContext = null;
    }
    stopAllRemoteSpeakingMonitors();
    if (speakingAudioContext) {
      try {
        await speakingAudioContext.close();
      } catch {
        /* ignore close failures */
      }
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
    setStatusIcon("offline");
    updateStatus("fa-solid fa-power-off", "Disconnected", "muted");
    showToast("Session ended and media released", "success");
    if (navigateHome) {
      navigateToHome();
    }
  }

  /* ── Voice changer ── */

  /** Push current processed stream track to all active calls. */
  function _replaceVoiceTrack() {
    if (typeof VoiceChanger === "undefined") return;
    const processedStream = VoiceChanger.getProcessedStream();
    const newTrack = processedStream && processedStream.getAudioTracks()[0];
    if (!newTrack) return;
    activeCalls.forEach((call) => {
      // Prefer the cached sender reference — it remains valid even if the
      // sender's current track has been set to null by a mute cycle.
      let sender = call.sendersByKind ? call.sendersByKind["audio"] : null;
      if (!sender && call.peerConnection) {
        sender = call.peerConnection.getSenders().find((s) => s.track && s.track.kind === "audio");
        if (sender && call.sendersByKind) call.sendersByKind["audio"] = sender;
      }
      if (sender) {
        sender.replaceTrack(newTrack).catch(() => {
          /* non-fatal — voice track replacement failed */
        });
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

  /** Persist current in-room voice settings for reload-safe UI restoration. */
  function _persistVoicePreferences() {
    if (typeof VoiceChanger === "undefined") return;
    try {
      const payload = {
        effectLevels: VoiceChanger.getEffectLevels(),
        monitorVolume: VoiceChanger.getMonitorVolume(),
        micGain: VoiceChanger.getMicGain(),
      };
      window.sessionStorage.setItem(VOICE_PREFS_STORAGE_KEY, JSON.stringify(payload));
    } catch {
      /* ignore storage failures */
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
      _persistVoicePreferences();
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
      _persistVoicePreferences();
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
    _persistVoicePreferences();
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
    _persistVoicePreferences();
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
    /* Monitor enablement is session-local; stored voice preferences do not rehydrate it. */
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
          <h3 style="display:flex;align-items:center;gap:0.5rem"><i class="fa-solid fa-shield-halved text-primary" aria-hidden="true"></i>Recording Consent Required</h3>
          <p>This call may be recorded for AI notes and security purposes. Do you consent to participate in this secure call with <strong id="consent-caller-name" style="color:#fff"></strong>?</p>
          <div class="alert alert-info" style="margin-bottom:1rem">
            <i class="fa-solid fa-circle-info text-primary" aria-hidden="true"></i>
            <span>Consent is cryptographically timestamped and stored locally. You can withdraw at any time.</span>
          </div>
          <div style="display:flex;gap:0.75rem;justify-content:flex-end">
            <button class="btn btn-secondary" id="consent-deny">Decline</button>
            <button class="btn btn-primary" id="consent-allow">I Consent</button>
          </div>
        </div>
      `;
      const callerNameEl = overlay.querySelector("#consent-caller-name");
      if (callerNameEl) callerNameEl.textContent = callerName;
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
        // Use cached sender reference (robust against null tracks)
        let sender = call.sendersByKind ? call.sendersByKind.video : null;
        if (!sender && call.peerConnection) {
          sender = call.peerConnection
            .getSenders()
            .find((s) => s.track && s.track.kind === "video");
        }
        if (sender) await sender.replaceTrack(screenTrack);
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
        // Use the cached sender reference so we reliably find the video sender
        // even when transitioning from a screen track (whose kind is also video)
        // back to the camera track.
        let sender = call.sendersByKind ? call.sendersByKind["video"] : null;
        if (!sender && call.peerConnection) {
          sender = call.peerConnection
            .getSenders()
            .find((s) => s.track && s.track.kind === "video");
        }
        if (sender) {
          sender.replaceTrack(videoTrack).catch(() => {
            /* non-fatal — camera track restoration failed */
          });
          // Keep the cache pointing at this sender for future toggles.
          if (call.sendersByKind) call.sendersByKind["video"] = sender;
        }
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
    const walkieParam = params.get("walkie");
    const isPrejoin = params.get("prejoin") === "1";
    const hasUrlPrefs = mic !== null || cam !== null;

    if (mic === "off" || mic === "on") {
      initialMediaPreferences.mic = mic === "on";
    }
    if (cam === "off" || cam === "on") {
      initialMediaPreferences.cam = cam === "on";
    }
    if (walkieParam === "1") {
      initialMediaPreferences.walkie = true;
    }

    if (hasUrlPrefs) {
      try {
        window.sessionStorage.setItem(
          MEDIA_PREFS_STORAGE_KEY,
          JSON.stringify({
            mic: Boolean(initialMediaPreferences.mic),
            cam: Boolean(initialMediaPreferences.cam),
          })
        );
      } catch {
        /* ignore storage failures */
      }
    } else {
      try {
        const raw = window.sessionStorage.getItem(MEDIA_PREFS_STORAGE_KEY);
        if (raw) {
          const parsed = JSON.parse(raw);
          if (parsed && typeof parsed === "object") {
            if (typeof parsed.mic === "boolean") {
              initialMediaPreferences.mic = parsed.mic;
            }
            if (typeof parsed.cam === "boolean") {
              initialMediaPreferences.cam = parsed.cam;
            }
          }
        }
      } catch {
        /* ignore storage failures */
      }
    }

    if (isPrejoin) {
      params.delete("prejoin");
      params.delete("mic");
      params.delete("cam");
      params.delete("name");
      params.delete("walkie");
      const query = params.toString();
      const cleanUrl = window.location.pathname + (query ? "?" + query : "");
      window.history.replaceState({}, "", cleanUrl);
    }
  }

  async function init() {
    state.displayName = resolveDisplayName();
    state.displayInitials = makeInitials(state.displayName);

    readInitialMediaPreferencesFromUrl();
    applyInitialMediaPreferences();
    updateLocalTilePresentation();

    // Activate walkie-talkie mode immediately if the user selected it from the lobby.
    if (initialMediaPreferences.walkie) {
      await setWalkieTalkieMode(true);
    }

    // Start media eagerly only when the initial preference explicitly enables mic/camera.
    if (!walkieTalkieMode && (initialMediaPreferences.mic || initialMediaPreferences.cam)) {
      const ok = await startLocalMedia();
      if (ok) {
        applyInitialMediaPreferences();
        updateLocalTilePresentation();
      }
    }

    _applyStoredVoicePreferences();
    syncRaiseHandButton();
    updateParticipantsList();

    // Always init peer regardless of success of startLocalMedia (can join without media)
    await initPeer();
    checkInitialPermissions();
    const pushToTalkBtn = $("btn-push-to-talk");
    if (pushToTalkBtn) {
      pushToTalkBtn.addEventListener("mousedown", () => {
        void onPushToTalkStart();
      });
      pushToTalkBtn.addEventListener("mouseup", () => {
        void onPushToTalkEnd();
      });
      pushToTalkBtn.addEventListener("mouseleave", () => {
        void onPushToTalkEnd();
      });
      pushToTalkBtn.addEventListener("touchstart", (event) => {
        event.preventDefault();
        void onPushToTalkStart();
      });
      pushToTalkBtn.addEventListener("touchend", (event) => {
        event.preventDefault();
        void onPushToTalkEnd();
      });
    }
    window.addEventListener("beforeunload", () => {
      // Inline synchronous teardown for unload – browsers don't wait for Promises
      try {
        if (peer) {
          peer.disconnect();
          peer.destroy();
        }
      } catch {
        /* ignore sync disconnect/destroy failures */
      }
      if (localStream) {
        localStream.getTracks().forEach((t) => t.stop());
      }
      if (typeof VoiceChanger !== "undefined") {
        try {
          VoiceChanger.destroy();
        } catch {
          /* ignore VoiceChanger destroy failures */
        }
      }
    });

    // pagehide is more reliable than beforeunload for cleanup across mobile and desktop.
    window.addEventListener("pagehide", (event) => {
      if (!event.persisted) {
        hangup({ navigateHome: false }).catch(() => {});
      }
    });
    return true;
  }

  return {
    init,
    callPeer,
    autoJoinFromInvite,
    disconnectPeer,
    toggleMic,
    toggleCamera,
    endCall,
    hangup,
    toggleNoiseSuppression,
    toggleRaiseHand,
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
    togglePeerAudioMute,
  };
})();

window.toggleParticipantMute = (peerId) => {
  if (typeof VideoChat !== "undefined" && VideoChat.togglePeerAudioMute) {
    VideoChat.togglePeerAudioMute(peerId);
  }
};
