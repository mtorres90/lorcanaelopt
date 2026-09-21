// Versao web de uma so pagina: ranking, jogador, eventos e sobre.
// Os dados (DATA) sao calculados em Python e embebidos na pagina.
(function () {
  var D = DATA;
  var byId = {};
  D.players.forEach(function (p) { byId[p.id] = p; });
  var app = document.getElementById('app');
  var query = '';

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function fold(s) { return s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, ''); }
  function fmtDate(iso) { var p = iso.split('-'); return p[2] + '/' + p[1] + '/' + p[0]; }
  function rnd(x) { return String(Math.round(x)); }
  function ordinal(n) {
    var r = n % 100;
    if (r >= 11 && r <= 13) return n + 'th';
    switch (n % 10) {
      case 1: return n + 'st';
      case 2: return n + 'nd';
      case 3: return n + 'rd';
      default: return n + 'th';
    }
  }
  function delta(x) {
    var r = Math.round(x);
    if (r === 0) return '0';
    return (r > 0 ? '+' : '\u2212') + Math.abs(r);
  }
  function chip(score) {
    if (score === 1) return '<span class="chip chip-w" title="Win">W</span>';
    if (score === 0) return '<span class="chip chip-l" title="Loss">L</span>';
    return '<span class="chip chip-d" title="Draw">D</span>';
  }
  function link(id) { return '#/player/' + encodeURIComponent(id); }
  function markScrollableTables() {
    [].slice.call(app.querySelectorAll('.tablewrap')).forEach(function (w) {
      if (w.scrollWidth > w.clientWidth + 1) w.classList.add('scrolls');
      else w.classList.remove('scrolls');
    });
  }

  // ---------- ranking ----------
  function rankingView() {
    var m = D.meta;
    var ranked = D.players.filter(function (p) { return p.rank; });
    var rows = D.players.map(function (p) {
      var form = p.h.slice(-5).map(function (h) { return chip(h[4]); }).join('');
      var nameAttr = p.realName ? ' title="' + esc(p.realName) + '"' : '';
      return '<tr' + (p.rank ? '' : ' class="prov"') + ' data-name="' + esc(fold(p.name)) + '">' +
        '<td class="num">' + (p.rank || '\u2013') + '</td>' +
        '<td><a href="' + link(p.id) + '"' + nameAttr + '>' + esc(p.name) + '</a></td>' +
        '<td class="num elo">' + rnd(p.rating) + '</td>' +
        '<td class="num">' + p.games + '</td>' +
        '<td class="num wide">' + p.wins + '\u2013' + p.draws + '\u2013' + p.losses + '</td>' +
        '<td class="wide">' + form + '</td></tr>';
    }).join('');
    var provNote = D.players.length > ranked.length
      ? ' Players with fewer than ' + m.minGames + ' matches appear at the bottom, unranked.' : '';
    return '<h1>Lorcana Portugal Elo Ranking</h1>' +
      '<p class="lead">' + D.players.length + ' players, ' + m.matches + ' matches and ' + m.events +
      ' events since ' + esc(m.since) + '.' + provNote + '</p>' +
      '<div class="search"><label class="sr-only" for="q">Search for a player</label>' +
      '<input id="q" type="search" placeholder="Search for a player" autocomplete="off"></div>' +
      '<div class="tablewrap"><table class="ranking"><caption class="sr-only">Elo ranking</caption>' +
      '<thead><tr><th class="num" scope="col">Rank</th><th scope="col">Player</th><th class="num" scope="col">Elo</th>' +
      '<th class="num" scope="col">Matches</th><th class="num wide" scope="col">W\u2013D\u2013L</th>' +
      '<th class="wide" scope="col">Last 5</th></tr></thead><tbody>' + rows + '</tbody></table></div>' +
      '<p id="empty" class="empty" hidden>No player found. Check the spelling of the name.</p>';
  }

  function wireSearch() {
    var input = document.getElementById('q');
    if (!input) return;
    var rows = [].slice.call(document.querySelectorAll('tbody tr[data-name]'));
    var empty = document.getElementById('empty');
    function apply() {
      var q = fold(query.trim()), shown = 0;
      rows.forEach(function (r) {
        var ok = !q || r.getAttribute('data-name').indexOf(q) !== -1;
        r.hidden = !ok;
        if (ok) shown++;
      });
      empty.hidden = shown !== 0;
    }
    input.value = query;
    input.addEventListener('input', function () { query = input.value; apply(); });
    apply();
  }

  // ---------- jogador ----------
  function chart(name, ratings) {
    var w = 640, h = 190, pl = 44, pr = 14, pt = 14, pb = 16, start = D.consts.start;
    var lo = Math.min.apply(null, ratings.concat([start])) - 10;
    var hi = Math.max.apply(null, ratings.concat([start])) + 10;
    if (hi - lo < 60) { var mid = (hi + lo) / 2; lo = mid - 30; hi = mid + 30; }
    var n = ratings.length;
    function x(i) { return pl + (w - pl - pr) * (n > 1 ? i / (n - 1) : 0.5); }
    function y(v) { return pt + (h - pt - pb) * (hi - v) / (hi - lo); }
    var base = y(start);
    function tick(v) {
      if (Math.abs(y(v) - base) < 16) return '';
      return '<text class="chart-tick" x="' + (pl - 6) + '" y="' + (y(v) + 4).toFixed(1) +
        '" text-anchor="end">' + rnd(v) + '</text>';
    }
    var pts = ratings.map(function (v, i) { return x(i).toFixed(1) + ',' + y(v).toFixed(1); }).join(' ');
    var label = 'Evolu\u00e7\u00e3o do Elo de ' + name + ': de ' + rnd(ratings[0]) + ' para ' + rnd(ratings[n - 1]);
    return '<svg class="chart" viewBox="0 0 ' + w + ' ' + h + '" role="img" aria-label="' + esc(label) + '">' +
      '<line class="chart-base" x1="' + pl + '" x2="' + (w - pr) + '" y1="' + base.toFixed(1) + '" y2="' + base.toFixed(1) + '"/>' +
      '<text class="chart-tick" x="' + (pl - 6) + '" y="' + (base + 4).toFixed(1) + '" text-anchor="end">' + rnd(start) + '</text>' +
      tick(hi) + tick(lo) +
      '<polyline class="chart-line" points="' + pts + '"/>' +
      '<circle class="chart-dot" cx="' + x(n - 1).toFixed(1) + '" cy="' + y(ratings[n - 1]).toFixed(1) + '" r="4"/></svg>';
  }

  function statTile(label, value, sub) {
    return '<div class="stat-tile"><span class="stat-label">' + label + '</span>' +
      '<span class="stat-value">' + value + '</span>' +
      (sub ? '<span class="stat-sub">' + sub + '</span>' : '') + '</div>';
  }

  function statGrid(p) {
    var e = p.extra || {};
    var favPct = e.fav_games ? Math.round((e.fav_wins / e.fav_games) * 100) + ' %' : '\u2013';
    var dogPct = e.dog_games ? Math.round((e.dog_wins / e.dog_games) * 100) + ' %' : '\u2013';
    return '<div class="stat-grid">' +
      statTile('Peak', rnd(p.peak)) +
      statTile('Low', rnd(e.low)) +
      statTile('Events', e.events) +
      statTile('Best win streak', e.best_win_streak) +
      statTile('Worst loss streak', e.best_loss_streak) +
      statTile('Biggest single-match gain', delta(e.best_gain)) +
      statTile('Biggest single-match drop', delta(e.worst_loss)) +
      statTile('As favorite', favPct, e.fav_games + ' matches') +
      statTile('As underdog', dogPct, e.dog_games + ' matches') +
      '</div>';
  }

  function h2hSection(p) {
    var list = (p.extra && p.extra.h2h) || [];
    if (!list.length) return '';
    var rows = list.map(function (o) {
      var opp = byId[o.id];
      var name = opp ? opp.name : 'Anonymous player';
      var cell = opp ? '<a href="' + link(o.id) + '">' + esc(name) + '</a>' : esc(name);
      var pct = Math.round(((o.wins + 0.5 * o.draws) / o.games) * 100);
      var tag = '';
      if (o.id === p.extra.nemesis) tag = ' <span class="tag tag-l">toughest rival</span>';
      else if (o.id === p.extra.victim) tag = ' <span class="tag tag-w">favorite victim</span>';
      return '<tr><td>' + cell + tag + '</td><td class="num">' + o.games + '</td>' +
        '<td class="num wide">' + o.wins + '\u2013' + o.draws + '\u2013' + o.losses + '</td>' +
        '<td class="num">' + pct + ' %</td></tr>';
    }).join('');
    return '<h2>Head-to-head</h2><div class="tablewrap"><table class="matches">' +
      '<thead><tr><th scope="col">Opponent</th><th class="num" scope="col">Matches</th>' +
      '<th class="num wide" scope="col">W\u2013D\u2013L</th><th class="num" scope="col">Win %</th></tr></thead>' +
      '<tbody>' + rows + '</tbody></table></div>';
  }

  function eventsSection(p) {
    var byEv = {}, order = [];
    p.h.forEach(function (h) {
      var eid = h[1];
      if (!byEv[eid]) {
        byEv[eid] = { date: h[0], w: 0, d: 0, l: 0, rounds: 0, start: h[5] - h[6], end: h[5] };
        order.push(eid);
      }
      var e = byEv[eid];
      e.rounds++;
      e.end = h[5];
      if (h[4] === 1) e.w++; else if (h[4] === 0) e.l++; else e.d++;
    });
    if (!order.length) return '';
    var rows = order.slice().reverse().map(function (eid) {
      var e = byEv[eid], ev = D.events[eid] || {}, evName = ev.name || eid;
      return '<tr><td>' + fmtDate(e.date) + '</td><td title="' + esc(evName) + '">' + esc(evName) + '</td>' +
        '<td class="num">' + e.rounds + '</td><td class="num wide">' + e.w + '\u2013' + e.d + '\u2013' + e.l + '</td>' +
        '<td class="num">' + delta(e.end - e.start) + '</td></tr>';
    }).join('');
    return '<h2>Events</h2><div class="tablewrap"><table class="matches">' +
      '<thead><tr><th scope="col">Date</th><th scope="col">Event</th><th class="num" scope="col">Rounds</th>' +
      '<th class="num wide" scope="col">W\u2013D\u2013L</th><th class="num" scope="col">Change</th></tr></thead>' +
      '<tbody>' + rows + '</tbody></table></div>';
  }

  function radarChart(dims) {
    var w = 320, h = 320, cx = w / 2, cy = h / 2, r = 96;
    var n = dims.length;
    function pt(i, rad) {
      var a = -Math.PI / 2 + i * (2 * Math.PI / n);
      return [cx + rad * Math.cos(a), cy + rad * Math.sin(a)];
    }
    var rings = [0.25, 0.5, 0.75, 1].map(function (f) {
      var pts = dims.map(function (_, i) { var p = pt(i, r * f); return p[0].toFixed(1) + ',' + p[1].toFixed(1); }).join(' ');
      return '<polygon class="dna-ring" points="' + pts + '"/>';
    }).join('');
    var axes = dims.map(function (_, i) {
      var p = pt(i, r);
      return '<line class="dna-axis" x1="' + cx + '" y1="' + cy + '" x2="' + p[0].toFixed(1) + '" y2="' + p[1].toFixed(1) + '"/>';
    }).join('');
    var dataPts = dims.map(function (d, i) { return pt(i, r * (d.value == null ? 0 : d.value) / 100); });
    var poly = dataPts.map(function (p) { return p[0].toFixed(1) + ',' + p[1].toFixed(1); }).join(' ');
    var dots = dims.map(function (d, i) {
      if (d.value == null) return '';
      var p = dataPts[i];
      return '<circle class="dna-dot" cx="' + p[0].toFixed(1) + '" cy="' + p[1].toFixed(1) + '" r="3.5"/>';
    }).join('');
    var labels = dims.map(function (d, i) {
      var p = pt(i, r + 44);
      var anchor = Math.abs(p[0] - cx) < 4 ? 'middle' : (p[0] > cx ? 'start' : 'end');
      return '<text class="dna-label" x="' + p[0].toFixed(1) + '" y="' + p[1].toFixed(1) + '" text-anchor="' + anchor + '">' + esc(d.label) + '</text>';
    }).join('');
    return '<svg class="dna-chart" viewBox="0 0 ' + w + ' ' + h + '" role="img" aria-label="Summoner\u2019s DNA radar chart">' +
      rings + axes + '<polygon class="dna-poly" points="' + poly + '"/>' + dots + labels + '</svg>';
  }

  function dnaSection(p) {
    var d = p.extra && p.extra.dna;
    if (!d) return '';
    var dims = [
      { key: 'dominance', label: 'Dominance', sub: d.dominance_n + ' matches' },
      { key: 'consistency', label: 'Consistency', sub: 'as favorite \u00b7 ' + d.consistency_n + ' matches' },
      { key: 'composure', label: 'Composure', sub: 'final round \u00b7 ' + d.composure_n + ' events' },
      { key: 'event_mastery', label: 'Event Mastery', sub: '60%+ win rate \u00b7 ' + d.event_mastery_n + ' events' },
      { key: 'grit', label: 'Grit', sub: 'as underdog \u00b7 ' + d.grit_n + ' matches' },
      { key: 'clutch', label: 'Clutch Closer', sub: 'after a loss \u00b7 ' + d.clutch_n + ' matches' }
    ];
    var rows = dims.map(function (x) {
      var v = d[x.key];
      var pct = v == null ? 'not enough data' : Math.round(v) + ' %';
      var bar = '<div class="dna-bar"><span style="width:' + (v == null ? 0 : Math.round(v)) + '%"></span></div>';
      return '<div class="dna-row"><div class="dna-row-head"><span class="dna-row-label">' + x.label + '</span>' +
        '<span class="dna-row-value">' + pct + '</span></div>' + bar +
        '<span class="dna-row-sub">' + x.sub + '</span></div>';
    }).join('');
    var radarDims = dims.map(function (x) { return { label: x.label, value: d[x.key] }; });
    return '<h2>Summoner\u2019s DNA</h2><p class="lead">Six dimensions of ' + esc(p.name) + '\u2019s competitive style.</p>' +
      '<div class="dna-wrap">' + radarChart(radarDims) + '<div class="dna-list">' + rows + '</div></div>';
  }

  function playerView(id) {
    var p = byId[id];
    if (!p) return notFound();
    var ratings = [D.consts.start].concat(p.h.map(function (h) { return h[5]; }));
    var standing = p.rank
      ? ordinal(p.rank) + ' out of ' + D.meta.ranked + ' ranked players.'
      : 'Not yet ranked: needs ' + D.meta.minGames + ' matches, has ' + p.games + '.';
    var pct = p.games ? Math.round(((p.wins + 0.5 * p.draws) / p.games) * 100) : 0;
    var rows = p.h.slice().reverse().map(function (h) {
      var ev = D.events[h[1]] || {};
      var opp = h[3] && byId[h[3]]
        ? '<a href="' + link(h[3]) + '">' + esc(byId[h[3]].name) + '</a>' : 'Anonymous player';
      var evName = ev.name || h[1];
      return '<tr><td>' + fmtDate(h[0]) + '</td><td title="' + esc(evName) + '">' + esc(evName) + '</td><td class="num">' + h[2] +
        '</td><td>' + opp + '</td><td>' + chip(h[4]) + '</td><td class="num">' + rnd(h[5]) +
        ' <span class="delta">(' + delta(h[6]) + ')</span></td></tr>';
    }).join('');
    var realNameLine = p.realName ? '<p class="crumb-sub">' + esc(p.realName) + '</p>' : '';
    return '<p class="crumb"><a href="#/">Ranking</a></p><h1>' + esc(p.name) + '</h1>' + realNameLine +
      '<div class="hero"><p class="bignum" aria-label="Current Elo">' + rnd(p.rating) + '</p>' +
      '<p class="hero-text">' + standing + '<br>Peak of ' + rnd(p.peak) + '. ' + p.wins + ' wins, ' +
      p.draws + ' draws and ' + p.losses + ' losses (' + pct + '% win rate).</p></div>' +
      statGrid(p) +
      '<h2>Elo progression</h2>' + chart(p.name, ratings) +
      dnaSection(p) +
      h2hSection(p) +
      eventsSection(p) +
      '<h2>Matches</h2><div class="tablewrap"><table class="matches"><thead><tr><th scope="col">Date</th>' +
      '<th scope="col">Event</th><th class="num" scope="col">Round</th><th scope="col">Opponent</th>' +
      '<th scope="col">Result</th><th class="num" scope="col">Elo after</th></tr></thead><tbody>' +
      rows + '</tbody></table></div>';
  }

  // ---------- events ----------
  function eventsView() {
    var list = Object.keys(D.events).map(function (k) { return D.events[k]; })
      .sort(function (a, b) { return a.date < b.date ? 1 : -1; });
    var rows = list.map(function (e) {
      var where = [e.store, e.city].filter(Boolean).join(', ');
      var evName = e.name || e.id;
      return '<tr><td>' + fmtDate(e.date) + '</td><td title="' + esc(evName) + '">' + esc(evName) + '</td><td>' + esc(where) +
        '</td><td class="num">' + e.players + '</td><td class="num">' + e.matches + '</td></tr>';
    }).join('');
    return '<h1>Events</h1><p class="lead">Events at Portuguese stores with results recorded since ' +
      esc(D.meta.since) + '.</p><div class="tablewrap"><table class="matches"><thead><tr><th scope="col">Date</th>' +
      '<th scope="col">Event</th><th scope="col">Store</th><th class="num" scope="col">Players</th>' +
      '<th class="num" scope="col">Matches</th></tr></thead><tbody>' + rows + '</tbody></table></div>';
  }

  // ---------- about ----------
  function aboutView() {
    var c = D.consts, m = D.meta;
    var contact = m.contact
      ? '<a href="mailto:' + esc(m.contact) + '">' + esc(m.contact) + '</a>'
      : 'the site contact (to be set)';
    return '<h1>About the ranking</h1>' +
      '<h2>What this is</h2><p>An Elo ranking of Disney Lorcana players in Portugal, calculated from tournament ' +
      'and league results recorded on the Ravensburger Play Hub. Only events at Portuguese stores count, held ' +
      'since ' + esc(m.since) + '.</p>' +
      '<h2>How Elo works</h2><p>Everyone starts with ' + c.start + ' points. After each match, the winner gains ' +
      'points and the loser loses them. Beating a higher-rated opponent is worth more than beating a lower-rated ' +
      'one. A draw counts as half a win.</p>' +
      '<p>In the first ' + c.prov + ' matches, swings are bigger (K = ' + c.k1 + '), so Elo reaches the right ' +
      'level quickly. After that it switches to K = ' + c.k2 + '. Matches within the same round are calculated ' +
      'using each player\u2019s Elo from before that round. Byes don\u2019t count.</p>' +
      '<h2>Who gets a rank</h2><p>Players with at least ' + m.minGames + ' matches. Others appear at the bottom ' +
      'of the table, unranked.</p>' +
      '<h2>Privacy</h2><p>We only show the name that the Play Hub makes publicly available. If you\u2019d rather not ' +
      'appear, contact ' + contact + ' and your profile will stop being shown. Your matches still count toward ' +
      'your opponents\u2019 Elo, but your name is replaced with \u201cAnonymous player\u201d.</p>';
  }

  function notFound() {
    return '<h1>Page not found</h1><p>This player doesn\u2019t exist or has been removed. ' +
      '<a href="#/">Back to ranking</a>.</p>';
  }

  // ---------- router ----------
  var first = true;
  function route() {
    var h = location.hash.replace(/^#\/?/, '');
    var parts = h.split('/');
    var html, key = 'ranking', title = 'Ranking';
    if (parts[0] === 'player' && parts[1]) {
      var id = decodeURIComponent(parts.slice(1).join('/'));
      html = playerView(id);
      title = byId[id] ? byId[id].name : 'Not found';
    } else if (parts[0] === 'events') {
      html = eventsView(); key = 'events'; title = 'Events';
    } else if (parts[0] === 'about') {
      html = aboutView(); key = 'about'; title = 'About';
    } else {
      html = rankingView();
    }
    app.innerHTML = html;
    document.title = title + ' \u00b7 Lorcana Portugal Elo';
    markScrollableTables();
    [].slice.call(document.querySelectorAll('nav a')).forEach(function (a) {
      if (a.getAttribute('data-key') === key) a.setAttribute('aria-current', 'page');
      else a.removeAttribute('aria-current');
    });
    wireSearch();
    if (!first) {
      window.scrollTo(0, 0);
      var h1 = app.querySelector('h1');
      if (h1) { h1.setAttribute('tabindex', '-1'); h1.focus({ preventScroll: true }); }
    }
    first = false;
  }
  window.addEventListener('hashchange', route);
  window.addEventListener('resize', markScrollableTables);
  route();
})();
