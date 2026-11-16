(function () {
  const doc = (window.parent && window.parent.document) ? window.parent.document : document;
  const win = (window.parent && window.parent.window) ? window.parent.window : window;
  const DEF_W = 300, MIN_W = 240, KEY = "nc_panel_width";
  const getMaxW = () => Math.min(480, Math.floor(win.innerWidth * 0.40));

  function applyWidth(panel, w) {
    const clamped = Math.max(MIN_W, Math.min(getMaxW(), w));
    panel.style.setProperty("width", clamped + "px", "important");
    panel.style.setProperty("height", "100%", "important");
    panel.style.setProperty("flex", "1 1 auto", "important");
    const wrapper = panel.closest('[data-testid="stLayoutWrapper"]');
    if (wrapper) {
      wrapper.style.setProperty("width", clamped + "px", "important");
      wrapper.style.setProperty("flex", "0 0 " + clamped + "px", "important");
      wrapper.style.setProperty("height", "100dvh", "important");
      wrapper.style.position = "relative";
    }
    try { win.sessionStorage.setItem(KEY, clamped.toString()); } catch (e) {}
  }

  function updateTooltips() {
    doc.querySelectorAll('[data-testid="stSidebar"] [data-testid="stRadioOption"]').forEach((opt) => {
      const p = opt.querySelector("p");
      if (p) {
        const text = p.textContent.trim();
        if (text && opt.getAttribute("title") !== text) {
          opt.setAttribute("title", text);
        }
      }
    });

    doc.querySelectorAll('[data-testid="stSidebar"] [data-testid="stFileUploader"] section span:not([data-testid="stIconMaterial"]), [data-testid="stSidebar"] [data-testid="stFileUploader"] section small').forEach((el) => {
      if (el.children.length === 0) {
        const text = el.textContent.trim();
        if (text && el.getAttribute("title") !== text) {
          el.setAttribute("title", text);
        }
      }
    });
  }

  function setupResizeHandle() {
    const settingsPanel = doc.querySelector('.st-key-nc-settings');
    if (!settingsPanel) return;

    const wrapper = settingsPanel.closest('[data-testid="stLayoutWrapper"]');
    const handleParent = wrapper || settingsPanel;
    handleParent.style.position = "relative";

    let saved = DEF_W;
    try { saved = parseInt(win.sessionStorage.getItem(KEY) || DEF_W, 10); } catch (e) {}
    applyWidth(settingsPanel, isNaN(saved) ? DEF_W : saved);

    if (handleParent.querySelector(".nc-resize-handle")) return;
    const handle = doc.createElement("div");
    handle.className = "nc-resize-handle";
    handle.title = "Drag to resize, double-click to reset";
    let startX = 0, startW = 0;

    const onMove = (e) => applyWidth(settingsPanel, startW + (startX - e.clientX));
    const onUp = () => {
      handle.classList.remove("dragging");
      doc.removeEventListener("mousemove", onMove);
      doc.removeEventListener("mouseup", onUp);
    };

    handle.addEventListener("mousedown", (e) => {
      startX = e.clientX;
      startW = (wrapper || settingsPanel).getBoundingClientRect().width;
      handle.classList.add("dragging");
      doc.addEventListener("mousemove", onMove);
      doc.addEventListener("mouseup", onUp);
      e.preventDefault();
    });

    handle.addEventListener("dblclick", () => applyWidth(settingsPanel, DEF_W));
    handleParent.prepend(handle);
  }

  function runAll() {
    updateTooltips();
    setupResizeHandle();
  }

  runAll();
  new MutationObserver(runAll).observe(doc.body, { childList: true, subtree: true });
})();
