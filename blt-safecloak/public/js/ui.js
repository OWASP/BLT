/**
 * BLT-SafeCloak — ui.js
 * Shared UI utilities: toasts, navbar toggle, modal helpers
 */

/* ── Toast notifications ── */
function showToast(message, type = "info", duration = 3500) {
  const container =
    document.getElementById("toast-container") ||
    (() => {
      const el = document.createElement("div");
      el.id = "toast-container";
      document.body.appendChild(el);
      return el;
    })();

  const icons = { success: "✅", error: "❌", info: "ℹ️", warning: "⚠️" };
  const toast = document.createElement("div");
  toast.className = `toast toast-${type === "error" ? "error" : type === "success" ? "success" : "info"}`;
  const iconSpan = document.createElement("span");
  iconSpan.textContent = icons[type] || icons.info;
  const messageSpan = document.createElement("span");
  messageSpan.textContent = String(message);
  toast.appendChild(iconSpan);
  toast.appendChild(messageSpan);
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transition = "opacity 0.3s";
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

/* ── Navbar toggle ── */
document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.getElementById("navbar-toggle");
  const nav = document.getElementById("navbar-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", () => {
      const isOpen = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
    });
    // Close on outside click
    document.addEventListener("click", (e) => {
      if (!toggle.contains(e.target) && !nav.contains(e.target)) {
        nav.classList.remove("open");
        toggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  // Mark active nav link
  const currentPage = window.location.pathname.split("/").pop() || "index.html";
  const links = document.querySelectorAll(".navbar-nav a");
  links.forEach((link) => {
    const href = link.getAttribute("href");
    if (link.href === window.location.href || href === currentPage) {
      link.classList.add("active");
    }
  });
});

/* ── Modal helpers ── */
function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.style.display = "flex";
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.style.display = "none";
}

// Close modal on overlay click
document.addEventListener("click", (e) => {
  if (e.target.classList.contains("modal-overlay")) {
    e.target.style.display = "none";
  }
});

/* ── Copy to clipboard ── */
async function copyToClipboard(text, label = "Copied") {
  try {
    let copied = false;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      try {
        await navigator.clipboard.writeText(text);
        copied = true;
      } catch {
        // Fall through to legacy copy path.
      }
    }

    if (!copied) {
      const fallback = document.createElement("textarea");
      fallback.value = text;
      fallback.setAttribute("readonly", "true");
      fallback.style.position = "fixed";
      fallback.style.left = "-9999px";
      document.body.appendChild(fallback);
      try {
        fallback.select();
        copied = document.execCommand("copy");
      } finally {
        document.body.removeChild(fallback);
      }
      if (!copied) {
        throw new Error("Clipboard copy fallback failed");
      }
    }
    showToast(`${label} copied to clipboard`, "success");
  } catch {
    showToast("Copy failed — please copy manually", "error");
  }
}

