const API_BASE = '';

// ---- TAB SWITCHING ----
document.querySelectorAll('.nav-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
    document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
    if (tab.dataset.tab === 'analytics') loadAnalytics();
    if (tab.dataset.tab === 'project') loadProjectView('overview');
  });
});

// ---- DEV MODE TOGGLE ----
document.getElementById('dev-toggle').addEventListener('change', function() {
  document.querySelectorAll('.dev-tab').forEach(t => {
    t.style.display = this.checked ? '' : 'none';
  });
  if (!this.checked) {
    const debugTab = document.querySelector('.nav-tab[data-tab="debug"]');
    if (debugTab.classList.contains('active')) {
      document.querySelector('.nav-tab[data-tab="chat"]').click();
    }
  }
});
document.getElementById('dev-toggle').dispatchEvent(new Event('change'));

// ---- CHAT ----
const input = document.getElementById('goal-input');
const sendBtn = document.getElementById('send-btn');
const messages = document.getElementById('messages');

function addMessage(text, isUser) {
  const div = document.createElement('div');
  div.className = 'message ' + (isUser ? 'user' : 'assistant');
  div.innerHTML = '<div class="msg-content"><p>' + text + '</p></div>';
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
  return div.querySelector('.msg-content');
}

function addAssistantResponse(container, data) {
  const status = data.status;
  const summary = data.summary;
  const statusLine = data.status_line;

  if (data.continuation && data.continuation.is_continuation) {
    const note = document.createElement('p');
    note.className = 'continuity-note';
    note.textContent = 'Continuing previous work: ' + escapeHtml(data.continuation.parent_description || '');
    container.appendChild(note);
  } else {
    const note = document.createElement('p');
    note.className = 'continuity-note new-task';
    note.textContent = 'Starting a new task';
    container.appendChild(note);
  }

  const p = document.createElement('p');
  p.className = 'summary' + (status === 'failed' ? ' failed' : status === 'clarification_required' ? ' clarification' : '');
  p.textContent = summary;
  container.appendChild(p);

  if (data.steps && data.steps.length > 0) {
    const toggle = document.createElement('button');
    toggle.className = 'steps-toggle';
    toggle.textContent = 'Show steps (' + data.steps.length + ')';
    container.appendChild(toggle);

    const list = document.createElement('div');
    list.className = 'steps-list hidden';
    data.steps.forEach(s => {
      const item = document.createElement('div');
      item.className = 'step-item';
      const dotClass = s.status === 'success' ? 'success' : s.status === 'failed' ? 'failed' : 'running';
      item.innerHTML = '<span class="dot ' + dotClass + '"></span><span class="step-label">' + escapeHtml(s.label) + '</span>';
      list.appendChild(item);
    });
    container.appendChild(list);

    toggle.addEventListener('click', () => {
      const hidden = list.classList.toggle('hidden');
      toggle.textContent = hidden ? 'Show steps (' + data.steps.length + ')' : 'Hide steps';
    });
  }

  if (statusLine) {
    const sl = document.createElement('div');
    sl.className = 'status-line';
    sl.textContent = statusLine;
    container.appendChild(sl);
  }
}

function escapeHtml(text) {
  const d = document.createElement('div');
  d.textContent = text;
  return d.innerHTML;
}

async function sendMessage() {
  const goal = input.value.trim();
  if (!goal) return;

  addMessage(goal, true);
  input.value = '';
  sendBtn.disabled = true;
  sendBtn.textContent = 'Running...';

  const contentDiv = addMessage('', false);
  contentDiv.innerHTML = '<p>Working...</p>';

  try {
    const res = await fetch(API_BASE + '/api/goal', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ goal }),
    });
    if (!res.ok) {
      const err = await res.json();
      contentDiv.innerHTML = '<p class="summary failed">Error: ' + escapeHtml(err.error || res.statusText) + '</p>';
      return;
    }
    const data = await res.json();
    contentDiv.innerHTML = '';
    addAssistantResponse(contentDiv, data);
  } catch (err) {
    contentDiv.innerHTML = '<p class="summary failed">Connection error: ' + escapeHtml(err.message) + '</p>';
  } finally {
    sendBtn.disabled = false;
    sendBtn.textContent = 'Send';
    input.focus();
  }
}

