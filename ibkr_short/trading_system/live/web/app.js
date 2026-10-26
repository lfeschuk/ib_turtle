'use strict';
// Dual-Strategy Trading Control App (Small-Cap 100%+ Gap Short & 0DTE SPX Put BWB).
// Builds every element with createElement/textContent: no HTML strings, no inline code.
(() => {
  const POLL_MS = 10000;
  const SVG_NS = 'http://www.w3.org/2000/svg';
  const root = document.getElementById('app');
  const view = {};
  let pollTimer = null;
  let bwbEnabled = true;

  // ---------------------------------------------------------------- DOM helpers
  function h(tag, props, ...kids) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(props || {})) {
      if (v === null || v === undefined || v === false) continue;
      if (k === 'class') el.className = v;
      else if (k === 'text') el.textContent = String(v);
      else if (k.startsWith('on')) { if (typeof v === 'function') el.addEventListener(k.slice(2), v); }
      else el.setAttribute(k, v === true ? '' : String(v));
    }
    for (const kid of kids.flat()) {
      if (kid === null || kid === undefined || kid === false) continue;
      el.appendChild(kid instanceof Node ? kid : document.createTextNode(String(kid)));
    }
    return el;
  }

  function svg(tag, attrs) {
    const el = document.createElementNS(SVG_NS, tag);
    for (const [k, v] of Object.entries(attrs || {})) el.setAttribute(k, String(v));
    return el;
  }

  function icon(size) {
    const s = svg('svg', { width: size, height: size, viewBox: '0 0 64 64', 'aria-hidden': 'true' });
    s.appendChild(svg('rect', { x: 0, y: 0, width: 64, height: 64, rx: 14, fill: '#1e293b' }));
    s.appendChild(svg('line', { x1: 22, y1: 12, x2: 22, y2: 50, stroke: '#ef4444', 'stroke-width': 3 }));
    s.appendChild(svg('rect', { x: 15, y: 18, width: 14, height: 24, rx: 2, fill: '#ef4444' }));
    s.appendChild(svg('polyline', { points: '36,16 44,30 50,26 56,46', fill: 'none', stroke: '#e2e8f0',
      'stroke-width': 4, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }));
    s.appendChild(svg('polyline', { points: '49,46 56,46 56,39', fill: 'none', stroke: '#e2e8f0', 'stroke-width': 4,
      'stroke-linecap': 'round', 'stroke-linejoin': 'round' }));
    return s;
  }

  const isNum = (v) => typeof v === 'number' && isFinite(v);
  const money = (v, signed) => !isNum(v) ? '–' : (signed && v > 0 ? '+' : '') +
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(v);
  const pct = (v, signed) => !isNum(v) ? '–' : (signed && v > 0 ? '+' : '') + v.toFixed(1) + '%';
  const frac = (v, signed) => isNum(v) ? pct(v * 100, signed) : '–';   // 0.034 -> 3.4%
  const price = (v) => !isNum(v) ? '–' : (v >= 1 ? v.toFixed(2) : v.toFixed(4));
  const shares = (v) => !isNum(v) ? '–' : Math.round(v).toLocaleString('en-US');
  const tone = (v) => !isNum(v) || v === 0 ? '' : (v > 0 ? 'pos' : 'neg');

  function stat(label, value, cls) {
    return h('div', { class: 'stat' }, h('div', { class: 'label', text: label }),
      h('div', { class: 'value ' + (cls || ''), text: value }));
  }

  // ---------------------------------------------------------------- API
  function csrfToken() {
    const c = document.cookie.split('; ').find((x) => x.startsWith('__Host-gs_csrf='));
    return c ? decodeURIComponent(c.slice('__Host-gs_csrf='.length)) : '';
  }

  async function api(path, body) {
    const opts = { credentials: 'same-origin', headers: { Accept: 'application/json' } };
    if (body !== undefined) {
      opts.method = 'POST';
      opts.headers['Content-Type'] = 'application/json';
      opts.headers['X-CSRF-Token'] = csrfToken();
      opts.body = JSON.stringify(body);
    }
    const res = await fetch(path, opts);
    let data = {};
    try { data = await res.json(); } catch (_) { data = {}; }
    const passwordCheck = body !== undefined && Object.prototype.hasOwnProperty.call(body, 'password');
    if (res.status === 401 && !passwordCheck) {
      showLogin('Signed out. Please sign in again.');
      throw new Error('Signed out');
    }
    if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : (data.error || 'Request failed'));
    return data;
  }

  // ---------------------------------------------------------------- dialogs
  function toast(message, kind) {
    const t = h('div', { class: 'toast ' + (kind || ''), role: 'status', text: message });
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 3500);
  }

  function ask({ title, message, confirmText, danger, password }) {
    return new Promise((resolve) => {
      const pw = password ? h('input', { type: 'password', autocomplete: 'current-password',
        placeholder: 'App password', maxlength: 256, required: true }) : null;
      const cancel = h('button', { class: 'btn', type: 'button', text: 'Cancel' });
      const ok = h('button', { class: 'btn ' + (danger ? 'danger' : 'primary'), type: 'submit', text: confirmText });
      const box = h('form', { class: 'modal', role: 'dialog', 'aria-modal': 'true' },
        h('h2', { text: title }), h('p', { text: message }), pw, h('div', { class: 'row' }, cancel, ok));
      const overlay = h('div', { class: 'overlay' }, box);
      const done = (value) => { overlay.remove(); resolve(value); };
      cancel.addEventListener('click', () => done(null));
      overlay.addEventListener('click', (e) => { if (e.target === overlay) done(null); });
      box.addEventListener('submit', (e) => { e.preventDefault(); done(password ? pw.value : true); });
      document.body.appendChild(overlay);
      (pw || ok).focus();
    });
  }

  // ---------------------------------------------------------------- screens
  function showLogin(message) {
    stopPolling();
    for (const k of Object.keys(view)) delete view[k];
    const pw = h('input', { type: 'password', autocomplete: 'current-password', placeholder: 'App password',
      maxlength: 256, required: true });
    const err = h('p', { class: 'error', text: message || '' });
    const btn = h('button', { class: 'btn primary wide', type: 'submit', text: 'Sign in' });
    const form = h('form', { class: 'login' }, h('div', { class: 'logo' }, icon(72)),
      h('h1', { text: 'Trading Control' }),
      h('p', { class: 'muted', text: 'Gap Short ($100k) · 0DTE Put BWB ($100k)' }), pw, btn, err);
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      btn.disabled = true;
      err.textContent = '';
      try {
        await api('/api/login', { password: pw.value });
        pw.value = '';
        showMain();
      } catch (ex) {
        err.textContent = ex.message;
      } finally {
        btn.disabled = false;
      }
    });
    root.className = '';
    root.replaceChildren(form);
    pw.focus();
  }

  const STRATEGIES = [
    ['both', 'Both ($200k)'],
    ['gapshort', 'Gap Short ($100k)'],
    ['bwb', '0DTE BWB ($100k)'],
  ];
  const TABS = [['now', 'Now'], ['report', 'Report'], ['activity', 'Activity']];
  let currentStrategy = 'both';
  let currentTab = TABS.some(([k]) => '#' + k === window.location.hash) ? window.location.hash.slice(1) : 'now';

  function selectStrategy(strat) {
    currentStrategy = strat;
    for (const [k, b] of Object.entries(view.stratButtons || {})) {
      b.className = 'strat-btn' + (k === strat ? ' on' : '');
    }
    if (view.tabbar) view.tabbar.hidden = (strat === 'both');
    updatePaneVisibility();
    refresh();
  }

  function selectTab(key) {
    currentTab = key;
    for (const [k, b] of Object.entries(view.tabButtons || {})) {
      b.className = 'tab' + (k === key ? ' on' : '');
      b.setAttribute('aria-selected', k === key ? 'true' : 'false');
    }
    updatePaneVisibility();
    history.replaceState(null, '', '#' + key);
    window.scrollTo(0, 0);
  }

  function updatePaneVisibility() {
    if (!view.panes) return;
    if (currentStrategy === 'both') {
      view.panes.overview.hidden = false;
      view.panes.now.hidden = true;
      view.panes.report.hidden = true;
      view.panes.activity.hidden = true;
    } else {
      view.panes.overview.hidden = true;
      for (const [k, pane] of Object.entries(view.panes)) {
        if (k === 'overview') continue;
        pane.hidden = k !== currentTab;
      }
    }
  }

  function showMain() {
    view.badge = h('span', { class: 'badge' });
    view.dot = h('span', { class: 'dot', title: 'TWS connection' });
    view.state = h('span', { class: 'state' });
    view.brandTitle = h('span', { text: 'Portfolio Control' });

    view.stratButtons = {};
    const stratbar = h('div', { class: 'strats', role: 'navigation', 'aria-label': 'Strategy selector' });
    for (const [key, label] of STRATEGIES) {
      if (!bwbEnabled && key !== 'gapshort') continue;
      view.stratButtons[key] = h('button', {
        class: 'strat-btn' + (key === currentStrategy ? ' on' : ''),
        type: 'button',
        text: label,
        onclick: () => selectStrategy(key),
      });
      stratbar.appendChild(view.stratButtons[key]);
    }
    if (!bwbEnabled) currentStrategy = 'gapshort';

    view.tabButtons = {};
    view.tabbar = h('nav', { class: 'tabs', role: 'tablist' });
    for (const [key, label] of TABS) {
      view.tabButtons[key] = h('button', { class: 'tab', type: 'button', role: 'tab', text: label, onclick: () => selectTab(key) });
      view.tabbar.appendChild(view.tabButtons[key]);
    }

    const top = h('header', { class: 'top' },
      h('div', { class: 'top-row' }, h('div', { class: 'brand' }, icon(26), view.brandTitle),
        h('div', { class: 'top-right' }, view.badge, view.dot, view.state)),
      bwbEnabled ? stratbar : null,
      view.tabbar);

    for (const k of ['ovCombined', 'ovGap', 'ovBwb', 'account', 'bwbStruct', 'controls', 'positions', 'signals',
                     'day', 'edge', 'compare', 'equity', 'orders', 'trades', 'events']) {
      view[k] = h('section', { class: 'card' });
    }
    view.panes = {
      overview: h('div', { class: 'pane' }, view.ovCombined, view.ovGap, view.ovBwb),
      now: h('div', { class: 'pane' }, view.account, view.bwbStruct, view.controls, view.positions, view.signals),
      report: h('div', { class: 'pane' }, view.day, view.edge, view.compare, view.equity),
      activity: h('div', { class: 'pane' }, view.orders, view.trades, view.events),
    };
    view.updated = h('span', { class: 'muted' });
    const foot = h('footer', { class: 'foot' }, view.updated,
      h('button', { class: 'link', type: 'button', text: 'Sign out', onclick: signOut }));
    root.className = '';
    root.replaceChildren(top, h('main', { class: 'content' },
      view.panes.overview, view.panes.now, view.panes.report, view.panes.activity, foot));
    selectStrategy(currentStrategy);
    selectTab(currentTab);
    startPolling();
  }

  // ---------------------------------------------------------------- renderers
  const STATE_TEXT = { running: 'Running', paused: 'Paused', connecting: 'Connecting', disconnected: 'Offline',
    error: 'Error', starting: 'Starting' };

  function sparkSvg(rows) {
    const vals = (rows || []).map((r) => r.nlv).filter(isNum);
    if (vals.length < 2) return null;
    const lo = Math.min(...vals), hi = Math.max(...vals), span = hi - lo || 1;
    const pts = vals.map((v, i) => (i / (vals.length - 1) * 100).toFixed(2) + ',' + (38 - (v - lo) / span * 34).toFixed(2)).join(' ');
    const chart = svg('svg', { class: 'spark', viewBox: '0 0 100 40', preserveAspectRatio: 'none', role: 'img', 'aria-label': 'Equity chart' });
    chart.appendChild(svg('line', { class: 'base', x1: 0, y1: 39.5, x2: 100, y2: 39.5 }));
    chart.appendChild(svg('polyline', { points: pts }));
    return chart;
  }

  function renderOverview(ov) {
    const comb = ov.combined || {};
    const gs = (ov.strategies && ov.strategies.gapshort) || {};
    const bwb = (ov.strategies && ov.strategies.bwb) || {};
    const gsSt = gs.status || {};
    const bwbSt = bwb.status || {};

    view.brandTitle.textContent = 'Both Strategies ($200k)';
    view.badge.textContent = (gsSt.mode || 'paper').toUpperCase();
    view.badge.className = 'badge mode-' + (gsSt.mode || 'paper');
    const conn = Boolean(gsSt.connected || bwbSt.connected);
    view.dot.className = 'dot ' + (conn ? 'ok' : 'bad');
    view.state.textContent = '2 Bots Active';

    // 1. Combined $200k Portfolio Card
    view.ovCombined.replaceChildren(
      h('h2', {}, h('span', { text: 'Combined Paper Portfolio' }), h('span', { text: 'Base ' + money(comb.initial_capital || 200000) })),
      h('div', { class: 'big', text: money(comb.net_liquidation) }),
      h('div', { class: 'grid' }, [
        stat('Total Return', pct(comb.total_return_pct, true), tone(comb.total_return_pct)),
        stat('Today P&L', money(comb.day_pnl, true), tone(comb.day_pnl)),
        stat('Active Positions', String(comb.positions || 0)),
        stat('Allocation', '2 × $100,000 Independent'),
      ]),
      h('div', { class: 'note', text: 'Each strategy trades and compounds its own independent $100,000 paper-trading ledger.' })
    );

    // 2. Strategy 1 Card: Small-Cap 100%+ Gap Short ($100k)
    const gsKids = [
      h('h2', {}, h('span', { text: 'Strategy 1 · Small-Cap 100%+ Gap Short' }),
        h('span', { text: STATE_TEXT[gsSt.state] || gsSt.state || '' })),
      h('div', { class: 'big', text: money(gsSt.net_liquidation) }),
      h('div', { class: 'grid' }, [
        stat('Return vs $100k', pct(gsSt.total_return_pct, true), tone(gsSt.total_return_pct)),
        stat('Today', money(gsSt.day_pnl, true), tone(gsSt.day_pnl)),
        stat('From Peak', pct(gsSt.drawdown_pct, true), tone(gsSt.drawdown_pct)),
        stat('Open Shorts', isNum(gsSt.positions) ? gsSt.positions + ' / ' + gsSt.max_positions : '0'),
      ]),
    ];
    const gsSpark = sparkSvg(gs.equity);
    if (gsSpark) gsKids.push(gsSpark);
    if (gsSt.last_decision && gsSt.last_decision.day) {
      const d = gsSt.last_decision;
      gsKids.push(h('div', { class: 'note', text: 'Last decision ' + d.day + ': ' + d.candidates + ' signals, ' + d.placed + ' shorts' }));
    }
    gsKids.push(h('div', { class: 'item-actions' },
      h('button', { class: 'btn primary small', type: 'button', text: 'Open Gap Short ($100k) →',
        onclick: () => selectStrategy('gapshort') })));
    view.ovGap.replaceChildren(...gsKids);

    // 3. Strategy 2 Card: 0DTE SPX Put BWB ($100k)
    if (bwbSt && bwbSt.strategy === 'bwb') {
      const sz = bwbSt.sizing || {};
      const bp = bwbSt.bwb_plan || {};
      const bwbKids = [
        h('h2', {}, h('span', { text: 'Strategy 2 · 0DTE SPX Put BWB' }),
          h('span', { text: STATE_TEXT[bwbSt.state] || bwbSt.state || '' })),
        h('div', { class: 'big', text: money(bwbSt.net_liquidation) }),
        h('div', { class: 'grid' }, [
          stat('Return vs $100k', pct(bwbSt.total_return_pct, true), tone(bwbSt.total_return_pct)),
          stat('Today', money(bwbSt.day_pnl, true), tone(bwbSt.day_pnl)),
          stat('From Peak', pct(bwbSt.drawdown_pct, true), tone(bwbSt.drawdown_pct)),
          stat('Earned Kelly %', pct(bwbSt.collat_pct) + ' (7.5%→20%)'),
          stat('House Cushion', money(sz.house_cushion_dollars, true), tone(sz.house_cushion_dollars)),
          stat('F1 Term Gate', bp.day ? (bp.f1_pass ? 'PASS (VIX1D < VIX)' : 'GATED (Cash)') : 'Waiting'),
        ]),
        h('div', { class: 'ramp-track' },
          h('div', { class: 'ramp-fill', style: 'width:' + Math.round(bwbSt.ramp_progress_pct || 0) + '%' })),
      ];
      if (bp.day && bp.k_mid) {
        bwbKids.push(h('div', { class: 'note',
          text: bp.day + ' ' + bp.trade_key + ' · Credit ' + price(bp.net_credit_pts) + ' pts · BE ' + Math.round(bp.k_be) + ' · ' + (sz.house_cushion_dollars > 0 ? 'House-money active' : 'Principal shield active') }));
      }
      const bwbSpark = sparkSvg(bwb.equity);
      if (bwbSpark) bwbKids.push(bwbSpark);
      bwbKids.push(h('div', { class: 'item-actions' },
        h('button', { class: 'btn primary small', type: 'button', text: 'Open 0DTE BWB ($100k) →',
          onclick: () => selectStrategy('bwb') })));
      view.ovBwb.hidden = false;
      view.ovBwb.replaceChildren(...bwbKids);
    } else {
      view.ovBwb.hidden = true;
    }
  }

  function renderStatus(s) {
    const isBwb = s.strategy === 'bwb';
    view.brandTitle.textContent = isBwb ? '0DTE Put BWB ($100k)' : 'Gap Short ($100k)';
    view.badge.textContent = (s.mode || '').toUpperCase();
    view.badge.className = 'badge mode-' + s.mode;
    view.dot.className = 'dot ' + (s.connected ? 'ok' : 'bad');
    view.state.textContent = STATE_TEXT[s.state] || s.state;

    const kids = [h('h2', {}, h('span', { text: isBwb ? '0DTE BWB Ledger ($100k Base)' : 'Gap Short Ledger ($100k Base)' }),
      h('span', { text: s.account || '' }))];
    kids.push(h('div', { class: 'big', text: money(s.net_liquidation) }));

    if (isBwb) {
      const sz = s.sizing || {};
      const grid = [
        stat('Return vs $100k', pct(s.total_return_pct, true), tone(s.total_return_pct)),
        stat('Today', money(s.day_pnl, true), tone(s.day_pnl)),
        stat('From peak', pct(s.drawdown_pct, true), tone(s.drawdown_pct)),
        stat('Dip below $100k', pct(s.initial_dd_pct, true), tone(s.initial_dd_pct)),
        stat('Earned Kelly %', pct(s.collat_pct) + ' (7.5%→20%)'),
        stat('House cushion', money(sz.house_cushion_dollars, true) + ' (' + pct(sz.house_cushion_pct, true) + ')', tone(sz.house_cushion_dollars)),
      ];
      kids.push(h('div', { class: 'grid' }, grid));
      kids.push(h('div', { class: 'ramp-track' },
        h('div', { class: 'ramp-fill', style: 'width:' + Math.round(s.ramp_progress_pct || 0) + '%' })));
      kids.push(h('div', { class: 'note', text: 'Earned-Money Kelly Ramp: starts at 7.5% collateral to protect your initial $100k, and scales with 50% of earned profits up to the 20.0% cap at +33% gain (+4.5%/yr T-Bill yield on cash).' }));
    } else {
      const grid = [
        stat('Return vs $100k', pct(s.total_return_pct, true), tone(s.total_return_pct)),
        stat('Today', money(s.day_pnl, true), tone(s.day_pnl)),
        stat('From peak', pct(s.drawdown_pct, true), tone(s.drawdown_pct)),
        stat('Open shorts', isNum(s.positions) ? s.positions + ' / ' + s.max_positions : '–'),
        stat('Margin used', pct(s.margin_use_pct)),
      ];
      const share = (m) => { const n = Math.round(1 / m); return Math.abs(1 / m - n) < 0.05 ? '1/' + n : m.toFixed(2); };
      if (s.sizing && s.sizing.mode === 'perbet_dd') {
        grid.push(stat('Room before limit', pct(s.cushion_pct)));
        grid.push(stat('Sizing', 'Per-bet Kelly, ' + Math.round(s.sizing.dd_limit * 100) + '% limit'));
      } else if (s.sizing && s.sizing.mode === 'perbet') {
        grid.push(stat('Sizing', 'Per-bet Kelly × ' + share(s.sizing.kelly_mult)));
      } else if (s.sizing && s.sizing.mode === 'perbet_house') {
        grid.push(stat('Profit this year', pct(s.house_pct) + ' of account'));
        grid.push(stat('Sizing', 'Kelly × ' + share(s.sizing.kelly_mult) + ', profit × ' + share(s.sizing.profit_kelly_mult)));
      } else if (s.sizing) {
        grid.push(stat('Sizing', (s.sizing.static_pct * 100).toFixed(1) + '% per short'));
      }
      kids.push(h('div', { class: 'grid' }, grid));
    }

    if (s.demo) kids.push(h('div', { class: 'note', text: 'Demo day ' + s.demo.day + ' (' + s.demo.done + ' of ' + s.demo.total + ')' }));
    else if (s.next && s.next.name) {
      const mins = s.next.in_minutes;
      const inText = isNum(mins) ? ' (in ' + (mins >= 60 ? Math.floor(mins / 60) + 'h ' : '') + (mins % 60) + 'm)' : '';
      kids.push(h('div', { class: 'note', text: 'Next: ' + s.next.name + ' ' + s.next.at + inText }));
    }
    if (s.last_decision && s.last_decision.day) {
      const d = s.last_decision;
      const txt = isBwb
        ? 'Last check ' + d.day + ': ' + (d.placed ? 'Placed 0DTE BWB' : 'Skipped') + (d.note ? ' (' + d.note + ')' : '')
        : 'Last close ' + d.day + ': ' + d.candidates + ' signals, ' + d.placed + ' shorts, ' + d.exits + ' day-3 exits' + (d.note ? ' (' + d.note + ')' : '');
      kids.push(h('div', { class: 'note', text: txt }));
    }
    if (s.mode === 'shadow') kids.push(h('div', { class: 'note', text: 'Shadow mode: read-only, the bot only logs what it would do.' }));
    if (s.problem) kids.push(h('div', { class: 'warn', text: s.problem }));
    view.account.replaceChildren(...kids);

    // Render BWB Structure Card when viewing Strategy 2
    if (isBwb && s.bwb_plan) {
      const bp = s.bwb_plan;
      view.bwbStruct.hidden = false;
      view.bwbStruct.replaceChildren(
        h('h2', {}, h('span', { text: '0DTE Put BWB Structure' }), h('span', { text: bp.day || '' })),
        h('div', { class: 'grid' }, [
          stat('Causal F1 Gate', bp.f1_pass ? 'PASS (VIX1D < VIX)' : 'GATED (Sit in Cash)', bp.f1_pass ? 'pos' : 'neg'),
          stat('SPX Open / 1D IV', price(bp.spot_open) + ' · ' + pct(bp.iv1d_pct)),
          stat('+1 Upper Long Put', Math.round(bp.k_hi) + 'P (W1=' + bp.w1_pts.toFixed(1) + 'pt)'),
          stat('-2 Middle Short Puts', Math.round(bp.k_mid) + 'P (' + Math.round(bp.delta_mid * 100) + 'Δ tent peak)'),
          stat('+1 Lower Long Put', Math.round(bp.k_lo) + 'P (W2=' + bp.w2_pts.toFixed(1) + 'pt)'),
          stat('Lower Breakeven', Math.round(bp.k_be) + ' (W_risk=' + bp.w_risk_pts.toFixed(1) + 'pt)'),
          stat('Net Credit', price(bp.net_credit_pts) + ' pts ($' + Math.round(bp.net_credit_pts * 100) + '/ct)'),
          stat('Target Size', bp.contracts.toFixed(2) + 'x (' + money(bp.collat_budget) + ' collat)'),
        ]),
        h('div', { class: 'note', text: bp.f1_reason || '' })
      );
    } else {
      view.bwbStruct.hidden = true;
    }
  }

  function renderControls(s, positions) {
    const isBwb = s.strategy === 'bwb';
    const paused = s.state === 'paused';
    const real = positions.filter((p) => !p.virtual);
    const pauseBtn = h('button', { class: 'btn ' + (paused ? 'primary' : ''), type: 'button',
      text: paused ? 'Resume trading' : (isBwb ? 'Pause new BWB' : 'Pause new shorts'), onclick: () => togglePause(paused) });
    const flatBtn = h('button', { class: 'btn danger', type: 'button', text: 'Close all',
      disabled: !real.length, onclick: flattenAll });
    view.controls.replaceChildren(h('h2', { text: 'Controls (' + (isBwb ? '0DTE BWB' : 'Gap Short') + ')' }),
      h('div', { class: 'row' }, pauseBtn, flatBtn),
      h('div', { class: 'note', text: paused
        ? 'Paused: no new entries for this strategy.'
        : 'Controls apply only to this strategy; the other $100k strategy continues unaffected.' }));
  }

  function renderPositions(list) {
    const isBwb = currentStrategy === 'bwb';
    const virtual = list.length > 0 && list.every((p) => p.virtual);
    const title = isBwb ? 'Open 0DTE BWB Spread' : (virtual ? 'Virtual shorts' : 'Open shorts');
    const kids = [h('h2', {}, h('span', { text: title }), h('span', { text: String(list.length) }))];
    if (!list.length) kids.push(h('div', { class: 'empty', text: isBwb ? 'No open 0DTE BWB spread (cash settles at 16:00 ET)' : 'No open shorts' }));
    for (const p of list) {
      kids.push(h('div', { class: 'item' },
        h('div', { class: 'item-head' },
          h('span', {}, h('span', { class: 'sym', text: p.symbol }), p.setups ? h('span', { class: 'chip', text: p.setups }) : null,
            p.virtual ? h('span', { class: 'chip would', text: 'virtual' }) : null),
          h('span', { class: tone(p.pnl), text: money(p.pnl, true) + '  ' + pct(p.pnl_pct, true) })),
        h('div', { class: 'sub', text: shares(p.shares) + (isBwb ? ' spread(s), credit ' : ' sh, entry ') + price(p.entry) + ', mark ' + price(p.last) }),
        h('div', { class: 'sub', text: (isBwb ? 'Floor ' : 'Stop ') + price(p.stop) + ' · ' + (isBwb ? 'tent peak ' : 'target ') + price(p.target) + (isNum(p.day) ? ' · day ' + p.day + ' of ' + p.hold_days : '') }),
        p.virtual ? null : h('div', { class: 'item-actions' }, h('button', { class: 'btn danger small', type: 'button', text: 'Close',
          onclick: () => closeOne(p.symbol) }))));
    }
    if (virtual) kids.push(h('div', { class: 'note', text: 'Shadow mode: what the bot would hold, priced at the last close it recorded.' }));
    view.positions.replaceChildren(...kids);
  }

  function renderSignals(data) {
    const kids = [h('h2', {}, h('span', { text: 'Signals' }), h('span', { text: data.day || '' }))];
    if (!data.signals || !data.signals.length) kids.push(h('div', { class: 'empty', text: 'No signals yet' }));
    for (const s of data.signals || []) {
      const cls = s.action === 'placed' ? 'placed' : (s.action === 'would place' ? 'would' : (s.action === 'error' ? 'error' : ''));
      kids.push(h('div', { class: 'item' },
        h('div', { class: 'item-head' },
          h('span', {}, h('span', { class: 'sym', text: s.symbol }), h('span', { class: 'chip', text: s.setups || '' })),
          h('span', { class: 'chip ' + cls, text: s.action })),
        h('div', { class: 'sub', text: 'Score ' + (isNum(s.score) ? s.score.toFixed(2) : '–') + (s.notional ? ' · ' + money(s.notional) : '') + ' · ' + (s.detail || '') })));
    }
    view.signals.replaceChildren(...kids);
  }

  function renderEquity(rows) {
    const kids = [h('h2', { text: 'Equity' })];
    const vals = rows.map((r) => r.nlv).filter(isNum);
    if (vals.length < 2) {
      kids.push(h('div', { class: 'empty', text: 'Builds up after a few trading days' }));
    } else {
      const lo = Math.min(...vals), hi = Math.max(...vals), span = hi - lo || 1;
      const pts = vals.map((v, i) => (i / (vals.length - 1) * 100).toFixed(2) + ',' + (38 - (v - lo) / span * 34).toFixed(2)).join(' ');
      const chart = svg('svg', { class: 'spark', viewBox: '0 0 100 40', preserveAspectRatio: 'none', role: 'img', 'aria-label': 'Equity chart' });
      chart.appendChild(svg('line', { class: 'base', x1: 0, y1: 39.5, x2: 100, y2: 39.5 }));
      chart.appendChild(svg('polyline', { points: pts }));
      const change = (vals[vals.length - 1] / vals[0] - 1) * 100;
      kids.push(chart, h('div', { class: 'note', text: rows[0].day + ' → ' + rows[rows.length - 1].day + ': ' + pct(change, true) + ' (low ' + money(lo) + ', high ' + money(hi) + ')' }));
    }
    view.equity.replaceChildren(...kids);
  }

  // ---------------------------------------------------------------- end-of-day report
  const VERDICT = { ok: 'On track', watch: 'Watch', bad: 'Problem', early: 'Too early' };
  const EXEC_VERDICT = { ok: 'Good', watch: 'Watch', bad: 'Problem', early: 'Too early' };

  function pill(verdict, labels) {
    return h('span', { class: 'pill ' + (verdict || 'early'), text: (labels || VERDICT)[verdict] || verdict || '' });
  }

  function legend(items) {
    return h('div', { class: 'legend' }, items.map(([cls, label]) => h('span', { class: 'key' }, h('span', { class: 'sw ' + cls }), label)));
  }

  function cumChart(series, shadow) {
    const W = 100, H = 60, n = series.length;
    const x = (i) => (i / (n - 1) * W).toFixed(2);
    const vals = [0];
    for (const s of series) {
      vals.push(s.theory, s.expected + 2 * s.sd, s.expected - 2 * s.sd);
      if (!shadow && isNum(s.actual)) vals.push(s.actual);
    }
    const lo = Math.min(...vals), hi = Math.max(...vals), span = hi - lo || 1;
    const y = (v) => (H - 2 - (v - lo) / span * (H - 4)).toFixed(2);
    const c = svg('svg', { class: 'chart', viewBox: '0 0 ' + W + ' ' + H, preserveAspectRatio: 'none', role: 'img',
      'aria-label': 'Profit since the start: actual, backtest and expected, with the normal range' });
    for (const [k, cls] of [[2, 'band2'], [1, 'band1']]) {
      const up = series.map((s, i) => x(i) + ',' + y(s.expected + k * s.sd));
      const down = series.map((s, i) => x(i) + ',' + y(s.expected - k * s.sd)).reverse();
      c.appendChild(svg('polygon', { class: cls, points: up.concat(down).join(' ') }));
    }
    c.appendChild(svg('line', { class: 'zero', x1: 0, x2: W, y1: y(0), y2: y(0) }));
    const line = (key, cls) => {
      const pts = series.map((s, i) => (isNum(s[key]) ? x(i) + ',' + y(s[key]) : null)).filter(Boolean);
      if (pts.length > 1) c.appendChild(svg('polyline', { class: cls, points: pts.join(' ') }));
    };
    line('expected', 'exp');
    line('theory', 'theory');
    if (!shadow) line('actual', 'actual');
    return c;
  }

  function dailyChart(daily, shadow) {
    const W = 100, H = 44, n = daily.length, slot = W / n;
    const keys = shadow ? ['theory'] : ['actual', 'theory'];
    const vals = [];
    for (const d of daily) for (const k of keys.concat(['expected'])) if (isNum(d[k])) vals.push(Math.abs(d[k]));
    const m = Math.max(1, ...vals);
    const y = (v) => H / 2 - v / m * (H / 2 - 1);
    const c = svg('svg', { class: 'bars', viewBox: '0 0 ' + W + ' ' + H, preserveAspectRatio: 'none', role: 'img',
      'aria-label': 'Daily profit: actual and backtest' });
    c.appendChild(svg('line', { class: 'zero', x1: 0, x2: W, y1: H / 2, y2: H / 2 }));
    daily.forEach((d, i) => {
      const width = slot * (shadow ? 0.6 : 0.34);
      keys.forEach((k, j) => {
        if (!isNum(d[k])) return;
        const top = Math.min(y(d[k]), H / 2), height = Math.max(Math.abs(y(d[k]) - H / 2), 0.3);
        c.appendChild(svg('rect', { class: 'bar-' + k, x: (i * slot + slot * 0.13 + j * width * 1.1).toFixed(2), y: top.toFixed(2),
          width: width.toFixed(2), height: height.toFixed(2) }));
      });
      if (isNum(d.expected)) {
        c.appendChild(svg('line', { class: 'exp-tick', x1: (i * slot + slot * 0.08).toFixed(2), x2: ((i + 1) * slot - slot * 0.08).toFixed(2),
          y1: y(d.expected).toFixed(2), y2: y(d.expected).toFixed(2) }));
      }
    });
    return c;
  }

  function eventItem(e) {
    const chipText = e.type === 'new' ? 'new' : e.type === 'exit' ? (e.reason || 'exit') : e.type === 'missed' ? 'missed' : 'differs';
    const chipCls = e.type === 'new' ? 'placed' : e.type === 'missed' ? 'error' : (e.type === 'diverged' ? 'warn' : '');
    const head = (right, cls) => h('div', { class: 'item-head' },
      h('span', {}, h('span', { class: 'sym', text: e.symbol }), h('span', { class: 'chip ' + chipCls, text: chipText }),
        e.virtual ? h('span', { class: 'chip would', text: 'virtual' }) : null),
      h('span', { class: cls || 'muted', text: right }));
    let right = '', cls = 'muted', sub = '';
    if (e.type === 'new') {
      right = 'edge ' + frac(e.exp_ret, true);
      sub = e.virtual ? 'Would enter ' + shares(e.shares) + ', ref ' + price(e.close)
        : 'Entered ' + shares(e.shares) + ' at ' + price(e.fill);
    } else if (e.type === 'exit') {
      right = money(e.pnl, true);
      cls = tone(e.pnl);
      sub = e.virtual ? 'Settled at ' + price(e.fill) + ', ' + frac(e.ret, true)
        : 'Settled · backtest ' + (e.model_open ? 'still open' : '(' + e.model_reason + '), fills ' + money(e.gap, true));
    } else if (e.type === 'missed') {
      right = 'edge ' + frac(e.exp_ret, true);
      sub = 'Not entered: ' + e.note;
    } else {
      right = 'check';
      cls = 'warn-text';
      sub = 'The backtest exited at the ' + e.reason + ', but the real position is still open.';
    }
    return h('div', { class: 'item' }, head(right, cls), h('div', { class: 'sub', text: sub }));
  }

  function renderDay(r) {
    const head = h('h2', {}, h('span', { text: 'Day report' }), h('span', { text: r.day || '' }));
    if (!r.day || !r.today) {
      view.day.replaceChildren(head, h('div', { class: 'empty', text: 'Appears after the first close the bot records (16:15 New York time).' }));
      return;
    }
    const t = r.today, shadow = r.mode === 'shadow';
    const grid = shadow
      ? [stat('Shadow book', money(t.theory, true), tone(t.theory)), stat('Expected', money(t.expected, true), tone(t.expected))]
      : [stat('Actual', money(t.actual, true), tone(t.actual)), stat('Backtest', money(t.theory, true), tone(t.theory)),
        stat('Fills vs backtest', money(t.gap, true), tone(t.gap)), stat('Expected', money(t.expected, true), tone(t.expected))];
    const kids = [head, h('div', { class: 'grid' }, grid)];
    const events = r.events || [];
    if (events.length) kids.push(h('div', { class: 'sub-h', text: 'Today' }), ...events.map(eventItem));
    else kids.push(h('div', { class: 'note', text: 'No new entries or exits on this day.' }));
    if ((r.daily || []).length >= 2) {
      kids.push(h('div', { class: 'sub-h', text: 'Last ' + r.daily.length + ' days' }), dailyChart(r.daily, shadow),
        legend(shadow ? [['theory', 'Shadow book'], ['exp', 'Expected']] : [['actual', 'Actual'], ['theory', 'Backtest'], ['exp', 'Expected']]));
    }
    view.day.replaceChildren(...kids);
  }

  function renderEdge(r) {
    const ed = r.edge || {}, ex = r.execution || {}, mi = r.missed || {}, shadow = r.mode === 'shadow';
    const kids = [h('h2', {}, h('span', { text: 'Edge check' }), h('span', { text: (ed.n || 0) + ' trades' }))];
    kids.push(h('div', { class: 'verdict' }, pill(ed.verdict), h('span', { text: ed.text || '' })));
    const series = r.series || [];
    if (series.length >= 2) {
      const last = series[series.length - 1];
      kids.push(h('div', { class: 'sub-h', text: 'Profit since the start' }), cumChart(series, shadow),
        legend((shadow ? [] : [['actual', 'Actual ' + money(last.actual, true)]]).concat([
          ['theory', (shadow ? 'Shadow book ' : 'Backtest ') + money(last.theory, true)],
          ['exp', 'Expected ' + money(last.expected, true)],
          ['band', 'Normal range ' + money(last.expected - 2 * last.sd, true) + ' to ' + money(last.expected + 2 * last.sd, true)]])));
    } else {
      kids.push(h('div', { class: 'empty', text: 'The chart builds up after a few closes.' }));
    }
    const grid = [stat('Per trade, backtest', frac(ed.live_mean, true), tone(ed.live_mean)), stat('Expected', frac(ed.expected_mean, true))];
    if (isNum(ed.rank)) grid.push(stat('Typical-trade rank', Math.round(ed.rank * 100) + ' (normal ' + Math.round(ed.rank_lo * 100) + '–' + Math.round(ed.rank_hi * 100) + ')'));
    if (ed.ci) grid.push(stat('95% range per trade', frac(ed.ci[0], true) + ' to ' + frac(ed.ci[1], true)));
    kids.push(h('div', { class: 'grid' }, grid));
    if (!shadow) {
      kids.push(h('div', { class: 'sub-h', text: 'Execution' }), h('div', { class: 'verdict' }, pill(ex.verdict, EXEC_VERDICT), h('span', { text: ex.text || '' })));
      if (ex.n) {
        kids.push(h('div', { class: 'grid' }, stat('Per trade, actual', frac(ex.actual_ret, true), tone(ex.actual_ret)),
          stat('Same trades, backtest', frac(ex.backtest_ret, true), tone(ex.backtest_ret)),
          stat('Fills vs backtest', frac(ex.gap, true) + ' per trade', tone(ex.gap)), stat('In dollars', money(ex.gap_usd, true), tone(ex.gap_usd))));
      }
    }
    if (mi.n) {
      const reasons = Object.entries(mi.reasons || {}).map(([k, v]) => v + ' ' + k).join(', ');
      kids.push(h('div', { class: 'note', text: 'Missed signals: ' + mi.n + ' (' + reasons + '). The backtest made ' + money(mi.theory_usd, true) + ' on them.' }));
    }
    view.edge.replaceChildren(...kids);
  }

  function renderCompare(r) {
    const list = r.trades || [];
    const kids = [h('h2', {}, h('span', { text: 'Trades vs backtest' }), h('span', { text: list.length ? 'last ' + list.length : '' }))];
    if (!list.length) kids.push(h('div', { class: 'empty', text: 'No closed trades yet' }));
    for (const t of list) {
      const main = isNum(t.actual) ? t.actual : t.backtest;
      const bits = ['backtest ' + frac(t.backtest, true) + ' (' + (t.backtest_reason || '') + ')'];
      if (isNum(t.actual)) bits.unshift('actual ' + frac(t.actual, true));
      if (isNum(t.gap)) bits.push('fills ' + frac(t.gap, true));
      bits.push('expected ' + frac(t.expected, true));
      kids.push(h('div', { class: 'item' },
        h('div', { class: 'item-head' },
          h('span', {}, h('span', { class: 'sym', text: t.symbol }), h('span', { class: 'chip', text: t.setups }),
            t.virtual ? h('span', { class: 'chip would', text: 'virtual' }) : null),
          h('span', { class: tone(main), text: frac(main, true) })),
        h('div', { class: 'sub', text: t.day + ' → ' + (t.exit_day || '') }),
        h('div', { class: 'sub', text: bits.join(' · ') })));
    }
    view.compare.replaceChildren(...kids);
  }

  function renderReport(r) {
    renderDay(r);
    renderEdge(r);
    renderCompare(r);
  }

  function renderOrders(list) {
    const kids = [h('h2', {}, h('span', { text: 'Working orders' }), h('span', { text: String(list.length) }))];
    if (!list.length) kids.push(h('div', { class: 'empty', text: 'None' }));
    for (const o of list) {
      const px = o.stop ? 'stop ' + price(o.stop) : (o.limit ? 'limit ' + price(o.limit) : o.type);
      kids.push(h('div', { class: 'item' }, h('div', { class: 'item-head' },
        h('span', {}, h('span', { class: 'sym', text: o.symbol }), h('span', { class: 'chip', text: o.role })),
        h('span', { class: 'muted', text: o.status })),
      h('div', { class: 'sub', text: o.action + ' ' + shares(o.qty) + ' · ' + px })));
    }
    view.orders.replaceChildren(...kids);
  }

  function renderTrades(list) {
    const kids = [h('h2', { text: 'Recent trades' })];
    const closed = list.filter((t) => t.status === 'closed').slice(0, 15);
    if (!closed.length) kids.push(h('div', { class: 'empty', text: 'No closed trades yet' }));
    for (const t of closed) {
      kids.push(h('div', { class: 'item' }, h('div', { class: 'item-head' },
        h('span', {}, h('span', { class: 'sym', text: t.symbol }), h('span', { class: 'chip', text: t.exit_reason || '' })),
        h('span', { class: tone(t.pnl), text: money(t.pnl, true) })),
      h('div', { class: 'sub', text: t.entry_date + ' → ' + (t.exit_date || '') + ' · ' + (t.setups || '') })));
    }
    view.trades.replaceChildren(...kids);
  }

  function renderEvents(list) {
    const kids = [h('h2', { text: 'Activity' })];
    for (const e of list.slice(0, 25)) {
      kids.push(h('div', { class: 'event ' + e.level }, h('span', { class: 'ts', text: (e.ts || '').replace('T', ' ').slice(5, 16) }), e.message));
    }
    view.events.replaceChildren(...kids);
  }

  // ---------------------------------------------------------------- actions
  function qStrat() {
    return '?strategy=' + encodeURIComponent(currentStrategy === 'bwb' ? 'bwb' : 'gapshort');
  }

  async function togglePause(paused) {
    const ok = await ask({
      title: paused ? 'Resume trading?' : 'Pause new entries?',
      message: paused ? 'The strategy will place new entries again at the next decision window.' : 'No new entries for this strategy until you resume.',
      confirmText: paused ? 'Resume' : 'Pause',
    });
    if (!ok) return;
    try {
      await api((paused ? '/api/resume' : '/api/pause') + qStrat(), {});
      toast(paused ? 'Resumed' : 'Paused', 'ok');
      refresh();
    } catch (e) { toast(e.message, 'bad'); }
  }

  async function closeOne(symbol) {
    const pw = await ask({ title: 'Close ' + symbol + '?', danger: true, password: true, confirmText: 'Close position',
      message: 'Closes this position now, or at the next open if the market is closed.' });
    if (!pw) return;
    try {
      const r = await api('/api/close' + qStrat(), { symbol, password: pw });
      toast('Close sent (' + r.order_type + ')', 'ok');
      refresh();
    } catch (e) { toast(e.message, 'bad'); }
  }

  async function flattenAll() {
    const pw = await ask({ title: 'Close all positions?', danger: true, password: true, confirmText: 'Close all',
      message: 'Closes every open position in this strategy and pauses it.' });
    if (!pw) return;
    try {
      const r = await api('/api/flatten' + qStrat(), { password: pw });
      toast(r.covered + ' closed; strategy paused', 'ok');
      refresh();
    } catch (e) { toast(e.message, 'bad'); }
  }

  async function signOut() {
    try { await api('/api/logout', {}); } catch (_) { /* reload regardless */ }
    window.location.replace('/');
  }

  // ---------------------------------------------------------------- polling
  async function refresh() {
    if (!view.account) return;
    try {
      if (currentStrategy === 'both') {
        const ov = await api('/api/overview');
        if (!view.account) return;
        renderOverview(ov);
      } else {
        const qs = qStrat();
        const [s, p, sg, eq, o, t, ev, rep] = await Promise.all([
          api('/api/status' + qs), api('/api/positions' + qs), api('/api/signals' + qs),
          api('/api/equity' + qs), api('/api/orders' + qs), api('/api/trades' + qs),
          api('/api/events' + qs), api('/api/report' + qs),
        ]);
        if (!view.account) return;
        renderStatus(s);
        renderControls(s, p.positions);
        renderPositions(p.positions);
        renderSignals(sg);
        renderReport(rep);
        renderEquity(eq.equity);
        renderOrders(o.orders);
        renderTrades(t.trades);
        renderEvents(ev.events);
      }
      view.updated.textContent = 'Updated ' + new Date().toLocaleTimeString();
    } catch (e) {
      if (view.updated) view.updated.textContent = e.message;
    }
  }

  function startPolling() {
    stopPolling();
    pollTimer = setInterval(() => { if (document.visibilityState === 'visible') refresh(); }, POLL_MS);
  }

  function stopPolling() {
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = null;
  }

  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && pollTimer) refresh();
  });

  async function boot() {
    if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => {});
    try {
      const s = await api('/api/session');
      bwbEnabled = s.bwb_enabled !== false;
      if (s.authenticated) showMain(); else showLogin();
    } catch (_) {
      showLogin('Cannot reach the laptop. Is the service running and Tailscale on?');
    }
  }

  boot();
})();