/* ── Format date/time ── */
function formatDateTime(ts) {
  return new Date(ts).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatDateShort(ts) {
  const d = new Date(ts);
  const now = new Date();
  const diff = now - d;
  if (diff < 60000) return "just now";
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return d.toLocaleDateString();
}

/* ── Sidebar Resize Handler ── */
class SidebarResize {
  constructor() {
    this.splitter = document.getElementById("sidebar-splitter");
    this.sidebar = document.getElementById("sidebar-content");

    // Configuration
    this.minWidth = 200; // Minimum sidebar width (px)
    this.maxWidth = 500; // Maximum sidebar width (px)
    this.isDragging = false;
    this.startX = 0;
    this.startWidth = 0;

    if (this.splitter && this.sidebar) {
      this.init();
    }
  }

  init() {
    // Set initial ARIA attributes
    this.splitter.setAttribute("aria-valuemin", this.minWidth);
    this.splitter.setAttribute("aria-valuemax", this.maxWidth);

    // Mouse events
    this.splitter.addEventListener("mousedown", (e) => this.handleMouseDown(e));
    document.addEventListener("mousemove", (e) => this.handleMouseMove(e));
    document.addEventListener("mouseup", () => this.handleMouseUp());

    // Touch events for mobile - non-passive to allow preventDefault
    this.splitter.addEventListener("touchstart", (e) => this.handleTouchStart(e), {
      passive: false,
    });
    document.addEventListener("touchmove", (e) => this.handleTouchMove(e), {
      passive: false,
    });
    document.addEventListener("touchend", () => this.handleMouseUp());

    // Keyboard support (arrow keys)
    this.splitter.addEventListener("keydown", (e) => this.handleKeyDown(e));

    // Restore saved width on load
    this.restoreWidth();
  }

  handleMouseDown(e) {
    this.startDrag(e.clientX);
  }

  handleTouchStart(e) {
    if (e.touches.length === 1) {
      this.startDrag(e.touches[0].clientX);
    }
  }

  startDrag(clientX) {
    this.isDragging = true;
    this.startX = clientX;
    this.startWidth = this.sidebar.offsetWidth;

    this.splitter.classList.add("active");
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }

  handleMouseMove(e) {
    if (!this.isDragging) return;
    this.resizeSidebar(e.clientX);
  }

  handleTouchMove(e) {
    if (!this.isDragging || e.touches.length !== 1) return;
    // Prevent scrolling during drag
    e.preventDefault();
    this.resizeSidebar(e.touches[0].clientX);
  }

  handleMouseUp() {
    if (!this.isDragging) return;

    this.isDragging = false;
    this.splitter.classList.remove("active");
    // Clear inline styles to restore stylesheet values
    document.body.style.cursor = "";
    document.body.style.userSelect = "";

    // Final save (applyWidth already saves, but ensure consistency)
    this.saveWidth();
  }

  handleKeyDown(e) {
    const keys = ["ArrowLeft", "ArrowRight", "Home", "End", "PageUp", "PageDown"];
    if (!keys.includes(e.key)) return;

    e.preventDefault();
    const step = 20;
    let newWidth = this.sidebar.offsetWidth;

    switch (e.key) {
      case "ArrowLeft":
        newWidth -= step;
        break;
      case "ArrowRight":
        newWidth += step;
        break;
      case "Home":
        newWidth = this.minWidth;
        break;
      case "End":
        newWidth = this.maxWidth;
        break;
      case "PageUp":
        newWidth -= step * 4;
        break;
      case "PageDown":
        newWidth += step * 4;
        break;
    }

    this.applyWidth(newWidth);
  }

  resizeSidebar(clientX) {
    // Calculate the change in position
    const delta = clientX - this.startX;
    const newWidth = this.startWidth - delta; // Negative because splitter is on the left of sidebar
    this.applyWidth(newWidth);
  }

  applyWidth(newWidth) {
    // Apply constraints
    const constrainedWidth = Math.max(this.minWidth, Math.min(this.maxWidth, newWidth));

    // Update sidebar width
    this.sidebar.style.width = `${constrainedWidth}px`;

    // Update ARIA for assistive tech
    this.splitter.setAttribute("aria-valuenow", constrainedWidth);

    // Persist
    this.saveWidth();
  }

  saveWidth() {
    try {
      localStorage.setItem("blt-sidebar-width", this.sidebar.offsetWidth);
    } catch (error) {
      console.warn("[SidebarResize] Failed to save width:", error);
    }
  }

  restoreWidth() {
    try {
      const savedWidth = localStorage.getItem("blt-sidebar-width");
      if (savedWidth) {
        const width = parseInt(savedWidth, 10);
        this.applyWidth(width);
      } else {
        // Set initial valuenow if no saved width
        this.applyWidth(this.sidebar.offsetWidth);
      }
    } catch (error) {
      console.warn("[SidebarResize] Failed to restore width:", error);
    }
  }
}

// Initialize when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    new SidebarResize();
  });
} else {
  new SidebarResize();
}
