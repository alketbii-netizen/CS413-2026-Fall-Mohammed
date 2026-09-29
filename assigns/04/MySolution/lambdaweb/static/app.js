/*
 * View-side script. This file ONLY forwards user interactions to the
 * Controller's HTTP endpoints and renders whatever JSON state comes
 * back. It contains no LAMBDA-specific logic (no parsing, no notion of
 * "free variable" or "d0exp") — that all lives behind the backend
 * adapter on the server. Rendering always uses .textContent (never
 * .innerHTML) for anything that came from user/source/output text, so
 * HTML-like content is shown literally rather than interpreted as
 * markup (F9).
 */
(() => {
  "use strict";

  const ACTION_LABELS = {
    lint: "Lint",
    interpret: "Interpret",
    typecheck: "Type-check",
    compile: "Compile",
    execute: "Execute",
  };
  const ACTION_ORDER = ["lint", "interpret", "typecheck", "compile", "execute"];

  const el = {
    fileInput: document.getElementById("file-input"),
    btnManual: document.getElementById("btn-manual"),
    btnFactorial: document.getElementById("btn-factorial"),
    btnFibonacci: document.getElementById("btn-fibonacci"),
    sourceName: document.getElementById("source-name"),
    sourceRevision: document.getElementById("source-revision"),
    editor: document.getElementById("editor"),
    btnApply: document.getElementById("btn-apply"),
    btnDiscard: document.getElementById("btn-discard"),
    statusText: document.getElementById("status-text"),
    resultsBody: document.getElementById("results-body"),
    actionButtons: Array.from(document.querySelectorAll(".action-btn")),
  };

  let editDebounce = null;
  let requestInFlight = false;

  function setAllControlsDisabled(disabled) {
    el.fileInput.disabled = disabled;
    el.btnManual.disabled = disabled;
    el.btnFactorial.disabled = disabled;
    el.btnFibonacci.disabled = disabled;
    el.btnApply.disabled = disabled;
    el.btnDiscard.disabled = disabled;
    el.actionButtons.forEach((b) => (b.disabled = disabled));
  }

  function setStatus(text) {
    el.statusText.textContent = text;
  }

  async function callApi(url, options, busyLabel) {
    requestInFlight = true;
    setAllControlsDisabled(true);
    if (busyLabel) setStatus(`Busy: ${busyLabel}...`);
    try {
      const resp = await fetch(url, options);
      const state = await resp.json();
      render(state);
      return state;
    } catch (netErr) {
      setStatus(`Environment error: could not reach the server (${netErr}). Your edits are preserved; you can retry.`);
      throw netErr;
    } finally {
      requestInFlight = false;
      applyControlAvailability(lastState);
    }
  }

  let lastState = null;

  function applyControlAvailability(state) {
    if (!state) return;
    const editable = !requestInFlight;
    el.fileInput.disabled = !editable;
    el.btnManual.disabled = !editable;
    el.btnFactorial.disabled = !editable;
    el.btnFibonacci.disabled = !editable;
    el.btnApply.disabled = !editable || !state.has_pending_edit;
    el.btnDiscard.disabled = !editable || !state.has_pending_edit;
    const actionable = editable && state.has_applied_source && !state.has_pending_edit;
    el.actionButtons.forEach((b) => {
      if (b.dataset.action === "execute") {
        b.disabled = !actionable || !state.execute_available;
      } else {
        b.disabled = !actionable;
      }
    });
  }

  function render(state) {
    lastState = state;
    el.sourceName.textContent = state.source_name;
    el.sourceRevision.textContent = String(state.revision);

    const shownText = state.has_pending_edit ? state.pending_source : state.applied_source;
    if (document.activeElement !== el.editor) {
      el.editor.value = shownText;
    }

    if (state.error) {
      setStatus(`${state.error.type}: ${state.error.message}`);
    } else if (!requestInFlight) {
      setStatus("Idle.");
    }

    renderResults(state.results);
    applyControlAvailability(state);
  }

  function renderResults(results) {
    el.resultsBody.textContent = "";
    for (const action of ACTION_ORDER) {
      const row = document.createElement("tr");

      const tdAction = document.createElement("td");
      tdAction.textContent = ACTION_LABELS[action];
      row.appendChild(tdAction);

      const r = results[action];
      const tdRev = document.createElement("td");
      tdRev.textContent = r ? String(r.revision) : "—";
      row.appendChild(tdRev);

      const tdStatus = document.createElement("td");
      tdStatus.textContent = r ? r.status : "(not run yet)";
      row.appendChild(tdStatus);

      const tdMsg = document.createElement("td");
      tdMsg.textContent = r ? r.message : "";
      tdMsg.style.whiteSpace = "pre-wrap";
      row.appendChild(tdMsg);

      el.resultsBody.appendChild(row);
    }
  }

  // ---- event wiring --------------------------------------------------

  el.fileInput.addEventListener("change", () => {
    const file = el.fileInput.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    callApi("/api/load/upload", { method: "POST", body: formData }, "loading file").catch(() => {});
    el.fileInput.value = "";
  });

  el.btnManual.addEventListener("click", () => {
    callApi("/api/load/manual", { method: "POST" }, "opening manual input").then(() => el.editor.focus()).catch(() => {});
  });

  el.btnFactorial.addEventListener("click", () => {
    callApi(
      "/api/load/example",
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: "factorial" }) },
      "loading factorial example"
    ).catch(() => {});
  });

  el.btnFibonacci.addEventListener("click", () => {
    callApi(
      "/api/load/example",
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: "fibonacci" }) },
      "loading fibonacci example"
    ).catch(() => {});
  });

  el.editor.addEventListener("input", () => {
    clearTimeout(editDebounce);
    const text = el.editor.value;
    editDebounce = setTimeout(() => {
      callApi(
        "/api/edit",
        { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) },
        null
      ).catch(() => {});
    }, 250);
  });

  el.btnApply.addEventListener("click", () => {
    callApi("/api/apply", { method: "POST" }, "applying changes").catch(() => {});
  });

  el.btnDiscard.addEventListener("click", () => {
    callApi("/api/discard", { method: "POST" }, "discarding changes").catch(() => {});
  });

  el.actionButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const action = btn.dataset.action;
      callApi(`/api/action/${action}`, { method: "POST" }, `running ${ACTION_LABELS[action]}`).catch(() => {});
    });
  });

  // ---- bootstrap -------------------------------------------------------

  const initialStateEl = document.getElementById("initial-state");
  const initialState = JSON.parse(initialStateEl.textContent);
  render(initialState);
})();
