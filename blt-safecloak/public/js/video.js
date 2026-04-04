/**
 * BLT-SafeCloak — video.js
 * Secure video chat using WebRTC (via PeerJS) with consent recording
 */

const VideoChat = (() => {
  let peer = null;
  let localStream = null;
  const activeCalls = new Map(); // peerId -> MediaConnection
  const activeDataConns = new Map(); // peerId -> DataConnection
  let audioContext = null;
  let analyser = null;
  let voiceAnimFrame = null;
  let micMuted = false;
  let camOff = false;
  let consentGiven = false;
  let screenSharing = false;
  let initialMediaPreferences = { mic: true, cam: true };

  const state = {
    peerId: null,
    connected: false,
    sessionId: null,
    sessionKey: null,
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
    startVoiceMeter(stream);
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
  }

  async function startLocalMedia() {
    // 1. Try full video + audio
    try {
      localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
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
      // For any other unexpected error fall through to the generic handler at the end.
      if (err.name !== "NotFoundError" && err.name !== "DevicesNotFoundError") {
        showToast("Could not access camera/microphone: " + err.message, "error");
        return false;
      }
    }

    // 2. No combined device found — try audio-only
    try {
      localStream = await navigator.mediaDevices.getUserMedia({ video: false, audio: true });
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
      if (audioErr.name !== "NotFoundError" && audioErr.name !== "DevicesNotFoundError") {
        showToast("Could not access microphone: " + audioErr.message, "error");
        return false;
      }
    }

    // 3. No microphone either — try video-only
    try {
      localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
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
      if (videoErr.name === "NotReadableError" || videoErr.name === "TrackStartError") {
        showToast(
          "Camera is already in use by another application. Please close it and reload.",
          "error"
        );
        return false;
      }
      if (videoErr.name !== "NotFoundError" && videoErr.name !== "DevicesNotFoundError") {
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
  }

  function startVoiceMeter(stream) {
    try {
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
    if (!bars.length || !analyser) return;
    const data = new Uint8Array(analyser.frequencyBinCount);
    function frame() {
      analyser.getByteFrequencyData(data);
      const slice = Math.floor(data.length / bars.length);
      bars.forEach((bar, i) => {
        const avg = data.slice(i * slice, (i + 1) * slice).reduce((a, b) => a + b, 0) / slice;
        bar.style.height = `${Math.max(4, (avg / 255) * 24)}px`;
      });
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

    peer = new Peer(state.peerId, Object.assign({
      host: "0.peerjs.com",
      port: 443,
      secure: true,
      path: "/",
      debug: 0,
    }, window.__PEERJS_CONFIG__ || {}));

    peer.on("open", (id) => {
      $("my-peer-id") && ($("my-peer-id").textContent = id);
      updateStatus("Ready — share your Room ID", "secondary");
      setDotStatus("online");
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
      incomingCall.answer(localStream);
      handleCallStream(incomingCall);
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
      item.className = "flex items-center justify-between py-1 text-sm";

      const nameSpan = document.createElement("span");
      nameSpan.className = "flex items-center gap-2";

      const dot = document.createElement("span");
      dot.className = "status-dot online";
      dot.setAttribute("aria-hidden", "true");

      const idLabel = document.createElement("span");
      idLabel.className = "font-mono font-bold truncate max-w-[120px]";
      idLabel.title = peerId;
      idLabel.textContent = peerId;

      nameSpan.appendChild(dot);
      nameSpan.appendChild(idLabel);

      const disconnectBtn = document.createElement("button");
      disconnectBtn.className = "control-btn";
      disconnectBtn.style.cssText = "width:32px;height:32px;font-size:0.75rem";
      disconnectBtn.title = `Disconnect ${peerId}`;
      disconnectBtn.setAttribute("aria-label", `Disconnect ${peerId}`);
      disconnectBtn.innerHTML = '<i class="fa-solid fa-phone-slash" aria-hidden="true"></i>';
      disconnectBtn.addEventListener("click", () => VideoChat.disconnectPeer(peerId));

      item.appendChild(nameSpan);
      item.appendChild(disconnectBtn);
      listEl.appendChild(item);
    });
  }

  function handleCallStream(call) {
    const remotePeerId = call.peer;

    const videoWrapper = document.createElement("div");
    videoWrapper.className = "video-wrapper rounded-xl bg-gray-900";
    videoWrapper.id = `wrapper-${remotePeerId}`;

    const videoEl = document.createElement("video");
    videoEl.autoplay = true;
    videoEl.playsInline = true;
    videoEl.setAttribute("aria-label", `Participant ${remotePeerId} video`);

    const label = document.createElement("div");
    label.className = "video-label";
    label.id = `label-${remotePeerId}`;

    const labelDot = document.createElement("span");
    labelDot.className = "status-dot connecting";
    labelDot.setAttribute("aria-hidden", "true");
    labelDot.id = `dot-${remotePeerId}`;

    const labelText = document.createElement("span");
    labelText.className = "font-mono font-bold";
    labelText.title = remotePeerId;
    labelText.textContent = remotePeerId;

    label.appendChild(labelDot);
    label.appendChild(labelText);

    videoWrapper.appendChild(videoEl);
    videoWrapper.appendChild(label);

    const videoGrid = $("video-grid");
    if (videoGrid) videoGrid.appendChild(videoWrapper);

    call.on("stream", (remoteStream) => {
      videoEl.srcObject = remoteStream;
      const dot = $(`dot-${remotePeerId}`);
      if (dot) dot.className = "status-dot online";
      state.connected = true;
      const count = activeCalls.size;
      updateStatus(
        `🔒 Encrypted call active (${count} participant${count !== 1 ? "s" : ""})`,
        "success"
      );
      setDotStatus("online");
      updateParticipantsList();
    });

    call.on("close", () => {
      activeCalls.delete(remotePeerId);
      const wrapper = $(`wrapper-${remotePeerId}`);
      if (wrapper) wrapper.remove();
      if (activeCalls.size === 0) {
        state.connected = false;
        updateStatus("Call ended", "muted");
        setDotStatus("offline");
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
      showToast("Call error: " + err.message, "error");
    });
  }

  /* ── Full-mesh helpers ── */
  function setupDataConn(conn) {
    activeDataConns.set(conn.peer, conn);
    conn.on("data", (data) => {
      if (data && data.type === "peers" && Array.isArray(data.ids)) {
        data.ids.forEach((id) => {
          if (id !== state.peerId && !activeCalls.has(id)) {
            callPeer(id);
          }
        });
      }
    });
    conn.on("close", () => activeDataConns.delete(conn.peer));
    conn.on("error", () => activeDataConns.delete(conn.peer));
  }

  function sendPeerListTo(remotePeerId) {
    const peerList = Array.from(activeCalls.keys()).filter((id) => id !== remotePeerId);
    if (peerList.length === 0) return;
    if (activeDataConns.has(remotePeerId)) {
      const existing = activeDataConns.get(remotePeerId);
      if (existing.open) {
        existing.send({ type: "peers", ids: peerList });
        return;
      }
    }
    const conn = peer.connect(remotePeerId);
    setupDataConn(conn);
    conn.on("open", () => conn.send({ type: "peers", ids: peerList }));
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
      showToast("No local stream — allow camera/mic first", "error");
      return;
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
      showToast("Room ID must be exactly 6 characters using only uppercase letters (A-Z except I,O) and digits (2-9)", "error");
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
    const call = peer.call(remotePeerId, localStream);
    activeCalls.set(remotePeerId, call);
    updateParticipantsList();
    handleCallStream(call);
  }

  /* ── Controls ── */
  function toggleMic() {
    if (!localStream) return;
    if (localStream.getAudioTracks().length === 0) {
      showToast("No microphone available", "warning");
      return;
    }

    micMuted = !micMuted;
    localStream.getAudioTracks().forEach((track) => (track.enabled = !micMuted));
    syncControlButtons();
    showToast(micMuted ? "Microphone muted" : "Microphone unmuted", "info");
  }

  function toggleCamera() {
    if (!localStream) return;
    if (localStream.getVideoTracks().length === 0) {
      showToast("No camera available", "warning");
      return;
    }

    camOff = !camOff;
    localStream.getVideoTracks().forEach((track) => (track.enabled = !camOff));
    syncControlButtons();
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
    state.connected = false;
    updateStatus("Call ended", "muted");
    setDotStatus("offline");
    const videoGrid = $("video-grid");
    if (videoGrid) {
      videoGrid.querySelectorAll(".video-wrapper:not(:first-child)").forEach((w) => w.remove());
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
    if (voiceAnimFrame) cancelAnimationFrame(voiceAnimFrame);
    if (audioContext) audioContext.close();
    setDotStatus("offline");
    updateStatus("Disconnected", "muted");
    showToast("Session ended and media released", "success");
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
      screenTrack.onended = () => {
        if (screenSharing) stopScreenShare();
      };
    } catch (err) {
      if (err.name !== "NotAllowedError") showToast("Screen share error: " + err.message, "error");
    }
  }

  function stopScreenShare() {
    if (!localStream || activeCalls.size === 0) return;
    const videoTrack = localStream.getVideoTracks()[0];
    if (!videoTrack) return;
    for (const call of activeCalls.values()) {
      const sender =
        call.peerConnection &&
        call.peerConnection.getSenders().find((s) => s.track && s.track.kind === "video");
      if (sender) sender.replaceTrack(videoTrack);
    }
    const localVideo = $("local-video");
    if (localVideo) {
      localVideo.srcObject = localStream;
    }
    $("btn-screen") && $("btn-screen").classList.remove("active");
    screenSharing = false;
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
      const query = params.toString();
      const cleanUrl = window.location.pathname + (query ? "?" + query : "");
      window.history.replaceState({}, "", cleanUrl);
    }
  }

  /* ── Init ── */
  async function init() {
    readInitialMediaPreferencesFromUrl();
    const ok = await startLocalMedia();
    if (ok) await initPeer();
  }

  return {
    init,
    callPeer,
    disconnectPeer,
    toggleMic,
    toggleCamera,
    endCall,
    hangup,
    toggleNoiseSuppression,
    shareScreen,
    stopScreenShare,
    copyRoomLink,
    state,
  };
})();
