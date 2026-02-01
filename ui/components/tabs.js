/**
 * Tab navigation: Chat, Trace, Stats.
 */
(function () {
  const tabChat = document.getElementById('tab-chat');
  const tabTrace = document.getElementById('tab-trace');
  const tabStats = document.getElementById('tab-stats');
  const tabTests = document.getElementById('tab-tests');
  const viewChat = document.getElementById('view-chat');
  const viewTrace = document.getElementById('view-trace');
  const viewStats = document.getElementById('view-stats');
  const viewTests = document.getElementById('view-tests');

  const tabs = [
    { btn: tabChat, view: viewChat, id: 'chat' },
    { btn: tabTrace, view: viewTrace, id: 'trace' },
    { btn: tabStats, view: viewStats, id: 'stats' },
    { btn: tabTests, view: viewTests, id: 'tests' },
  ];

  function show(id) {
    tabs.forEach(function (t) {
      const active = t.id === id;
      t.btn.classList.toggle('active', active);
      t.btn.setAttribute('aria-selected', active);
      t.view.classList.toggle('view-active', active);
      t.view.setAttribute('aria-hidden', !active);
    });
    if (id === 'trace') window.dispatchEvent(new CustomEvent('trace-view-show'));
    if (id === 'stats') window.dispatchEvent(new CustomEvent('stats-view-show'));
    else window.dispatchEvent(new CustomEvent('stats-view-hide'));
    if (id === 'tests') window.dispatchEvent(new CustomEvent('tests-view-show'));
  }

  if (tabChat) tabChat.addEventListener('click', function () { show('chat'); });
  if (tabTrace) tabTrace.addEventListener('click', function () { show('trace'); });
  if (tabStats) tabStats.addEventListener('click', function () { show('stats'); });
  if (tabTests) tabTests.addEventListener('click', function () { show('tests'); });
})();
