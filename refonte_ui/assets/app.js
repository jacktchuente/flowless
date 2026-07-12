/* Flowless refonte — shared interaction layer for the static mockups.
   No framework, no build step: just enough JS to make the proposal feel
   real (tabs, modals, filter chips, toasts, mock timeline rendering). */

const CATEGORY_COLOR = {
  fiction:      { fg: '#3947A0', bg: '#E4E6F8', sw: 'var(--cat-fiction)' },
  documentary:  { fg: '#1E7167', bg: '#DFF3EF', sw: 'var(--cat-documentary)' },
  news:         { fg: '#8C3F29', bg: '#F8E4DC', sw: 'var(--cat-news)' },
  comedy:       { fg: '#8C6A1F', bg: '#F8EFD9', sw: 'var(--cat-comedy)' },
  music:        { fg: '#733F8A', bg: '#F1E3F7', sw: 'var(--cat-music)' },
  live:         { fg: '#96305D', bg: '#F8DFE9', sw: 'var(--cat-live)' },
  kids:         { fg: '#2A6E93', bg: '#DFEEF7', sw: 'var(--cat-kids)' },
  filler:       { fg: '#5C6663', bg: '#E7EAE9', sw: 'var(--cat-filler)' },
};

function initTabs(root = document) {
  root.querySelectorAll('.tabs').forEach(tabbar => {
    const panelGroup = tabbar.dataset.panels ? document.getElementById(tabbar.dataset.panels) : tabbar.parentElement;
    tabbar.querySelectorAll('button[data-tab]').forEach(btn => {
      btn.addEventListener('click', () => {
        tabbar.querySelectorAll('button').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        panelGroup.querySelectorAll('.tab-panel').forEach(p => {
          p.classList.toggle('active', p.dataset.tab === btn.dataset.tab);
        });
      });
    });
  });
}

function openModal(id) {
  const scrim = document.getElementById(id);
  if (!scrim) return;
  scrim.classList.add('open');
  document.body.style.overflow = 'hidden';
}
function closeModal(el) {
  const scrim = el.closest('.modal-scrim');
  if (!scrim) return;
  scrim.classList.remove('open');
  document.body.style.overflow = '';
}
function initModals(root = document) {
  root.querySelectorAll('[data-open-modal]').forEach(btn => {
    btn.addEventListener('click', () => openModal(btn.dataset.openModal));
  });
  root.querySelectorAll('[data-close-modal]').forEach(btn => {
    btn.addEventListener('click', () => closeModal(btn));
  });
  root.querySelectorAll('.modal-scrim').forEach(scrim => {
    scrim.addEventListener('click', e => { if (e.target === scrim) closeModal(e.target); });
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') document.querySelectorAll('.modal-scrim.open').forEach(s => s.classList.remove('open'));
  });
}

function showToast(message, opts = {}) {
  const host = document.querySelector('.toast-host') || (() => {
    const h = document.createElement('div');
    h.className = 'toast-host';
    document.body.appendChild(h);
    return h;
  })();
  const t = document.createElement('div');
  t.className = 'toast';
  t.innerHTML = `<span class="dot" style="background:${opts.color || 'var(--success)'}"></span><span>${message}</span>`;
  if (opts.action) {
    const b = document.createElement('button');
    b.textContent = opts.action;
    b.addEventListener('click', () => { opts.onAction && opts.onAction(); t.remove(); });
    t.appendChild(b);
  }
  host.appendChild(t);
  setTimeout(() => { t.style.transition = 'opacity .25s'; t.style.opacity = '0'; setTimeout(() => t.remove(), 250); }, opts.duration || 4200);
}

function initFilterChips(root = document) {
  root.querySelectorAll('[data-chip-remove]').forEach(btn => {
    btn.addEventListener('click', () => btn.closest('.chip-filter')?.remove());
  });
}

/** Renders a vertical day timeline of blocks into a container.
 *  blocks: [{start:'00:00', end:'01:00', title, sub, category}] within startHour..endHour range (default 0..24)
 */
