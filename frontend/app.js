const API_BASE = '';

// ---- Failure UX helpers ----
const FAILURE_LABELS = {
  execution_failure: 'Execution issue',
  context_failure: 'System issue',
  workspace_failure: 'Workspace issue',
  api_failure: 'System issue',
  ui_failure: 'System issue',
  internal_guard_failure: 'System issue',
  unknown_failure: 'System issue',
};

function classifyApiError(data) {
  const f = data && data.failure;
  if (!f) return null;
  const label = FAILURE_LABELS[f.category] || 'Something didn\u2019t complete successfully';
  const isDev = document.getElementById('dev-toggle') && document.getElementById('dev-toggle').checked;
  return {
    label: label,
    safeMessage: f.safe_message || label,
    debug: isDev ? (f.debug || null) : null,
    category: f.category || 'unknown_failure',
  };
}

function makeErrorHtml(data, fallbackMsg) {
  const classified = classifyApiError(data);
  if (classified) {
    let html = '<p class="summary failed">' + escapeHtml(classified.label) + '</p>';
    html += '<p class="failure-detail">' + escapeHtml(classified.safeMessage) + '</p>';
    if (classified.debug) {
      html += '<pre class="failure-debug hidden">' + escapeHtml(JSON.stringify(classified.debug, null, 2)) + '</pre>';
      const devToggle = document.getElementById('dev-toggle');
      if (devToggle && devToggle.checked) {
        html = html.replace('hidden"', '"');
      }
    }
    return html;
  }
  return '<p class="summary failed">' + escapeHtml(fallbackMsg || 'Something didn\u2019t complete successfully') + '</p>';
}

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
    const sysTab = document.querySelector('.nav-tab[data-tab="debug"]');
    const insTab = document.querySelector('.nav-tab[data-tab="analytics"]');
    if (sysTab && sysTab.classList.contains('active') ||
        insTab && insTab.classList.contains('active')) {
      document.querySelector('.nav-tab[data-tab="chat"]').click();
    }
  }
});
document.getElementById('dev-toggle').dispatchEvent(new Event('change'));

// ---- FILE OPERATIONS ----
const fileDialog = document.getElementById('file-dialog');
const fdTitle = document.getElementById('file-dialog-title');
const fdPath = document.getElementById('fd-path');
const fdContent = document.getElementById('fd-content');
const fdContext = document.getElementById('fd-context');
const fdConfirm = document.getElementById('fd-confirm');
const fdCancel = document.getElementById('fd-cancel');

let fileActionMode = 'create';

document.getElementById('fa-create').addEventListener('click', () => {
  fileActionMode = 'create';
  fdTitle.textContent = 'Create File';
  fdContent.style.display = '';
  fdConfirm.textContent = 'Save';
  fdPath.value = '';
  fdContent.value = '';
  fileDialog.classList.remove('hidden');
  fdPath.focus();
});

document.getElementById('fa-read').addEventListener('click', () => {
  fileActionMode = 'read';
  fdTitle.textContent = 'Read File';
  fdContent.style.display = 'none';
  fdConfirm.textContent = 'Read';
  fdPath.value = '';
  fileDialog.classList.remove('hidden');
  fdPath.focus();
});

document.getElementById('fa-list').addEventListener('click', () => {
  fileActionMode = 'list';
  fdTitle.textContent = 'List Directory';
  fdContent.style.display = 'none';
  fdConfirm.textContent = 'List';
  fdPath.value = '.';
  fileDialog.classList.remove('hidden');
  fdPath.focus();
});

fdCancel.addEventListener('click', () => {
  fileDialog.classList.add('hidden');
});

