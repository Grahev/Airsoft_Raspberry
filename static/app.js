let ws;
let snapshot = {};

function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(proto + '//' + location.host + '/ws');
  ws.onopen = () => document.getElementById('wsStatus').innerText = 'connected';
  ws.onclose = () => {
    document.getElementById('wsStatus').innerText = 'disconnected, retrying…';
    setTimeout(connectWS, 1000);
  };
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.type === 'snapshot') {
      snapshot.targets = msg.targets || [];
      snapshot.players = msg.players || [];
      snapshot.scoresTargets = msg.scores_targets || [];
      snapshot.scoresPlayers = msg.scores_players || [];
      snapshot.game = msg.game || null;
      renderAll();
    } else if (msg.type === 'announce') {
      snapshot.targets = msg.targets;
      renderTargets();
    } else if (msg.type === 'hit') {
      snapshot.scoresTargets = msg.scores_targets;
      snapshot.scoresPlayers = msg.scores_players;
      prependFeed(`${msg.system_id}/${msg.target_id} hit`);
      renderScores();
    }
  };
}

function api(path, opts={}) {
  return fetch(path, Object.assign({headers: {'Content-Type':'application/json'}}, opts)).then(r => r.json());
}

function renderTargets() {
  const c = document.getElementById('targets');
  c.innerHTML = '';
  snapshot.targets.forEach(t => {
    const box = document.createElement('div');
    box.className = 'border rounded-xl p-3 flex items-center justify-between';
    const left = document.createElement('div');
    left.innerHTML = `<div class="font-medium">${t.system_id}/${t.target_id}</div>
                      <div class="text-xs text-gray-500">LED ${t.led_color}, ${t.led_time_ms} ms</div>`;

    const right = document.createElement('div');
    right.className = 'flex items-center space-x-2';

    const chk = document.createElement('input');
    chk.type = 'checkbox';
    chk.checked = !!t.active;
    chk.onchange = () => api('/api/targets/select', {method:'POST', body: JSON.stringify({
      system_id: t.system_id, target_id: t.target_id, active: chk.checked
    })});

    const color = document.createElement('input');
    color.type = 'color';
    color.value = /^#/.test(t.led_color) ? t.led_color : '#ff0000';

    const dur = document.createElement('input');
    dur.type = 'number';
    dur.min = 50; dur.max = 5000; dur.step = 50;
    dur.value = t.led_time_ms || 1000;
    dur.className = 'w-24 border rounded px-2 py-1';

    const btn = document.createElement('button');
    btn.className = 'bg-gray-900 text-white rounded px-3 py-1';
    btn.innerText = 'Set LED';
    btn.onclick = () => api(`/api/targets/${t.system_id}/${t.target_id}/led`, {
      method: 'POST', body: JSON.stringify({color: color.value, time_ms: parseInt(dur.value, 10)})
    }).then(() => { /* ok */ });

    right.append(chk, color, dur, btn);
    box.append(left, right);
    c.append(box);
  });
}

function renderPlayers() {
  const c = document.getElementById('players');
  c.innerHTML = '';
  snapshot.players.forEach(p => {
    const row = document.createElement('div');
    row.className = 'flex items-center justify-between border rounded px-3 py-2';
    row.innerHTML = `<div>${p.name}</div>`;
    const del = document.createElement('button');
    del.className = 'text-red-600'; del.innerText = 'Remove';
    del.onclick = () => api('/api/players/' + p.id, {method:'DELETE'}).then(r => { snapshot.players = r.players; renderPlayers(); });
    row.appendChild(del);
    c.appendChild(row);
  });
}

function renderScores() {
  const t = document.getElementById('scoresTargets');
  const p = document.getElementById('scoresPlayers');
  t.innerHTML = '';
  p.innerHTML = '';

  (snapshot.scoresTargets || []).forEach(s => {
    const row = document.createElement('div');
    row.innerText = `${s.system_id}/${s.target_id}: ${s.hits}`;
    t.appendChild(row);
  });
  (snapshot.scoresPlayers || []).forEach(s => {
    const row = document.createElement('div');
    row.innerText = `${s.name}: ${s.hits}`;
    p.appendChild(row);
  });
}

function prependFeed(txt) {
  const f = document.getElementById('feed');
  const el = document.createElement('div');
  el.innerText = new Date().toLocaleTimeString() + ' — ' + txt;
  f.prepend(el);
  while (f.children.length > 200) f.removeChild(f.lastChild);
}

function renderGame() {
  const g = snapshot.game;
  const el = document.getElementById('gameState');
  if (!g) { el.innerText = 'No active game'; return; }
  el.innerText = `Active: ${g.mode}`;
}

function renderAll() {
  renderTargets();
  renderPlayers();
  renderScores();
  renderGame();
}

document.getElementById('addPlayerForm').addEventListener('submit', (e) => {
  e.preventDefault();
  const name = document.getElementById('playerName').value.trim();
  if (!name) return;
  api('/api/players', {method: 'POST', body: JSON.stringify({name})}).then(r => {
    snapshot.players = r.players; renderPlayers(); e.target.reset();
  });
});

document.getElementById('startGame').onclick = () => {
  const mode = document.getElementById('mode').value;
  const paramA = document.getElementById('paramA').value || '';
  const params = {};
  if (mode === 'race_to_n') {
    const n = parseInt(paramA.split('=')[1] || '10', 10);
    params.n = isFinite(n) ? n : 10;
  } else if (mode === 'time_attack') {
    const s = parseInt(paramA.split('=')[1] || '30', 10);
    params.seconds = isFinite(s) ? s : 30;
  }
  api('/api/games/start', {method:'POST', body: JSON.stringify({mode, params, player_ids: []})})
    .then(r => { snapshot.game = r.game; renderGame(); });
};

document.getElementById('stopGame').onclick = () => {
  api('/api/games/stop', {method:'POST'}).then(r => { snapshot.game = r.game; renderGame(); });
};

connectWS();
