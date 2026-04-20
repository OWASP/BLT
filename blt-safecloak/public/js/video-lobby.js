/**
 * BLT-SafeCloak — video-lobby.js
 * Lobby pre-join experience with camera preview and one-entry media preferences.
 */

(() => {
  const ROOM_ID_RE = /^[ABCDEFGHJKLMNPQRSTUVWXYZ23456789]{6}$/;
  const VOICE_PREFS_STORAGE_KEY = "blt-safecloak-voice-preferences";
  const DISPLAY_NAME_STORAGE_KEY = "blt-safecloak-display-name";
  const MEDIA_PREFS_STORAGE_KEY = "blt-safecloak-media-preferences";
  const LOBBY_EFFECT_ORDER = ["deep", "chipmunk", "robot", "echo", "voice1", "voice2", "voice3"];

  let previewStream = null;
  let micEnabled = false;
  let camEnabled = false;
  let voiceUiBound = false;

  const $ = (id) => document.getElementById(id);

  function normalizeRoomId(value) {
    return (value || "").trim().toUpperCase();
  }

  function normalizeDisplayName(value) {
    return (value || "").trim().replace(/\s+/g, " ").slice(0, 40);
  }

  function isValidRoomId(value) {
    return ROOM_ID_RE.test(value);
  }

  function getDisplayNameInput() {
    return $("display-name-input");
  }

  function restoreDisplayNameFromStorage() {
    const input = getDisplayNameInput();
    if (!input) return;

    const params = new URLSearchParams(window.location.search);
    const fromUrl = normalizeDisplayName(params.get("name"));
    if (fromUrl) {
      input.value = fromUrl;
      try {
        window.sessionStorage.setItem(DISPLAY_NAME_STORAGE_KEY, fromUrl);
      } catch {
        /* ignore storage failures */
      }
      return;
    }

    let fromStorage = "";
    try {
      fromStorage = normalizeDisplayName(window.sessionStorage.getItem(DISPLAY_NAME_STORAGE_KEY));
    } catch {
      /* ignore storage failures */
    }
    if (fromStorage) {
      input.value = fromStorage;
    }
  }

  function getValidatedDisplayName() {
    const input = getDisplayNameInput();
    if (!input) return "";

    const name = normalizeDisplayName(input.value);
    input.value = name;
    if (!name) {
      showToast("Enter your display name before continuing", "warning");
      input.focus();
      return null;
    }

    try {
      window.sessionStorage.setItem(DISPLAY_NAME_STORAGE_KEY, name);
    } catch {
      /* ignore storage failures */
    }
    return name;
  }

  function hasAudioTrack() {
    return Boolean(previewStream && previewStream.getAudioTracks().length > 0);
  }

  function hasVideoTrack() {
    return Boolean(previewStream && previewStream.getVideoTracks().length > 0);
  }

  function _syncSliderFill(el) {
    if (!el) return;
    const min = parseFloat(el.min) || 0;
    const max = parseFloat(el.max) || 100;
    const pct = (((parseFloat(el.value) || 0) - min) / (max - min)) * 100;
    el.style.background = `linear-gradient(to right, #e10101 ${pct}%, #e5e7eb ${pct}%)`;
  }

  function getStoredVoicePreferences() {
    try {
      const raw = window.sessionStorage.getItem(VOICE_PREFS_STORAGE_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      return parsed && typeof parsed === "object" ? parsed : null;
    } catch {
      return null;
    }
  }

  function persistVoicePreferences() {
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

  function _syncPreviewNormalChip() {
    if (typeof VoiceChanger === "undefined") return;

    const levels = VoiceChanger.getEffectLevels();
    const anyActive = Object.values(levels).some((v) => v > 0);
    const normalBtn = document.querySelector('[data-lobby-voice-mode="normal"]');
    if (normalBtn) {
      normalBtn.classList.toggle("active", !anyActive);
      normalBtn.setAttribute("aria-pressed", String(!anyActive));
    }
  }

  function _addPreviewEffectSliderRow(mode, level) {
    const container = $("prejoin-effect-sliders-container");
    if (!container || typeof VoiceChanger === "undefined") return;
    if (container.querySelector(`[data-prejoin-effect-slider="${mode}"]`)) return;

    const modes = VoiceChanger.getModes();
    const modeInfo = modes[mode] || { label: mode, icon: "fa-music" };
    const initialPct = Math.round(level * 100);

    const row = document.createElement("div");
    row.className = "mt-1.5 flex items-center gap-2";
    row.setAttribute("data-prejoin-effect-slider", mode);

    const lbl = document.createElement("span");
    lbl.className = "flex-none flex items-center gap-1 text-[11px] font-semibold text-gray-500";
    lbl.style.minWidth = "4.5rem";
    lbl.innerHTML = `<i class="fa-solid ${modeInfo.icon} text-[10px]" aria-hidden="true"></i>${modeInfo.label}`;
    row.appendChild(lbl);

    const slider = document.createElement("input");
    slider.type = "range";
    slider.className = "voice-slider min-w-0 flex-1";
    slider.min = "0";
    slider.max = "100";
    slider.step = "1";
    slider.value = String(initialPct);
    slider.setAttribute("aria-label", `${modeInfo.label} effect level`);
    _syncSliderFill(slider);
    row.appendChild(slider);

    const valueLabel = document.createElement("span");
    valueLabel.className = "w-7 flex-none text-right text-[11px] font-semibold text-primary";
    valueLabel.textContent = `${initialPct}%`;
    row.appendChild(valueLabel);

    slider.addEventListener("input", () => {
      const value = parseInt(slider.value, 10);
      valueLabel.textContent = `${value}%`;
      _syncSliderFill(slider);
      setPreviewVoiceLevel(mode, value / 100);
    });

    container.appendChild(row);
  }

  function _removePreviewEffectSliderRow(mode) {
    const container = $("prejoin-effect-sliders-container");
    if (!container) return;
    const row = container.querySelector(`[data-prejoin-effect-slider="${mode}"]`);
    if (row) row.remove();
  }

  function _clearPreviewEffectSliders() {
    const container = $("prejoin-effect-sliders-container");
    if (container) container.innerHTML = "";
  }

  function _syncMonitorButton() {
    if (typeof VoiceChanger === "undefined") return;
    const btn = $("btn-preview-monitor");
    if (!btn) return;
    const enabled = VoiceChanger.getMonitorEnabled();
    btn.classList.toggle("active", enabled);
    btn.setAttribute("aria-pressed", String(enabled));
  }

  function _syncPreviewVoiceAvailability() {
    const audioAvailable = hasAudioTrack();

    document.querySelectorAll("[data-lobby-voice-mode]").forEach((btn) => {
      const mode = btn.dataset.lobbyVoiceMode;
      const disable = !audioAvailable && mode !== "normal";
      btn.disabled = disable;
      btn.classList.toggle("opacity-50", disable);
      btn.classList.toggle("cursor-not-allowed", disable);
    });

    const monitorBtn = $("btn-preview-monitor");
    if (monitorBtn) {
      monitorBtn.disabled = !audioAvailable;
      monitorBtn.classList.toggle("opacity-50", !audioAvailable);
      monitorBtn.classList.toggle("cursor-not-allowed", !audioAvailable);
    }

    const monitorSlider = $("slider-preview-monitor-volume");
    const micSlider = $("slider-preview-mic-gain");
    [monitorSlider, micSlider].forEach((slider) => {
      if (!slider) return;
      slider.disabled = !audioAvailable;
      slider.classList.toggle("opacity-50", !audioAvailable);
      slider.classList.toggle("cursor-not-allowed", !audioAvailable);
    });
  }

  function _syncPreviewVoiceSliders() {
    if (typeof VoiceChanger === "undefined") return;

    const monitorSlider = $("slider-preview-monitor-volume");
    const monitorLabel = $("label-preview-monitor-volume");
    if (monitorSlider && monitorLabel) {
      const value = Math.round(VoiceChanger.getMonitorVolume() * 100);
      monitorSlider.value = String(value);
      monitorLabel.textContent = `${value}%`;
      _syncSliderFill(monitorSlider);
    }

    const micSlider = $("slider-preview-mic-gain");
    const micLabel = $("label-preview-mic-gain");
    if (micSlider && micLabel) {
      const value = Math.round(VoiceChanger.getMicGain() * 100);
      micSlider.value = String(value);
      micLabel.textContent = `${value}%`;
      _syncSliderFill(micSlider);
    }
  }

  function _syncPreviewEffectButtonsAndRows() {
    if (typeof VoiceChanger === "undefined") return;

    _clearPreviewEffectSliders();
    const levels = VoiceChanger.getEffectLevels();

    LOBBY_EFFECT_ORDER.forEach((mode) => {
      const level = Number(levels[mode]) || 0;
      const btn = document.querySelector(`[data-lobby-voice-mode="${mode}"]`);
      if (btn) {
        const active = level > 0;
        btn.classList.toggle("active", active);
        btn.setAttribute("aria-pressed", String(active));
      }
      if (level > 0) {
        _addPreviewEffectSliderRow(mode, level);
      }
    });

    _syncPreviewNormalChip();
  }

  function applyStoredPreviewVoicePreferences() {
    if (typeof VoiceChanger === "undefined") return;

    const saved = getStoredVoicePreferences();
    if (!saved) {
      _syncPreviewEffectButtonsAndRows();
      _syncPreviewVoiceSliders();
      _syncMonitorButton();
      return;
    }

    const levels = saved.effectLevels && typeof saved.effectLevels === "object" ? saved.effectLevels : {};
    LOBBY_EFFECT_ORDER.forEach((mode) => {
      const raw = Number(levels[mode]);
      const value = Number.isFinite(raw) ? Math.max(0, Math.min(1, raw)) : 0;
      VoiceChanger.setEffectLevel(mode, value);
    });

    if (Number.isFinite(Number(saved.monitorVolume))) {
      VoiceChanger.setMonitorVolume(Math.max(0, Math.min(1, Number(saved.monitorVolume))));
    }

    if (Number.isFinite(Number(saved.micGain))) {
      VoiceChanger.setMicGain(Math.max(0, Math.min(2, Number(saved.micGain))));
    }

    _syncPreviewEffectButtonsAndRows();
    _syncPreviewVoiceSliders();
    _syncMonitorButton();
  }

  function setPreviewVoiceMode(mode) {
    if (typeof VoiceChanger === "undefined") return;

    if (mode === "normal") {
      const levels = VoiceChanger.getEffectLevels();
      Object.keys(levels).forEach((effectMode) => VoiceChanger.setEffectLevel(effectMode, 0));
      _clearPreviewEffectSliders();
      document.querySelectorAll("[data-lobby-voice-mode]").forEach((btn) => {
        const isNormal = btn.dataset.lobbyVoiceMode === "normal";
        btn.classList.toggle("active", isNormal);
        btn.setAttribute("aria-pressed", String(isNormal));
      });
      persistVoicePreferences();
      return;
    }

    VoiceChanger.setMode(mode);
    _syncPreviewEffectButtonsAndRows();
    persistVoicePreferences();
  }

  function togglePreviewEffectMode(mode) {
    if (typeof VoiceChanger === "undefined") return;

    const newLevel = VoiceChanger.toggleEffect(mode);
    const btn = document.querySelector(`[data-lobby-voice-mode="${mode}"]`);
    if (btn) {
      btn.classList.toggle("active", newLevel > 0);
      btn.setAttribute("aria-pressed", String(newLevel > 0));
    }

    if (newLevel > 0) {
      _addPreviewEffectSliderRow(mode, newLevel);
    } else {
      _removePreviewEffectSliderRow(mode);
    }

    _syncPreviewNormalChip();
    persistVoicePreferences();
  }

  function setPreviewVoiceLevel(mode, level) {
    if (typeof VoiceChanger === "undefined") return;

    VoiceChanger.setEffectLevel(mode, level);

    const enabled = level > 0;
    const btn = document.querySelector(`[data-lobby-voice-mode="${mode}"]`);
    if (btn) {
      btn.classList.toggle("active", enabled);
      btn.setAttribute("aria-pressed", String(enabled));
    }

    if (!enabled) {
      _removePreviewEffectSliderRow(mode);
    }

    _syncPreviewNormalChip();
    persistVoicePreferences();
  }

  function togglePreviewMonitor() {
    if (typeof VoiceChanger === "undefined") return;
    VoiceChanger.toggleMonitor();
    _syncMonitorButton();
    persistVoicePreferences();
  }

  function resetPreviewVoiceUi() {
    _clearPreviewEffectSliders();
    document.querySelectorAll("[data-lobby-voice-mode]").forEach((btn) => {
      const isNormal = btn.dataset.lobbyVoiceMode === "normal";
      btn.classList.toggle("active", isNormal);
      btn.setAttribute("aria-pressed", String(isNormal));
    });

    const monitorBtn = $("btn-preview-monitor");
    if (monitorBtn) {
      monitorBtn.classList.remove("active");
      monitorBtn.setAttribute("aria-pressed", "false");
    }
  }

  function initPreviewVoiceEngine() {
    if (typeof VoiceChanger === "undefined") return;

    if (!previewStream || !hasAudioTrack()) {
      resetPreviewVoiceUi();
      _syncPreviewVoiceAvailability();
      return;
    }

    VoiceChanger.init(previewStream);
    applyStoredPreviewVoicePreferences();
    _syncPreviewVoiceAvailability();
  }

  function bindPreviewVoiceControls() {
    if (voiceUiBound) return;

    document.querySelectorAll("[data-lobby-voice-mode]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const mode = btn.dataset.lobbyVoiceMode;
        if (!mode) return;

        if (!hasAudioTrack()) {
          showToast("Microphone required for voice effects", "warning");
          return;
        }

        if (mode === "normal") {
          setPreviewVoiceMode("normal");
        } else {
          togglePreviewEffectMode(mode);
        }
      });
    });

    const monitorBtn = $("btn-preview-monitor");
    if (monitorBtn) {
      monitorBtn.addEventListener("click", () => {
        if (!hasAudioTrack()) {
          showToast("Microphone required for monitor", "warning");
          return;
        }
        togglePreviewMonitor();
      });
    }

    const monitorSlider = $("slider-preview-monitor-volume");
    const monitorLabel = $("label-preview-monitor-volume");
    if (monitorSlider && monitorLabel) {
      monitorSlider.addEventListener("input", () => {
        const value = parseInt(monitorSlider.value, 10);
        monitorLabel.textContent = `${value}%`;
        _syncSliderFill(monitorSlider);
        if (typeof VoiceChanger !== "undefined") {
          VoiceChanger.setMonitorVolume(value / 100);
          persistVoicePreferences();
        }
      });
      _syncSliderFill(monitorSlider);
    }

    const micSlider = $("slider-preview-mic-gain");
    const micLabel = $("label-preview-mic-gain");
    if (micSlider && micLabel) {
      micSlider.addEventListener("input", () => {
        const value = parseInt(micSlider.value, 10);
        micLabel.textContent = `${value}%`;
        _syncSliderFill(micSlider);
        if (typeof VoiceChanger !== "undefined") {
          VoiceChanger.setMicGain(value / 100);
          persistVoicePreferences();
        }
      });
      _syncSliderFill(micSlider);
    }

    voiceUiBound = true;
  }

  function stopPreviewStream() {
    if (previewStream) {
      previewStream.getTracks().forEach((track) => track.stop());
      previewStream = null;
    }

    if (typeof VoiceChanger !== "undefined") {
      VoiceChanger.destroy();
    }

    resetPreviewVoiceUi();
  }

  function updatePreviewUI() {
    const status = $("prejoin-status");
    const videoEl = $("prejoin-video");
    const placeholder = $("prejoin-placeholder");
    const micBtn = $("btn-preview-mic");
    const camBtn = $("btn-preview-cam");

    const audioAvailable = hasAudioTrack();
    const videoAvailable = hasVideoTrack();

    if (videoEl) {
      if (videoAvailable) {
        videoEl.style.display = "block";
        videoEl.srcObject = previewStream;
      } else {
        videoEl.style.display = "none";
        videoEl.srcObject = null;
      }
    }

    if (placeholder) {
      placeholder.style.display = videoAvailable ? "none" : "flex";
      placeholder.textContent = "Camera preview unavailable";
    }

    if (status) {
      if (audioAvailable && videoAvailable) {
        status.textContent = "Camera and microphone are ready.";
      } else if (videoAvailable) {
        status.textContent = "Microphone not available. You will join with video only.";
      } else if (audioAvailable) {
        status.textContent = "Camera not available. You will join with audio only.";
      } else {
        status.textContent = "No camera or microphone available. You can still continue.";
      }
    }

    if (micBtn) {
      micBtn.innerHTML = micEnabled
        ? '<i class="fa-solid fa-microphone" aria-hidden="true"></i>'
        : '<i class="fa-solid fa-microphone-slash" aria-hidden="true"></i>';
      micBtn.title = micEnabled ? "Mute microphone before joining" : "Unmute microphone";
      micBtn.classList.toggle("active", !micEnabled);
      micBtn.setAttribute("aria-pressed", (!micEnabled).toString());
      micBtn.disabled = !audioAvailable;
      micBtn.classList.toggle("opacity-50", !audioAvailable);
      micBtn.classList.toggle("cursor-not-allowed", !audioAvailable);
    }

    if (camBtn) {
      camBtn.innerHTML = camEnabled
        ? '<i class="fa-solid fa-video" aria-hidden="true"></i>'
        : '<i class="fa-solid fa-video-slash" aria-hidden="true"></i>';
      camBtn.title = camEnabled ? "Disable camera before joining" : "Enable camera";
      camBtn.classList.toggle("active", !camEnabled);
      camBtn.setAttribute("aria-pressed", (!camEnabled).toString());
      camBtn.disabled = !videoAvailable;
      camBtn.classList.toggle("opacity-50", !videoAvailable);
      camBtn.classList.toggle("cursor-not-allowed", !videoAvailable);
    }

    _syncPreviewVoiceAvailability();
  }

  function setTrackEnabled(kind, enabled) {
    if (!previewStream) return;
    const tracks =
      kind === "audio" ? previewStream.getAudioTracks() : previewStream.getVideoTracks();
    tracks.forEach((track) => {
      track.enabled = enabled;
    });
  }

  async function initPreviewStream() {
    const constraints = [
      { video: true, audio: true },
      { video: true, audio: false },
      { video: false, audio: true },
    ];

    for (const mediaConstraints of constraints) {
      try {
        previewStream = await navigator.mediaDevices.getUserMedia(mediaConstraints);
        micEnabled = false;
        camEnabled = false;
        setTrackEnabled("audio", false);
        setTrackEnabled("video", false);
        updatePreviewUI();
        initPreviewVoiceEngine();
        return;
      } catch {
        // Try next fallback profile.
      }
    }

    micEnabled = false;
    camEnabled = false;
    updatePreviewUI();
    resetPreviewVoiceUi();
    showToast("Could not access camera/microphone preview", "warning");
  }

  function buildRoomUrl(roomId = "") {
    const target = new URL(`${window.location.origin}/video-room`);
    if (roomId) {
      target.searchParams.set("room", roomId);
    }

    const micPref = hasAudioTrack() ? (micEnabled ? "on" : "off") : "off";
    const camPref = hasVideoTrack() ? (camEnabled ? "on" : "off") : "off";

    target.searchParams.set("prejoin", "1");
    target.searchParams.set("mic", micPref);
    target.searchParams.set("cam", camPref);
    return target;
  }

  function persistMediaPreferences() {
    const micPref = hasAudioTrack() ? micEnabled : false;
    const camPref = hasVideoTrack() ? camEnabled : false;

    try {
      window.sessionStorage.setItem(
        MEDIA_PREFS_STORAGE_KEY,
        JSON.stringify({ mic: micPref, cam: camPref })
      );
    } catch {
      /* ignore storage failures */
    }
  }

  function goToRoom(roomId = "", displayName = "") {
    if (displayName) {
      try {
        window.sessionStorage.setItem(DISPLAY_NAME_STORAGE_KEY, displayName);
      } catch {
        /* ignore storage failures */
      }
    }
    persistVoicePreferences();
    persistMediaPreferences();
    const target = buildRoomUrl(roomId);
    stopPreviewStream();
    window.location.href = target.toString();
  }

  function toggleMicPreview() {
    if (!hasAudioTrack()) {
      showToast("No microphone available", "warning");
      return;
    }

    micEnabled = !micEnabled;
    setTrackEnabled("audio", micEnabled);
    updatePreviewUI();
  }

  function toggleCamPreview() {
    if (!hasVideoTrack()) {
      showToast("No camera available", "warning");
      return;
    }

    camEnabled = !camEnabled;
    setTrackEnabled("video", camEnabled);
    updatePreviewUI();
  }

  function joinRoom() {
    const roomInput = $("room-id-input");
    if (!roomInput) return;
    const displayName = getValidatedDisplayName();
    if (!displayName) return;

    const roomId = normalizeRoomId(roomInput.value);
    roomInput.value = roomId;

    if (!roomId) {
      showToast("Enter a Room ID to continue", "warning");
      return;
    }

    if (!isValidRoomId(roomId)) {
      showToast(
        "Room ID must be 6 characters: A-Z (except I,O) and digits 2-9",
        "error"
      );
      return;
    }

    goToRoom(roomId, displayName);
  }

  document.addEventListener("DOMContentLoaded", async () => {
    const createBtn = $("btn-create-room");
    const joinBtn = $("btn-join-room");
    const roomInput = $("room-id-input");
    const displayNameInput = getDisplayNameInput();
    const micBtn = $("btn-preview-mic");
    const camBtn = $("btn-preview-cam");
    let shouldAutoJoinFromInvite = false;

    bindPreviewVoiceControls();
    restoreDisplayNameFromStorage();

    if (createBtn) {
      createBtn.addEventListener("click", () => {
        const displayName = getValidatedDisplayName();
        if (!displayName) return;
        goToRoom("", displayName);
      });
    }

    if (joinBtn) {
      joinBtn.addEventListener("click", joinRoom);
    }

    if (roomInput) {
      roomInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          joinRoom();
        }
      });

      const params = new URLSearchParams(window.location.search);
      const sharedRoomId = normalizeRoomId(params.get("room"));
      if (sharedRoomId) {
        roomInput.value = sharedRoomId;
        if (isValidRoomId(sharedRoomId)) {
          shouldAutoJoinFromInvite = true;
          showToast("Room ID loaded from share link", "info");
        }
        
        try {
          const createCard = $("card-create-room");
          const joinCard = $("card-join-room");
          const createBtn = $("btn-create-room");
          const joinBtn = $("btn-join-room");

          if (createCard && joinCard && createBtn && joinBtn && createCard.parentNode === joinCard.parentNode) {
            joinCard.parentNode.insertBefore(joinCard, createCard);

            const createClasses = createBtn.className;
            const joinClasses = joinBtn.className;

            createBtn.className = joinClasses;
            joinBtn.className = createClasses;
          }
        } catch (e) {
          // Handled silently in production
        }
      }
    }

    if (displayNameInput) {
      displayNameInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          const hasRoom = normalizeRoomId(roomInput ? roomInput.value : "");
          if (hasRoom) {
            joinRoom();
            return;
          }
          const displayName = getValidatedDisplayName();
          if (!displayName) return;
          goToRoom("", displayName);
        }
      });
    }

    if (micBtn) micBtn.addEventListener("click", toggleMicPreview);
    if (camBtn) camBtn.addEventListener("click", toggleCamPreview);

    try {
      await initPreviewStream();
    } catch (e) {
      // Fallback if initPreviewVoiceEngine(), VoiceChanger.init(), or updatePreviewUI() fails
      // inside initPreviewStream(). We reset to a safe "null" state so the UI reflects a 
      // non-previewable state and users can still proceed.
      micEnabled = false;
      camEnabled = false;
      updatePreviewUI();
      resetPreviewVoiceUi();

      const status = $("prejoin-status");
      if (status) {
        status.textContent = "Preview unavailable";
      }

      const micBtn = $("btn-preview-mic");
      if (micBtn) {
        micBtn.disabled = false;
        micBtn.classList.remove("opacity-50", "cursor-not-allowed");
      }

      const camBtn = $("btn-preview-cam");
      if (camBtn) {
        camBtn.disabled = false;
        camBtn.classList.remove("opacity-50", "cursor-not-allowed");
      }
    }

    if (shouldAutoJoinFromInvite) {
      const existingName = normalizeDisplayName(displayNameInput ? displayNameInput.value : "");
      if (existingName) {
        joinRoom();
      }
    }
  });

  window.addEventListener("beforeunload", stopPreviewStream);

  window.toggleParticipantMute = function(peerId) {
    if (typeof VideoChat !== "undefined" && VideoChat.togglePeerAudioMute) {
      VideoChat.togglePeerAudioMute(peerId);
    }
  };
})();
