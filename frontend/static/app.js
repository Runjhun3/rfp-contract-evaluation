// Small progressive enhancements. Every page works without this file.
(function () {
  // Live progress on the run page: poll the JSON endpoint every 5 s.
  const board = document.querySelector("[data-run-id]");
  if (board) {
    const url = "/api/v1/runs/" + board.dataset.runId + "/progress";
    const tick = function () {
      const ctrl = new AbortController();
      const timer = setTimeout(function () { ctrl.abort(); }, 10000);
      fetch(url, { signal: ctrl.signal, credentials: "same-origin" })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (body) {
          if (!body || !body.data) { return; }
          body.data.rows.forEach(function (row) {
            const bar = document.getElementById("bar-" + row.submission_id);
            const label = document.getElementById("label-" + row.submission_id);
            if (bar) { bar.value = row.percent; }
            if (label) { label.textContent = row.label; }
          });
          if (body.data.status === "DONE" || body.data.status === "FAILED") {
            window.location.reload();
          }
        })
        .catch(function () { /* next tick retries */ })
        .finally(function () { clearTimeout(timer); });
    };
    if (board.dataset.status !== "DONE" && board.dataset.status !== "FAILED") {
      setInterval(tick, 5000);
    }
  }

  // Pages waiting on the worker (e.g. criteria extraction) refresh themselves.
  const wait = document.querySelector("[data-refresh]");
  if (wait) {
    setTimeout(function () { window.location.reload(); }, Number(wait.dataset.refresh) * 1000);
  }

  // Override marks box only when "Override" is chosen.
  const marks = document.getElementById("override-marks");
  document.querySelectorAll("input[name=action]").forEach(function (radio) {
    radio.addEventListener("change", function () {
      if (marks) { marks.disabled = radio.value !== "OVERRIDE" || !radio.checked; }
    });
  });
})();
