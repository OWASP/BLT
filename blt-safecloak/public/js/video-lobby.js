/**
 * BLT-SafeCloak — video-lobby.js
 * Lobby-only room creation/join flow. No media is initialized on this page.
 */

(() => {
  const ROOM_ID_RE = /^[ABCDEFGHJKLMNPQRSTUVWXYZ23456789]{6}$/;

  function normalizeRoomId(value) {
    return (value || "").trim().toUpperCase();
  }

  function isValidRoomId(value) {
    return ROOM_ID_RE.test(value);
  }

  function goToRoom(roomId = "") {
    const target = new URL(`${window.location.origin}/video-room`);
    if (roomId) {
      target.searchParams.set("room", roomId);
    }
    window.location.href = target.toString();
  }

  document.addEventListener("DOMContentLoaded", () => {
    const createBtn = document.getElementById("btn-create-room");
    const joinBtn = document.getElementById("btn-join-room");
    const roomInput = document.getElementById("room-id-input");

    if (createBtn) {
      createBtn.addEventListener("click", () => {
        goToRoom();
      });
    }

    function joinRoom() {
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
  });
})();
