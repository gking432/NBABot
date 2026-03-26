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
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700&display=swap');
        :root {
            --bg: #f5f6f9;
            --surface: #ffffff;
            --card: #ffffff;
            --border: #e4e8f0;
            --text: #111827;
            --muted: #6b7280;
            --conservative: #4fc3f7;
            --tiered: #66bb6a;
            --tiered-classic: #ab47bc;
            --heavy: #ffa726;
            --conservative-hold: #26c6da;
            --conservative-hold-flip: #00838f;
            --tiered-hold: #9ccc65;
            --tiered-hold-flip: #558b2f;
            --tiered-classic-hold: #ce93d8;
            --tiered-flip: #2e7d32;
            --pulse: #ff5252;
            --positive: #1f9d55;
            --negative: #d14343;
        }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            font-family: "SF Pro Display", "SF Pro Text", "Manrope", "Helvetica Neue", sans-serif;
            background: radial-gradient(1200px 600px at 10% -20%, #ffffff 0%, var(--bg) 70%);
            color: var(--text);
            min-height: 100vh;
        }
        .top-bar {
            display: grid; grid-template-columns: auto 1fr auto auto auto auto auto; gap: 12px; padding: 12px 20px;
            background: var(--surface); border-bottom: 1px solid var(--border);
        }
        .status-dot { width: 12px; height: 12px; border-radius: 50%; }
        .status-dot.running { background: var(--positive); }
        .status-dot.paused { background: var(--negative); }
        .mode-badge { padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        .mode-badge.paper { background: #dbeafe; color: #1e3a8a; }
        .mode-badge.live { background: #fee2e2; color: #7f1d1d; }
        .live-games-panel {
            display: flex; gap: 12px; padding: 12px 20px; overflow-x: auto;
            background: var(--surface); border-bottom: 1px solid var(--border); min-height: 140px;
        }
        .game-card {
            flex: 0 0 280px; padding: 12px; border-radius: 12px; border: 1px solid var(--border);
            background: var(--card); min-width: 280px; box-shadow: 0 10px 24px rgba(18,24,38,0.08);
        }
        .game-card.profit { border-color: var(--positive); }
        .game-card.loss { border-color: var(--negative); }
        .game-score { font-size: 18px; font-weight: bold; margin-bottom: 4px; }
        .game-meta { font-size: 12px; color: var(--muted); }
        .game-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; font-size: 11px; margin-top: 8px; }
        .signal-dots { display: flex; gap: 4px; margin-top: 6px; }
        .signal-dot { width: 8px; height: 8px; border-radius: 50%; }
        .signal-dot.conservative { background: var(--conservative); }
        .signal-dot.tiered { background: var(--tiered); }
        .signal-dot.tiered-classic { background: var(--tiered-classic); }
        .signal-dot.heavy { background: var(--heavy); }
        .signal-dot.conservative-hold { background: var(--conservative-hold); }
        .signal-dot.conservative-hold-flip { background: var(--conservative-hold-flip); }
        .signal-dot.tiered-hold { background: var(--tiered-hold); }
        .signal-dot.tiered-hold-flip { background: var(--tiered-hold-flip); }
        .signal-dot.tiered-classic-hold { background: var(--tiered-classic-hold); }
        .signal-dot.tiered-flip { background: var(--tiered-flip); }
        .signal-dot.pulse { background: var(--pulse); }
        .tab-nav {
            display: flex; gap: 6px; padding: 10px 20px; background: var(--surface);
            border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 100; flex-wrap: wrap;
        }
        .tab-btn {
            padding: 6px 12px; border: 1px solid transparent; background: #f3f4f6; color: var(--text);
            cursor: pointer; border-radius: 999px; font-weight: 600; font-size: 12px;
        }
        .tab-btn:hover { background: #e8ecf2; }
        .tab-btn.active { background: #111827; border-color: #111827; color: #ffffff; }
        .tab-content { display: none; padding: 20px; min-height: 500px; }
        .tab-content.active { display: block; }
        .card {
            background: var(--card); border: 1px solid var(--border); border-radius: 16px; padding: 18px;
            margin-bottom: 16px; box-shadow: 0 12px 30px rgba(18,24,38,0.08);
        }
        .card-header { font-weight: 700; margin-bottom: 12px; font-size: 14px; letter-spacing: 0.2px; }
        .strategy-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }
        .strategy-card { padding: 16px; border-radius: 12px; border: 1px solid var(--border); background: #fbfcfe; }
        .strategy-card.conservative .card-header { color: var(--conservative); }
        .strategy-card.tiered .card-header { color: var(--tiered); }
        .strategy-card.tiered-classic .card-header { color: var(--tiered-classic); }
        .strategy-card.heavy .card-header { color: var(--heavy); }
        .strategy-card.conservative-hold .card-header { color: var(--conservative-hold); }
        .strategy-card.conservative-hold-flip .card-header { color: var(--conservative-hold-flip); }
        .strategy-card.tiered-hold .card-header { color: var(--tiered-hold); }
        .strategy-card.tiered-hold-flip .card-header { color: var(--tiered-hold-flip); }
        .strategy-card.tiered-classic-hold .card-header { color: var(--tiered-classic-hold); }
        .strategy-card.tiered-flip .card-header { color: var(--tiered-flip); }
        .strategy-card.pulse .card-header { color: var(--pulse); }
        .overview-grid { display: grid; grid-template-columns: minmax(0, 2.2fr) minmax(0, 1fr); gap: 20px; }
        table { width: 100%; border-collapse: collapse; font-size: 13px; }
        th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid var(--border); }
        th { background: var(--card); position: sticky; top: 0; }
        tr:nth-child(even) { background: #f8fafc; }
        .positive { color: var(--positive); }
        .negative { color: var(--negative); }
        .activity-feed { max-height: 520px; overflow-y: auto; }
        .activity-item { padding: 8px; border-bottom: 1px solid var(--border); font-size: 12px; color: var(--muted); }
        .position-ledger { display: flex; flex-direction: column; gap: 12px; }
        .ledger-pos {
            border: 1px solid var(--border); border-radius: 12px; overflow: hidden;
            background: #fbfcfe; box-shadow: 0 4px 14px rgba(18,24,38,0.06);
        }
        .ledger-pos-head {
            display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: space-between; gap: 8px;
            padding: 10px 14px; background: linear-gradient(180deg, #f1f5f9 0%, #e8eef5 100%);
            border-bottom: 1px solid var(--border);
        }
        .ledger-pos-title { font-weight: 700; font-size: 13px; color: var(--text); }
        .ledger-pos-title .strat-pill {
            display: inline-block; margin-left: 8px; padding: 2px 8px; border-radius: 999px;
            font-size: 10px; font-weight: 700; letter-spacing: 0.03em; background: #111827; color: #fff;
        }
        .ledger-pos-stats {
            display: flex; flex-wrap: wrap; gap: 14px; font-size: 11px; color: var(--muted);
        }
        .ledger-pos-stats span strong { color: var(--text); font-weight: 600; }
        .ledger-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; }
        .ledger-table { width: 100%; border-collapse: collapse; font-size: 12px; min-width: 520px; }
        .ledger-table th {
            text-align: left; padding: 6px 12px; background: #fff; color: var(--muted);
            font-weight: 700; font-size: 10px; text-transform: uppercase; letter-spacing: 0.06em;
            border-bottom: 1px solid var(--border);
        }
        .ledger-table td { padding: 8px 12px; border-bottom: 1px solid var(--border); vertical-align: middle; }
        .ledger-table tr:last-child td { border-bottom: none; }
        .ledger-side-long { color: var(--positive); font-weight: 700; font-size: 11px; }
        .ledger-side-reduce { color: #b45309; font-weight: 700; font-size: 11px; }
        .ledger-side-close { color: var(--negative); font-weight: 700; font-size: 11px; }
        .ledger-settle-win { color: var(--positive); font-weight: 700; font-size: 11px; }
        .ledger-settle-loss { color: var(--negative); font-weight: 700; font-size: 11px; }
        .ledger-mono { font-variant-numeric: tabular-nums; }
        .chart-container { position: relative; height: 250px; margin-bottom: 20px; }
        .stats-row { display: flex; flex-wrap: wrap; gap: 16px; margin-bottom: 20px; }
        .stat-box { padding: 12px 16px; background: #f8fafc; border-radius: 12px; border: 1px solid var(--border); }
        .stat-label { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.4px; }
        .stat-value { font-size: 18px; font-weight: bold; }
        .filter-bar { display: flex; gap: 12px; margin-bottom: 16px; align-items: center; }
        .filter-bar select { padding: 6px 12px; background: #f8fafc; border: 1px solid var(--border); color: var(--text); border-radius: 8px; }
        .export-btn { padding: 8px 16px; background: #111827; color: #ffffff; border: none; border-radius: 12px; cursor: pointer; font-weight: 700; }
        .export-btn:hover { opacity: 0.9; }
        .insight-card { padding: 12px; background: #f8fafc; border-left: 4px solid var(--tiered); margin-bottom: 8px; font-size: 13px; color: var(--muted); }
        .empty-state { padding: 40px; text-align: center; color: var(--muted); }
        .guide-section { margin-bottom: 32px; }
        .guide-section h2 { margin: 0 0 4px 0; font-size: 20px; }
        .guide-section h3 { margin: 16px 0 6px 0; font-size: 15px; color: var(--muted); }
        .guide-subtitle { font-size: 13px; color: var(--muted); margin-bottom: 12px; }
        .guide-section p, .guide-section li { font-size: 13px; line-height: 1.6; color: var(--muted); }
        .guide-section ul { padding-left: 20px; margin: 4px 0 8px 0; }
        .guide-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 8px 0; }
        .guide-param { padding: 8px 12px; background: #f8fafc; border-radius: 10px; font-size: 12px; }
        .guide-param .label { color: var(--muted); }
        .guide-param .value { color: var(--text); font-weight: bold; }
        .guide-example { background: #f8fafc; border-left: 3px solid var(--border); padding: 10px 14px; margin: 8px 0; font-size: 12px; line-height: 1.7; border-radius: 0 10px 10px 0; }
        .guide-example .heading { color: var(--muted); font-weight: bold; margin-bottom: 4px; }
        .guide-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; margin-right: 6px; }
        .guide-badge.entry { background: #1b5e20; color: #a5d6a7; }
        .guide-badge.exit { background: #b71c1c; color: #ef9a9a; }
        .guide-badge.stop { background: #e65100; color: #ffcc80; }
        .guide-badge.time { background: #283593; color: #9fa8da; }
        .guide-divider { border: none; border-top: 1px solid var(--border); margin: 24px 0; opacity: 0.7; }
        @media (max-width: 768px) { .guide-grid { grid-template-columns: 1fr; } }
        .games-toggle {
            display: flex; align-items: center; gap: 8px; padding: 8px 20px; cursor: pointer;
            background: var(--surface); border-bottom: 1px solid var(--border); user-select: none;
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

            .strategy-cards { grid-template-columns: repeat(4, 1fr) !important; gap: 8px; }
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

            .activity-feed { max-height: 280px; }
            .activity-item { font-size: 10px; padding: 6px; word-break: break-word; white-space: normal; }
            .ledger-pos-head { flex-direction: column; align-items: stretch !important; }
            .ledger-table { font-size: 10px; min-width: 480px; }
            .ledger-table th, .ledger-table td { padding: 5px 6px; }

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
            .strategy-cards { grid-template-columns: repeat(2, 1fr) !important; }
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
        <button class="tab-btn" data-tab="bounceback">Bounceback</button>
        <button class="tab-btn" data-tab="conservativeHold">Conservative Hold</button>
        <button class="tab-btn" data-tab="conservativeHoldFlip">Conservative Hold Flip</button>
        <button class="tab-btn" data-tab="tieredHold">Tiered Hold</button>
        <button class="tab-btn" data-tab="tieredHoldFlip">Tiered Hold Flip</button>
        <button class="tab-btn" data-tab="tieredClassicHold">Tiered Classic Hold</button>
        <button class="tab-btn" data-tab="tieredFlip">Tiered Flip</button>
        <button class="tab-btn" data-tab="pulse">Pulse</button>
        <button class="tab-btn" data-tab="comparison">Comparison</button>
        <button class="tab-btn" data-tab="signals">Signal Log</button>
        <button class="tab-btn" data-tab="strategyGuide">Strategy Guide</button>
    </div>

    <div id="tabOverview" class="tab-content active"></div>
    <div id="tabConservative" class="tab-content"></div>
    <div id="tabTiered" class="tab-content"></div>
    <div id="tabTieredClassic" class="tab-content"></div>
    <div id="tabBounceback" class="tab-content"></div>
    <div id="tabConservativeHold" class="tab-content"></div>
    <div id="tabConservativeHoldFlip" class="tab-content"></div>
    <div id="tabTieredHold" class="tab-content"></div>
    <div id="tabTieredHoldFlip" class="tab-content"></div>
    <div id="tabTieredClassicHold" class="tab-content"></div>
    <div id="tabTieredFlip" class="tab-content"></div>
    <div id="tabPulse" class="tab-content"></div>
    <div id="tabComparison" class="tab-content"></div>
    <div id="tabSignals" class="tab-content"></div>
    <div id="tabStrategyGuide" class="tab-content"></div>

    <script>
        const COLORS = {
            conservative: '#4fc3f7',
            tiered: '#66bb6a',
            tieredClassic: '#ab47bc',
            heavy: '#ffa726',
            conservativeHold: '#26c6da',
            conservativeHoldFlip: '#00838f',
            tieredHold: '#9ccc65',
            tieredHoldFlip: '#558b2f',
            tieredClassicHold: '#ce93d8',
            tieredFlip: '#2e7d32',
            pulse: '#ff5252'
        };
        const STRATEGIES = [
            'CONSERVATIVE', 'TIERED', 'TIERED_CLASSIC', 'GARBAGE_TIME',
            'CONSERVATIVE_HOLD', 'CONSERVATIVE_HOLD_FLIP',
            'TIERED_HOLD', 'TIERED_HOLD_FLIP', 'TIERED_CLASSIC_HOLD',
            'TIERED_FLIP', 'PULSE'
        ];
        const STRATEGY_LABELS = {
            CONSERVATIVE: 'Conservative',
            TIERED: 'Tiered V2',
            TIERED_CLASSIC: 'Tiered Classic',
            GARBAGE_TIME: 'Bounceback',
            HEAVY_FAVORITE: 'Bounceback',
            CONSERVATIVE_HOLD: 'Conservative Hold',
            CONSERVATIVE_HOLD_FLIP: 'Conservative Hold Flip',
            TIERED_HOLD: 'Tiered Hold',
            TIERED_HOLD_FLIP: 'Tiered Hold Flip',
            TIERED_CLASSIC_HOLD: 'Tiered Classic Hold',
            TIERED_FLIP: 'Tiered Flip',
            PULSE: 'Pulse'
        };
        function canonicalStrategy(strat) {
            if (strat == null || strat === '') return '';
            const s = String(strat).trim();
            const bounceAliases = ['HEAVY_FAVORITE', 'Heavy Favorite', 'heavy_favorite', 'Heavy_Favorite', 'HEAVY FAVORITE'];
            if (bounceAliases.indexOf(s) >= 0) return 'GARBAGE_TIME';
            if (s.replace(/\s+/g, '_').toUpperCase() === 'HEAVY_FAVORITE') return 'GARBAGE_TIME';
            return s;
        }
        function stratDisplay(strat) {
            const c = canonicalStrategy(strat);
            return STRATEGY_LABELS[strat] || STRATEGY_LABELS[c] || (c || '').replace(/_/g, ' ');
        }
        let chartInstances = {};
        let refreshTimer = 10;
        let lastDataSignature = null;

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
        function getDateLocal(ts) {
            if (!ts) return '';
            let s = String(ts).trim().replace(' ', 'T');
            if (!s.endsWith('Z') && !/[+-]\\d{2}:\\d{2}$/.test(s)) s += 'Z';
            const d = new Date(s);
            return isNaN(d.getTime()) ? '' : d.toLocaleDateString('en-CA', { timeZone: 'America/Chicago' });
        }
        function todayChicago() { return new Date().toLocaleDateString('en-CA', { timeZone: 'America/Chicago' }); }
        function yesterdayChicago() { const d = new Date(); d.setDate(d.getDate() - 1); return d.toLocaleDateString('en-CA', { timeZone: 'America/Chicago' }); }
        function escHtml(s) {
            return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }
        function ledgerSideLabel(action) {
            if (action === 'BUY') return '<span class="ledger-side-long">OPEN / ADD</span>';
            if (action === 'SELL_PARTIAL') return '<span class="ledger-side-reduce">REDUCE</span>';
            if (action === 'SELL_ALL') return '<span class="ledger-side-close">CLOSE</span>';
            if (action === 'SETTLED_WIN') return '<span class="ledger-settle-win">SETTLE WIN</span>';
            if (action === 'SETTLED_LOSS') return '<span class="ledger-settle-loss">SETTLE LOSS</span>';
            return '<span class="ledger-mono">' + escHtml(action) + '</span>';
        }
        function ledgerRowDetail(t) {
            if (t.action === 'BUY') {
                const en = t.entry_number != null ? '#' + t.entry_number : '';
                const q = t.game_quarter != null ? 'Q' + t.game_quarter : '';
                const gt = fmtGameTime(t);
                const bits = ['Fill' + en, q, gt !== '—' ? gt : ''].filter(Boolean);
                return bits.join(' · ');
            }
            return (t.reason || '—').slice(0, 100);
        }
        function parseTsMs(ts) {
            if (!ts) return 0;
            let s = String(ts).trim().replace(' ', 'T');
            if (!s.endsWith('Z') && !/[+-]\\d{2}:\\d{2}$/.test(s)) s += 'Z';
            const n = new Date(s).getTime();
            return Number.isNaN(n) ? 0 : n;
        }
        function computePositionMetrics(rows) {
            let buyShares = 0, buyCost = 0, sellShares = 0, totalPnl = 0;
            rows.forEach(t => {
                const sh = Number(t.shares) || 0;
                if (t.action === 'BUY') {
                    buyShares += sh;
                    buyCost += t.total_cents != null ? t.total_cents : sh * (t.price_cents || 0);
                }
                if (t.action === 'SELL_PARTIAL' || t.action === 'SELL_ALL' || t.action === 'SETTLED_WIN' || t.action === 'SETTLED_LOSS') {
                    sellShares += sh;
                }
                if (t.pnl_cents != null) totalPnl += t.pnl_cents;
            });
            const avgEntry = buyShares > 0 ? buyCost / buyShares : 0;
            const remaining = buyShares - sellShares;
            const status = remaining > 0.001 ? 'OPEN' : 'CLOSED';
            return { buyShares, avgEntry, totalPnl, status, remaining };
        }
        function positionKey(t) {
            return t.position_id || ((t.game_id || '') + '|' + (t.strategy || '') + '|' + (t.team || ''));
        }
        function groupTradesByPosition(tradeList) {
            const m = {};
            tradeList.forEach(t => {
                const pid = positionKey(t);
                if (!m[pid]) m[pid] = [];
                m[pid].push(t);
            });
            Object.keys(m).forEach(k => {
                m[k].sort((a, b) => parseTsMs(a.timestamp) - parseTsMs(b.timestamp));
            });
            return m;
        }
        /** Keep every fill for positions whose *first* trade (open) falls on the selected Chicago date — so exits after midnight UTC still show with that session. */
        function filterTradesByPositionOpenDate(tradeList, dateVal) {
            if (!tradeList || tradeList.length === 0) return [];
            if (dateVal === 'all') return tradeList.slice();
            const groups = groupTradesByPosition(tradeList);
            const today = todayChicago();
            const yesterday = yesterdayChicago();
            const target = dateVal === 'today' ? today : (dateVal === 'yesterday' ? yesterday : null);
            if (!target) return tradeList.slice();
            const keep = new Set();
            Object.keys(groups).forEach(pid => {
                const rows = groups[pid];
                const openChicagoDate = getDateLocal(rows[0].timestamp);
                if (openChicagoDate === target) keep.add(pid);
            });
            return tradeList.filter(t => keep.has(positionKey(t)));
        }
        function buildPositionLedgerInner(tradeList, dateVal) {
            const filtered = filterTradesByPositionOpenDate(tradeList, dateVal);
            if (filtered.length === 0) {
                return '<div class="empty-state">No positions for this filter</div>';
            }
            const groups = groupTradesByPosition(filtered);
            const pids = Object.keys(groups).sort((a, b) => {
                const ra = groups[a], rb = groups[b];
                return parseTsMs(rb[rb.length - 1].timestamp) - parseTsMs(ra[ra.length - 1].timestamp);
            }).slice(0, 50);
            return '<div class="position-ledger">' + pids.map(pid => {
                const rows = groups[pid];
                const first = rows[0];
                const meta = computePositionMetrics(rows);
                const pnlCls = meta.totalPnl > 0 ? 'positive' : (meta.totalPnl < 0 ? 'negative' : '');
                const statHtml = meta.status === 'OPEN'
                    ? '<strong style="color:var(--positive)">OPEN</strong>'
                    : '<strong style="color:var(--muted)">CLOSED</strong>';
                let block = '<div class="ledger-pos"><div class="ledger-pos-head">';
                block += '<div class="ledger-pos-title">' + escHtml(first.team || '—') + ' <span class="strat-pill">' + escHtml(stratDisplay(first.strategy)) + '</span></div>';
                block += '<div class="ledger-pos-stats">';
                block += '<span><strong>Avg entry</strong> ' + (meta.avgEntry > 0 ? meta.avgEntry.toFixed(1) + '¢' : '—') + '</span>';
                block += '<span><strong>Contracts in</strong> ' + meta.buyShares + '</span>';
                if (meta.status === 'OPEN') block += '<span><strong>Remaining</strong> ~' + (meta.remaining > 0 ? Math.round(meta.remaining) : 0) + '</span>';
                block += '<span><strong>Realized P&amp;L</strong> <span class="' + pnlCls + '">' + fmt(meta.totalPnl) + '</span></span>';
                block += '<span>' + statHtml + '</span>';
                block += '</div></div>';
                block += '<div class="ledger-wrap"><table class="ledger-table"><thead><tr>';
                block += '<th>Time</th><th>Side</th><th>Qty</th><th>Price</th><th>Notional</th><th>Leg P&amp;L</th><th>Notes</th>';
                block += '</tr></thead><tbody>';
                block += rows.map(t => {
                    const legPnl = t.action !== 'BUY' && t.pnl_cents != null ? fmt(t.pnl_cents) : '—';
                    const legCls = (t.pnl_cents || 0) > 0 ? 'positive' : ((t.pnl_cents || 0) < 0 ? 'negative' : '');
                    const nom = t.total_cents != null && t.total_cents > 0 ? fmt(t.total_cents) : '—';
                    const pc = t.price_cents != null ? t.price_cents + '¢' : '—';
                    return '<tr><td class="ledger-mono">' + fmtTs(t.timestamp) + '</td><td>' + ledgerSideLabel(t.action) + '</td><td class="ledger-mono">' + (t.shares != null ? t.shares : '—') + '</td><td class="ledger-mono">' + pc + '</td><td class="ledger-mono">' + nom + '</td><td class="ledger-mono ' + legCls + '">' + legPnl + '</td><td style="font-size:11px;color:var(--muted);max-width:220px">' + escHtml(ledgerRowDetail(t)) + '</td></tr>';
                }).join('');
                block += '</tbody></table></div></div>';
                return block;
            }).join('') + '</div>';
        }
        function filterActivityFeed() {
            const sel = document.getElementById('activityDateFilter');
            const feed = document.getElementById('activityFeed');
            if (!sel || !feed || !window._ledgerTrades) return;
            feed.innerHTML = buildPositionLedgerInner(window._ledgerTrades, sel.value);
        }
        function fmtTs(ts) {
            if (!ts) return '—';
            let s = String(ts).trim().replace(' ', 'T');
            if (!s) return '—';
            if (!s.endsWith('Z') && !/[+-]\\d{2}:\\d{2}$/.test(s)) s += 'Z';
            const d = new Date(s);
            if (isNaN(d.getTime())) return '—';
            return d.toLocaleString('en-US', { timeZone: 'America/Chicago' });
        }
        function latestTs(arr) {
            if (!arr || arr.length === 0) return '';
            const ts = arr[0].timestamp || arr[0].date;
            if (!ts) return '';
            return ts;
        }
        function computeStatsSignature(stats) {
            return STRATEGIES.map(s => {
                const st = stats[s] || {};
                return [
                    st.total_trades ?? 0,
                    st.total_pnl ?? 0,
                    st.win_rate ?? 0
                ].join(':');
            }).join('|');
        }
        function captureScrollState() {
            const activity = document.querySelector('#tabOverview .activity-feed');
            return {
                windowScroll: window.scrollY,
                activeTabId: document.querySelector('.tab-content.active')?.id || '',
                activityScroll: activity ? activity.scrollTop : null,
            };
        }
        function restoreScrollState(state) {
            if (!state) return;
            if (typeof state.windowScroll === 'number') {
                window.scrollTo(0, state.windowScroll);
            }
            const activity = document.querySelector('#tabOverview .activity-feed');
            if (activity && state.activityScroll != null) {
                activity.scrollTop = state.activityScroll;
            }
        }

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
                    fetchJson('/api/trades?limit=500'),
                    fetchJson('/api/signals?limit=500'),
                    fetchJson('/api/positions/active'),
                    fetchJson('/api/performance?days=30')
                ]);

                const stats = {};
                for (const s of STRATEGIES) {
                    stats[s] = await fetchJson('/api/stats/' + s) || {};
                }

                if (status) {
                    updateTopBar(status);
                    updateLiveGames(status, signals || []);
                    document.getElementById('statusText').textContent = status.running ? 'Running' : 'Paused';
                } else {
                    document.getElementById('statusText').textContent = 'API error (see console)';
                }
                const signature = [
                    (trades || []).length,
                    latestTs(trades || []),
                    (signals || []).length,
                    latestTs(signals || []),
                    (positions || []).length,
                    (performance || []).length,
                    latestTs(performance || []),
                    computeStatsSignature(stats)
                ].join('|');

                if (signature !== lastDataSignature) {
                    const scrollState = captureScrollState();
                    const s = status || {};
                    updateTabOverview(s, trades || [], signals || [], performance || [], stats);
                    updateTabConservative(trades || [], positions || [], stats.CONSERVATIVE || {});
                    updateTabTiered(trades || [], positions || [], stats.TIERED || {});
                    updateTabTieredClassic(trades || [], positions || [], stats.TIERED_CLASSIC || {});
                    updateTabBounceback(trades || [], positions || [], stats.GARBAGE_TIME || {});
                    updateTabConservativeHold(trades || [], positions || [], stats.CONSERVATIVE_HOLD || {});
                    updateTabConservativeHoldFlip(trades || [], positions || [], stats.CONSERVATIVE_HOLD_FLIP || {});
                    updateTabTieredHold(trades || [], positions || [], stats.TIERED_HOLD || {});
                    updateTabTieredHoldFlip(trades || [], positions || [], stats.TIERED_HOLD_FLIP || {});
                    updateTabTieredClassicHold(trades || [], positions || [], stats.TIERED_CLASSIC_HOLD || {});
                    updateTabTieredFlip(trades || [], positions || [], stats.TIERED_FLIP || {});
                    updateTabPulse(trades || [], positions || [], stats.PULSE || {});
                    updateTabComparison(trades || [], stats);
                    updateTabSignals(signals || []);
                    lastDataSignature = signature;
                    requestAnimationFrame(() => restoreScrollState(scrollState));
                }

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
                    recentByGame[sig.game_id].add(canonicalStrategy(sig.strategy));
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
                    const bid = pos.current_bid_cents ?? g.kalshi_bid ?? 0;
                    const val = (pos.shares_remaining || 0) * bid;
                    borderClass = val > cost ? 'profit' : 'loss';
                }
                const priceDisplay = g.kalshi_bid != null || g.kalshi_ask != null
                    ? `Bid: ${g.kalshi_bid ?? '—'}¢ / Ask: ${g.kalshi_ask ?? '—'}¢`
                    : (g.kalshi_last != null ? `Last: ${g.kalshi_last}¢` : (g.kalshi_ticker ? 'Matched (no quotes)' : 'No Kalshi market'));
                const isPre = (g.status || '').toLowerCase() === 'pre';
                const timeDisplay = isPre && g.start_time
                    ? (() => { const d = new Date(g.start_time); return isNaN(d.getTime()) ? '—' : d.toLocaleTimeString('en-US', { timeZone: 'America/Chicago', hour: 'numeric', minute: '2-digit' }); })()
                    : `Q${g.quarter || '?'} ${Math.floor((g.time_remaining || 0) / 60)}:${String((g.time_remaining || 0) % 60).padStart(2,'0')}`;
                return `
                    <div class="game-card ${borderClass}">
                        <div class="game-score">${g.away_team || 'Away'} ${g.away_score || 0} @ ${g.home_team || 'Home'} ${g.home_score || 0}</div>
                        <div class="game-meta">${timeDisplay} | Spread: ${g.spread || '—'} | Fav: ${g.favorite || '—'}</div>
                        <div class="game-stats">
                            <span>${priceDisplay}</span>
                            <span class="${(g.price_drop_pct || 0) < 0 ? 'negative' : ''}">Drop: ${g.price_drop_pct ?? '—'}%</span>
                            <span>Fair: ${g.fair_value ?? '—'}%</span>
                            <span class="${(g.edge || 0) > 0 ? 'positive' : ''}">Edge: ${g.edge != null ? '+' : ''}${g.edge ?? '—'}%</span>
                            <span>Deficit: ${g.deficit_vs_spread ?? '—'}</span>
                            <span>Depth: ${g.book_depth ?? '—'}</span>
                        </div>
                        <div class="signal-dots">
                            ${STRATEGIES.map(st => {
                                const cls = strategyClass(st);
                                const lab = STRATEGY_LABELS[st] || st;
                                return `<span class="signal-dot ${cls}" style="opacity:${sigs.has(st) ? 1 : 0.25}" title="${lab}${sigs.has(st) ? ' (signal in last 5m)' : ''}"></span>`;
                            }).join('')}
                        </div>
                        ${pos ? `<div class="game-meta" style="margin-top:6px">Position: ${stratDisplay(pos.strategy)} (${pos.entry_count} entries) — ${pos.mode || '—'}</div>` : ''}
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
                if ((pos.entry_count || 0) >= 3) {
                    targets.push({ label: 'Recovery Exit (breakeven)', price: Math.round(avg), hit: false });
                    targets.push({ label: 'Recovery Stop (-50%)', price: Math.round(avg * 0.5), hit: false });
                } else if (avg < 30) {
                    targets.push({ label: 'TP1 (+17.5%)', price: Math.round(avg * 1.175), hit: pos.capital_recovered });
                    targets.push({ label: 'TP2 (40¢)', price: 40, hit: false });
                } else {
                    targets.push({ label: 'TP (48¢)', price: 48, hit: false });
                }
            } else if (strat === 'TIERED_CLASSIC') {
                targets.push({ label: 'Recovery (1.5x)', price: Math.round(avg * 1.5), hit: pos.capital_recovered });
                targets.push({ label: 'HM1 (2.0x)', price: Math.round(avg * 2.0), hit: pos.house_money_1_hit });
                targets.push({ label: 'HM2 (2.2x)', price: Math.round(avg * 2.2), hit: pos.house_money_2_hit });
                targets.push({ label: 'Late Lock (80¢)', price: 80, hit: false });
            } else if (canonicalStrategy(strat) === 'GARBAGE_TIME') {
                targets.push({ label: 'TP1 (+30%)', price: Math.round(avg * 1.30), hit: pos.capital_recovered });
                targets.push({ label: 'TP2 (50¢)', price: 50, hit: false });
                targets.push({ label: 'Stop (-35%, 6m hold)', price: Math.round(avg * 0.65), hit: false });
            } else if (strat === 'CONSERVATIVE_HOLD' || strat === 'CONSERVATIVE_HOLD_FLIP' || strat === 'TIERED_HOLD' || strat === 'TIERED_HOLD_FLIP' || strat === 'TIERED_CLASSIC_HOLD') {
                targets.push({ label: 'Settlement (100¢)', price: 100, hit: false });
            } else if (strat === 'TIERED_FLIP') {
                if ((pos.entry_count || 0) >= 3) {
                    targets.push({ label: 'Recovery Exit (breakeven)', price: Math.round(avg), hit: false });
                    targets.push({ label: 'Recovery Stop (-50%)', price: Math.round(avg * 0.5), hit: false });
                } else if (avg < 30) {
                    targets.push({ label: 'TP1 (+17.5%)', price: Math.round(avg * 1.175), hit: pos.capital_recovered });
                    targets.push({ label: 'TP2 (40¢)', price: 40, hit: false });
                } else {
                    targets.push({ label: 'TP (48¢)', price: 48, hit: false });
                }
            } else if (strat === 'PULSE') {
                targets.push({ label: 'TP1 (+12%)', price: Math.round(avg * 1.12), hit: false });
                targets.push({ label: 'TP2 (+25%)', price: Math.round(avg * 1.25), hit: false });
            }
            return targets;
        }

        function strategyClass(strat) {
            if (strat === 'CONSERVATIVE') return 'conservative';
            if (strat === 'TIERED') return 'tiered';
            if (strat === 'TIERED_CLASSIC') return 'tiered-classic';
            if (canonicalStrategy(strat) === 'GARBAGE_TIME') return 'heavy';
            if (strat === 'CONSERVATIVE_HOLD') return 'conservative-hold';
            if (strat === 'CONSERVATIVE_HOLD_FLIP') return 'conservative-hold-flip';
            if (strat === 'TIERED_HOLD') return 'tiered-hold';
            if (strat === 'TIERED_HOLD_FLIP') return 'tiered-hold-flip';
            if (strat === 'TIERED_CLASSIC_HOLD') return 'tiered-classic-hold';
            if (strat === 'TIERED_FLIP') return 'tiered-flip';
            if (strat === 'PULSE') return 'pulse';
            return 'conservative';
        }

        function stratColor(strat) {
            if (strat === 'CONSERVATIVE') return 'var(--conservative)';
            if (strat === 'TIERED') return 'var(--tiered)';
            if (strat === 'TIERED_CLASSIC') return 'var(--tiered-classic)';
            if (canonicalStrategy(strat) === 'GARBAGE_TIME') return 'var(--heavy)';
            if (strat === 'CONSERVATIVE_HOLD') return 'var(--conservative-hold)';
            if (strat === 'CONSERVATIVE_HOLD_FLIP') return 'var(--conservative-hold-flip)';
            if (strat === 'TIERED_HOLD') return 'var(--tiered-hold)';
            if (strat === 'TIERED_HOLD_FLIP') return 'var(--tiered-hold-flip)';
            if (strat === 'TIERED_CLASSIC_HOLD') return 'var(--tiered-classic-hold)';
            if (strat === 'TIERED_FLIP') return 'var(--tiered-flip)';
            if (strat === 'PULSE') return 'var(--pulse)';
            return 'var(--text)';
        }

        function updateTabOverview(s, trades, signals, performance, stats) {
            const risk = s.risk || {};
            const activePositions = s.active_positions || [];
            const liveGames = s.live_games || [];
            const gamesById = {};
            liveGames.forEach(g => { gamesById[g.game_id] = g; });

            let html = '<div class="overview-grid"><div>';
            // ─── OPEN POSITIONS CARDS (one card per live position) ───
            html += '<div class="card"><div class="card-header">Open Positions</div>';
            if (activePositions.length === 0) {
                html += '<div class="empty-state">No open positions</div>';
            } else {
                let totalUnrealized = 0;
                html += '<div class="strategy-cards">';
                activePositions.forEach(pos => {
                    const game = gamesById[pos.game_id];
                    const currentPrice = pos.current_bid_cents ?? pos.current_ask_cents ?? (game ? (game.kalshi_bid || game.kalshi_ask || game.kalshi_last || 0) : 0);
                    const avg = pos.avg_cost_cents || 0;
                    const shares = pos.shares_remaining || 0;
                    const remainingCost = Math.round(shares * avg);
                    const currentValue = shares * currentPrice;
                    const unrealizedPnl = currentPrice > 0 ? currentValue - remainingCost : 0;
                    totalUnrealized += unrealizedPnl;
                    const pnlClass = unrealizedPnl >= 0 ? 'positive' : 'negative';
                    const color = strategyClass(pos.strategy);
                    const stratLabel = stratDisplay(pos.strategy);
                    const entries = pos.entries || [];
                    const entryLines = entries.map((e, i) => 'Entry ' + (i + 1) + ': ' + (e.price || e.price_cents || '—') + '¢').join(' | ');
                    const targets = getTPTargets(pos);
                    const stopTarget = targets.find(t => /stop|recovery stop/i.test(t.label));
                    const tpTargets = targets.filter(t => !/stop|recovery stop/i.test(t.label));
                    const stopDist = (currentPrice > 0 && stopTarget) ? (currentPrice - stopTarget.price) : null;
                    const stopStr = stopTarget ? stopTarget.price + '¢' + (stopDist != null ? (stopDist >= 0 ? ' (' + stopDist + '¢ away)' : ' <span class="negative">' + (-stopDist) + '¢ past</span>') : '') : '—';
                    const tpStr = tpTargets.filter(t => !t.hit).map(t => t.label + ' ' + t.price + '¢').join(', ') || '—';
                    html += `<div class="strategy-card ${color}">
                        <div class="card-header">${pos.team || '—'} — ${stratLabel}</div>
                        <div style="font-size:12px;margin-bottom:4px">${entryLines || 'Entry: —'}</div>
                        <div style="font-size:12px">Current: ${currentPrice > 0 ? currentPrice + '¢' : '—'} | Shares: ${shares}</div>
                        <div style="font-size:11px;color:var(--muted);margin-top:4px">Stop: ${stopStr}</div>
                        <div style="font-size:11px;color:var(--muted)">TP: ${tpStr}</div>
                        <div class="${pnlClass}" style="font-weight:bold;margin-top:6px">P&L: ${fmt(unrealizedPnl)}</div>
                    </div>`;
                });
                html += '</div>';
                if (activePositions.length > 1) {
                    const totalClass = totalUnrealized >= 0 ? 'positive' : 'negative';
                    html += '<div style="margin-top:8px;font-weight:bold;font-size:13px">Total Unrealized: <span class="' + totalClass + '">' + fmt(totalUnrealized) + '</span></div>';
                }
            }
            html += '</div>';

            // ─── COMPARISON CARD (strategies as rows, Win Rate & P&L last) ───
            const cols = ['total_trades','avg_win','avg_loss','best_trade','worst_trade','win_rate','total_pnl'];
            const colLabels = ['Trades','Avg Win','Avg Loss','Best','Worst','Win Rate','Total P&L'];
            html += '<div class="card"><div class="card-header">Comparison</div><table><thead><tr><th></th>';
            colLabels.forEach(l => { html += '<th>' + l + '</th>'; });
            html += '</tr></thead><tbody>';
            STRATEGIES.forEach(st => {
                html += '<tr><td>' + (STRATEGY_LABELS[st] || st) + '</td>';
                cols.forEach((c, i) => {
                    const v = (stats[st] || {})[c];
                    const disp = c === 'win_rate' ? fmtPct(v) : (c === 'total_trades' ? (v ?? 0) : fmt(v));
                    const cls = (c === 'total_pnl' || c === 'avg_win' || c === 'best_trade') && v > 0 ? 'positive' : (v < 0 ? 'negative' : '');
                    html += '<td class="' + cls + '">' + disp + '</td>';
                });
                html += '</tr>';
            });
            html += '</tbody></table></div>';

            // ─── POSITION LEDGER (perps-style: entries / exits / avg / PnL by position) ───
            window._ledgerTrades = (trades || []).slice().sort((a, b) => parseTsMs(b.timestamp) - parseTsMs(a.timestamp));
            html += '<div class="card"><div class="card-header">Trade ledger (by position)</div>';
            html += '<div class="guide-subtitle" style="margin:-8px 0 10px 0">Each card is one Kalshi position (entries, partials, closes, settlement). <strong>Date filter uses America/Chicago</strong> and matches the <strong>first fill</strong> (open) — so overnight exits (e.g. UTC next day) stay with that game. Signals: Signal Log tab.</div>';
            html += '<div class="filter-bar" style="margin-bottom:8px"><select id="activityDateFilter" onchange="filterActivityFeed()">';
            html += '<option value="all">All positions</option><option value="today">Opened today (Chicago)</option><option value="yesterday">Opened yesterday (Chicago)</option>';
            html += '</select></div><div class="activity-feed" id="activityFeed">';
            html += buildPositionLedgerInner(window._ledgerTrades, 'all');
            html += '</div></div>';

            html += '</div><div>';

            // ─── POSITION DETAILS TABLE (right column) ───
            const gamesByIdOP = gamesById;

            html += '<div class="card"><div class="card-header">Position Details</div>';
            if (activePositions.length === 0) {
                html += '<div class="empty-state">No open positions</div>';
            } else {
                let totalUnrealizedPnl = 0;
                let totalCost = 0;
                const posData = activePositions.map(pos => {
                    const game = gamesByIdOP[pos.game_id];
                    const currentPrice = pos.current_bid_cents ?? pos.current_ask_cents ?? (game ? (game.kalshi_bid || game.kalshi_ask || game.kalshi_last || 0) : 0);
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
                    html += '<td style="color:' + stratColor(d.pos.strategy) + '">' + stratDisplay(d.pos.strategy) + '</td>';
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
                    html += '<div class="pos-mobile-team" style="color:' + stratColor(d.pos.strategy) + '">' + (d.pos.team || '—') + ' <span style="font-size:11px;opacity:0.7">' + stratDisplay(d.pos.strategy) + '</span></div>';
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

            // ─── COMBINED P&L CHART (swapped from left column) ───
            html += '<div class="card"><div class="card-header">Combined P&L Chart</div><div class="chart-container"><canvas id="chartOverview"></canvas></div></div>';
            html += '</div></div>';

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
                if (!pnlByDate[d]) {
                    pnlByDate[d] = {};
                    STRATEGIES.forEach(s => { pnlByDate[d][s] = 0; });
                }
                const sk = canonicalStrategy(t.strategy);
                pnlByDate[d][sk] = (pnlByDate[d][sk] || 0) + pnl;
            });
            const dates = Object.keys(pnlByDate).sort();
            if (dates.length === 0) return;

            const cumulative = {};
            const running = {};
            STRATEGIES.forEach(s => { cumulative[s] = []; running[s] = 0; });
            dates.forEach(d => {
                for (const s of STRATEGIES) {
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
                    datasets: STRATEGIES.map(s => {
                        let color = COLORS.conservative;
                        if (s === 'TIERED') color = COLORS.tiered;
                        else if (s === 'TIERED_CLASSIC') color = COLORS.tieredClassic;
                        else if (s === 'GARBAGE_TIME') color = COLORS.heavy;
                        else if (s === 'CONSERVATIVE_HOLD') color = COLORS.conservativeHold;
                        else if (s === 'CONSERVATIVE_HOLD_FLIP') color = COLORS.conservativeHoldFlip;
                        else if (s === 'TIERED_HOLD') color = COLORS.tieredHold;
                        else if (s === 'TIERED_HOLD_FLIP') color = COLORS.tieredHoldFlip;
                        else if (s === 'TIERED_CLASSIC_HOLD') color = COLORS.tieredClassicHold;
                        else if (s === 'TIERED_FLIP') color = COLORS.tieredFlip;
                        else if (s === 'PULSE') color = COLORS.pulse;
                        return {
                            label: STRATEGY_LABELS[s] || s,
                            data: (cumulative[s] || []).map(v => v / 100),
                            borderColor: color,
                            fill: false,
                            tension: 0.2
                        };
                    })
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    scales: {
                        x: { grid: { color: 'rgba(17,24,39,0.08)' } },
                        y: { grid: { color: 'rgba(17,24,39,0.08)' }, ticks: { callback: v => '$' + v.toFixed(2) } }
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

        function updateTabBounceback(trades, positions, st) {
            const isBounceStrat = (s) => canonicalStrategy(s) === 'GARBAGE_TIME';
            const heavy = trades.filter(t => isBounceStrat(t.strategy));
            const active = positions.filter(p => isBounceStrat(p.strategy));

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

            html += '<div class="card"><div class="card-header">Spread Analysis</div><div class="chart-container"><canvas id="chartBouncebackSpread"></canvas></div></div>';
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

            document.getElementById('tabBounceback').innerHTML = html;
            renderBarChart('chartBouncebackSpread', Object.keys(spreadBuckets), Object.values(spreadBuckets).map(arr => {
                const wins = arr.filter(t => heavy.some(c => c.position_id === t.position_id && c.pnl_cents > 0));
                return arr.length ? (wins.length / arr.length) * 100 : 0;
            }), COLORS.heavy);
        }

        function updateTabSimpleStrategy(trades, positions, st, key, label, color) {
            const filtTrades = trades.filter(t => t.strategy === key);
            const active = positions.filter(p => p.strategy === key);

            let html = '<div class="stats-row">';
            html += `<div class="stat-box"><div class="stat-label">Strategy</div><div class="stat-value" style="color:${color}">${label}</div></div>`;
            html += `<div class="stat-box"><div class="stat-label">Total P&L</div><div class="stat-value ${(st?.total_pnl || 0) >= 0 ? 'positive' : 'negative'}">${fmt(st?.total_pnl)}</div></div>`;
            html += `<div class="stat-box"><div class="stat-label">Win Rate</div><div class="stat-value">${fmtPct(st?.win_rate)}</div></div>`;
            html += `<div class="stat-box"><div class="stat-label">Avg Win</div><div class="stat-value positive">${fmt(st?.avg_win)}</div></div>`;
            html += `<div class="stat-box"><div class="stat-label">Avg Loss</div><div class="stat-value negative">${fmt(st?.avg_loss)}</div></div>`;
            html += `<div class="stat-box"><div class="stat-label">Trades</div><div class="stat-value">${st?.total_trades ?? 0}</div></div>`;
            html += '</div>';

            html += '<div class="card"><div class="card-header">Active Positions</div>';
            if (active.length === 0) html += '<div class="empty-state">No active positions</div>';
            else html += '<table><thead><tr><th>Team</th><th>Entries</th><th>Avg Cost</th><th>Shares</th><th>Mode</th></tr></thead><tbody>' +
                active.map(p => `<tr><td>${p.team}</td><td>${p.entry_count}</td><td>${(p.avg_cost_cents ?? 0).toFixed(1)}¢</td><td>${p.shares_remaining}</td><td>${p.current_mode || '—'}</td></tr>`).join('') + '</tbody></table>';
            html += '</div>';

            html += '<div class="card"><div class="card-header">Trade History</div>';
            if (filtTrades.length === 0) html += '<div class="empty-state">No trades yet</div>';
            else html += '<table><thead><tr><th>Date</th><th>Team</th><th>Action</th><th>Price</th><th>P&L</th><th>Game Time</th><th>Score</th></tr></thead><tbody>' +
                filtTrades.slice(0, 50).map(t => `<tr><td>${fmtTs(t.timestamp)}</td><td>${t.team}</td><td>${t.action}</td><td>${t.price_cents}¢</td><td class="${(t.pnl_cents || 0) >= 0 ? 'positive' : 'negative'}">${fmt(t.pnl_cents)}</td><td>${fmtGameTime(t)}</td><td>${fmtGameScore(t)}</td></tr>`).join('') + '</tbody></table>';
            html += '</div>';

            const target = document.getElementById('tab' + label.replace(/\\s+/g,''));
            if (target) target.innerHTML = html;
        }

        function updateTabConservativeHold(trades, positions, st) {
            updateTabSimpleStrategy(trades, positions, st, 'CONSERVATIVE_HOLD', 'Conservative Hold', COLORS.conservativeHold);
        }

        function updateTabConservativeHoldFlip(trades, positions, st) {
            updateTabSimpleStrategy(trades, positions, st, 'CONSERVATIVE_HOLD_FLIP', 'Conservative Hold Flip', COLORS.conservativeHoldFlip);
        }

        function updateTabTieredHold(trades, positions, st) {
            updateTabSimpleStrategy(trades, positions, st, 'TIERED_HOLD', 'Tiered Hold', COLORS.tieredHold);
        }

        function updateTabTieredHoldFlip(trades, positions, st) {
            updateTabSimpleStrategy(trades, positions, st, 'TIERED_HOLD_FLIP', 'Tiered Hold Flip', COLORS.tieredHoldFlip);
        }

        function updateTabTieredClassicHold(trades, positions, st) {
            updateTabSimpleStrategy(trades, positions, st, 'TIERED_CLASSIC_HOLD', 'Tiered Classic Hold', COLORS.tieredClassicHold);
        }

        function updateTabTieredFlip(trades, positions, st) {
            updateTabSimpleStrategy(trades, positions, st, 'TIERED_FLIP', 'Tiered Flip', COLORS.tieredFlip);
        }

        function updateTabPulse(trades, positions, st) {
            updateTabSimpleStrategy(trades, positions, st, 'PULSE', 'Pulse', COLORS.pulse);
        }

        function updateTabComparison(trades, stats) {
            let html = '<div class="card"><div class="card-header">Head-to-Head</div><table><thead><tr><th></th><th>Conservative</th><th>Tiered V2</th><th>Tiered Classic</th><th>Bounceback</th></tr></thead><tbody>';
            ['win_rate','avg_win','avg_loss','best_trade','worst_trade','total_pnl'].forEach((r, i) => {
                const labels = ['Win Rate','Avg Win','Avg Loss','Best','Worst','Total P&L'];
                html += '<tr><td>' + labels[i] + '</td>';
                ['CONSERVATIVE','TIERED','TIERED_CLASSIC','GARBAGE_TIME'].forEach(st => {
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
            const heavy12 = trades.filter(t => canonicalStrategy(t.strategy) === 'GARBAGE_TIME' && t.action === 'BUY' && Math.abs(t.pre_game_spread || 0) >= 12);
            if (heavy12.length > 0) {
                const losses = heavy12.filter(t => trades.some(c => c.position_id === t.position_id && c.pnl_cents < 0));
                if (losses.length === 0) insights.push('Bounceback at 12+ spread has never lost.');
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
            const stratOpts = [
                ['','All Strategies'],
                ['CONSERVATIVE','Conservative'],
                ['TIERED','Tiered V2'],
                ['TIERED_CLASSIC','Tiered Classic'],
                ['GARBAGE_TIME','Bounceback'],
                ['CONSERVATIVE_HOLD','Conservative Hold'],
                ['TIERED_HOLD','Tiered Hold'],
                ['TIERED_CLASSIC_HOLD','Tiered Classic Hold'],
                ['PULSE','Pulse']
            ];
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
                html += '<tr class="' + rowClass + '"><td>' + fmtTs(s.timestamp) + '</td><td>' + stratDisplay(s.strategy) + '</td><td>' + (s.team || '') + '</td><td>' + (s.signal_type || '') + '</td><td>' + (s.deficit ?? '—') + '</td><td>' + (s.edge != null ? (s.edge <= 1 ? (s.edge*100).toFixed(1) + '%' : s.edge + '%') : '—') + '</td><td>' + (s.price_drop_pct != null ? (s.price_drop_pct <= 1 ? (s.price_drop_pct*100).toFixed(1) + '%' : s.price_drop_pct + '%') : '—') + '</td><td>' + (s.kalshi_price ?? '—') + '¢</td><td>' + (s.pre_game_spread ?? '—') + '</td><td>' + (s.confidence ?? '—') + '</td><td>' + (s.action_taken ? 'Yes' : 'No') + '</td><td>' + (s.skip_reason || '—') + '</td></tr>';
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
<div class="card guide-section">
    <h2>Strategy Guide (Source of Truth)</h2>
    <p>This tab mirrors the live code in <code>core/config.py</code> and <code>strategies/*.py</code>. The bot runs eight strategies in parallel with fixed bankrolls: $100 per strategy.</p>
    <p>Global behavior: entries are Q1-Q2 by default, no new entries in final 2 minutes. Tiered/Tiered Classic allow a limited Q3 Entry-2 window (first 6 minutes) with relaxed gates. Bounceback is Q3-only. Q3 has a neutral window before defensive mode, and each strategy has per-position tail-risk stops.</p>
</div>

<hr class="guide-divider">

<div class="card guide-section">
    <h2 style="color:var(--conservative)">Conservative (Regime-Aware Edge)</h2>
    <ul>
        <li>Entry gates: spread &ge; 1, deficit_vs_spread &ge; 12, ask &le; 35&cent;, depth &ge; 100, Q1-Q2 only.</li>
        <li>Edge threshold is spread-aware: close spread (&le; 3.5) needs 13%+, mid spread (&le; 7) needs 10%+, otherwise 8%+.</li>
        <li>Sizing: 8% / 12% / 16% of conservative bankroll by edge bucket.</li>
        <li>Exits: TP1 +30% (sell 50%), TP2 +60% (sell rest), -30% stop with 12-minute hold guard, thesis invalidation (deficit &gt; 25 in Q3+ late clock).</li>
        <li>Max concurrent positions: 2.</li>
    </ul>
</div>

<hr class="guide-divider">

<div class="card guide-section">
    <h2 style="color:var(--tiered)">Tiered V2 (Regime-Aware)</h2>
    <ul>
        <li>Base entry gates: spread 1-7, deficit_vs_spread &ge; 10, ask &le; 35&cent;, depth &ge; 50, Q1-Q2 only. No minimum tipoff drop for Entry 1.</li>
        <li>Close-spread regime (&le; 3.5): scalp-only, max 2 entries, TP1 at avg+6&cent;, TP2 at min(avg+10&cent;, 42&cent;), stop at -25%, time-stop in Q3 (&lt;300s).</li>
        <li>Mid-spread regime (&gt; 3.5): recovery logic. Entry 3+ requires stronger spread (&ge; 6.0).</li>
        <li>Entry 2 requires additional price drop; no extra deficit growth required.</li>
        <li>Q3 Entry-2 window (first 6 minutes): allows a second entry if price drops &ge; 15% from Entry 1 and depth &ge; 50.</li>
        <li>Standard exits: +17.5% partial then 40&cent; target when avg&lt;30&cent;; otherwise 48&cent; target.</li>
        <li>3+ entry positions switch to capital recovery mode with breakeven exit plus recovery stop at -60%.</li>
        <li>Tail risk controls: universal max-loss cap at -55% per position plus Q3+ dynamic stop geometry and Q4 time exit (&lt;300s).</li>
    </ul>
</div>

<hr class="guide-divider">

<div class="card guide-section">
    <h2 style="color:var(--tiered-classic)">Tiered Classic (A/B Track)</h2>
    <ul>
        <li>Entry logic follows Tiered regime rules, but max entry price is 40&cent;.</li>
        <li>Close-spread games still cap at 2 entries; entry 3+ also requires spread &ge; 6.0.</li>
        <li>Reachable ladder exits: 1.5x (sell 50%), 2.0x (sell 25%), 2.2x (sell 25%).</li>
        <li>Additional exits: 80&cent; late-game lock (Q4 &lt;180s), 50% trailing stop after recovery, defensive hard-floor behavior.</li>
        <li>Risk controls: universal tail stop at -55%, Q3+ universal stop at -60%, recovery stop at -60%.</li>
    </ul>
</div>

<hr class="guide-divider">

<div class="card guide-section">
    <h2 style="color:var(--heavy)">Bounceback (Q3 Halftime-Dip)</h2>
    <ul>
        <li>Q3-only strategy. Entry window: first 6 minutes of Q3 (halftime-dip exploitation).</li>
        <li>Entry 1 gates: spread &ge; 5, favorite trailing by 6-18 pts, deficit_vs_spread &ge; 8, ask 15-42&cent;, price drop from tipoff &ge; 15%, depth &ge; 25.</li>
        <li>Edge confirmation: if fair value available, requires &ge; 6% edge vs Kalshi price.</li>
        <li>Entry 2: price must drop 20%+ from Entry 1, still in Q3 (&ge; 3 min left), deficit &lt; 25.</li>
        <li>Sizing: 14% of bankroll per game (70/30 split between Entry 1 and 2).</li>
        <li>Exits: TP1 +30% (sell 50%), TP2 at 50&cent; (sell rest), -35% stop (6 min hold guard), thesis invalid at deficit &gt; 30, time exit Q4 &lt; 5 min.</li>
        <li>Remaining shares ride to settlement — need ~30% win rate at avg 30&cent; entry to profit.</li>
        <li>Max concurrent positions: 3.</li>
        <li>Max concurrent positions: 2.</li>
    </ul>
</div>

<hr class="guide-divider">

<div class="card guide-section">
    <h2>Settlement-Only Variants</h2>
    <ul>
        <li><strong>Conservative Hold</strong>: same entry logic as Conservative, no early exits (settlement only).</li>
        <li><strong>Tiered Hold</strong>: same entry logic as Tiered V2, no early exits (settlement only).</li>
        <li><strong>Tiered Classic Hold</strong>: same entry logic as Tiered Classic, no early exits (settlement only).</li>
        <li>These exist to compare pure settlement outcomes vs. active exits in paper trading.</li>
    </ul>
</div>

<hr class="guide-divider">

<div class="card guide-section">
    <h2 style="color:var(--pulse)">Pulse (Aggressive Scalp)</h2>
    <ul>
        <li>High-action entry gates: spread 1-12, deficit_vs_spread &ge; 6, drop from tipoff &ge; 10%, ask &le; 60&cent;, depth &ge; 20.</li>
        <li>Entries allowed through Q3 (no entries after Q3).</li>
        <li>Exits: TP1 +12% (sell 60%), TP2 +25% (sell rest), stop at -12% after 4 min hold.</li>
        <li>Designed for frequent trades with tight risk control.</li>
    </ul>
</div>

<hr class="guide-divider">

<div class="card guide-section">
    <h2>Global Risk Controls</h2>
    <ul>
        <li>Daily strategy-game loss pause: 30%.</li>
        <li>Weekly strategy pause threshold: 25%.</li>
        <li>Global hard floor: halt all trading below 60% of starting bankroll.</li>
        <li>Max liquidity consumption per order: 30% of visible depth.</li>
        <li>No new entries in final 120 seconds of regulation.</li>
        <li>Execution slippage alert threshold: 3&cent;.</li>
    </ul>
</div>

<hr class="guide-divider">

<div class="card guide-section">
    <h2>Weekly Scorecard Workflow</h2>
    <p>Use <code>tools/weekly_scorecard.py</code> to generate governance outputs from exports:</p>
    <ul>
        <li><code>docs/weekly_scorecard.md</code> for human review</li>
        <li><code>docs/weekly_scorecard.json</code> for automation/dashboard consumption</li>
    </ul>
    <p>The scorecard reports strategy, spread-bucket, and entry-count expectancy, then emits parameter governance recommendations when degradation is detected.</p>
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