sendBtn.addEventListener('click', sendMessage);
input.addEventListener('keydown', e => { if (e.key === 'Enter') sendMessage(); });

// ---- ANALYTICS ----
async function loadAnalytics() {
  try {
    const res = await fetch(API_BASE + '/api/analytics');
    const data = await res.json();

    document.getElementById('stat-total').textContent = data.goals.total;
    document.getElementById('stat-active').textContent = data.goals.active;
    document.getElementById('stat-done').textContent = data.goals.completed;
    document.getElementById('stat-failed').textContent = data.goals.failed;
    document.getElementById('stat-runs').textContent = data.feedback.total;
    document.getElementById('stat-successes').textContent = data.feedback.successes;
    document.getElementById('stat-fails').textContent = data.feedback.failures;
    document.getElementById('stat-failrate').textContent = data.feedback.failure_rate + '%';

    const fill = document.getElementById('feedback-fill');
    const rate = data.feedback.failure_rate;
    fill.style.width = Math.min(rate, 100) + '%';
    fill.style.background = rate > 50 ? 'var(--red)' : rate > 20 ? 'var(--yellow)' : 'var(--green)';

    const list = document.getElementById('pattern-list');
    if (data.failure_patterns.length === 0) {
      list.innerHTML = '<li class="empty-state">No issues recorded</li>';
    } else {
      list.innerHTML = data.failure_patterns.map(p =>
        '<li><span class="pattern-error">' + escapeHtml(p.error) + '</span><span class="pattern-count">' + p.count + '</span></li>'
      ).join('');
    }
  } catch (err) {
    console.error('Analytics load error:', err);
  }
}

// ---- PROJECT ----
async function loadProjectView(lens) {
  const container = document.getElementById('project-content');
  container.innerHTML = '<div class="project-empty">Loading...</div>';
  try {
    const res = await fetch(API_BASE + '/api/project?lens=' + lens);
    const data = await res.json();
    renderProjectView(container, data);
  } catch (err) {
    container.innerHTML = '<div class="project-empty">Error: ' + escapeHtml(err.message) + '</div>';
  }
}

document.querySelectorAll('.lens-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.lens-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    loadProjectView(btn.dataset.lens);
  });
});