function renderTimeline(container, blocks, opts = {}) {
  const startHour = opts.startHour ?? 0;
  const endHour = opts.endHour ?? 24;
  const pxPerHour = opts.pxPerHour ?? 64;
  const totalPx = (endHour - startHour) * pxPerHour;

  const toMinutes = (t) => { const [h, m] = t.split(':').map(Number); return h * 60 + m; };

  const wrap = document.createElement('div');
  wrap.className = 'timeline-inner';
  wrap.style.position = 'relative';
  wrap.style.height = totalPx + 'px';

  for (let h = startHour; h <= endHour; h++) {
    const y = (h - startHour) * pxPerHour;
    const row = document.createElement('div');
    row.className = 'timeline-hour';
    row.style.cssText = `position:absolute; top:${y}px; left:0; right:0; display:flex; align-items:flex-start; gap:8px;`;
    row.innerHTML = `<span class="mono" style="width:44px; flex:none; font-size:11px; color:var(--slate-400); transform:translateY(-6px);">${String(h % 24).padStart(2, '0')}:00</span><span style="flex:1; border-top:1px solid var(--slate-100);"></span>`;
    wrap.appendChild(row);
  }

  const track = document.createElement('div');
  track.style.cssText = `position:absolute; top:0; left:52px; right:6px; bottom:0;`;
  blocks.forEach(b => {
    const startMin = toMinutes(b.start) - startHour * 60;
    const endMin = toMinutes(b.end) - startHour * 60;
    const top = (startMin / 60) * pxPerHour;
    const height = Math.max(((endMin - startMin) / 60) * pxPerHour - 3, 16);
    const col = CATEGORY_COLOR[b.category] || CATEGORY_COLOR.filler;
    const el = document.createElement('div');
    el.className = 'timeline-block';
    el.style.cssText = `position:absolute; top:${top}px; height:${height}px; left:0; right:0; background:${col.bg}; color:${col.fg}; border-radius:8px; padding:6px 10px; overflow:hidden; border-left:3px solid ${col.sw};`;
    el.innerHTML = `<div style="font-size:12px; font-weight:600; line-height:1.25;">${b.title}</div>${height > 34 ? `<div class="mono" style="font-size:10.5px; opacity:.85; margin-top:2px;">${b.start} – ${b.end}${b.sub ? ' · ' + b.sub : ''}</div>` : ''}`;
    if (b.tooltip) el.title = b.tooltip;
    track.appendChild(el);
  });
  wrap.appendChild(track);

  container.innerHTML = '';
  container.style.position = 'relative';
  container.style.overflowY = 'auto';
  container.appendChild(wrap);
}

function initMenus(root = document) {
  const menus = Array.from(root.querySelectorAll('details.menu'));
  menus.forEach(m => {
    m.addEventListener('toggle', () => {
      if (m.open) menus.filter(o => o !== m).forEach(o => o.open = false);
    });
  });
  document.addEventListener('click', e => {
    menus.forEach(m => { if (m.open && !m.contains(e.target)) m.open = false; });
  });
}

function startProgressSequence(container) {
  const bar = container.querySelector('.progress-track > span');
  const steps = Array.from(container.querySelectorAll('.gen-step'));
  const status = container.querySelector('.gen-status');
  const onDone = container.querySelector('.gen-done');
  steps.forEach(s => s.classList.remove('done', 'active'));
  if (onDone) onDone.style.display = 'none';
  if (bar) bar.style.width = '0%';
  let i = 0;
  function tick() {
    if (i > 0) steps[i - 1].classList.remove('active'), steps[i - 1].classList.add('done');
    if (i >= steps.length) {
      if (status) status.textContent = 'Terminé';
      if (onDone) onDone.style.display = '';
      return;
    }
    steps[i].classList.add('active');
    if (bar) bar.style.width = `${Math.round(((i + 1) / steps.length) * 100)}%`;
    if (status) status.textContent = steps[i].dataset.label || '';
    i++;
    setTimeout(tick, 650 + Math.random() * 500);
  }
  tick();
}

function initTagInputs(root = document) {
  root.querySelectorAll('.tag-input').forEach(box => {
    const input = box.querySelector('input');
    if (!input) return;
    input.addEventListener('keydown', e => {
      if (e.key === 'Enter' && input.value.trim()) {
        e.preventDefault();
        const cls = box.dataset.tagClass || '';
        const tag = document.createElement('span');
        tag.className = `tag ${cls}`;
        tag.innerHTML = `${input.value.trim()}<button type="button" aria-label="Retirer">✕</button>`;
        tag.querySelector('button').addEventListener('click', () => tag.remove());
        box.insertBefore(tag, input);
        input.value = '';
      }
    });
  });
  root.querySelectorAll('.tag button').forEach(b => {
    b.addEventListener('click', () => b.closest('.tag')?.remove());
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initModals();
  initFilterChips();
  initMenus();
  initTagInputs();
});
