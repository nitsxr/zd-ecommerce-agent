/**
 * Test runner: list tests, run all/selected, show results with link to trace.
 */
(function () {
  const listEl = document.getElementById('tests-list');
  const resultsEl = document.getElementById('tests-results');
  const btnRunAll = document.getElementById('btn-run-all');
  const btnRunSelected = document.getElementById('btn-run-selected');
  let tests = [];
  let running = false;

  function renderList() {
    if (!listEl) return;
    listEl.innerHTML = '';
    if (tests.length === 0) {
      listEl.innerHTML = '<p class="tests-empty">No tests</p>';
      return;
    }
    tests.forEach(function (t) {
      const label = document.createElement('label');
      label.className = 'test-row';
      const cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.className = 'test-checkbox';
      cb.dataset.testId = t.id;
      const name = document.createElement('span');
      name.className = 'test-name';
      name.textContent = t.name || t.id;
      label.appendChild(cb);
      label.appendChild(name);
      listEl.appendChild(label);
    });
  }

  function getSelectedIds() {
    if (!listEl) return [];
    var checkboxes = listEl.querySelectorAll('.test-checkbox:checked');
    return Array.prototype.map.call(checkboxes, function (cb) { return cb.dataset.testId; });
  }

  function setRunning(flag) {
    running = flag;
    if (btnRunAll) btnRunAll.disabled = flag;
    if (btnRunSelected) btnRunSelected.disabled = flag;
  }

  function renderResults(data) {
    if (!resultsEl) return;
    var results = (data && data.results) ? data.results : (Array.isArray(data) ? data : []);
    var total = results.length;
    var passed = results.filter(function (r) { return r.passed; }).length;
    var failed = total - passed;

    var html = '<div class="tests-summary">' +
      '<span class="tests-summary-pass">' + passed + ' passed</span>' +
      '<span class="tests-summary-fail">' + failed + ' failed</span>' +
      '<span class="tests-summary-total">' + total + ' total</span>' +
      '</div>';

    if (total === 0) {
      html += '<p class="tests-empty">No test scenarios were run. Load test scenarios (or run all) and try again.</p>';
      resultsEl.innerHTML = html;
      return;
    }

    results.forEach(function (r) {
      var cls = r.passed ? 'result-pass' : 'result-fail';
      html += '<div class="test-result ' + cls + '" data-test-id="' + r.test_id + '">';
      html += '<div class="test-result-header">';
      html += '<span class="test-result-status">' + (r.passed ? 'Pass' : 'Fail') + '</span>';
      html += '<span class="test-result-id">' + r.test_id + '</span>';
      if (r.session_id) {
        html += '<a href="#" class="test-result-trace" data-session-id="' + r.session_id + '" title="View trace">View trace</a>';
      }
      html += '</div>';
      if (r.turns && r.turns.length) {
        html += '<div class="test-result-turns">';
        r.turns.forEach(function (turn, i) {
          var turnCls = turn.passed ? '' : 'turn-fail';
          html += '<div class="test-turn ' + turnCls + '">';
          html += '<span class="test-turn-msg">Turn ' + (i + 1) + ': ' + (turn.message || '').slice(0, 60) + (turn.message && turn.message.length > 60 ? '…' : '') + '</span>';
          html += '<span class="test-turn-status">' + (turn.passed ? '✓' : '✗ ' + (turn.reason || '')) + '</span>';
          if (!turn.passed && turn.reason) {
            html += '<div class="test-turn-detail">' + turn.reason + '</div>';
          }
          html += '</div>';
        });
        html += '</div>';
      }
      if (r.error) html += '<div class="test-result-error">' + r.error + '</div>';
      html += '</div>';
    });
    resultsEl.innerHTML = html;
    resultsEl.scrollTop = 0;
    resultsEl.querySelectorAll('.test-result-trace').forEach(function (a) {
      a.addEventListener('click', function (e) {
        e.preventDefault();
        var sessionId = a.dataset.sessionId;
        if (sessionId) {
          document.getElementById('tab-trace').click();
          setTimeout(function () {
            window.dispatchEvent(new CustomEvent('trace-session-select', { detail: { sessionId: sessionId } }));
          }, 100);
        }
      });
    });
  }

  function loadTests() {
    getTests()
      .then(function (data) {
        tests = data.tests || [];
        renderList();
      })
      .catch(function () {
        if (listEl) listEl.innerHTML = '<p class="tests-empty">Failed to load tests</p>';
      });
  }

  function runTests(testIds) {
    setRunning(true);
    if (resultsEl) resultsEl.innerHTML = '<p class="tests-progress">Running tests…</p>';
    var body = testIds && testIds.length ? { test_ids: testIds } : {};
    fetch('/tests/run-all', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
      .then(function (res) {
        if (!res.ok) throw new Error('Run failed');
        return res.json();
      })
      .then(function (data) {
        renderResults(data);
      })
      .catch(function (err) {
        if (resultsEl) resultsEl.innerHTML = '<p class="tests-error">' + (err.message || 'Run failed') + '</p>';
      })
      .finally(function () {
        setRunning(false);
      });
  }

  if (btnRunAll) btnRunAll.addEventListener('click', function () { runTests(null); });
  if (btnRunSelected) btnRunSelected.addEventListener('click', function () {
    var ids = getSelectedIds();
    if (ids.length === 0) {
      if (resultsEl) resultsEl.innerHTML = '<p class="tests-empty">Select at least one test</p>';
      return;
    }
    runTests(ids);
  });
  window.addEventListener('tests-view-show', loadTests);

  var viewTests = document.getElementById('view-tests');
  if (listEl && viewTests && viewTests.classList.contains('view-active')) loadTests();
})();