fdConfirm.addEventListener('click', async () => {
  const path = fdPath.value.trim();
  if (!path) return;
  const context = fdContext.value;
  fileDialog.classList.add('hidden');

  const body = { path, context };
  let endpoint = '';
  let label = '';

  if (fileActionMode === 'create') {
    body.content = fdContent.value;
    endpoint = '/api/files/create';
    label = 'Created: ' + path;
  } else if (fileActionMode === 'read') {
    endpoint = '/api/files/read';
    label = 'Read: ' + path;
  } else {
    endpoint = '/api/files/list';
    label = 'Listed: ' + path;
  }

  addMessage(label, true);

  const contentDiv = addMessage('', false);
  contentDiv.innerHTML = '<p>Working...</p>';

  try {
    const res = await fetch(API_BASE + endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    contentDiv.innerHTML = '';
    if (data.status === 'success') {
      if (fileActionMode === 'read') {
        const pre = document.createElement('pre');
        pre.className = 'file-content';
        pre.textContent = data.content || '';
        contentDiv.appendChild(pre);
      } else if (fileActionMode === 'list') {
        const list = document.createElement('ul');
        list.className = 'file-list';
        (data.items || []).forEach(item => {
          const li = document.createElement('li');
          li.textContent = item;
          list.appendChild(li);
        });
        contentDiv.appendChild(list);
      } else {
        const p = document.createElement('p');
        p.className = 'summary';
        p.textContent = 'Saved: ' + data.file;
        contentDiv.appendChild(p);
      }
    } else {
      contentDiv.innerHTML = '<p class="summary failed">Error: ' + escapeHtml(data.error || 'unknown') + '</p>';
    }
  } catch (err) {
    contentDiv.innerHTML = '<p class="summary failed">Connection error: ' + escapeHtml(err.message) + '</p>';
  }
});

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
  const meta = data.meta || {};
  const trace = data.trace || {};
  const status = meta.status || 'unknown';
  const summary = trace.summary || '';
  const statusLine = trace.status_line || '';
  const steps = trace.steps || [];

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

  if (steps.length > 0) {
    const toggle = document.createElement('button');
    toggle.className = 'steps-toggle';
    toggle.textContent = 'Show steps (' + steps.length + ')';
    container.appendChild(toggle);

    const list = document.createElement('div');
    list.className = 'steps-list hidden';
    steps.forEach(s => {
      const item = document.createElement('div');
      item.className = 'step-item';
      const dotClass = s.status === 'success' ? 'success' : s.status === 'failed' ? 'failed' : 'running';
      item.innerHTML = '<span class="dot ' + dotClass + '"></span><span class="step-label">' + escapeHtml(s.label) + '</span>';
      list.appendChild(item);
    });
    container.appendChild(list);

    toggle.addEventListener('click', () => {
      const hidden = list.classList.toggle('hidden');
      toggle.textContent = hidden ? 'Show steps (' + steps.length + ')' : 'Hide steps';
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
    const data = await res.json();
    if (!res.ok || data.status === 'error') {
      contentDiv.innerHTML = makeErrorHtml(data, data.error || 'Request failed');
      return;
    }
    contentDiv.innerHTML = '';
    addAssistantResponse(contentDiv, data);
  } catch (err) {
    contentDiv.innerHTML = '<p class="summary failed">Something didn\u2019t complete successfully. Check your connection and try again.</p>';
  } finally {
    sendBtn.disabled = false;
    sendBtn.textContent = 'Send';
    input.focus();
  }
}

sendBtn.addEventListener('click', sendMessage);
input.addEventListener('keydown', e => { if (e.key === 'Enter') sendMessage(); });

// ---- COMMAND PALETTE ----
const cmdInput = document.getElementById('cmd-input');
const cmdBtn = document.getElementById('cmd-btn');

async function executeCommand() {
  const request = cmdInput.value.trim();
  if (!request) return;
  cmdInput.value = '';
  cmdBtn.disabled = true;
  cmdBtn.textContent = '...';

  // First try routing to see if it's a known command
  let routeData;
  try {
    const routeRes = await fetch(API_BASE + '/api/command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ request }),
    });
    routeData = await routeRes.json();
  } catch (err) {
    cmdBtn.disabled = false;
    cmdBtn.textContent = 'Go';
    addMessage('Command error: ' + err.message, true);
    addMessage('Something didn\u2019t complete successfully. Check your connection and try again.', false);
    return;
  } finally {
    cmdBtn.disabled = false;
    cmdBtn.textContent = 'Go';
  }

  const command = routeData.command || 'execute_goal';

  // Route to appropriate tab/view
  if (command === 'show_overview') {
    document.querySelector('.nav-tab[data-tab="project"]').click();
    document.querySelector('.lens-btn[data-lens="overview"]').click();
  } else if (command === 'show_structure') {
    document.querySelector('.nav-tab[data-tab="project"]').click();
    document.querySelector('.lens-btn[data-lens="structure"]').click();
  } else if (command === 'show_relationships') {
    document.querySelector('.nav-tab[data-tab="project"]').click();
    document.querySelector('.lens-btn[data-lens="relationships"]').click();
  } else if (command === 'show_workspace') {
    document.querySelector('.nav-tab[data-tab="project"]').click();
    document.querySelector('.lens-btn[data-lens="workspace"]').click();
  } else if (command === 'generate_handoff') {
    document.querySelector('.nav-tab[data-tab="project"]').click();
    document.querySelector('.lens-btn[data-lens="handoff"]').click();
  } else if (command === 'execute_goal') {
    // Send as normal goal in chat
    document.querySelector('.nav-tab[data-tab="chat"]').click();
    input.value = request;
    sendMessage();
  } else {
    // File operation — show in chat
    document.querySelector('.nav-tab[data-tab="chat"]').click();
    addMessage(command.replace(/_/g, ' ') + ': ' + request, true);
    const contentDiv = addMessage('', false);
    contentDiv.innerHTML = '<p>Working...</p>';
    // Re-post to command endpoint to get the result with proper lens data
    try {
      const res = await fetch(API_BASE + '/api/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ request }),
      });
      const data = await res.json();
      contentDiv.innerHTML = '';
      if (data.status === 'success') {
        if (command === 'read_file' && data.content) {
          const pre = document.createElement('pre');
          pre.className = 'file-content';
          pre.textContent = data.content || '';
          contentDiv.appendChild(pre);
        } else if (command === 'list_workspace' && data.items) {
          const list = document.createElement('ul');
          list.className = 'file-list';
          (data.items || []).forEach(item => {
            const li = document.createElement('li');
            li.textContent = item;
            list.appendChild(li);
          });
          contentDiv.appendChild(list);
        } else if (command === 'list_workspace' && data.files) {
          const list = document.createElement('ul');
          list.className = 'file-list';
          (data.files || []).forEach(item => {
            const li = document.createElement('li');
            if (typeof item === 'object') li.textContent = item.name || item.path || '';
            else li.textContent = item;
            list.appendChild(li);
          });
          contentDiv.appendChild(list);
        } else {
          const p = document.createElement('p');
          p.className = 'summary';
          const path = data.path || data.file || '';
          p.textContent = command.replace(/_/g, ' ') + ': ' + (path || 'done');
          contentDiv.appendChild(p);
        }
      } else {
        contentDiv.innerHTML = '<p class="summary failed">Error: ' + escapeHtml(data.error || 'unknown') + '</p>';
      }
    } catch (err) {
      contentDiv.innerHTML = '<p class="summary failed">Connection error: ' + escapeHtml(err.message) + '</p>';
    }
  }
}

