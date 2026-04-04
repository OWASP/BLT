/**
 * BLT-SafeCloak — video-lobby.js
 * Lobby pre-join experience with camera preview and one-entry media preferences.
 */

(() => {
  const ROOM_ID_RE = /^[ABCDEFGHJKLMNPQRSTUVWXYZ23456789]{6}$/;

  let previewStream = null;
  let micEnabled = true;
  let camEnabled = true;

  const $ = (id) => document.getElementById(id);

  function normalizeRoomId(value) {
    return (value || "").trim().toUpperCase();
  }

  function isValidRoomId(value) {
    return ROOM_ID_RE.test(value);
  }

  function hasAudioTrack() {
    return Boolean(previewStream && previewStream.getAudioTracks().length > 0);
  }

  function hasVideoTrack() {
    return Boolean(previewStream && previewStream.getVideoTracks().length > 0);
  }

  function stopPreviewStream() {
    if (!previewStream) return;
    previewStream.getTracks().forEach((track) => track.stop());
    previewStream = null;
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
        micEnabled = hasAudioTrack();
        camEnabled = hasVideoTrack();
        updatePreviewUI();
        return;
      } catch {
        // Try next fallback profile.
      }
    }

    micEnabled = false;
    camEnabled = false;
    updatePreviewUI();
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

  function goToRoom(roomId = "") {
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

    goToRoom(roomId);
  }

  document.addEventListener("DOMContentLoaded", async () => {
    const createBtn = $("btn-create-room");
    const joinBtn = $("btn-join-room");
    const roomInput = $("room-id-input");
    const micBtn = $("btn-preview-mic");
    const camBtn = $("btn-preview-cam");

    if (createBtn) {
      createBtn.addEventListener("click", () => {
        goToRoom();
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
          showToast("Room ID loaded from share link", "info");
        }
      }
    }

    if (micBtn) micBtn.addEventListener("click", toggleMicPreview);
    if (camBtn) camBtn.addEventListener("click", toggleCamPreview);

    await initPreviewStream();
  });

  window.addEventListener("beforeunload", stopPreviewStream);
})();