function renderProjectView(container, data) {
  if (data.lens === 'overview') {
    let html = '<div id="project-overview">';

    // goal counts
    html += '<div id="project-goal-bar">';
    const gc = data.goal_count || {};
    html += '<span class="proj-stat">Active: <strong>' + gc.active + '</strong></span>';
    html += '<span class="proj-stat">Blocked: <strong>' + gc.blocked + '</strong></span>';
    html += '<span class="proj-stat">Completed: <strong>' + gc.completed + '</strong></span>';
    html += '<span class="proj-stat">Total: <strong>' + gc.total + '</strong></span>';
    html += '</div>';

    // active
    html += '<div class="proj-section"><h3>Active Work</h3>';
    if (data.active_goals && data.active_goals.length) {
      html += '<ul class="proj-list">';
      data.active_goals.forEach(g => {
        html += '<li><span class="proj-goal-text">' + escapeHtml(g.description) + '</span></li>';
      });
      html += '</ul>';
    } else {
      html += '<div class="proj-empty">No active goals</div>';
    }
    html += '</div>';

    // blocked
    html += '<div class="proj-section"><h3>Blocked Work</h3>';
    if (data.blocked_goals && data.blocked_goals.length) {
      html += '<ul class="proj-list">';
      data.blocked_goals.forEach(g => {
        html += '<li><span class="proj-goal-text">' + escapeHtml(g.description) + '</span><span class="proj-reason">' + escapeHtml(g.reason) + '</span></li>';
      });
      html += '</ul>';
    } else {
      html += '<div class="proj-empty">No blocked goals</div>';
    }
    html += '</div>';

    // completed
    html += '<div class="proj-section"><h3>Recently Completed</h3>';
    if (data.completed_goals && data.completed_goals.length) {
      html += '<ul class="proj-list">';
      data.completed_goals.slice(-5).forEach(g => {
        html += '<li><span class="proj-goal-text">' + escapeHtml(g.description) + '</span></li>';
      });
      html += '</ul>';
    } else {
      html += '<div class="proj-empty">No completed goals</div>';
    }
    html += '</div>';

    // continuations
    html += '<div class="proj-section"><h3>Continuation Chains</h3>';
    if (data.continuation_links && data.continuation_links.length) {
      html += '<ul class="proj-list">';
      data.continuation_links.forEach(c => {
        html += '<li><span class="proj-chain">' + escapeHtml(c.parent_description) + ' → ' + escapeHtml(c.child_description) + '</span></li>';
      });
      html += '</ul>';
    } else {
      html += '<div class="proj-empty">No continuation chains</div>';
    }
    html += '</div>';

    // failures
    html += '<div class="proj-section"><h3>Recurring Failures</h3>';
    if (data.recurring_failures && data.recurring_failures.length) {
      html += '<ul class="proj-list">';
      data.recurring_failures.forEach(f => {
        html += '<li><span class="proj-goal-text">' + escapeHtml(f.error) + '</span><span class="proj-count">x' + f.count + '</span></li>';
      });
      html += '</ul>';
    } else {
      html += '<div class="proj-empty">No recurring failures</div>';
    }
    html += '</div>';

    container.innerHTML = html + '</div>';
  } else if (data.lens === 'history') {
    let html = '<div id="project-history"><h3>Activity Log</h3>';
    if (data.entries && data.entries.length) {
      html += '<div class="proj-timeline">';
      data.entries.slice().reverse().forEach(e => {
        const color = e.type === 'execution' ? 'var(--accent)' : e.type === 'decision' ? 'var(--green)' : 'var(--yellow)';
        html += '<div class="proj-entry"><span class="proj-dot" style="background:' + color + '"></span><span class="proj-entry-type">' + e.type + '</span><span class="proj-entry-desc">' + escapeHtml(e.description) + '</span></div>';
      });
      html += '</div>';
    } else {
      html += '<div class="proj-empty">No activity yet</div>';
    }
    container.innerHTML = html + '</div>';
  } else if (data.lens === 'continuity') {
    let html = '<div id="project-continuity">';

    html += '<div class="proj-section"><h3>Goal Chains</h3>';
    if (data.goal_chains && data.goal_chains.length) {
      html += '<ul class="proj-list">';
      data.goal_chains.forEach(ch => {
        const root = ch.root || {};
        html += '<li class="proj-chain-item"><span class="proj-chain-root">' + escapeHtml(root.description) + '</span>';
        if (ch.children && ch.children.length) {
          html += '<ul class="proj-children">';
          ch.children.forEach(c => {
            html += '<li>→ ' + escapeHtml(c.description) + ' <span class="proj-child-status">(' + c.status + ')</span></li>';
          });
          html += '</ul>';
        }
        html += '</li>';
      });
      html += '</ul>';
    } else {
      html += '<div class="proj-empty">No goal chains</div>';
    }
    html += '</div>';

    html += '<div class="proj-section"><h3>Repeated Attempts</h3>';
    if (data.repeated_attempts && data.repeated_attempts.length) {
      html += '<ul class="proj-list">';
      data.repeated_attempts.forEach(a => {
        html += '<li><span class="proj-goal-text">' + escapeHtml(a.description) + '</span><span class="proj-count">x' + a.attempt_count + '</span><span class="proj-child-status">' + a.last_status + '</span></li>';
      });
      html += '</ul>';
    } else {
      html += '<div class="proj-empty">No repeated attempts</div>';
    }
    html += '</div>';

    container.innerHTML = html + '</div>';
  }
}

// ---- DEBUG ----
document.querySelectorAll('.debug-btn').forEach(btn => {
  btn.addEventListener('click', async () => {
    const source = btn.dataset.source;
    const output = document.getElementById('debug-output');
    output.textContent = 'Loading...';
    try {
      const res = await fetch(API_BASE + '/api/debug/' + source);
      const data = await res.json();
      output.textContent = JSON.stringify(data, null, 2);
    } catch (err) {
      output.textContent = 'Error: ' + err.message;
    }
  });
});