cmdBtn.addEventListener('click', executeCommand);
cmdInput.addEventListener('keydown', e => { if (e.key === 'Enter') executeCommand(); });

// ---- Command palette suggestions with grouping ----
const cmdGroups = [
  { label: 'Work', commands: ['create file', 'create folder', 'read file', 'update file', 'delete file'] },
  { label: 'Navigation', commands: ['show overview', 'show layout', 'show connections', 'show workspace', 'list workspace'] },
  { label: 'System', commands: ['generate handoff'] },
  { label: 'Advanced', commands: ['switch workspace', 'create workspace'] },
];

const cmdSuggestions = document.createElement('div');
cmdSuggestions.id = 'cmd-suggestions';
cmdSuggestions.className = 'hidden';
cmdInput.parentNode.appendChild(cmdSuggestions);

function renderCmdSuggestions() {
  cmdSuggestions.innerHTML = '';
  const val = cmdInput.value.toLowerCase().trim();
  let hasMatch = false;
  cmdGroups.forEach(group => {
    const matches = group.commands.filter(c => !val || c.includes(val));
    if (!matches.length) return;
    hasMatch = true;
    const header = document.createElement('div');
    header.className = 'cmd-group-header';
    header.textContent = group.label;
    cmdSuggestions.appendChild(header);
    matches.forEach(cmd => {
      const item = document.createElement('div');
      item.className = 'cmd-suggestion';
      item.textContent = cmd;
      item.addEventListener('click', () => {
        cmdInput.value = cmd;
        cmdSuggestions.classList.add('hidden');
        executeCommand();
      });
      cmdSuggestions.appendChild(item);
    });
  });
  if (hasMatch) {
    cmdSuggestions.classList.remove('hidden');
  } else {
    cmdSuggestions.classList.add('hidden');
  }
}

