/**
 * BLT-SafeCloak — video.js
 * Secure video chat using WebRTC (via PeerJS) with consent recording
 */

const VideoChat = (() => {
  let peer = null;
  let localStream = null;
  let currentCall = null;
  let audioContext = null;
  let analyser = null;
  let voiceAnimFrame = null;
  let micMuted = false;
  let camOff = false;
  let consentGiven = false;
  let screenSharing = false;

  const state = {
    peerId: null,
    connected: false,
    sessionId: null,
    sessionKey: null,
  };

  /* ── DOM helpers ── */
  const $ = id => document.getElementById(id);

  function updateStatus(text, type = 'muted') {
    const el = $('connection-status');
    if (!el) return;
    el.textContent = text;
    el.className = `text-${type}`;
  }

  function setDotStatus(status) {
    const dot = $('status-dot');
    if (dot) dot.className = `status-dot ${status}`;
  }

  /* ── Media ── */
  async function startLocalMedia() {
    try {
      localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      const localVideo = $('local-video');
      if (localVideo) { localVideo.srcObject = localStream; localVideo.muted = true; }
      startVoiceMeter(localStream);
      return true;
    } catch (err) {
      showToast('Camera/mic access denied: ' + err.message, 'error');
      return false;
    }
  }

  function startVoiceMeter(stream) {
    try {
      audioContext = new (window.AudioContext || window.webkitAudioContext)();
      analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      const src = audioContext.createMediaStreamSource(stream);
      src.connect(analyser);
      animateVoiceMeter();
    } catch { /* audio context not available */ }
  }

  function animateVoiceMeter() {
    const bars = document.querySelectorAll('.voice-bar');
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
    if (typeof Peer === 'undefined') {
      showToast('PeerJS not loaded', 'error');
      return;
    }
    state.peerId = Crypto.randomId(6);
    state.sessionKey = await Crypto.generateKey();
    state.sessionId = state.peerId;

    peer = new Peer(state.peerId, {
      host: '0.peerjs.com',
      port: 443,
      secure: true,
      path: '/',
      debug: 0,
    });

    peer.on('open', id => {
      $('my-peer-id') && ($('my-peer-id').textContent = id);
      updateStatus('Ready — share your Room ID', 'secondary');
      setDotStatus('online');
      showToast('Connected to signaling server', 'success');
    });

    peer.on('call', async incomingCall => {
      if (!consentGiven) {
        const ok = await askConsent(incomingCall.peer);
        if (!ok) { incomingCall.close(); return; }
      }
      currentCall = incomingCall;
      incomingCall.answer(localStream);
      handleCallStream(incomingCall);
    });

    peer.on('error', err => {
      updateStatus('Error: ' + err.message, 'danger');
      setDotStatus('offline');
      showToast('Connection error: ' + err.type, 'error');
    });

    peer.on('disconnected', () => {
      updateStatus('Disconnected', 'warning');
      setDotStatus('offline');
    });
  }

  function handleCallStream(call) {
    call.on('stream', remoteStream => {
      const remoteVideo = $('remote-video');
      if (remoteVideo) { remoteVideo.srcObject = remoteStream; }
      state.connected = true;
      updateStatus('🔒 Encrypted call active', 'success');
      setDotStatus('online');
      $('call-controls') && ($('call-controls').classList.remove('hidden'));
    });

    call.on('close', () => {
      state.connected = false;
      updateStatus('Call ended', 'muted');
      setDotStatus('offline');
      const remoteVideo = $('remote-video');
      if (remoteVideo) remoteVideo.srcObject = null;
    });

    call.on('error', err => {
      showToast('Call error: ' + err.message, 'error');
    });
  }

  async function callPeer(remotePeerId) {
    if (!peer) { showToast('Not connected to server', 'error'); return; }
    if (!localStream) { showToast('No local stream — allow camera/mic first', 'error'); return; }
    if (!remotePeerId) { showToast('Enter a Room ID to call', 'warning'); return; }

    if (!consentGiven) {
      const ok = await askConsent('the remote participant');
      if (!ok) return;
    }

    updateStatus('Calling…', 'warning');
    setDotStatus('connecting');
    const call = peer.call(remotePeerId, localStream);
    currentCall = call;
    handleCallStream(call);
  }

  /* ── Controls ── */
  function toggleMic() {
    if (!localStream) return;
    micMuted = !micMuted;
    localStream.getAudioTracks().forEach(t => (t.enabled = !micMuted));
    const btn = $('btn-mic');
    if (btn) {
      btn.textContent = micMuted ? '🔇' : '🎙️';
      btn.title = micMuted ? 'Unmute mic' : 'Mute mic';
      btn.classList.toggle('active', micMuted);
    }
    showToast(micMuted ? 'Microphone muted' : 'Microphone unmuted', 'info');
  }

  function toggleCamera() {
    if (!localStream) return;
    camOff = !camOff;
    localStream.getVideoTracks().forEach(t => (t.enabled = !camOff));
    const btn = $('btn-cam');
    if (btn) {
      btn.textContent = camOff ? '📷' : '🎥';
      btn.title = camOff ? 'Enable camera' : 'Disable camera';
      btn.classList.toggle('active', camOff);
    }
    showToast(camOff ? 'Camera disabled' : 'Camera enabled', 'info');
  }

  function endCall() {
    if (currentCall) { currentCall.close(); currentCall = null; }
    state.connected = false;
    updateStatus('Call ended', 'muted');
    setDotStatus('offline');
    const remoteVideo = $('remote-video');
    if (remoteVideo) remoteVideo.srcObject = null;
    showToast('Call ended', 'info');
    // Record consent end
    ConsentManager && ConsentManager.record({
      type: 'recorded',
      name: 'Call session ended',
      details: `Session ID: ${state.sessionId} — ended at ${new Date().toISOString()}`
    });
  }

  function hangup() {
    endCall();
    if (peer) { peer.disconnect(); peer.destroy(); peer = null; }
    if (localStream) { localStream.getTracks().forEach(t => t.stop()); localStream = null; }
    if (voiceAnimFrame) cancelAnimationFrame(voiceAnimFrame);
    if (audioContext) audioContext.close();
    setDotStatus('offline');
    updateStatus('Disconnected', 'muted');
    showToast('Session ended and media released', 'success');
  }

  /* ── Noise suppression hint ── */
  async function toggleNoiseSuppression() {
    if (!localStream) return;
    const audioTrack = localStream.getAudioTracks()[0];
    if (!audioTrack) return;
    try {
      const settings = audioTrack.getSettings();
      const current = settings.noiseSuppression;
      await audioTrack.applyConstraints({ noiseSuppression: !current, echoCancellation: true, autoGainControl: true });
      showToast(`Noise suppression ${!current ? 'enabled' : 'disabled'}`, 'success');
      const btn = $('btn-noise');
      if (btn) btn.classList.toggle('active', !current);
    } catch {
      showToast('Noise suppression not supported on this device', 'warning');
    }
  }

  /* ── Consent gate ── */
  function askConsent(callerName) {
    return new Promise(resolve => {
      const overlay = document.createElement('div');
      overlay.className = 'modal-overlay';
      overlay.style.display = 'flex';
      overlay.innerHTML = `
        <div class="modal" style="max-width:440px">
          <h3>🔒 Recording Consent Required</h3>
          <p>This call may be recorded for AI notes and security purposes. Do you consent to participate in this secure call with <strong style="color:#fff">${callerName}</strong>?</p>
          <div class="alert alert-info" style="margin-bottom:1rem">
            <span>ℹ️</span>
            <span>Consent is cryptographically timestamped and stored locally. You can withdraw at any time.</span>
          </div>
          <div style="display:flex;gap:0.75rem;justify-content:flex-end">
            <button class="btn btn-secondary" id="consent-deny">Decline</button>
            <button class="btn btn-primary" id="consent-allow">I Consent</button>
          </div>
        </div>
      `;
      document.body.appendChild(overlay);

      overlay.querySelector('#consent-allow').onclick = () => {
        consentGiven = true;
        overlay.remove();
        ConsentManager && ConsentManager.record({
          type: 'given',
          name: `Consent given for call with ${callerName}`,
          details: `Session ID: ${state.sessionId}`
        });
        resolve(true);
      };
      overlay.querySelector('#consent-deny').onclick = () => {
        overlay.remove();
        resolve(false);
      };
    });
  }

  /* ── Screen share ── */
  async function shareScreen() {
    try {
      const screenStream = await navigator.mediaDevices.getDisplayMedia({ video: true });
      const screenTrack = screenStream.getVideoTracks()[0];
      if (currentCall && currentCall.peerConnection) {
        const sender = currentCall.peerConnection.getSenders().find(s => s.track && s.track.kind === 'video');
        if (sender) await sender.replaceTrack(screenTrack);
      }
      const localVideo = $('local-video');
      if (localVideo) localVideo.srcObject = screenStream;
      showToast('Screen sharing started', 'success');
      screenSharing = true;
      $('btn-screen') && $('btn-screen').classList.add('active');
      screenTrack.onended = () => {
        if (screenSharing) stopScreenShare();
      };
    } catch (err) {
      if (err.name !== 'NotAllowedError') showToast('Screen share error: ' + err.message, 'error');
    }
  }

  function stopScreenShare() {
    if (!localStream || !currentCall) return;
    const videoTrack = localStream.getVideoTracks()[0];
    if (!videoTrack) return;
    const sender = currentCall.peerConnection && currentCall.peerConnection.getSenders().find(s => s.track && s.track.kind === 'video');
    if (sender) sender.replaceTrack(videoTrack);
    const localVideo = $('local-video');
    if (localVideo) { localVideo.srcObject = localStream; }
    $('btn-screen') && $('btn-screen').classList.remove('active');
    screenSharing = false;
    showToast('Screen sharing stopped', 'info');
  }

  /* ── Init ── */
  async function init() {
    const ok = await startLocalMedia();
    if (ok) await initPeer();
  }

  return { init, callPeer, toggleMic, toggleCamera, endCall, hangup, toggleNoiseSuppression, shareScreen, stopScreenShare, state };
})();
