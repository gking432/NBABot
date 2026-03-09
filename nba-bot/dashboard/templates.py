"""
Dashboard Templates.
Full 6-tab NBA Trading Bot dashboard with embedded CSS and JS.
"""
# pylint: disable=line-too-long


def render_dashboard() -> str:
    """Return the full dashboard HTML with all 6 tabs."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NBA Trading Bot Dashboard</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
    <style>
        :root {
            --bg: #1a1a2e;
            --card: #16213e;
            --border: #0f3460;
            --text: #e0e0e0;
            --conservative: #4fc3f7;
            --tiered: #66bb6a;
            --tiered-classic: #ab47bc;
            --heavy: #ffa726;
            --positive: #4caf50;
            --negative: #ef5350;
        }
        * { box-sizing: border-box; }
        body { margin: 0; font-family: system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }
        .top-bar {
            display: flex; align-items: center; gap: 16px; padding: 12px 20px;
            background: var(--card); border-bottom: 1px solid var(--border);
        }
        .status-dot { width: 12px; height: 12px; border-radius: 50%; }
        .status-dot.running { background: var(--positive); }
        .status-dot.paused { background: var(--negative); }
        .mode-badge { padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        .mode-badge.paper { background: #2196f3; color: white; }
        .mode-badge.live { background: #f44336; color: white; }
        .live-games-panel {
            display: flex; gap: 12px; padding: 12px 20px; overflow-x: auto;
            background: var(--card); border-bottom: 1px solid var(--border); min-height: 140px;
        }
        .game-card {
            flex: 0 0 280px; padding: 12px; border-radius: 8px; border: 1px solid var(--border);
            background: var(--bg); min-width: 280px;
        }
        .game-card.profit { border-color: var(--positive); }
        .game-card.loss { border-color: var(--negative); }
        .game-score { font-size: 18px; font-weight: bold; margin-bottom: 4px; }
        .game-meta { font-size: 12px; color: #aaa; }
        .game-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; font-size: 11px; margin-top: 8px; }
        .signal-dots { display: flex; gap: 4px; margin-top: 6px; }
        .signal-dot { width: 8px; height: 8px; border-radius: 50%; }
        .signal-dot.conservative { background: var(--conservative); }
        .signal-dot.tiered { background: var(--tiered); }
        .signal-dot.tiered-classic { background: var(--tiered-classic); }
        .signal-dot.heavy { background: var(--heavy); }
        .tab-nav { display: flex; gap: 4px; padding: 8px 20px; background: var(--card); border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 100; }
        .tab-btn { padding: 8px 16px; border: none; background: transparent; color: var(--text); cursor: pointer; border-radius: 4px; }
        .tab-btn:hover { background: var(--border); }
        .tab-btn.active { background: var(--border); font-weight: bold; }
        .tab-content { display: none; padding: 20px; min-height: 500px; }
        .tab-content.active { display: block; }
        .card { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; margin-bottom: 16px; }
        .card-header { font-weight: bold; margin-bottom: 12px; font-size: 14px; }
        .strategy-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 20px; }
        .strategy-card { padding: 16px; border-radius: 8px; border: 1px solid var(--border); }
        .strategy-card.conservative .card-header { color: var(--conservative); }
        .strategy-card.tiered .card-header { color: var(--tiered); }
        .strategy-card.tiered-classic .card-header { color: var(--tiered-classic); }
        .strategy-card.heavy .card-header { color: var(--heavy); }
        .overview-grid { display: grid; grid-template-columns: 60% 40%; gap: 20px; }
        table { width: 100%; border-collapse: collapse; font-size: 13px; }
        th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid var(--border); }
        th { background: var(--card); position: sticky; top: 0; }
        tr:nth-child(even) { background: rgba(255,255,255,0.03); }
        .positive { color: var(--positive); }
        .negative { color: var(--negative); }
        .activity-feed { max-height: 300px; overflow-y: auto; }
        .activity-item { padding: 8px; border-bottom: 1px solid var(--border); font-size: 12px; }
        .chart-container { position: relative; height: 250px; margin-bottom: 20px; }
        .stats-row { display: flex; flex-wrap: wrap; gap: 16px; margin-bottom: 20px; }
        .stat-box { padding: 12px 20px; background: var(--card); border-radius: 8px; border: 1px solid var(--border); }
        .stat-label { font-size: 11px; color: #aaa; }
        .stat-value { font-size: 18px; font-weight: bold; }
        .filter-bar { display: flex; gap: 12px; margin-bottom: 16px; align-items: center; }
        .filter-bar select { padding: 6px 12px; background: var(--card); border: 1px solid var(--border); color: var(--text); border-radius: 4px; }
        .export-btn { padding: 8px 16px; background: var(--tiered); color: white; border: none; border-radius: 4px; cursor: pointer; }
        .export-btn:hover { opacity: 0.9; }
        .insight-card { padding: 12px; background: var(--card); border-left: 4px solid var(--tiered); margin-bottom: 8px; font-size: 13px; }
        .empty-state { padding: 40px; text-align: center; color: #888; }
        .guide-section { margin-bottom: 32px; }
        .guide-section h2 { margin: 0 0 4px 0; font-size: 20px; }
        .guide-section h3 { margin: 16px 0 6px 0; font-size: 15px; color: #ccc; }
        .guide-subtitle { font-size: 13px; color: #999; margin-bottom: 12px; }
        .guide-section p, .guide-section li { font-size: 13px; line-height: 1.6; color: #ccc; }
        .guide-section ul { padding-left: 20px; margin: 4px 0 8px 0; }
        .guide-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 8px 0; }
        .guide-param { padding: 8px 12px; background: var(--bg); border-radius: 6px; font-size: 12px; }
        .guide-param .label { color: #999; }
        .guide-param .value { color: var(--text); font-weight: bold; }
        .guide-example { background: var(--bg); border-left: 3px solid var(--border); padding: 10px 14px; margin: 8px 0; font-size: 12px; line-height: 1.7; border-radius: 0 6px 6px 0; }
        .guide-example .heading { color: #999; font-weight: bold; margin-bottom: 4px; }
        .guide-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; margin-right: 6px; }
        .guide-badge.entry { background: #1b5e20; color: #a5d6a7; }
        .guide-badge.exit { background: #b71c1c; color: #ef9a9a; }
        .guide-badge.stop { background: #e65100; color: #ffcc80; }
        .guide-badge.time { background: #283593; color: #9fa8da; }
        .guide-divider { border: none; border-top: 1px solid var(--border); margin: 24px 0; }
        @media (max-width: 768px) { .guide-grid { grid-template-columns: 1fr; } }
        .games-toggle {
            display: flex; align-items: center; gap: 8px; padding: 8px 20px; cursor: pointer;
            background: var(--card); border-bottom: 1px solid var(--border); user-select: none;
        }
        .games-toggle:hover { background: var(--border); }
        .games-toggle .arrow { transition: transform 0.2s; display: inline-block; }
        .games-toggle .arrow.open { transform: rotate(90deg); }
        .live-games-panel.collapsed { display: none; }
        .pos-card-mobile { display: none; }

        @media (max-width: 768px) {
            .top-bar {
                display: grid; grid-template-columns: auto 1fr; gap: 4px 8px;
                padding: 8px 12px; font-size: 12px; align-items: center;
            }
            .top-bar #statusDot { grid-row: 1; grid-column: 1; }
            .top-bar #statusText { grid-row: 1; grid-column: 2; }
            .top-bar #modeBadge { grid-row: 2; grid-column: 1; }
            .top-bar #bankroll { grid-row: 2; grid-column: 2; font-weight: bold; font-size: 14px; }
            .top-bar #oddsQuota, .top-bar #loopCount, .top-bar #refreshCountdown {
                grid-column: 1 / -1; font-size: 11px; color: #aaa;
            }

            .tab-nav {
                display: flex; overflow-x: auto; -webkit-overflow-scrolling: touch;
                padding: 4px 8px; gap: 2px; flex-wrap: nowrap;
            }
            .tab-btn { padding: 6px 8px; font-size: 11px; white-space: nowrap; flex-shrink: 0; }

            .tab-content { padding: 8px; min-height: auto; }

            .strategy-cards { grid-template-columns: 1fr 1fr !important; gap: 8px; }
            .strategy-card { padding: 10px; font-size: 12px; }
            .strategy-card .card-header { font-size: 12px; margin-bottom: 6px; }

            .overview-grid { display: flex !important; flex-direction: column !important; gap: 10px; }

            .stats-row { flex-direction: column; gap: 6px; }
            .stat-box { padding: 8px 12px; width: 100%; }
            .stat-value { font-size: 15px; }

            .card { padding: 10px; margin-bottom: 10px; overflow: hidden; }
            .card-header { font-size: 13px; }

            .card table { display: block; overflow-x: auto; -webkit-overflow-scrolling: touch; }
            table { font-size: 11px; min-width: 500px; }
            th, td { padding: 4px 6px; white-space: nowrap; }

            .chart-container { height: 180px; }
            .filter-bar { flex-wrap: wrap; gap: 6px; }
            .filter-bar select { font-size: 12px; }

            .game-card { flex: 0 0 220px; min-width: 220px; padding: 10px; }
            .game-score { font-size: 15px; }
            .live-games-panel { padding: 8px; min-height: auto; gap: 8px; }

            .activity-feed { max-height: 200px; }
            .activity-item { font-size: 10px; padding: 6px; word-break: break-word; white-space: normal; }

            .games-toggle { padding: 8px 12px; font-size: 13px; }
            .insight-card { font-size: 12px; padding: 8px; }
            .empty-state { padding: 20px; font-size: 13px; }

            .pos-table-desktop { display: none !important; }
            .pos-card-mobile { display: block !important; }
            .pos-mobile-item {
                padding: 10px; border-bottom: 1px solid var(--border); font-size: 12px;
            }
            .pos-mobile-item:last-child { border-bottom: none; }
            .pos-mobile-row { display: flex; justify-content: space-between; margin-bottom: 3px; }
            .pos-mobile-team { font-weight: bold; font-size: 14px; margin-bottom: 4px; }
            .pos-mobile-tp { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px; font-size: 11px; }
        }

        @media (max-width: 480px) {
            .strategy-cards { grid-template-columns: 1fr !important; }
            .tab-btn { padding: 5px 6px; font-size: 10px; }
        }
    </style>
</head>
<body>
    <div class="top-bar">
        <span class="status-dot paused" id="statusDot"></span>
        <span id="statusText">Loading...</span>
        <span class="mode-badge paper" id="modeBadge">PAPER</span>
        <span id="bankroll">$0.00</span>
        <span id="oddsQuota">—/500 remaining</span>
        <span id="loopCount">Loop: 0</span>
        <span id="refreshCountdown">Refresh in 10s</span>
    </div>

    <div class="games-toggle" id="gamesToggle" onclick="toggleGamesPanel()">
        <span class="arrow" id="gamesArrow">&#9654;</span>
        <span id="gamesToggleLabel">Live Games (0)</span>
    </div>
    <div class="live-games-panel collapsed" id="liveGamesPanel">
        <div class="empty-state">No live games</div>
    </div>

    <div class="tab-nav">
        <button class="tab-btn active" data-tab="overview">Overview</button>
        <button class="tab-btn" data-tab="conservative">Conservative</button>
        <button class="tab-btn" data-tab="tiered">Tiered V2</button>
        <button class="tab-btn" data-tab="tieredClassic">Tiered Classic</button>
        <button class="tab-btn" data-tab="heavy">Heavy Favorite</button>
        <button class="tab-btn" data-tab="comparison">Comparison</button>
        <button class="tab-btn" data-tab="signals">Signal Log</button>
        <button class="tab-btn" data-tab="strategyGuide">Strategy Guide</button>
    </div>

    <div id="tabOverview" class="tab-content active"></div>
    <div id="tabConservative" class="tab-content"></div>
    <div id="tabTiered" class="tab-content"></div>
    <div id="tabTieredClassic" class="tab-content"></div>
    <div id="tabHeavy" class="tab-content"></div>
    <div id="tabComparison" class="tab-content"></div>
    <div id="tabSignals" class="tab-content"></div>
    <div id="tabStrategyGuide" class="tab-content"></div>

    <script>
        const COLORS = { conservative: '#4fc3f7', tiered: '#66bb6a', tieredClassic: '#ab47bc', heavy: '#ffa726' };
        let chartInstances = {};
        let refreshTimer = 10;

        function fmt(cents) { return cents != null ? '$' + (cents / 100).toFixed(2) : '—'; }
        function fmtGameTime(t) {
            const q = t.game_quarter;
            const sec = t.game_time_remaining ?? t.game_time_remaining_seconds;
            if (!q) return '—';
            if (sec == null) return 'Q' + q;
            const m = Math.floor(sec / 60);
            const s = String(sec % 60).padStart(2, '0');
            return 'Q' + q + ' ' + m + ':' + s;
        }
        function fmtGameScore(t) {
            const h = t.game_score_home;
            const a = t.game_score_away;
            if (h == null && a == null) return '—';
            return (h ?? 0) + '-' + (a ?? 0);
        }
        function fmtPct(val) { return val != null ? (val * 100).toFixed(1) + '%' : '—'; }
        function fmtTs(ts) { return ts ? new Date(ts).toLocaleString() : '—'; }

        function toggleGamesPanel() {
            const panel = document.getElementById('liveGamesPanel');
            const arrow = document.getElementById('gamesArrow');
            panel.classList.toggle('collapsed');
            arrow.classList.toggle('open');
        }

        function initTabs() {
            document.querySelectorAll('.tab-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    const tabId = this.getAttribute('data-tab');
                    if (!tabId) return;
                    const targetId = 'tab' + tabId.charAt(0).toUpperCase() + tabId.slice(1);
                    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                    this.classList.add('active');
                    const target = document.getElementById(targetId);
                    if (target) target.classList.add('active');
                });
            });
        }

        async function fetchJson(url) {
            try {
                const r = await fetch(url);
                if (!r.ok) {
                    const err = await r.text();
                    console.error('API error ' + url + ':', r.status, err);
                    return null;
                }
                return await r.json();
            } catch (e) {
                console.error('Fetch failed ' + url + ':', e);
                return null;
            }
        }

        async function refreshData() {
            try {
                const [status, trades, signals, positions, performance] = await Promise.all([
                    fetchJson('/api/status'),
                    fetchJson('/api/trades?limit=200'),
                    fetchJson('/api/signals?limit=500'),
                    fetchJson('/api/positions/active'),
                    fetchJson('/api/performance?days=30')
                ]);

                const stats = {};
                for (const s of ['CONSERVATIVE', 'TIERED', 'TIERED_CLASSIC', 'HEAVY_FAVORITE']) {
                    stats[s] = await fetchJson('/api/stats/' + s) || {};
                }

                if (status) {
                    updateTopBar(status);
                    updateLiveGames(status, signals || []);
                    document.getElementById('statusText').textContent = status.running ? 'Running' : 'Paused';
                } else {
                    document.getElementById('statusText').textContent = 'API error (see console)';
                }
                const s = status || {};
                updateTabOverview(s, trades || [], signals || [], performance || [], stats);
                updateTabConservative(trades || [], positions || [], stats.CONSERVATIVE || {});
                updateTabTiered(trades || [], positions || [], stats.TIERED || {});
                updateTabTieredClassic(trades || [], positions || [], stats.TIERED_CLASSIC || {});
                updateTabHeavy(trades || [], positions || [], stats.HEAVY_FAVORITE || {});
                updateTabComparison(trades || [], stats);
                updateTabSignals(signals || []);

                refreshTimer = 10;
            } catch (err) {
                console.error('Dashboard refresh error:', err);
                document.getElementById('statusText').textContent = 'Error (check console)';
            }
        }

        function updateTopBar(s) {
            document.getElementById('statusDot').className = 'status-dot ' + (s.running ? 'running' : 'paused');
            document.getElementById('statusText').textContent = s.running ? 'Running' : 'Paused';
            document.getElementById('modeBadge').textContent = s.mode || 'PAPER';
            document.getElementById('modeBadge').className = 'mode-badge ' + (s.mode === 'LIVE' ? 'live' : 'paper');
            document.getElementById('bankroll').textContent = fmt((s.risk && s.risk.total_bankroll) || 0);
            const q = s.odds_quota || {};
            const oddsSource = s.odds_source || 'The Odds API';
            if (oddsSource === 'BetStack') {
                document.getElementById('oddsQuota').textContent = 'BetStack (' + (s.betstack_requests || 0) + ' reqs)';
            } else {
                document.getElementById('oddsQuota').textContent = (q.remaining ?? '—') + '/500 remaining';
            }
            document.getElementById('loopCount').textContent = 'Loop: ' + (s.loop_count || 0);
        }

        function updateLiveGames(s, signals) {
            const games = s.live_games || [];
            const positions = s.active_positions || [];
            const fiveMinAgo = Date.now() - 5 * 60 * 1000;
            const recentByGame = {};
            (signals || []).forEach(sig => {
                const t = new Date(sig.timestamp).getTime();
                if (t > fiveMinAgo && sig.game_id) {
                    if (!recentByGame[sig.game_id]) recentByGame[sig.game_id] = new Set();
                    recentByGame[sig.game_id].add(sig.strategy);
                }
            });

            const posByGame = {};
            positions.forEach(p => { posByGame[p.game_id] = p; });

            const panel = document.getElementById('liveGamesPanel');
            const label = document.getElementById('gamesToggleLabel');
            if (label) label.textContent = 'Live Games (' + games.length + ')';
            if (games.length === 0) {
                panel.innerHTML = '<div class="empty-state">No live games</div>';
                return;
            }
            panel.innerHTML = games.map(g => {
                const pos = posByGame[g.game_id];
                const sigs = recentByGame[g.game_id] || new Set();
                let borderClass = '';
                if (pos) {
                    const cost = pos.total_cost_cents || 0;
                    const bid = g.kalshi_bid || 0;
                    const val = (pos.shares_remaining || 0) * bid;
                    borderClass = val > cost ? 'profit' : 'loss';
                }
                return `
                    <div class="game-card ${borderClass}">
                        <div class="game-score">${g.away_team || 'Away'} ${g.away_score || 0} @ ${g.home_team || 'Home'} ${g.home_score || 0}</div>
                        <div class="game-meta">Q${g.quarter || '?'} ${Math.floor((g.time_remaining || 0) / 60)}:${String((g.time_remaining || 0) % 60).padStart(2,'0')} | Spread: ${g.spread ?? '—'}</div>
                        <div class="game-stats">
                            <span>Bid: ${g.kalshi_bid ?? '—'}¢ / Ask: ${g.kalshi_ask ?? '—'}¢</span>
                            <span class="${(g.price_drop_pct || 0) < 0 ? 'negative' : ''}">Drop: ${g.price_drop_pct ?? '—'}%</span>
                            <span>Fair: ${g.fair_value ?? '—'}%</span>
                            <span class="${(g.edge || 0) > 0 ? 'positive' : ''}">Edge: ${g.edge != null ? '+' : ''}${g.edge ?? '—'}%</span>
                            <span>Deficit: ${g.deficit_vs_spread ?? '—'}</span>
                            <span>Depth: ${g.book_depth ?? '—'}</span>
                        </div>
                        <div class="signal-dots">
                            ${['CONSERVATIVE','TIERED','TIERED_CLASSIC','HEAVY_FAVORITE'].map(st => {
                                const cls = st === 'TIERED_CLASSIC' ? 'tiered-classic' : st.toLowerCase().replace('_',' ').split(' ')[0];
                                return `<span class="signal-dot ${cls}" style="opacity:${sigs.has(st) ? 1 : 0.25}" title="${st}${sigs.has(st) ? ' (signal in last 5m)' : ''}"></span>`;
                            }).join('')}
                        </div>
                        ${pos ? `<div class="game-meta" style="margin-top:6px">Position: ${pos.strategy} (${pos.entry_count} entries) — ${pos.mode || '—'}</div>` : ''}
                    </div>
                `;
            }).join('');
        }

        function getTPTargets(pos) {
            const strat = pos.strategy;
            const avg = pos.avg_cost_cents || 0;
            const targets = [];

            if (strat === 'CONSERVATIVE') {
                targets.push({ label: 'TP1 (+30%)', price: Math.round(avg * 1.30), hit: false });
                targets.push({ label: 'TP2 (+60%)', price: Math.round(avg * 1.60), hit: false });
            } else if (strat === 'TIERED') {
                let mult = 1.5, sellPct = '40%';
                if (avg <= 14) { mult = 3.0; sellPct = '18%'; }
                else if (avg <= 19) { mult = 2.5; sellPct = '22%'; }
                else if (avg <= 24) { mult = 2.0; sellPct = '28%'; }
                else if (avg <= 29) { mult = 1.75; sellPct = '33%'; }
                targets.push({ label: 'Recovery (' + mult + 'x)', price: Math.round(avg * mult), hit: pos.capital_recovered });
                targets.push({ label: 'HM1 (65¢)', price: 65, hit: pos.house_money_1_hit });
                targets.push({ label: 'HM2 (82¢)', price: 82, hit: pos.house_money_2_hit });
            } else if (strat === 'TIERED_CLASSIC') {
                targets.push({ label: 'Recovery (1.75x)', price: Math.round(avg * 1.75), hit: pos.capital_recovered });
                targets.push({ label: 'HM1 (3x)', price: Math.round(avg * 3.0), hit: pos.house_money_1_hit });
                targets.push({ label: 'HM2 (5x)', price: Math.round(avg * 5.0), hit: pos.house_money_2_hit });
            } else if (strat === 'HEAVY_FAVORITE') {
                targets.push({ label: 'Recovery (2x)', price: Math.round(avg * 2.0), hit: pos.capital_recovered });
                targets.push({ label: 'HM1 (3x)', price: Math.round(avg * 3.0), hit: pos.house_money_1_hit });
                targets.push({ label: 'HM2 (60¢)', price: 60, hit: pos.house_money_2_hit });
            }
            return targets;
        }

        function stratColor(strat) {
            if (strat === 'CONSERVATIVE') return 'var(--conservative)';
            if (strat === 'TIERED') return 'var(--tiered)';
            if (strat === 'TIERED_CLASSIC') return 'var(--tiered-classic)';
            if (strat === 'HEAVY_FAVORITE') return 'var(--heavy)';
            return 'var(--text)';
        }

        function updateTabOverview(s, trades, signals, performance, stats) {
            const risk = s.risk || {};
            const bankrolls = risk.bankrolls || {};
            const today = new Date().toISOString().slice(0, 10);
            const todayTrades = (trades || []).filter(t => (t.timestamp || '').slice(0, 10) === today);
            const todaySignals = (signals || []).filter(sg => (sg.timestamp || '').slice(0, 10) === today);

            let html = '<div class="overview-grid"><div>';
            html += '<div class="strategy-cards">';
            for (const [name, color] of [['CONSERVATIVE','conservative'],['TIERED','tiered'],['TIERED_CLASSIC','tiered-classic'],['HEAVY_FAVORITE','heavy']]) {
                const bal = bankrolls[name] || 0;
                const st = stats[name] || {};
                const paused = (risk.strategy_pauses || {})[name];
                const pausedGames = ((risk.paused_games || {})[name] || []).length;
                html += `<div class="strategy-card ${color}">
                    <div class="card-header">${name.replace('_',' ')}</div>
                    <div>Balance: ${fmt(bal)}</div>
                    <div>Total P&L: <span class="${(st.total_pnl || 0) >= 0 ? 'positive' : 'negative'}">${fmt(st.total_pnl)}</span></div>
                    <div>Win Rate: ${fmtPct(st.win_rate)}</div>
                    <div>Active: ${(risk.positions_count || {})[name] || 0}</div>
                    ${paused ? '<div class="negative">PAUSED (weekly limit)</div>' : ''}
                    ${pausedGames > 0 ? '<div class="negative">' + pausedGames + ' game(s) paused</div>' : ''}
                </div>`;
            }
            html += '</div>';

            // ─── OPEN POSITIONS CARD ───
            const activePositions = s.active_positions || [];
            const liveGames = s.live_games || [];
            const gamesByIdOP = {};
            liveGames.forEach(g => { gamesByIdOP[g.game_id] = g; });

            html += '<div class="card"><div class="card-header">Open Positions</div>';
            if (activePositions.length === 0) {
                html += '<div class="empty-state">No open positions</div>';
            } else {
                let totalUnrealizedPnl = 0;
                let totalCost = 0;
                const posData = activePositions.map(pos => {
                    const game = gamesByIdOP[pos.game_id];
                    const currentPrice = game ? (game.kalshi_bid || game.kalshi_ask || 0) : 0;
                    const avg = pos.avg_cost_cents || 0;
                    const shares = pos.shares_remaining || 0;
                    const remainingCost = Math.round(shares * avg);
                    const currentValue = shares * currentPrice;
                    const unrealizedPnl = currentPrice > 0 ? currentValue - remainingCost : 0;
                    const pctChange = (avg > 0 && currentPrice > 0) ? ((currentPrice - avg) / avg) * 100 : 0;
                    totalUnrealizedPnl += unrealizedPnl;
                    totalCost += remainingCost;
                    const entries = (pos.entries || []);
                    const entryStr = entries.map(e => e.price + '¢').join(', ');
                    const targets = getTPTargets(pos);
                    return { pos, currentPrice, avg, shares, unrealizedPnl, pctChange, entryStr, targets };
                });
                const totalPctChange = totalCost > 0 ? (totalUnrealizedPnl / totalCost) * 100 : 0;
                const totalPnlClass = totalUnrealizedPnl >= 0 ? 'positive' : 'negative';

                const tpSpans = (targets) => targets.map(t => {
                    const style = t.hit ? 'text-decoration:line-through;opacity:0.5' : '';
                    const icon = t.hit ? '✓ ' : '';
                    return '<span style="' + style + ';margin-right:6px;white-space:nowrap">' + icon + t.label + ' ' + t.price + '¢</span>';
                }).join('');

                // Desktop table
                html += '<div class="pos-table-desktop"><table style="font-size:12px"><thead><tr><th>Team</th><th>Strategy</th><th>Entries</th><th>Avg Cost</th><th>Current</th><th>Shares</th><th>Unreal. P&L</th><th>% Chg</th><th>Take-Profit Targets</th></tr></thead><tbody>';
                posData.forEach(d => {
                    const pnlClass = d.unrealizedPnl >= 0 ? 'positive' : 'negative';
                    const pctClass = d.pctChange >= 0 ? 'positive' : 'negative';
                    html += '<tr>';
                    html += '<td><strong>' + (d.pos.team || '—') + '</strong></td>';
                    html += '<td style="color:' + stratColor(d.pos.strategy) + '">' + (d.pos.strategy || '').replace('_', ' ') + '</td>';
                    html += '<td>' + (d.entryStr || '—') + '</td>';
                    html += '<td>' + d.avg.toFixed(1) + '¢</td>';
                    html += '<td>' + (d.currentPrice > 0 ? d.currentPrice + '¢' : '—') + '</td>';
                    html += '<td>' + d.shares + '</td>';
                    html += '<td class="' + pnlClass + '">' + fmt(d.unrealizedPnl) + '</td>';
                    html += '<td class="' + pctClass + '">' + (d.currentPrice > 0 ? d.pctChange.toFixed(1) + '%' : '—') + '</td>';
                    html += '<td style="font-size:11px">' + tpSpans(d.targets) + '</td>';
                    html += '</tr>';
                });
                html += '<tr style="border-top:2px solid var(--border);font-weight:bold"><td colspan="6" style="text-align:right">Total Unrealized:</td>';
                html += '<td class="' + totalPnlClass + '">' + fmt(totalUnrealizedPnl) + '</td>';
                html += '<td class="' + totalPnlClass + '">' + totalPctChange.toFixed(1) + '%</td>';
                html += '<td></td></tr>';
                html += '</tbody></table></div>';

                // Mobile card layout
                html += '<div class="pos-card-mobile">';
                posData.forEach(d => {
                    const pnlClass = d.unrealizedPnl >= 0 ? 'positive' : 'negative';
                    const pctClass = d.pctChange >= 0 ? 'positive' : 'negative';
                    html += '<div class="pos-mobile-item">';
                    html += '<div class="pos-mobile-team" style="color:' + stratColor(d.pos.strategy) + '">' + (d.pos.team || '—') + ' <span style="font-size:11px;opacity:0.7">' + (d.pos.strategy || '').replace('_',' ') + '</span></div>';
                    html += '<div class="pos-mobile-row"><span>Entries: ' + (d.entryStr || '—') + '</span><span>Avg: ' + d.avg.toFixed(1) + '¢</span></div>';
                    html += '<div class="pos-mobile-row"><span>Current: ' + (d.currentPrice > 0 ? d.currentPrice + '¢' : '—') + '</span><span>Shares: ' + d.shares + '</span></div>';
                    html += '<div class="pos-mobile-row"><span>P&L: <span class="' + pnlClass + '">' + fmt(d.unrealizedPnl) + '</span></span>';
                    html += '<span class="' + pctClass + '">' + (d.currentPrice > 0 ? d.pctChange.toFixed(1) + '%' : '—') + '</span></div>';
                    if (d.targets.length > 0) html += '<div class="pos-mobile-tp">' + tpSpans(d.targets) + '</div>';
                    html += '</div>';
                });
                html += '<div class="pos-mobile-item" style="font-weight:bold;border-top:2px solid var(--border)">';
                html += '<div class="pos-mobile-row"><span>Total Unrealized:</span><span class="' + totalPnlClass + '">' + fmt(totalUnrealizedPnl) + ' (' + totalPctChange.toFixed(1) + '%)</span></div>';
                html += '</div></div>';
            }
            html += '</div>';

            html += '<div class="card"><div class="card-header">Combined P&L Chart</div><div class="chart-container"><canvas id="chartOverview"></canvas></div></div>';
            html += '</div><div>';

            html += '<div class="card"><div class="card-header">Today' + "'" + 's Activity</div><div class="activity-feed">';
            const combined = [
                ...todayTrades.map(t => ({ ...t, type: 'trade', sort: new Date(t.timestamp).getTime() })),
                ...todaySignals.filter(sg => sg.action_taken).map(sg => ({ ...sg, type: 'signal', sort: new Date(sg.timestamp).getTime() }))
            ].sort((a, b) => b.sort - a.sort).slice(0, 30);
            if (combined.length === 0) html += '<div class="empty-state">No activity today</div>';
            else combined.forEach(x => {
                const pnl = x.pnl_cents;
                const cls = pnl > 0 ? 'positive' : (pnl < 0 ? 'negative' : '');
                html += `<div class="activity-item ${cls}">${fmtTs(x.timestamp)} | ${x.strategy || ''} | ${x.team || ''} | ${x.action || 'SIGNAL'} | ${fmt(x.price_cents || x.kalshi_price)} | ${pnl != null ? fmt(pnl) : ''}</div>`;
            });
            html += '</div></div>';

            html += '<div class="card"><div class="card-header">Comparison</div><table><thead><tr><th></th><th>Conservative</th><th>Tiered V2</th><th>Tiered Classic</th><th>Heavy Fav</th></tr></thead><tbody>';
            const rows = ['win_rate','avg_win','avg_loss','best_trade','worst_trade','total_pnl'];
            const labels = ['Win Rate','Avg Win','Avg Loss','Best','Worst','Total P&L'];
            rows.forEach((r, i) => {
                html += `<tr><td>${labels[i]}</td>`;
                ['CONSERVATIVE','TIERED','TIERED_CLASSIC','HEAVY_FAVORITE'].forEach(st => {
                    const v = (stats[st] || {})[r];
                    const disp = r === 'win_rate' ? fmtPct(v) : fmt(v);
                    const cls = (r === 'total_pnl' || r === 'avg_win' || r === 'best_trade') && v > 0 ? 'positive' : (v < 0 ? 'negative' : '');
                    html += `<td class="${cls}">${disp}</td>`;
                });
                html += '</tr>';
            });
            html += '</tbody></table></div></div></div>';

            document.getElementById('tabOverview').innerHTML = html;
            renderOverviewChart(performance || [], trades || []);
        }

        function renderOverviewChart(perf, trades) {
            if (typeof Chart === 'undefined') return;
            try {
            const pnlByDate = {};
            (trades || []).forEach(t => {
                const pnl = t.pnl_cents || 0;
                if (pnl === 0 && t.action === 'BUY') return;
                const d = (t.timestamp || '').slice(0, 10);
                if (!d) return;
                if (!pnlByDate[d]) pnlByDate[d] = { CONSERVATIVE: 0, TIERED: 0, TIERED_CLASSIC: 0, HEAVY_FAVORITE: 0 };
                pnlByDate[d][t.strategy] = (pnlByDate[d][t.strategy] || 0) + pnl;
            });
            const dates = Object.keys(pnlByDate).sort();
            if (dates.length === 0) return;

            const cumulative = { CONSERVATIVE: [], TIERED: [], TIERED_CLASSIC: [], HEAVY_FAVORITE: [] };
            let running = { CONSERVATIVE: 0, TIERED: 0, TIERED_CLASSIC: 0, HEAVY_FAVORITE: 0 };
            dates.forEach(d => {
                for (const s of ['CONSERVATIVE', 'TIERED', 'TIERED_CLASSIC', 'HEAVY_FAVORITE']) {
                    running[s] += pnlByDate[d][s] || 0;
                    cumulative[s].push(running[s]);
                }
            });

            if (chartInstances.overview) chartInstances.overview.destroy();
            const ctx = document.getElementById('chartOverview');
            if (!ctx) return;
            chartInstances.overview = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: dates,
                    datasets: [
                        { label: 'Conservative', data: cumulative.CONSERVATIVE.map(v => v / 100), borderColor: COLORS.conservative, fill: false, tension: 0.2 },
                        { label: 'Tiered V2', data: cumulative.TIERED.map(v => v / 100), borderColor: COLORS.tiered, fill: false, tension: 0.2 },
                        { label: 'Tiered Classic', data: cumulative.TIERED_CLASSIC.map(v => v / 100), borderColor: COLORS.tieredClassic, fill: false, tension: 0.2 },
                        { label: 'Heavy Favorite', data: cumulative.HEAVY_FAVORITE.map(v => v / 100), borderColor: COLORS.heavy, fill: false, tension: 0.2 }
                    ]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    scales: {
                        x: { grid: { color: 'rgba(255,255,255,0.1)' } },
                        y: { grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { callback: v => '$' + v.toFixed(2) } }
                    },
                    plugins: { tooltip: { callbacks: { label: ctx => ctx.dataset.label + ': $' + ctx.parsed.y.toFixed(2) } } }
                }
            });
            } catch (e) { console.warn('Chart error:', e); }
        }

        function updateTabConservative(trades, positions, st) {
            const cons = trades.filter(t => t.strategy === 'CONSERVATIVE');
            const active = positions.filter(p => p.strategy === 'CONSERVATIVE');

            let html = '<div class="stats-row">';
            html += `<div class="stat-box"><div class="stat-label">Balance</div><div class="stat-value">${fmt(st?.total_pnl != null ? 500 * 0.35 + (st.total_pnl || 0) : null)}</div></div>`;
            html += `<div class="stat-box"><div class="stat-label">Total P&L</div><div class="stat-value ${(st?.total_pnl || 0) >= 0 ? 'positive' : 'negative'}">${fmt(st?.total_pnl)}</div></div>`;
            html += `<div class="stat-box"><div class="stat-label">Win Rate</div><div class="stat-value">${fmtPct(st?.win_rate)}</div></div>`;
            html += `<div class="stat-box"><div class="stat-label">Avg Win</div><div class="stat-value positive">${fmt(st?.avg_win)}</div></div>`;
            html += `<div class="stat-box"><div class="stat-label">Avg Loss</div><div class="stat-value negative">${fmt(st?.avg_loss)}</div></div>`;
            html += `<div class="stat-box"><div class="stat-label">Trades</div><div class="stat-value">${st?.total_trades ?? 0}</div></div>`;
            html += '</div>';

            const edgeBuckets = { '8-10%': [], '10-12%': [], '12%+': [] };
            cons.filter(t => t.action === 'BUY').forEach(t => {
                const e = t.edge != null ? t.edge : (t.fair_value != null && t.price_cents != null ? (t.fair_value - t.price_cents/100) : null);
                if (e != null) {
                    const pct = (typeof e === 'number' && e <= 1 && e > -1) ? e * 100 : e;
                    if (pct >= 12) edgeBuckets['12%+'].push(t);
                    else if (pct >= 10) edgeBuckets['10-12%'].push(t);
                    else if (pct >= 8) edgeBuckets['8-10%'].push(t);
                }
            });

            const deficitBuckets = { '12-15': [], '15-18': [], '18-20': [], '20+': [] };
            cons.filter(t => t.action === 'BUY').forEach(t => {
                const d = t.deficit_vs_spread || 0;
                if (d >= 20) deficitBuckets['20+'].push(t);
                else if (d >= 18) deficitBuckets['18-20'].push(t);
                else if (d >= 15) deficitBuckets['15-18'].push(t);
                else if (d >= 12) deficitBuckets['12-15'].push(t);
            });

            const exitCounts = {};
            cons.filter(t => t.action !== 'BUY').forEach(t => {
                const r = (t.reason || '').toUpperCase();
                let key = 'OTHER';
                if (r.includes('TP') || r.includes('TAKE')) key = r.includes('50') ? 'TP2' : 'TP1';
                else if (r.includes('STOP')) key = 'Stop Loss';
                else if (r.includes('SETTLE') && (t.pnl_cents || 0) > 0) key = 'Settlement Win';
                else if (r.includes('SETTLE') && (t.pnl_cents || 0) < 0) key = 'Settlement Loss';
                exitCounts[key] = (exitCounts[key] || 0) + 1;
            });

            html += '<div class="card"><div class="card-header">Edge Analysis</div><div class="chart-container"><canvas id="chartConsEdge"></canvas></div></div>';
            html += '<div class="card"><div class="card-header">Entry Analysis (Deficit)</div><div class="chart-container"><canvas id="chartConsDeficit"></canvas></div></div>';
            html += '<div class="card"><div class="card-header">Exit Breakdown</div><div class="chart-container"><canvas id="chartConsExit"></canvas></div></div>';
            html += '<div class="card"><div class="card-header">Active Positions</div>';
            if (active.length === 0) html += '<div class="empty-state">No active positions</div>';
            else html += '<table><thead><tr><th>Team</th><th>Entry</th><th>Shares</th><th>Cost</th><th>Mode</th></tr></thead><tbody>' +
                active.map(p => `<tr><td>${p.team}</td><td>${fmt(p.avg_cost_cents)}</td><td>${p.shares_remaining}</td><td>${fmt(p.total_cost_cents)}</td><td>${p.current_mode || '—'}</td></tr>`).join('') + '</tbody></table>';
            html += '</div>';
            html += '<div class="card"><div class="card-header">Trade History</div>';
            if (cons.length === 0) html += '<div class="empty-state">No trades yet</div>';
            else html += '<table><thead><tr><th>Date</th><th>Team</th><th>Action</th><th>Price</th><th>P&L</th><th>Edge</th><th>Deficit</th><th>Game Time</th><th>Score</th></tr></thead><tbody>' +
                cons.slice(0, 50).map(t => `<tr><td>${fmtTs(t.timestamp)}</td><td>${t.team}</td><td>${t.action}</td><td>${t.price_cents}¢</td><td class="${(t.pnl_cents || 0) >= 0 ? 'positive' : 'negative'}">${fmt(t.pnl_cents)}</td><td>${t.edge != null ? t.edge + '%' : '—'}</td><td>${t.deficit_vs_spread ?? '—'}</td><td>${fmtGameTime(t)}</td><td>${fmtGameScore(t)}</td></tr>`).join('') + '</tbody></table>';
            html += '</div>';

            document.getElementById('tabConservative').innerHTML = html;
            renderBarChart('chartConsEdge', Object.keys(edgeBuckets), Object.values(edgeBuckets).map(arr => {
                const wins = arr.filter(t => cons.some(c => c.position_id === t.position_id && c.pnl_cents > 0));
                return arr.length ? (wins.length / arr.length) * 100 : 0;
            }), COLORS.conservative);
            renderBarChart('chartConsDeficit', Object.keys(deficitBuckets), Object.values(deficitBuckets).map(arr => {
                const wins = arr.filter(t => cons.some(c => c.position_id === t.position_id && c.pnl_cents > 0));
                return arr.length ? (wins.length / arr.length) * 100 : 0;
            }), COLORS.conservative);
            try {
                if (chartInstances.consExit) chartInstances.consExit.destroy();
                const ctxExit = document.getElementById('chartConsExit');
                if (typeof Chart !== 'undefined' && ctxExit && Object.keys(exitCounts).length > 0) chartInstances.consExit = new Chart(ctxExit, { type: 'pie', data: { labels: Object.keys(exitCounts), datasets: [{ data: Object.values(exitCounts), backgroundColor: [COLORS.conservative, '#81d4fa', '#4caf50', '#ef5350', '#888'] }] }, options: { responsive: true, maintainAspectRatio: false } });
            } catch (e) { console.warn('Chart error:', e); }
        }

        function renderBarChart(canvasId, labels, data, color) {
            if (typeof Chart === 'undefined') return;
            try {
                if (chartInstances[canvasId]) chartInstances[canvasId].destroy();
                const ctx = document.getElementById(canvasId);
                if (!ctx) return;
                chartInstances[canvasId] = new Chart(ctx, {
                    type: 'bar',
                    data: { labels, datasets: [{ label: 'Win Rate %', data, backgroundColor: color }] },
                    options: { responsive: true, maintainAspectRatio: false, scales: { y: { max: 100, grid: { color: 'rgba(255,255,255,0.1)' } } } }
                });
            } catch (e) { console.warn('Chart error:', e); }
        }

        function updateTabTiered(trades, positions, st) {
            const tiered = trades.filter(t => t.strategy === 'TIERED');
            const active = positions.filter(p => p.strategy === 'TIERED');

            let html = '<div class="stats-row">';
            html += `<div class="stat-box"><div class="stat-label">Total P&L</div><div class="stat-value ${(st?.total_pnl || 0) >= 0 ? 'positive' : 'negative'}">${fmt(st?.total_pnl)}</div></div>`;
            html += `<div class="stat-box"><div class="stat-label">Win Rate</div><div class="stat-value">${fmtPct(st?.win_rate)}</div></div>`;
            html += `<div class="stat-box"><div class="stat-label">Trades</div><div class="stat-value">${st?.total_trades ?? 0}</div></div>`;
            html += '</div>';

            const entryCounts = { 1: [], 2: [], '3+': [] };
            const byPos = {};
            tiered.forEach(t => {
                const pid = t.position_id || t.game_id + t.team;
                if (!byPos[pid]) byPos[pid] = [];
                byPos[pid].push(t);
            });
            Object.values(byPos).forEach(arr => {
                const buys = arr.filter(x => x.action === 'BUY');
                const cnt = new Set(buys.map(x => x.entry_number || 1)).size || 1;
                const bucket = cnt >= 3 ? '3+' : cnt;
                if (entryCounts[bucket]) entryCounts[bucket].push(...arr);
            });

            const priceDropBuckets = { '25-35%': [], '35-45%': [], '45%+': [] };
            tiered.filter(t => t.action === 'BUY').forEach(t => {
                const raw = t.price_drop_pct != null ? t.price_drop_pct : 0;
                const p = (raw <= 1 && raw > 0) ? raw * 100 : raw;
                if (p >= 45) priceDropBuckets['45%+'].push(t);
                else if (p >= 35) priceDropBuckets['35-45%'].push(t);
                else if (p >= 25) priceDropBuckets['25-35%'].push(t);
            });

            html += '<div class="card"><div class="card-header">Multi-Entry Analysis</div><div class="chart-container"><canvas id="chartTieredEntry"></canvas></div></div>';
            html += '<div class="card"><div class="card-header">House Money Tracker</div>';
            const posPnl = {};
            tiered.forEach(t => {
                const pid = t.position_id || t.game_id + t.team;
                if (!posPnl[pid]) posPnl[pid] = { cost: 0, pnl: 0, team: t.team };
                if (t.action === 'BUY') posPnl[pid].cost += t.total_cents || 0;
                posPnl[pid].pnl += t.pnl_cents || 0;
            });
            const recovered = Object.values(posPnl).filter(p => p.pnl > 0);
            if (recovered.length === 0) html += '<div class="empty-state">No profitable positions yet</div>';
            else html += '<table><thead><tr><th>Team</th><th>Entry Cost</th><th>Final P&L</th></tr></thead><tbody>' +
                recovered.map(p => `<tr><td>${p.team}</td><td>${fmt(p.cost)}</td><td class="positive">${fmt(p.pnl)}</td></tr>`).join('') + '</tbody></table>';
            html += '</div>';
            const modeCounts = {};
            tiered.filter(t => t.action !== 'BUY').forEach(t => {
                const m = (t.game_mode || t.reason || 'OTHER').toUpperCase();
                let key = m.includes('SETTLE') ? 'Settlement' : (m.includes('DEFENSIVE') ? 'Defensive' : (m.includes('NEUTRAL') ? 'Neutral' : 'Offensive'));
                modeCounts[key] = (modeCounts[key] || 0) + 1;
            });
            html += '<div class="card"><div class="card-header">Game Mode Analysis</div><div class="chart-container"><canvas id="chartTieredMode"></canvas></div></div>';
            html += '<div class="card"><div class="card-header">Price Drop Analysis</div><div class="chart-container"><canvas id="chartTieredPrice"></canvas></div></div>';
            html += '<div class="card"><div class="card-header">Time Analysis (Q1 vs Q2)</div><div class="chart-container"><canvas id="chartTieredTime"></canvas></div></div>';
            html += '<div class="card"><div class="card-header">Active Positions</div>';
            if (active.length === 0) html += '<div class="empty-state">No active positions</div>';
            else html += '<table><thead><tr><th>Team</th><th>Entries</th><th>Mode</th><th>House $</th></tr></thead><tbody>' +
                active.map(p => `<tr><td>${p.team}</td><td>${p.entry_count}</td><td>${p.current_mode || '—'}</td><td>${p.capital_recovered ? 'Yes' : 'No'}</td></tr>`).join('') + '</tbody></table>';
            html += '</div>';
            html += '<div class="card"><div class="card-header">Trade History</div>';
            if (tiered.length === 0) html += '<div class="empty-state">No trades yet</div>';
            else html += '<table><thead><tr><th>Date</th><th>Team</th><th>Action</th><th>Entry #</th><th>Price</th><th>P&L</th><th>Game Time</th><th>Score</th></tr></thead><tbody>' +
                tiered.slice(0, 80).map(t => `<tr><td>${fmtTs(t.timestamp)}</td><td>${t.team}</td><td>${t.action}</td><td>${t.entry_number ?? '—'}</td><td>${t.price_cents}¢</td><td class="${(t.pnl_cents || 0) >= 0 ? 'positive' : 'negative'}">${fmt(t.pnl_cents)}</td><td>${fmtGameTime(t)}</td><td>${fmtGameScore(t)}</td></tr>`).join('') + '</tbody></table>';
            html += '</div>';

            document.getElementById('tabTiered').innerHTML = html;
            renderBarChart('chartTieredEntry', ['1 entry', '2 entries', '3+ entries'], [1,2,'3+'].map(k => {
                const arr = entryCounts[k] || [];
                const posIds = [...new Set(arr.filter(t => t.action === 'BUY').map(t => t.position_id))];
                const wins = posIds.filter(pid => tiered.some(c => c.position_id === pid && c.pnl_cents > 0));
                return posIds.length ? (wins.length / posIds.length) * 100 : 0;
            }), COLORS.tiered);
            renderBarChart('chartTieredPrice', Object.keys(priceDropBuckets), Object.values(priceDropBuckets).map(arr => {
                const wins = arr.filter(t => tiered.some(c => c.position_id === t.position_id && c.pnl_cents > 0));
                return arr.length ? (wins.length / arr.length) * 100 : 0;
            }), COLORS.tiered);
            const q1 = tiered.filter(t => t.action === 'BUY' && t.game_quarter === 1);
            const q2 = tiered.filter(t => t.action === 'BUY' && t.game_quarter === 2);
            renderBarChart('chartTieredTime', ['Q1', 'Q2'], [
                q1.length ? q1.filter(t => tiered.some(c => c.position_id === t.position_id && c.pnl_cents > 0)).length / q1.length * 100 : 0,
                q2.length ? q2.filter(t => tiered.some(c => c.position_id === t.position_id && c.pnl_cents > 0)).length / q2.length * 100 : 0
            ], COLORS.tiered);
            try {
                if (chartInstances.tieredMode) chartInstances.tieredMode.destroy();
                const ctxMode = document.getElementById('chartTieredMode');
                if (typeof Chart !== 'undefined' && ctxMode && Object.keys(modeCounts).length > 0) chartInstances.tieredMode = new Chart(ctxMode, { type: 'pie', data: { labels: Object.keys(modeCounts), datasets: [{ data: Object.values(modeCounts), backgroundColor: [COLORS.tiered, '#81d4fa', '#ffa726', '#4caf50'] }] }, options: { responsive: true, maintainAspectRatio: false } });
            } catch (e) { console.warn('Chart error:', e); }
        }

        function updateTabTieredClassic(trades, positions, st) {
            const classic = trades.filter(t => t.strategy === 'TIERED_CLASSIC');
            const active = positions.filter(p => p.strategy === 'TIERED_CLASSIC');

            let html = '<div class="stats-row">';
            html += `<div class="stat-box"><div class="stat-label">Total P&L</div><div class="stat-value ${(st?.total_pnl || 0) >= 0 ? 'positive' : 'negative'}">${fmt(st?.total_pnl)}</div></div>`;
            html += `<div class="stat-box"><div class="stat-label">Win Rate</div><div class="stat-value">${fmtPct(st?.win_rate)}</div></div>`;
            html += `<div class="stat-box"><div class="stat-label">Trades</div><div class="stat-value">${st?.total_trades ?? 0}</div></div>`;
            html += '</div>';

            const entryCounts = { 1: [], 2: [], '3+': [] };
            const byPos = {};
            classic.forEach(t => {
                const pid = t.position_id || t.game_id + t.team;
                if (!byPos[pid]) byPos[pid] = [];
                byPos[pid].push(t);
            });
            Object.values(byPos).forEach(arr => {
                const buys = arr.filter(x => x.action === 'BUY');
                const cnt = new Set(buys.map(x => x.entry_number || 1)).size || 1;
                const bucket = cnt >= 3 ? '3+' : cnt;
                if (entryCounts[bucket]) entryCounts[bucket].push(...arr);
            });

            html += '<div class="card"><div class="card-header">Multi-Entry Analysis</div><div class="chart-container"><canvas id="chartClassicEntry"></canvas></div></div>';
            html += '<div class="card"><div class="card-header">House Money Tracker</div>';
            const posPnl = {};
            classic.forEach(t => {
                const pid = t.position_id || t.game_id + t.team;
                if (!posPnl[pid]) posPnl[pid] = { cost: 0, pnl: 0, team: t.team };
                if (t.action === 'BUY') posPnl[pid].cost += t.total_cents || 0;
                posPnl[pid].pnl += t.pnl_cents || 0;
            });
            const recovered = Object.values(posPnl).filter(p => p.pnl > 0);
            if (recovered.length === 0) html += '<div class="empty-state">No profitable positions yet</div>';
            else html += '<table><thead><tr><th>Team</th><th>Entry Cost</th><th>Final P&L</th></tr></thead><tbody>' +
                recovered.map(p => `<tr><td>${p.team}</td><td>${fmt(p.cost)}</td><td class="positive">${fmt(p.pnl)}</td></tr>`).join('') + '</tbody></table>';
            html += '</div>';
            html += '<div class="card"><div class="card-header">Active Positions</div>';
            if (active.length === 0) html += '<div class="empty-state">No active positions</div>';
            else html += '<table><thead><tr><th>Team</th><th>Entries</th><th>Mode</th><th>House $</th></tr></thead><tbody>' +
                active.map(p => `<tr><td>${p.team}</td><td>${p.entry_count}</td><td>${p.current_mode || '—'}</td><td>${p.capital_recovered ? 'Yes' : 'No'}</td></tr>`).join('') + '</tbody></table>';
            html += '</div>';
            html += '<div class="card"><div class="card-header">Trade History</div>';
            if (classic.length === 0) html += '<div class="empty-state">No trades yet</div>';
            else html += '<table><thead><tr><th>Date</th><th>Team</th><th>Action</th><th>Entry #</th><th>Price</th><th>P&L</th><th>Game Time</th><th>Score</th></tr></thead><tbody>' +
                classic.slice(0, 80).map(t => `<tr><td>${fmtTs(t.timestamp)}</td><td>${t.team}</td><td>${t.action}</td><td>${t.entry_number ?? '—'}</td><td>${t.price_cents}¢</td><td class="${(t.pnl_cents || 0) >= 0 ? 'positive' : 'negative'}">${fmt(t.pnl_cents)}</td><td>${fmtGameTime(t)}</td><td>${fmtGameScore(t)}</td></tr>`).join('') + '</tbody></table>';
            html += '</div>';

            document.getElementById('tabTieredClassic').innerHTML = html;
            renderBarChart('chartClassicEntry', ['1 entry', '2 entries', '3+ entries'], [1,2,'3+'].map(k => {
                const arr = entryCounts[k] || [];
                const posIds = [...new Set(arr.filter(t => t.action === 'BUY').map(t => t.position_id))];
                const wins = posIds.filter(pid => classic.some(c => c.position_id === pid && c.pnl_cents > 0));
                return posIds.length ? (wins.length / posIds.length) * 100 : 0;
            }), COLORS.tieredClassic);
        }

        function updateTabHeavy(trades, positions, st) {
            const heavy = trades.filter(t => t.strategy === 'HEAVY_FAVORITE');
            const active = positions.filter(p => p.strategy === 'HEAVY_FAVORITE');

            let html = '<div class="stats-row">';
            html += `<div class="stat-box"><div class="stat-label">Total P&L</div><div class="stat-value ${(st?.total_pnl || 0) >= 0 ? 'positive' : 'negative'}">${fmt(st?.total_pnl)}</div></div>`;
            html += `<div class="stat-box"><div class="stat-label">Win Rate</div><div class="stat-value">${fmtPct(st?.win_rate)}</div></div>`;
            html += '</div>';

            const spreadBuckets = { '8-10': [], '10-12': [], '12+': [] };
            heavy.filter(t => t.action === 'BUY').forEach(t => {
                const sp = t.pre_game_spread ?? t.deficit_vs_spread ?? 0;
                const s = Math.abs(sp);
                if (s >= 12) spreadBuckets['12+'].push(t);
                else if (s >= 10) spreadBuckets['10-12'].push(t);
                else if (s >= 8) spreadBuckets['8-10'].push(t);
            });

            const settled = heavy.filter(t => (t.reason || '').toUpperCase().includes('SETTLE'));
            const settledWins = settled.filter(t => (t.pnl_cents || 0) > 0);

            html += '<div class="card"><div class="card-header">Spread Analysis</div><div class="chart-container"><canvas id="chartHeavySpread"></canvas></div></div>';
            html += '<div class="card"><div class="card-header">Settlement Rate</div><p>Settled: ' + settled.length + ' trades, ' + settledWins.length + ' wins (' + (settled.length ? (settledWins.length / settled.length * 100).toFixed(1) : 0) + '%)</p></div>';
            html += '<div class="card"><div class="card-header">Active Positions</div>';
            if (active.length === 0) html += '<div class="empty-state">No active positions</div>';
            else html += '<table><thead><tr><th>Team</th><th>Entries</th><th>Mode</th></tr></thead><tbody>' +
                active.map(p => `<tr><td>${p.team}</td><td>${p.entry_count}</td><td>${p.current_mode || '—'}</td></tr>`).join('') + '</tbody></table>';
            html += '</div>';
            html += '<div class="card"><div class="card-header">Trade History</div>';
            if (heavy.length === 0) html += '<div class="empty-state">No trades yet</div>';
            else html += '<table><thead><tr><th>Date</th><th>Team</th><th>Action</th><th>Price</th><th>P&L</th><th>Spread</th><th>Game Time</th><th>Score</th></tr></thead><tbody>' +
                heavy.slice(0, 50).map(t => `<tr><td>${fmtTs(t.timestamp)}</td><td>${t.team}</td><td>${t.action}</td><td>${t.price_cents}¢</td><td class="${(t.pnl_cents || 0) >= 0 ? 'positive' : 'negative'}">${fmt(t.pnl_cents)}</td><td>${t.pre_game_spread ?? '—'}</td><td>${fmtGameTime(t)}</td><td>${fmtGameScore(t)}</td></tr>`).join('') + '</tbody></table>';
            html += '</div>';

            document.getElementById('tabHeavy').innerHTML = html;
            renderBarChart('chartHeavySpread', Object.keys(spreadBuckets), Object.values(spreadBuckets).map(arr => {
                const wins = arr.filter(t => heavy.some(c => c.position_id === t.position_id && c.pnl_cents > 0));
                return arr.length ? (wins.length / arr.length) * 100 : 0;
            }), COLORS.heavy);
        }

        function updateTabComparison(trades, stats) {
            let html = '<div class="card"><div class="card-header">Head-to-Head</div><table><thead><tr><th></th><th>Conservative</th><th>Tiered V2</th><th>Tiered Classic</th><th>Heavy Fav</th></tr></thead><tbody>';
            ['win_rate','avg_win','avg_loss','best_trade','worst_trade','total_pnl'].forEach((r, i) => {
                const labels = ['Win Rate','Avg Win','Avg Loss','Best','Worst','Total P&L'];
                html += '<tr><td>' + labels[i] + '</td>';
                ['CONSERVATIVE','TIERED','TIERED_CLASSIC','HEAVY_FAVORITE'].forEach(st => {
                    const v = (stats[st] || {})[r];
                    html += '<td class="' + ((r === 'total_pnl' || r === 'avg_win' || r === 'best_trade') && v > 0 ? 'positive' : (v < 0 ? 'negative' : '')) + '">' + (r === 'win_rate' ? fmtPct(v) : fmt(v)) + '</td>';
                });
                html += '</tr>';
            });
            html += '</tbody></table></div>';

            html += '<div class="card"><div class="card-header">Factor Analysis</div><div class="chart-container"><canvas id="chartFactorQ"></canvas></div></div>';
            const byQuarter = { 1: [], 2: [], 3: [], 4: [] };
            trades.forEach(t => {
                if (t.action === 'BUY' && t.game_quarter) byQuarter[t.game_quarter].push(t);
            });

            html += '<div class="card"><div class="card-header">Auto-Insights</div>';
            const insights = [];
            const cons12 = trades.filter(t => {
                if (t.strategy !== 'CONSERVATIVE' || t.action !== 'BUY') return false;
                const e = t.edge != null ? t.edge : (t.fair_value != null && t.price_cents != null ? (t.fair_value - t.price_cents/100) : null);
                if (e == null) return false;
                const pct = (typeof e === 'number' && e <= 1) ? e * 100 : e;
                return pct >= 12;
            });
            if (cons12.length > 0) {
                const wins = cons12.filter(t => trades.some(c => c.position_id === t.position_id && c.pnl_cents > 0));
                if (wins.length / cons12.length > 0.8) insights.push('Conservative has ' + (wins.length/cons12.length*100).toFixed(0) + '% win rate at 12%+ edge — consider raising minimum.');
            }
            const tieredQ3 = trades.filter(t => t.strategy === 'TIERED' && t.action === 'BUY' && t.game_quarter === 3);
            if (tieredQ3.length > 0) {
                const loss = tieredQ3.filter(t => trades.some(c => c.position_id === t.position_id && c.pnl_cents < 0));
                if (loss.length > tieredQ3.length / 2) insights.push('Tiered loses on Q3 entries — restrict to Q1-Q2.');
            }
            const heavy12 = trades.filter(t => t.strategy === 'HEAVY_FAVORITE' && t.action === 'BUY' && Math.abs(t.pre_game_spread || 0) >= 12);
            if (heavy12.length > 0) {
                const losses = heavy12.filter(t => trades.some(c => c.position_id === t.position_id && c.pnl_cents < 0));
                if (losses.length === 0) insights.push('Heavy Favorite at 12+ spread has never lost.');
            }
            if (insights.length === 0) insights.push('No strong insights yet. Keep trading to gather data.');
            insights.forEach(i => { html += '<div class="insight-card">' + i + '</div>'; });
            html += '</div>';

            html += '<button class="export-btn" onclick="exportTrades()">Export Trades CSV</button>';
            document.getElementById('tabComparison').innerHTML = html;

            try {
                if (chartInstances.factorQ) chartInstances.factorQ.destroy();
                const ctxF = document.getElementById('chartFactorQ');
                if (typeof Chart !== 'undefined' && ctxF) chartInstances.factorQ = new Chart(ctxF, {
                    type: 'bar',
                    data: {
                        labels: ['Q1','Q2','Q3','Q4'],
                        datasets: [{ label: 'Win Rate %', data: [1,2,3,4].map(q => {
                            const arr = byQuarter[q] || [];
                            const wins = arr.filter(t => trades.some(c => c.position_id === t.position_id && c.pnl_cents > 0));
                            return arr.length ? (wins.length / arr.length) * 100 : 0;
                        }), backgroundColor: [COLORS.conservative, COLORS.tiered, COLORS.heavy, '#888'] }]
                    },
                    options: { responsive: true, maintainAspectRatio: false }
                });
            } catch (e) { console.warn('Chart error:', e); }
        }

        async function exportTrades() {
            const trades = await fetchJson('/api/trades?limit=5000');
            if (!trades || trades.length === 0) { alert('No trades to export'); return; }
            const headers = ['timestamp','game_id','team','strategy','action','entry_number','price_cents','shares','total_cents','pnl_cents','reason','game_quarter','deficit_vs_spread','edge','fair_value'];
            const csv = [headers.join(',')].concat(trades.map(t => headers.map(h => '"' + String(t[h] ?? '').replace(/"/g,'""') + '"').join(','))).join('\\n');
            const a = document.createElement('a');
            a.href = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv);
            a.download = 'trades_' + new Date().toISOString().slice(0,10) + '.csv';
            a.click();
        }

        function updateTabSignals(signals) {
            window._allSignals = signals || [];
            const today = new Date().toISOString().slice(0, 10);
            const todaySigs = window._allSignals.filter(s => (s.timestamp || '').slice(0, 10) === today);
            const traded = todaySigs.filter(s => s.action_taken);
            const skipped = todaySigs.filter(s => !s.action_taken);

            let html = '<div class="stats-row"><div class="stat-box"><div class="stat-label">Today: Signals</div><div class="stat-value">' + todaySigs.length + '</div></div>';
            html += '<div class="stat-box"><div class="stat-label">Traded</div><div class="stat-value positive">' + traded.length + '</div></div>';
            html += '<div class="stat-box"><div class="stat-label">Skipped</div><div class="stat-value">' + skipped.length + '</div></div></div>';

            const stratVal = document.getElementById('signalStrategy')?.value || '';
            const outcomeVal = document.getElementById('signalOutcome')?.value || '';
            const stratOpts = [['','All Strategies'],['CONSERVATIVE','Conservative'],['TIERED','Tiered V2'],['TIERED_CLASSIC','Tiered Classic'],['HEAVY_FAVORITE','Heavy Favorite']];
            const outcomeOpts = [['','All'],['traded','Traded'],['skipped','Skipped']];
            html += '<div class="filter-bar"><select id="signalStrategy">';
            stratOpts.forEach(([v,l]) => { html += '<option value="'+v+'"'+(v===stratVal?' selected':'')+'>'+l+'</option>'; });
            html += '</select><select id="signalOutcome">';
            outcomeOpts.forEach(([v,l]) => { html += '<option value="'+v+'"'+(v===outcomeVal?' selected':'')+'>'+l+'</option>'; });
            html += '</select></div>';

            let filtered = window._allSignals;
            if (stratVal) filtered = filtered.filter(s => s.strategy === stratVal);
            if (outcomeVal === 'traded') filtered = filtered.filter(s => s.action_taken);
            if (outcomeVal === 'skipped') filtered = filtered.filter(s => !s.action_taken);

            html += '<div class="card"><table id="signalTable"><thead><tr><th>Timestamp</th><th>Strategy</th><th>Team</th><th>Type</th><th>Deficit</th><th>Edge</th><th>Price Drop</th><th>Kalshi</th><th>Spread</th><th>Conf</th><th>Traded</th><th>Skip Reason</th></tr></thead><tbody id="signalTableBody">';
                filtered.forEach(s => {
                const rowClass = s.action_taken ? 'positive' : '';
                html += '<tr class="' + rowClass + '"><td>' + fmtTs(s.timestamp) + '</td><td>' + (s.strategy || '') + '</td><td>' + (s.team || '') + '</td><td>' + (s.signal_type || '') + '</td><td>' + (s.deficit ?? '—') + '</td><td>' + (s.edge != null ? (s.edge <= 1 ? (s.edge*100).toFixed(1) + '%' : s.edge + '%') : '—') + '</td><td>' + (s.price_drop_pct != null ? (s.price_drop_pct <= 1 ? (s.price_drop_pct*100).toFixed(1) + '%' : s.price_drop_pct + '%') : '—') + '</td><td>' + (s.kalshi_price ?? '—') + '¢</td><td>' + (s.pre_game_spread ?? '—') + '</td><td>' + (s.confidence ?? '—') + '</td><td>' + (s.action_taken ? 'Yes' : 'No') + '</td><td>' + (s.skip_reason || '—') + '</td></tr>';
            });
            html += '</tbody></table></div>';
            document.getElementById('tabSignals').innerHTML = html;
            document.getElementById('signalStrategy')?.addEventListener('change', () => updateTabSignals(window._allSignals || []));
            document.getElementById('signalOutcome')?.addEventListener('change', () => updateTabSignals(window._allSignals || []));
        }

        function renderStrategyGuide() {
            const el = document.getElementById('tabStrategyGuide');
            if (!el) return;
            el.innerHTML = `

<!-- ═══════════ OVERVIEW ═══════════ -->
<div class="card guide-section">
    <h2>How This Bot Works</h2>
    <p>This bot trades NBA "winner" prediction markets on Kalshi. It buys YES contracts on the pre-game favorite
    when that team falls behind early in the game, betting on a comeback. Contracts pay $1.00 if the team wins
    and $0.00 if they lose.</p>
    <p>The bot runs four strategies simultaneously, each with its own bankroll allocation, entry criteria, and
    exit rules. All entries are restricted to Q1 and Q2 &mdash; once halftime hits, no new positions are opened.
    Exits are managed automatically based on price targets, stop losses, and game clock.</p>

    <h3>Bankroll Allocation</h3>
    <div class="guide-grid">
        <div class="guide-param"><span class="label">Conservative:</span> <span class="value">30% ($150)</span></div>
        <div class="guide-param"><span class="label">Tiered (Quick Scalp):</span> <span class="value">30% ($150)</span></div>
        <div class="guide-param"><span class="label">Tiered Classic:</span> <span class="value">30% ($150)</span></div>
        <div class="guide-param"><span class="label">Heavy Favorite:</span> <span class="value">10% ($50)</span></div>
    </div>

    <h3>Key Concepts</h3>
    <ul>
        <li><strong>Deficit vs Spread</strong> &mdash; How much worse the favorite is doing compared to what Vegas expected. A spread of -5 means Vegas expected the favorite to win by 5. If the favorite is currently losing by 8, the deficit vs spread is 13. Higher = more panic = cheaper contracts.</li>
        <li><strong>Price Drop from Tipoff</strong> &mdash; How far the Kalshi contract price has fallen since the game started. A 25% drop means the market now prices the favorite's win probability 25% lower than at tip-off.</li>
        <li><strong>Edge</strong> &mdash; The gap between the Vegas-implied fair value and the current Kalshi price. If Vegas says 45% chance but Kalshi is selling at 30&cent;, the edge is +15%.</li>
        <li><strong>Book Depth</strong> &mdash; Number of contracts available at the current ask price. Ensures there's enough liquidity to fill the order without excessive slippage.</li>
        <li><strong>Game Modes</strong> &mdash; Q1-Q2 = Offensive (buy). Early Q3 = Neutral (hold). Late Q3/Q4 while underwater = Defensive (look to exit).</li>
    </ul>
</div>

<hr class="guide-divider">

<!-- ═══════════ CONSERVATIVE ═══════════ -->
<div class="card guide-section">
    <h2 style="color:var(--conservative)">Strategy 1: Conservative</h2>
    <div class="guide-subtitle">Edge-based. Only enters when Kalshi is provably mispriced vs Vegas consensus.</div>

    <h3>Philosophy</h3>
    <p>The safest strategy. It only buys when the math shows a clear discrepancy between what Vegas thinks and
    what Kalshi is pricing. Single entry per game, no averaging down. Mechanical profit-taking in two stages.</p>

    <h3><span class="guide-badge entry">ENTRY</span> Entry Conditions (all must be true)</h3>
    <ul>
        <li>Quarter 1 or 2 only</li>
        <li>Deficit vs spread &ge; 12</li>
        <li>Edge &ge; 8% (Vegas fair value minus Kalshi price)</li>
        <li>Kalshi ask price &le; 35&cent;</li>
        <li>Order book depth &ge; 100 contracts</li>
    </ul>

    <h3>Position Sizing (% of conservative bankroll)</h3>
    <div class="guide-grid">
        <div class="guide-param"><span class="label">Edge 8-10%:</span> <span class="value">8% of bankroll</span></div>
        <div class="guide-param"><span class="label">Edge 10-12%:</span> <span class="value">12% of bankroll</span></div>
        <div class="guide-param"><span class="label">Edge 12%+:</span> <span class="value">16% of bankroll</span></div>
    </div>

    <h3><span class="guide-badge exit">EXIT</span> Exit Rules</h3>
    <ul>
        <li><strong>Take Profit 1:</strong> Sell 50% of shares at +30% gain</li>
        <li><strong>Take Profit 2:</strong> Sell remaining shares at +60% gain</li>
        <li><strong>Stop Loss:</strong> Sell all at -30%, but only after holding for 12+ minutes AND the deficit is still &ge; 12 (if deficit is shrinking, the thesis may still be alive)</li>
        <li><strong>Thesis Invalid:</strong> Sell all if deficit exceeds 25, it's Q3+, and less than 8 minutes remain (the game is out of reach)</li>
    </ul>

    <div class="guide-example">
        <div class="heading">Example Trade</div>
        Vegas has the Celtics as -5 favorites. Mid Q1, the Hornets go on a run and lead by 8. Deficit vs spread = 13.
        Vegas fair value says 42% Celtics win, but Kalshi is selling at 30&cent; (edge = 12%). Bot buys at 30&cent;.
        Celtics rally in Q2, price climbs to 39&cent; (+30%) &rarr; sell half. Later hits 48&cent; (+60%) &rarr; sell the rest.
    </div>

    <h3>Limits</h3>
    <div class="guide-grid">
        <div class="guide-param"><span class="label">Max concurrent positions:</span> <span class="value">2</span></div>
        <div class="guide-param"><span class="label">Entries per game:</span> <span class="value">1 (no averaging)</span></div>
    </div>
</div>

<hr class="guide-divider">

<!-- ═══════════ TIERED (QUICK SCALP) ═══════════ -->
<div class="card guide-section">
    <h2 style="color:var(--tiered)">Strategy 2: Tiered (Quick Scalp)</h2>
    <div class="guide-subtitle">Buy the dip on close-spread favorites. Quick profit targets with a 2:1 reward/risk dynamic stop loss. Only need to win 1 out of 3 to be profitable.</div>

    <h3>Philosophy</h3>
    <p>The core money-maker. When a close-spread favorite (spread 1-7) gets punched early in the game, their
    Kalshi price dumps to bargain levels. We buy in stages as the price falls, then sell when the team makes
    any sort of comeback and the price bounces. The goal is consistent 10-20% gains with losses capped at half
    the potential gain &mdash; meaning we only need a 33% win rate to break even.</p>

    <h3><span class="guide-badge entry">ENTRY</span> Entry 1 Conditions (all must be true)</h3>
    <ul>
        <li>Quarter 1 or 2 only</li>
        <li>Pre-game spread between 1 and 7 points</li>
        <li>Deficit vs spread &ge; 10</li>
        <li>Price dropped &ge; 25% from tipoff</li>
        <li>Kalshi ask price &le; 35&cent;</li>
        <li>Order book depth &ge; 50 contracts</li>
    </ul>

    <h3><span class="guide-badge entry">ENTRY</span> Entries 2-4 (Averaging Down)</h3>
    <p>If the price keeps dropping, the bot buys more to lower the average cost. Each additional entry requires
    the price to have fallen at least 25% further from the previous entry.</p>
    <ul>
        <li><strong>Entry 2:</strong> Price dropped 25%+ from Entry 1, deficit grew by 8+, at least 6 min left in Q2</li>
        <li><strong>Entry 3-4:</strong> Price dropped 25%+ from previous entry, at least 8 min left in Q2 for Entry 4</li>
    </ul>

    <h3>Position Sizing</h3>
    <div class="guide-grid">
        <div class="guide-param"><span class="label">Entry 1:</span> <span class="value">12% of bankroll (half of 24% game budget)</span></div>
        <div class="guide-param"><span class="label">Entry 2:</span> <span class="value">12% of bankroll (other half of game budget)</span></div>
        <div class="guide-param"><span class="label">Entry 3:</span> <span class="value">12% of bankroll (half of 24% nuclear reserve)</span></div>
        <div class="guide-param"><span class="label">Entry 4:</span> <span class="value">12% of bankroll (other half of nuclear)</span></div>
        <div class="guide-param"><span class="label">Max per game:</span> <span class="value">48% of bankroll</span></div>
    </div>

    <h3><span class="guide-badge exit">EXIT</span> Exit Rules (1-2 entries)</h3>
    <p>Exit strategy depends on the average entry price:</p>

    <p><strong>If average cost &lt; 30&cent; (cheap entries):</strong></p>
    <ul>
        <li>Stage 1: Sell 50% at +17.5% profit (lock in gains early)</li>
        <li>Stage 2: Sell remaining when price hits 40&cent;</li>
    </ul>

    <p><strong>If average cost &ge; 30&cent;:</strong></p>
    <ul>
        <li>Sell all when price hits 48&cent;</li>
    </ul>

    <h3><span class="guide-badge exit">EXIT</span> Capital Recovery Mode (3+ entries)</h3>
    <p>If we've made 3 or more entries, the position is deep. The goal shifts from profit to getting our money back.
    <strong>Sell everything the moment the price reaches the average cost (breakeven or better).</strong></p>

    <h3><span class="guide-badge stop">STOP</span> Dynamic Stop Loss (Q3+ only, 1-2 entries)</h3>
    <p>The stop loss is calculated dynamically to maintain a 2:1 reward-to-risk ratio against the 48&cent; target:</p>
    <ul>
        <li><strong>Formula:</strong> Max loss = half of potential gain to 48&cent;</li>
        <li><code>stop_price = avg_cost - (48 - avg_cost) / 2</code></li>
    </ul>

    <div class="guide-example">
        <div class="heading">Dynamic Stop Examples</div>
        Avg 35&cent; &rarr; Gain to 48&cent; = 13&cent;, max loss = 6.5&cent;, stop at 28.5&cent;<br>
        Avg 32&cent; &rarr; Gain to 48&cent; = 16&cent;, max loss = 8&cent;, stop at 24&cent;<br>
        Avg 25&cent; &rarr; Gain to 48&cent; = 23&cent;, max loss = 11.5&cent;, stop at 13.5&cent;<br>
        Avg 20&cent; &rarr; Gain to 48&cent; = 28&cent;, max loss = 14&cent;, stop at 6&cent;
    </div>

    <p>This means if we win, we make $X. If we lose, we lose $X/2. We only need to win 1 out of 3 trades to break even.</p>

    <h3><span class="guide-badge time">TIME</span> Time Exit</h3>
    <ul>
        <li>Q4 with less than 5 minutes remaining: sell everything regardless of P&L</li>
    </ul>

    <div class="guide-example">
        <div class="heading">Example Trade</div>
        Celtics -4 favorites vs Nets. Nets jump out to a 15-point lead in Q1. Deficit vs spread = 19, price drops
        from 55&cent; to 28&cent; (-49%). Bot buys Entry 1 at 28&cent;. Price keeps falling &rarr; Entry 2 at 21&cent;.
        Average cost now 24.5&cent;. Celtics go on a 12-0 run, price bounces to 29&cent; (+18%) &rarr; sell 50%.
        Game tightens up, price hits 40&cent; &rarr; sell the rest. Net gain: ~15&cent; per share on half, ~16&cent; on the other half.
    </div>

    <h3>Limits</h3>
    <div class="guide-grid">
        <div class="guide-param"><span class="label">Max concurrent positions:</span> <span class="value">3</span></div>
        <div class="guide-param"><span class="label">Max entries per game:</span> <span class="value">4</span></div>
    </div>
</div>

<hr class="guide-divider">

<!-- ═══════════ TIERED CLASSIC ═══════════ -->
<div class="card guide-section">
    <h2 style="color:var(--tiered-classic)">Strategy 2b: Tiered Classic</h2>
    <div class="guide-subtitle">Same entry logic as Tiered, but with the original multiplier-based house money exit system. Run in parallel for A/B comparison.</div>

    <h3>Philosophy</h3>
    <p>This is the "swing for the fences" version. Instead of quick scalps, it uses fixed multiplier profit targets
    (1.75x, 3x, 5x) that sell in stages as the price climbs. It's more patient, aiming for bigger wins at the
    cost of potentially giving back gains. Runs alongside Tiered V2 so we can see which approach performs better
    over time.</p>

    <h3><span class="guide-badge entry">ENTRY</span> Entry Conditions</h3>
    <p>Same as Tiered (Quick Scalp) above, except the max entry price is 40&cent; instead of 35&cent;.</p>

    <h3><span class="guide-badge exit">EXIT</span> Capital Recovery Mode (3+ entries)</h3>
    <p>Same as Tiered: if 3+ entries have been made, sell everything at breakeven or better.</p>

    <h3><span class="guide-badge stop">STOP</span> Universal Stop Loss (Q3+ only)</h3>
    <ul>
        <li>Sell all if price drops 50% below average cost, starting from Q3</li>
    </ul>

    <h3><span class="guide-badge exit">EXIT</span> House Money Exit System (1-2 entries)</h3>
    <p>Profits are taken in stages based on how much the price has multiplied from average cost:</p>
    <ul>
        <li><strong>Capital Recovery (1.75x):</strong> Sell 40% of shares when price reaches 1.75x average cost</li>
        <li><strong>House Money 1 (3x):</strong> Sell 25% of remaining shares at 3x</li>
        <li><strong>House Money 2 (5x):</strong> Sell 30% of remaining at 5x</li>
        <li><strong>Late Game Lock (80&cent;+):</strong> If price &ge; 80&cent; in Q4 with &lt; 3 min left, sell 60% to lock in gains</li>
        <li><strong>Trailing Stop (50%):</strong> After capital is recovered, if price drops 50% from its peak, sell all remaining</li>
    </ul>

    <div class="guide-example">
        <div class="heading">Example Exit Cascade</div>
        Buy 100 shares at avg 20&cent; ($20 cost).<br>
        Price hits 35&cent; (1.75x) &rarr; sell 40 shares at 35&cent; ($14 back, nearly recovered cost).<br>
        Price hits 60&cent; (3x) &rarr; sell 15 of remaining 60 shares ($9).<br>
        Price hits 85&cent; in Q4 with 2 min left &rarr; sell 60% of remaining 45 shares (27 shares at 85&cent; = $23).<br>
        Hold 18 shares for settlement &rarr; if they win, that's $18 more.
    </div>

    <h3><span class="guide-badge stop">STOP</span> Defensive Exits (when losing)</h3>
    <ul>
        <li><strong>Hard Floor:</strong> In Q4, if position value drops below 15% of total invested, sell all</li>
        <li><strong>Sell into Strength:</strong> In defensive mode, if the team shows brief positive momentum (score &gt; 0.3), sell everything to cut losses at a less-bad price</li>
    </ul>

    <h3>Limits</h3>
    <div class="guide-grid">
        <div class="guide-param"><span class="label">Max concurrent positions:</span> <span class="value">3</span></div>
        <div class="guide-param"><span class="label">Max entries per game:</span> <span class="value">4</span></div>
        <div class="guide-param"><span class="label">Max entry price:</span> <span class="value">40&cent; (vs 35&cent; for Tiered V2)</span></div>
    </div>
</div>

<hr class="guide-divider">

<!-- ═══════════ HEAVY FAVORITE ═══════════ -->
<div class="card guide-section">
    <h2 style="color:var(--heavy)">Strategy 3: Heavy Favorite Collapse</h2>
    <div class="guide-subtitle">When a big favorite gets blown out early, buy at panic prices. The wider the spread, the more we bet. Patient exits aiming for settlement.</div>

    <h3>Philosophy</h3>
    <p>This strategy targets rare, high-conviction situations: a team favored by 8+ points is getting demolished
    early. The market panics and dumps the contract to rock-bottom prices. But heavy favorites exist for a reason &mdash;
    they have superior talent. The wider the Vegas spread, the more confident we are in a comeback, and the bigger
    we size the position. Exits are more patient than Tiered, often holding for settlement (full $1.00 payout).</p>

    <h3><span class="guide-badge entry">ENTRY</span> Entry 1 Conditions</h3>
    <ul>
        <li>Quarter 1 or early Q2 (at least 8 min left in Q2)</li>
        <li>Pre-game spread &ge; 8 points (big favorite)</li>
        <li>Deficit vs spread &ge; 15</li>
        <li>Kalshi ask price &le; 30&cent;</li>
        <li>Order book depth &ge; 50 contracts</li>
    </ul>

    <h3><span class="guide-badge entry">ENTRY</span> Entries 2-4</h3>
    <p>Same averaging-down logic as Tiered, but position sizing is scaled by the spread:</p>
    <div class="guide-grid">
        <div class="guide-param"><span class="label">Spread 8-10:</span> <span class="value">1.0x base budget</span></div>
        <div class="guide-param"><span class="label">Spread 10-12:</span> <span class="value">1.25x base budget</span></div>
        <div class="guide-param"><span class="label">Spread 12+:</span> <span class="value">1.5x base budget</span></div>
    </div>

    <h3><span class="guide-badge exit">EXIT</span> House Money System (Patient)</h3>
    <p>Higher multiplier targets than Tiered Classic because we have more conviction:</p>
    <ul>
        <li><strong>Capital Recovery (2x):</strong> Sell 35% at 2x average cost</li>
        <li><strong>House Money 1 (3x):</strong> Sell 20% at 3x</li>
        <li><strong>House Money 2 (60&cent;+):</strong> Sell 20% when price hits 60&cent;</li>
        <li><strong>Trailing Stop (40%):</strong> After recovery, sell all if price drops 40% from peak (tighter than Classic because we expect these to resolve decisively)</li>
    </ul>

    <h3><span class="guide-badge stop">STOP</span> Defensive Exits</h3>
    <ul>
        <li><strong>Hard Floor:</strong> In Q4, sell all if position value &lt; 15% of cost</li>
        <li><strong>Sell into Strength:</strong> In defensive mode, sell into any positive momentum</li>
    </ul>

    <div class="guide-example">
        <div class="heading">Example Trade</div>
        Bucks -12 favorites vs Wizards. Wizards go on a 20-2 run to start. Deficit vs spread = 30, price
        crashes from 80&cent; to 18&cent;. Bot buys Entry 1 at 18&cent; with 1.5x sizing (spread 12+). Entry 2 at 12&cent;.
        Avg cost: 15&cent;. Bucks stage a furious comeback. Price hits 30&cent; (2x) &rarr; sell 35%. Hits 45&cent; (3x) &rarr;
        sell 20%. Hits 60&cent; &rarr; sell 20%. Hold the rest &mdash; Bucks win, remaining shares pay out at $1.00.
    </div>

    <h3>Limits</h3>
    <div class="guide-grid">
        <div class="guide-param"><span class="label">Max concurrent positions:</span> <span class="value">2</span></div>
        <div class="guide-param"><span class="label">Max entries per game:</span> <span class="value">4</span></div>
    </div>
</div>

<hr class="guide-divider">

<!-- ═══════════ RISK MANAGEMENT ═══════════ -->
<div class="card guide-section">
    <h2>Global Risk Management</h2>
    <div class="guide-subtitle">Safeguards that apply across all strategies to prevent catastrophic losses.</div>
    <ul>
        <li><strong>Daily Loss Limit (30%):</strong> If any strategy loses 30% of its bankroll in a single day on a game, that game is paused for that strategy</li>
        <li><strong>Weekly Loss Limit (25%):</strong> If a strategy loses 25% of its bankroll in a week, the entire strategy is paused pending review</li>
        <li><strong>Global Hard Floor (60%):</strong> If total bankroll drops below 60% of starting balance, all trading halts</li>
        <li><strong>Liquidity Cap (30%):</strong> Never consume more than 30% of visible order book depth in a single order</li>
        <li><strong>No Late Trading:</strong> No new entries in the final 2 minutes of any game</li>
        <li><strong>Slippage Alert (3&cent;):</strong> Alert if average execution slippage exceeds 3&cent;</li>
        <li><strong>Duplicate Prevention:</strong> PID lockfile prevents multiple bot instances; database-level check prevents duplicate Entry 1s</li>
    </ul>
</div>

<hr class="guide-divider">

<!-- ═══════════ STRATEGY COMPARISON ═══════════ -->
<div class="card guide-section">
    <h2>Strategy Comparison at a Glance</h2>
    <table style="font-size:12px">
        <thead>
            <tr><th></th><th style="color:var(--conservative)">Conservative</th><th style="color:var(--tiered)">Tiered (Quick Scalp)</th><th style="color:var(--tiered-classic)">Tiered Classic</th><th style="color:var(--heavy)">Heavy Favorite</th></tr>
        </thead>
        <tbody>
            <tr><td>Bankroll</td><td>30%</td><td>30%</td><td>30%</td><td>10%</td></tr>
            <tr><td>Entries per game</td><td>1</td><td>Up to 4</td><td>Up to 4</td><td>Up to 4</td></tr>
            <tr><td>Max entry price</td><td>35&cent;</td><td>35&cent;</td><td>40&cent;</td><td>30&cent;</td></tr>
            <tr><td>Min spread</td><td>Any</td><td>1-7 pts</td><td>1-7 pts</td><td>8+ pts</td></tr>
            <tr><td>Edge required</td><td>8%+</td><td>No</td><td>No</td><td>No</td></tr>
            <tr><td>Profit style</td><td>2-stage TP</td><td>Quick scalp / 48&cent;</td><td>House money (1.75x/3x/5x)</td><td>Patient house money (2x/3x/60&cent;)</td></tr>
            <tr><td>Stop loss</td><td>-30% (12m hold)</td><td>Dynamic 2:1 R/R (Q3+)</td><td>-50% (Q3+)</td><td>Hard floor (Q4)</td></tr>
            <tr><td>Risk profile</td><td>Low</td><td>Medium</td><td>Medium-High</td><td>High (rare, big)</td></tr>
        </tbody>
    </table>
</div>
`;
        }

        setInterval(() => {
            refreshTimer--;
            document.getElementById('refreshCountdown').textContent = 'Refresh in ' + refreshTimer + 's';
            if (refreshTimer <= 0) refreshData();
        }, 1000);

        initTabs();
        renderStrategyGuide();
        refreshData();
    </script>
</body>
</html>
"""