cmdInput.addEventListener('focus', () => {
  if (cmdInput.value.trim()) renderCmdSuggestions();
  else renderCmdSuggestions(); // show all
});
cmdInput.addEventListener('blur', () => {
  setTimeout(() => cmdSuggestions.classList.add('hidden'), 200);
});
cmdInput.addEventListener('input', renderCmdSuggestions);

// ---- WORKSPACE INDICATOR ----
const wsSelector = document.getElementById('ws-selector');

async function loadWorkspaceIndicator() {
  try {
    const [curRes, listRes] = await Promise.all([
      fetch(API_BASE + '/api/workspaces/current'),
      fetch(API_BASE + '/api/workspaces'),
    ]);
    const cur = await curRes.json();
    const workspaces = await listRes.json();
    wsSelector.innerHTML = '';
    workspaces.forEach(w => {
      const opt = document.createElement('option');
      opt.value = w.name;
      const opened = w.last_opened || '';
      const suffix = opened ? ' (' + formatTimestamp(opened) + ')' : '';
      opt.textContent = w.name + suffix;
      if (w.name === cur.name) opt.selected = true;
      wsSelector.appendChild(opt);
    });
  } catch (err) {
    console.error('Workspace indicator error:', err);
  }
}

wsSelector.addEventListener('change', async () => {
  const name = wsSelector.value;
  if (!name) return;
  try {
    await fetch(API_BASE + '/api/workspaces/switch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    });
    loadWorkspaceIndicator();
  } catch (err) {
    console.error('Switch workspace error:', err);
  }
});

loadWorkspaceIndicator();

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
    let data;
    if (lens === 'handoff') {
      const res = await fetch(API_BASE + '/api/handoff?mode=standard');
      data = await res.json();
    } else if (lens === 'workspace') {
      const res = await fetch(API_BASE + '/api/workspace');
      data = await res.json();
    } else {
      const res = await fetch(API_BASE + '/api/project?lens=' + lens);
      data = await res.json();
    }
    if (data.failure) {
      container.innerHTML = '<div class="project-empty">' + makeErrorHtml(data, data.failure.safe_message) + '</div>';
    } else {
      renderProjectView(container, data);
    }
  } catch (err) {
    container.innerHTML = '<div class="project-empty">Something didn\u2019t complete successfully.</div>';
  }
}

document.querySelectorAll('.lens-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.lens-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    loadProjectView(btn.dataset.lens);
  });
});

document.getElementById('lens-expand-btn').addEventListener('click', function() {
  const more = document.getElementById('lens-more');
  const hidden = more.classList.toggle('hidden');
  this.textContent = hidden ? '\u00B7\u00B7\u00B7' : '\u00D7';
});

