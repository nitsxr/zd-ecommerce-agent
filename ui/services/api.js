/**
 * API client for the E-commerce Assistant backend.
 */

const API_BASE = '';

/**
 * Send a chat message and get the assistant response.
 * @param {string} sessionId - Session ID for conversation continuity
 * @param {string} message - User message
 * @returns {Promise<{session_id: string, response: string, agent: string, handover?: string, confidence?: number, metadata?: object}>}
 */
async function sendMessage(sessionId, message) {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message: message.trim() }),
  });

  if (!res.ok) {
    const text = await res.text();
    let detail = text;
    try {
      const json = JSON.parse(text);
      detail = json.detail || (Array.isArray(json.detail) ? json.detail.map(d => d.msg || d).join(', ') : text);
    } catch (_) {}
    throw new Error(detail || `Request failed (${res.status})`);
  }

  return res.json();
}

/**
 * Check API health.
 * @returns {Promise<{status: string, redis: string}>}
 */
async function healthCheck() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}

/**
 * List recent sessions.
 * @param {number} limit
 * @returns {Promise<{sessions: Array<{session_id: string, message_count: number, created_at: string, updated_at: string}>}>}
 */
async function getSessions(limit = 100) {
  const res = await fetch(`${API_BASE}/sessions?limit=${limit}`);
  if (!res.ok) throw new Error('Failed to list sessions');
  return res.json();
}

/**
 * Get session details and full trace.
 * @param {string} sessionId
 * @returns {Promise<{session: object, trace: Array<object}>}>}
 */
async function getSession(sessionId) {
  const res = await fetch(`${API_BASE}/sessions/${encodeURIComponent(sessionId)}`);
  if (!res.ok) {
    if (res.status === 404) throw new Error('Session not found');
    throw new Error('Failed to load session');
  }
  return res.json();
}

/**
 * Get trace events for a session.
 * @param {string} sessionId
 * @returns {Promise<{session_id: string, events: Array<object}>}>}
 */
async function getTrace(sessionId) {
  const res = await fetch(`${API_BASE}/sessions/${encodeURIComponent(sessionId)}/trace`);
  if (!res.ok) throw new Error('Failed to load trace');
  return res.json();
}

/**
 * Get aggregate stats.
 * @returns {Promise<{total_sessions: number, total_messages: number, success_rate: number, avg_latency_ms: number, p50_latency_ms: number, p95_latency_ms: number, p99_latency_ms: number, tokens_used: number, agent_distribution: object}>}
 */
async function getStats() {
  const res = await fetch(`${API_BASE}/stats`);
  if (!res.ok) throw new Error('Failed to load stats');
  return res.json();
}

/**
 * List test scenarios.
 * @returns {Promise<{tests: Array<object}>}>}
 */
async function getTests() {
  const res = await fetch(`${API_BASE}/tests`);
  if (!res.ok) throw new Error('Failed to list tests');
  return res.json();
}

/**
 * Get one test scenario.
 * @param {string} testId
 * @returns {Promise<object>}
 */
async function getTest(testId) {
  const res = await fetch(`${API_BASE}/tests/${encodeURIComponent(testId)}`);
  if (!res.ok) throw new Error('Failed to load test');
  return res.json();
}

/**
 * Create or update test scenario.
 * @param {object} scenario - { id, name, description, turns }
 * @returns {Promise<object>}
 */
async function saveTest(scenario) {
  const res = await fetch(`${API_BASE}/tests`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(scenario),
  });
  if (!res.ok) throw new Error('Failed to save test');
  return res.json();
}

/**
 * Update test scenario.
 * @param {string} testId
 * @param {object} scenario
 * @returns {Promise<object>}
 */
async function updateTest(testId, scenario) {
  const res = await fetch(`${API_BASE}/tests/${encodeURIComponent(testId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...scenario, id: testId }),
  });
  if (!res.ok) throw new Error('Failed to update test');
  return res.json();
}

/**
 * Delete test scenario.
 * @param {string} testId
 */
async function deleteTest(testId) {
  const res = await fetch(`${API_BASE}/tests/${encodeURIComponent(testId)}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to delete test');
}

/**
 * Run a single test.
 * @param {string} testId
 * @returns {Promise<object>}
 */
async function runTest(testId) {
  const res = await fetch(`${API_BASE}/tests/${encodeURIComponent(testId)}/run`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to run test');
  return res.json();
}

/**
 * Run all tests or a subset.
 * @param {string[]} [testIds]
 * @returns {Promise<{results: Array<object}>}>}
 */
async function runAllTests(testIds) {
  const res = await fetch(`${API_BASE}/tests/run-all`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(testIds ? { test_ids: testIds } : {}),
  });
  if (!res.ok) throw new Error('Failed to run tests');
  return res.json();
}
