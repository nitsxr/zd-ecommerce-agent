/**
 * E2E Scenarios panel: list scenarios, Run runs steps and shows pass/fail (reviewable in chat UI).
 */
function renderE2EScenarios(container, onLoadSession) {
  const scenarios = getScenarios();
  let html = '<section class="e2e-scenarios"><h2>E2E Scenarios</h2><p class="muted">Run a scenario to verify behavior; results and conversation are reviewable below.</p><ul class="scenario-list">';
  scenarios.forEach((s) => {
    html += `
      <li class="scenario-item" data-scenario-id="${escapeAttr(s.id)}">
        <div class="scenario-header">
          <strong>${escapeHtml(s.name)}</strong>
          <button type="button" class="run-scenario-btn" data-id="${escapeAttr(s.id)}">Run</button>
        </div>
        <p class="scenario-desc">${escapeHtml(s.description)}</p>
        <div class="scenario-result" id="result-${escapeAttr(s.id)}"></div>
      </li>`;
  });
  html += "</ul></section>";
  container.innerHTML = html;

  container.querySelectorAll(".run-scenario-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.getAttribute("data-id");
      const scenario = getScenarioById(id);
      if (!scenario) return;
      const resultEl = container.querySelector(`#result-${id}`);
      resultEl.textContent = "Running…";
      resultEl.className = "scenario-result running";
      btn.disabled = true;

      const sessionId = `e2e-review-${id}-${Date.now()}`;
      let lastResponse = null;
      try {
        for (const step of scenario.steps) {
          lastResponse = await postChat(sessionId, step.message);
        }
        const expect = scenario.expectLast;
        const agentOk = !expect.agent || lastResponse.agent === expect.agent;
        const containsOk = !expect.responseContains || expect.responseContains.some(
          (sub) => (lastResponse.response || "").toLowerCase().includes(sub.toLowerCase())
        );
        const pass = agentOk && containsOk;
        resultEl.className = "scenario-result " + (pass ? "pass" : "fail");
        resultEl.innerHTML = pass
          ? "✓ Pass. <a href=\"#\" class=\"view-session\" data-session=\"" + escapeAttr(sessionId) + "\">View conversation</a>"
          : "✗ Fail (agent or response mismatch). <a href=\"#\" class=\"view-session\" data-session=\"" + escapeAttr(sessionId) + "\">View conversation</a>";
      } catch (err) {
        resultEl.className = "scenario-result fail";
        resultEl.textContent = "✗ Error: " + (err.message || String(err));
      }
      btn.disabled = false;

      resultEl.querySelectorAll(".view-session").forEach((a) => {
        a.addEventListener("click", (e) => {
          e.preventDefault();
          if (onLoadSession) onLoadSession(a.getAttribute("data-session"));
        });
      });
    });
  });
}

function escapeHtml(s) {
  if (s == null) return "";
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

function escapeAttr(s) {
  if (s == null) return "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}