function renderProjectView(container, data) {
  if (data.lens === 'overview') {
    let html = '<div id="project-overview">';

    html += '<div id="project-goal-bar">';
    const gc = data.goal_count || {};
    html += '<span class="proj-stat">Active: <strong>' + gc.active + '</strong></span>';
    html += '<span class="proj-stat">Blocked: <strong>' + gc.blocked + '</strong></span>';
    html += '<span class="proj-stat">Completed: <strong>' + gc.completed + '</strong></span>';
    html += '<span class="proj-stat">Total: <strong>' + gc.total + '</strong></span>';
    html += '</div>';

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
  } else if (data.lens === 'structure') {
    let html = '<div id="project-structure">';

    // Stats bar
    html += '<div id="project-goal-bar">';
    html += '<span class="proj-stat">Files: <strong>' + (data.file_count || 0) + '</strong></span>';
    html += '<span class="proj-stat">Directories: <strong>' + (data.directory_count || 0) + '</strong></span>';
    html += '</div>';

    // Components
    html += '<div class="proj-section"><h3>Components</h3>';
    if (data.components && data.components.length) {
      html += '<div class="struc-grid">';
      data.components.forEach(c => {
        html += '<div class="struc-card"><div class="struc-card-name">' + escapeHtml(c.name) + '</div>';
        html += '<div class="struc-card-stats"><span>' + c.file_count + ' files</span><span>' + c.directory_count + ' dirs</span></div>';
        html += '</div>';
      });
      html += '</div>';
    } else {
      html += '<div class="proj-empty">No components detected</div>';
    }
    html += '</div>';

    // Extension breakdown
    html += '<div class="proj-section"><h3>File Types</h3>';
    const extData = data.extension_breakdown || {};
    const extKeys = Object.keys(extData);
    if (extKeys.length) {
      html += '<ul class="proj-list ext-list">';
      extKeys.forEach(ext => {
        html += '<li><span class="pattern-error">' + escapeHtml(ext) + '</span><span class="pattern-count">' + extData[ext] + '</span></li>';
      });
      html += '</ul>';
    } else {
      html += '<div class="proj-empty">No files scanned</div>';
    }
    html += '</div>';

    // Recent activity
    html += '<div class="proj-section"><h3>Recent Activity</h3>';
    if (data.recent_activity && data.recent_activity.length) {
      html += '<ul class="proj-list">';
      data.recent_activity.slice(0, 10).forEach(a => {
        html += '<li><span class="proj-goal-text">' + escapeHtml(a.file_path) + '</span><span class="proj-child-status">' + escapeHtml(a.action) + '</span></li>';
      });
      html += '</ul>';
    } else {
      html += '<div class="proj-empty">No recent activity</div>';
    }
    html += '</div>';

    // Goal associations per component
    html += '<div class="proj-section"><h3>Goal Associations</h3>';
    if (data.goal_associations && data.goal_associations.length) {
      data.goal_associations.forEach(assoc => {
        html += '<div class="proj-subsection"><strong>' + escapeHtml(assoc.component) + '</strong> (' + assoc.total_goals + ' goals)';
        if (assoc.goals && assoc.goals.length) {
          html += '<ul class="proj-list">';
          assoc.goals.forEach(g => {
            html += '<li><span class="proj-goal-text">' + escapeHtml(g.description) + '</span></li>';
          });
          html += '</ul>';
        }
        html += '</div>';
      });
    } else {
      html += '<div class="proj-empty">No goal associations</div>';
    }
    html += '</div>';

    container.innerHTML = html + '</div>';
  } else if (data.lens === 'changes') {
    let html = '<div id="project-changes">';

    // Timeline
    html += '<div class="proj-section"><h3>Timeline</h3>';
    if (data.timeline && data.timeline.length) {
      html += '<div class="proj-timeline ch-timeline">';
      data.timeline.forEach(c => {
        const actionColor = c.action_type === 'created' ? 'var(--green)' : c.action_type === 'deleted' ? 'var(--red)' : 'var(--accent)';
        html += '<div class="proj-entry ch-entry">';
        html += '<span class="ch-time">' + escapeHtml(formatTimestamp(c.timestamp)) + '</span>';
        html += '<span class="ch-action" style="color:' + actionColor + '">' + escapeHtml(c.action_type) + '</span>';
        html += '<span class="ch-file">' + escapeHtml(c.file_path) + '</span>';
        if (c.component) html += '<span class="ch-component">' + escapeHtml(c.component) + '</span>';
        if (c.goal_description) html += '<span class="ch-goal-desc">' + escapeHtml(c.goal_description) + '</span>';
        html += '</div>';
      });
      html += '</div>';
    } else {
      html += '<div class="proj-empty">No changes recorded</div>';
    }
    html += '</div>';

    // Component Activity
    html += '<div class="proj-section"><h3>Component Activity</h3>';
    if (data.component_activity && data.component_activity.length) {
      html += '<ul class="proj-list">';
      data.component_activity.slice(0, 10).forEach(comp => {
        html += '<li><span class="proj-goal-text">' + escapeHtml(comp.component) + '</span>';
        html += '<span class="ch-change-count">' + comp.total_changes + ' changes</span></li>';
      });
      html += '</ul>';
    } else {
      html += '<div class="proj-empty">No component activity</div>';
    }
    html += '</div>';

    // Goal Activity
    html += '<div class="proj-section"><h3>Goal Activity</h3>';
    if (data.goal_activity && data.goal_activity.length) {
      html += '<ul class="proj-list">';
      data.goal_activity.slice(0, 10).forEach(g => {
        html += '<li>';
        html += '<span class="proj-goal-text">' + escapeHtml(g.goal_description || g.goal_id) + '</span>';
        html += '<span class="ch-change-count">' + g.files_changed.length + ' files, ' + g.components_changed.length + ' components</span>';
        html += '</li>';
      });
      html += '</ul>';
    } else {
      html += '<div class="proj-empty">No goal activity</div>';
    }
    html += '</div>';

    container.innerHTML = html + '</div>';
  } else if (data.lens === 'relationships') {
    let html = '<div id="project-relationships">';

    // File Relationships
    html += '<div class="proj-section"><h3>Files Frequently Changed Together</h3>';
    if (data.file_relationships && data.file_relationships.length) {
      data.file_relationships.slice(0, 10).forEach(fr => {
        html += '<div class="rel-card">';
        html += '<div class="rel-card-name">' + escapeHtml(fr.file_path) + '</div>';
        html += '<div class="rel-card-peers">';
        const topPeers = (fr.observed_with || []).slice(0, 5);
        topPeers.forEach(p => {
          html += '<span class="rel-peer"><span class="rel-peer-name">' + escapeHtml(p.file_path) + '</span><span class="rel-peer-count">' + p.cooccurrence_count + '</span></span>';
        });
        html += '</div></div>';
      });
    } else {
      html += '<div class="proj-empty">No file relationships observed yet</div>';
    }
    html += '</div>';

    // Component Relationships
    html += '<div class="proj-section"><h3>Components Frequently Worked On Together</h3>';
    if (data.component_relationships && data.component_relationships.length) {
      data.component_relationships.slice(0, 10).forEach(cr => {
        html += '<div class="rel-card">';
        html += '<div class="rel-card-name">' + escapeHtml(cr.component) + '</div>';
        html += '<div class="rel-card-peers">';
        const topPeers = (cr.observed_with || []).slice(0, 5);
        topPeers.forEach(p => {
          html += '<span class="rel-peer"><span class="rel-peer-name">' + escapeHtml(p.component) + '</span><span class="rel-peer-count">' + p.cooccurrence_count + '</span></span>';
        });
        html += '</div></div>';
      });
    } else {
      html += '<div class="proj-empty">No component relationships observed yet</div>';
    }
    html += '</div>';

    // Goal Relationships
    html += '<div class="proj-section"><h3>Goals Affecting Similar Areas</h3>';
    if (data.goal_relationships && data.goal_relationships.length) {
      html += '<ul class="proj-list">';
      data.goal_relationships.slice(0, 10).forEach(gr => {
        html += '<li class="rel-goal-item">';
        html += '<div class="rel-goal-pair"><span class="proj-goal-text">' + escapeHtml(gr.goal_description_a || gr.goal_id_a) + '</span>';
        html += '<span class="rel-goal-with">with</span>';
        html += '<span class="proj-goal-text">' + escapeHtml(gr.goal_description_b || gr.goal_id_b) + '</span></div>';
        html += '<span class="ch-change-count">' + gr.overlap_count + ' overlaps</span>';
        html += '</li>';
      });
      html += '</ul>';
    } else {
      html += '<div class="proj-empty">No overlapping goals yet</div>';
    }
    html += '</div>';

    container.innerHTML = html + '</div>';
  } else if (data.handoff_mode) {
    let html = '<div id="project-handoff">';

    const summary = data.project_summary || {};
    const gc = summary.goal_count || {};
    html += '<div id="project-goal-bar">';
    html += '<span class="proj-stat">Active: <strong>' + gc.active + '</strong></span>';
    html += '<span class="proj-stat">Blocked: <strong>' + gc.blocked + '</strong></span>';
    html += '<span class="proj-stat">Completed: <strong>' + gc.completed + '</strong></span>';
    html += '<span class="proj-stat">Total: <strong>' + gc.total + '</strong></span>';
    html += '</div>';

    const focus = data.current_focus || {};
    html += '<div class="proj-section"><h3>Current Focus</h3>';
    if (focus.salient_goals && focus.salient_goals.length) {
      html += '<ul class="proj-list">';
      focus.salient_goals.forEach(g => {
        html += '<li><span class="proj-goal-text">' + escapeHtml(g.description) + '</span><span class="proj-child-status">' + g.status + '</span></li>';
      });
      html += '</ul>';
    } else {
      html += '<div class="proj-empty">No active goals</div>';
    }
    html += '</div>';

    // Extra details hidden behind toggle
    html += '<div id="handoff-details" class="hidden">';
    if (data.recent_decisions && data.recent_decisions.length) {
      html += '<div class="proj-section"><h3>Recent Decisions</h3><ul class="proj-list">';
      data.recent_decisions.slice(0, 5).forEach(d => {
        html += '<li><span class="proj-goal-text">' + escapeHtml(d.decision_point) + ': ' + escapeHtml(d.selected) + '</span></li>';
      });
      html += '</ul></div>';
    }
    const issues = data.recurring_issues || {};
    if (issues.recurring_failures && issues.recurring_failures.length) {
      html += '<div class="proj-section"><h3>Recurring Issues</h3><ul class="proj-list">';
      issues.recurring_failures.slice(0, 5).forEach(f => {
        html += '<li><span class="proj-goal-text">' + escapeHtml(f.error) + '</span><span class="pattern-count">x' + f.count + '</span></li>';
      });
      html += '</ul></div>';
    }
    const struct = data.project_structure || {};
    if (struct.components && struct.components.length) {
      html += '<div class="proj-section"><h3>Project Areas</h3><div class="struc-grid">';
      struct.components.forEach(c => {
        html += '<div class="struc-card"><div class="struc-card-name">' + escapeHtml(c.name) + '</div>';
        html += '<div class="struc-card-stats"><span>' + c.file_count + ' files</span></div></div>';
      });
      html += '</div></div>';
    }
    html += '</div>';
    html += '<button id="handoff-toggle" class="proj-toggle-btn">More details</button>';

    container.innerHTML = html + '</div>';

    // Wire up the toggle after render
    setTimeout(() => {
      const toggle = document.getElementById('handoff-toggle');
      if (toggle) {
        toggle.addEventListener('click', function() {
          const details = document.getElementById('handoff-details');
          const open = details.classList.toggle('hidden');
          this.textContent = open ? 'More details' : 'Less details';
        });
      }
    }, 0);
  } else if (data.lens === 'workspace') {
    let html = '<div id="project-workspace">';

    // Summary bar
    const ws = data.workspace_summary || {};
    html += '<div id="project-goal-bar">';
    html += '<span class="proj-stat">Files: <strong>' + (ws.total_files || 0) + '</strong></span>';
    html += '<span class="proj-stat">Directories: <strong>' + (ws.directory_count || 0) + '</strong></span>';
    html += '<span class="proj-stat">Modified 24h: <strong>' + (ws.recently_modified_24h || 0) + '</strong></span>';
    html += '</div>';

    // Recent Activity
    html += '<div class="proj-section"><h3>Recent Activity</h3>';
    const recent = data.recent_activity || [];
    if (recent.length) {
      html += '<div class="proj-timeline ws-timeline">';
      recent.slice(0, 20).forEach(r => {
        html += '<div class="proj-entry ws-entry">';
        html += '<span class="ws-time">' + escapeHtml(formatTimestamp(r.modified_at)) + '</span>';
        html += '<span class="ws-ext">' + escapeHtml(r.extension || '') + '</span>';
        html += '<span class="ws-file">' + escapeHtml(r.filename) + '</span>';
        html += '<span class="ws-path">' + escapeHtml(r.path) + '</span>';
        html += '</div>';
      });
      html += '</div>';
    } else {
      html += '<div class="proj-empty">No recent workspace activity</div>';
    }
    html += '</div>';

    // Active Files
    html += '<div class="proj-section"><h3>Active Files</h3>';
    const active = data.active_files || [];
    if (active.length) {
      html += '<ul class="proj-list">';
      active.slice(0, 10).forEach(f => {
        html += '<li><span class="proj-goal-text ws-active-file">' + escapeHtml(f.filename) + '</span>';
        html += '<span class="proj-child-status">' + escapeHtml(f.path) + '</span></li>';
      });
      html += '</ul>';
    } else {
      html += '<div class="proj-empty">No active files</div>';
    }
    html += '</div>';

    // Extension breakdown
    html += '<div class="proj-section"><h3>File Types</h3>';
    const extData = ws.extension_breakdown || {};
    const extKeys = Object.keys(extData);
    if (extKeys.length) {
      html += '<ul class="proj-list ext-list">';
      extKeys.slice(0, 15).forEach(ext => {
        html += '<li><span class="pattern-error">' + escapeHtml(ext) + '</span><span class="pattern-count">' + extData[ext] + '</span></li>';
      });
      html += '</ul>';
    } else {
      html += '<div class="proj-empty">No files scanned</div>';
    }
    html += '</div>';

    container.innerHTML = html + '</div>';
  }
}

function formatTimestamp(ts) {
  if (!ts) return '';
  try {
    const d = new Date(ts);
    if (isNaN(d.getTime())) return ts.slice(0, 19);
    return d.toLocaleString();
  } catch {
    return ts.slice(0, 19);
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
