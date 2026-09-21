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
  function eventUrl(id) { return 'https://tcg.ravensburgerplay.com/events/' + encodeURIComponent(id); }
  function eventLink(id, name) {
    return '<a href="' + eventUrl(id) + '" target="_blank" rel="noopener noreferrer" title="' +
      esc(name) + '">' + esc(name) + '</a>';
  }
  function markScrollableTables() {
    [].slice.call(app.querySelectorAll('.tablewrap')).forEach(function (w) {
      if (w.scrollWidth > w.clientWidth + 1) w.classList.add('scrolls');
      else w.classList.remove('scrolls');
    });
  }

  var PAGE_SIZE = 25;

  // Tabela com paginacao: as linhas vao todas para o HTML e o JS mostra 25 de cada vez.
  function pagedTable(cls, head, rows, label, caption, id) {
    return '<div class="tablewrap" data-paged' + (id ? ' id="' + id + '"' : '') + '><table class="' + cls + '">' +
      (caption ? '<caption class="sr-only">' + caption + '</caption>' : '') +
      '<thead><tr>' + head + '</tr></thead><tbody>' + rows.join('') + '</tbody></table></div>' +
      '<nav class="pager" aria-label="' + label + ' pages"></nav>';
  }

  function paginate(wrap, rows, nav) {
    var shown = rows, page = 1, prev, next, status;
    if (nav) {
      nav.innerHTML = '<button type="button" data-dir="-1">Previous</button>' +
        '<span class="pager-status" aria-live="polite"></span>' +
        '<button type="button" data-dir="1">Next</button>';
      prev = nav.firstChild; status = prev.nextSibling; next = nav.lastChild;
      nav.addEventListener('click', function (ev) {
        var b = ev.target.closest('button');
        if (!b || b.disabled) return;
        page += Number(b.getAttribute('data-dir'));
        render();
        var top = wrap.getBoundingClientRect().top;
        if (top < 0) window.scrollTo(0, window.scrollY + top - 16);
      });
    }
    function render() {
      var total = Math.max(1, Math.ceil(shown.length / PAGE_SIZE));
      if (page > total) page = total;
      var start = (page - 1) * PAGE_SIZE, end = start + PAGE_SIZE;
      rows.forEach(function (r) { r.hidden = true; r.classList.remove('last'); });
      shown.forEach(function (r, i) { r.hidden = !(i >= start && i < end); });
      var visible = shown.slice(start, end);
      if (visible.length) visible[visible.length - 1].classList.add('last');
      if (nav) {
        nav.hidden = shown.length <= PAGE_SIZE;
        prev.disabled = page <= 1;
        next.disabled = page >= total;
        status.textContent = 'Page ' + page + ' of ' + total;
      }
      markScrollableTables();
    }
    return { show: function (list) { shown = list; page = 1; render(); } };
  }

  function wirePagers() {
    var pagers = {};
    [].slice.call(app.querySelectorAll('.tablewrap[data-paged]')).forEach(function (wrap) {
      var rows = [].slice.call(wrap.querySelectorAll('tbody tr'));
      var pg = paginate(wrap, rows, wrap.nextElementSibling);
      pg.rows = rows;
      pg.show(rows);
      if (wrap.id) pagers[wrap.id] = pg;
    });
    return pagers;
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
        '<td class="txt"><a href="' + link(p.id) + '"' + nameAttr + '>' + esc(p.name) + '</a></td>' +
        '<td class="num elo">' + rnd(p.rating) + '</td>' +
        '<td class="num">' + p.games + '</td>' +
        '<td class="num wide">' + p.wins + '\u2013' + p.draws + '\u2013' + p.losses + '</td>' +
        '<td class="wide">' + form + '</td></tr>';
    });
    var provNote = D.players.length > ranked.length
      ? ' Players with fewer than ' + m.minGames + ' matches appear at the bottom, unranked.' : '';
    return '<h1>Lorcana Portugal Elo Ranking</h1>' +
      '<p class="lead">' + D.players.length + ' players, ' + m.matches + ' matches and ' + m.events +
      ' events since ' + esc(m.since) + '.' + provNote + '</p>' +
      '<div class="search"><label class="sr-only" for="q">Search for a player</label>' +
      '<input id="q" type="search" placeholder="Search for a player" autocomplete="off"></div>' +
      pagedTable('ranking',
        '<th class="num" scope="col">Rank</th><th scope="col">Player</th><th class="num" scope="col">Elo</th>' +
        '<th class="num" scope="col">Matches</th><th class="num wide" scope="col">W\u2013D\u2013L</th>' +
        '<th class="wide" scope="col">Last 5</th>', rows, 'Ranking', 'Elo ranking', 'ranking-table') +
      '<p id="empty" class="empty" hidden>No player found. Check the spelling of the name.</p>';
  }

  function wireSearch(pg) {
    var input = document.getElementById('q');
    if (!input || !pg) return;
    var empty = document.getElementById('empty');
    function apply() {
      var q = fold(query.trim());
      var matches = pg.rows.filter(function (r) {
        return !q || r.getAttribute('data-name').indexOf(q) !== -1;
      });
      pg.show(matches);
      empty.hidden = matches.length !== 0;
    }
    input.value = query;
    input.addEventListener('input', function () { query = input.value; apply(); });
    apply();
  }

  // ---------- jogador ----------
  var MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  function dayNum(iso) { var p = iso.split('-'); return Date.UTC(+p[0], +p[1] - 1, +p[2]) / 86400000; }

  // ratings[0] e o Elo inicial; dates[i] e a data de ratings[i] (dates[0] = data da 1a partida).
  // O eixo x e o tempo: partidas do mesmo dia repartem-se pela largura desse dia.
  function chart(name, ratings, dates) {
    var w = 640, h = 220, pl = 44, pr = 14, pt = 14, pb = 38, start = D.consts.start;
    var n = ratings.length;
    var peak = Math.max.apply(null, ratings), low = Math.min.apply(null, ratings);
    // margem so na geometria: os rotulos do eixo mostram o pico e o minimo reais
    var lo = low - 10, hi = peak + 10;
    if (hi - lo < 60) { var mid = (hi + lo) / 2; lo = mid - 30; hi = mid + 30; }

    var perDay = {};
    dates.slice(1).forEach(function (d) { perDay[d] = (perDay[d] || 0) + 1; });
    var seen = {}, t = [dayNum(dates[0])];
    dates.slice(1).forEach(function (d) {
      seen[d] = (seen[d] || 0) + 1;
      t.push(dayNum(d) + seen[d] / (perDay[d] + 1));
    });
    var t0 = t[0], t1 = Math.floor(t[n - 1]) + 1;
    function x(i) { return pl + (w - pl - pr) * (n > 1 ? (t[i] - t0) / (t1 - t0) : 0.5); }
    function y(v) { return pt + (h - pt - pb) * (hi - v) / (hi - lo); }
    var base = y(start);
    function tick(v) {
      if (Math.abs(y(v) - base) < 13) return '';
      return '<text class="chart-tick" x="' + (pl - 6) + '" y="' + (y(v) + 4).toFixed(1) +
        '" text-anchor="end">' + rnd(v) + '</text>';
    }

    // meses: linha e rotulo no dia 1; o rotulo do 1.o mes fica na margem esquerda se houver espaco
    var months = '', lastEnd = 0, drawn = false;
    function monthLabel(px, month, year) {
      if (px < lastEnd || px + 22 > w - 2) return;
      months += '<text class="chart-tick" x="' + px.toFixed(1) + '" y="' + (h - 19) + '">' + month + '</text>';
      if (year) months += '<text class="chart-tick" x="' + px.toFixed(1) + '" y="' + (h - 6) + '">' + year + '</text>';
      lastEnd = px + 30;
      drawn = true;
    }
    var first = new Date(t0 * 86400000);
    var yr = first.getUTCFullYear(), mo = first.getUTCMonth();
    var bounds = [];
    for (var d = Date.UTC(yr, mo + 1, 1) / 86400000; d < t1; d = Date.UTC(yr, ++mo + 1, 1) / 86400000) {
      bounds.push({ px: pl + (w - pl - pr) * (d - t0) / (t1 - t0), m: new Date(d * 86400000) });
    }
    if (!bounds.length || bounds[0].px - pl >= 28) {
      monthLabel(pl, MONTHS[first.getUTCMonth()], first.getUTCFullYear());
    }
    bounds.forEach(function (bd) {
      months += '<line class="chart-grid" x1="' + bd.px.toFixed(1) + '" x2="' + bd.px.toFixed(1) +
        '" y1="' + pt + '" y2="' + (h - pb) + '"/>';
      monthLabel(bd.px + 3, MONTHS[bd.m.getUTCMonth()],
        !drawn || bd.m.getUTCMonth() === 0 ? bd.m.getUTCFullYear() : '');
    });

    var pts = ratings.map(function (v, i) { return x(i).toFixed(1) + ',' + y(v).toFixed(1); }).join(' ');
    var label = 'Evolu\u00e7\u00e3o do Elo de ' + name + ': de ' + rnd(ratings[0]) + ' para ' + rnd(ratings[n - 1]);
    return '<svg class="chart" viewBox="0 0 ' + w + ' ' + h + '" role="img" aria-label="' + esc(label) + '">' +
      months +
      '<line class="chart-base" x1="' + pl + '" x2="' + (w - pr) + '" y1="' + base.toFixed(1) + '" y2="' + base.toFixed(1) + '"/>' +
      '<text class="chart-tick" x="' + (pl - 6) + '" y="' + (base + 4).toFixed(1) + '" text-anchor="end">' + rnd(start) + '</text>' +
      tick(peak) + tick(low) +
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
    });
    return '<h2>Head-to-head</h2>' + pagedTable('matches',
      '<th scope="col">Opponent</th><th class="num" scope="col">Matches</th>' +
      '<th class="num wide" scope="col">W\u2013D\u2013L</th><th class="num" scope="col">Win %</th>',
      rows, 'Head-to-head');
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
      return '<tr><td>' + fmtDate(e.date) + '</td><td class="txt">' + eventLink(eid, evName) + '</td>' +
        '<td class="num">' + e.rounds + '</td><td class="num wide">' + e.w + '\u2013' + e.d + '\u2013' + e.l + '</td>' +
        '<td class="num">' + delta(e.end - e.start) + '</td></tr>';
    });
    return '<h2>Events</h2>' + pagedTable('matches',
      '<th scope="col">Date</th><th scope="col">Event</th><th class="num" scope="col">Rounds</th>' +
      '<th class="num wide" scope="col">W\u2013D\u2013L</th><th class="num" scope="col">Change</th>',
      rows, 'Events');
  }

  function playerView(id) {
    var p = byId[id];
    if (!p) return notFound();
    var ratings = [D.consts.start].concat(p.h.map(function (h) { return h[5]; }));
    var dates = [p.h.length ? p.h[0][0] : '1970-01-01'].concat(p.h.map(function (h) { return h[0]; }));
    var standing = p.rank
      ? ordinal(p.rank) + ' out of ' + D.meta.ranked + ' ranked players.'
      : 'Not yet ranked: needs ' + D.meta.minGames + ' matches, has ' + p.games + '.';
    var pct = p.games ? Math.round(((p.wins + 0.5 * p.draws) / p.games) * 100) : 0;
    var rows = p.h.slice().reverse().map(function (h) {
      var ev = D.events[h[1]] || {};
      var opp = h[3] && byId[h[3]]
        ? '<a href="' + link(h[3]) + '">' + esc(byId[h[3]].name) + '</a>' : 'Anonymous player';
      var evName = ev.name || h[1];
      return '<tr><td>' + fmtDate(h[0]) + '</td><td class="txt">' + eventLink(h[1], evName) + '</td><td class="num">' + h[2] +
        '</td><td>' + opp + '</td><td>' + chip(h[4]) + '</td><td class="num">' + rnd(h[5]) +
        ' <span class="delta">(' + delta(h[6]) + ')</span></td></tr>';
    });
    var realNameLine = p.realName ? '<p class="crumb-sub">' + esc(p.realName) + '</p>' : '';
    return '<p class="crumb"><a href="#/">Ranking</a></p><h1>' + esc(p.name) + '</h1>' + realNameLine +
      '<div class="hero"><p class="bignum" aria-label="Current Elo">' + rnd(p.rating) + '</p>' +
      '<p class="hero-text">' + standing + '<br>Peak of ' + rnd(p.peak) + '. ' + p.wins + ' wins, ' +
      p.draws + ' draws and ' + p.losses + ' losses (' + pct + '% win rate).</p></div>' +
      '<h2>Elo progression</h2>' + chart(p.name, ratings, dates) +
      statGrid(p) +
      h2hSection(p) +
      eventsSection(p) +
      '<h2>Matches</h2>' + pagedTable('matches',
        '<th scope="col">Date</th><th scope="col">Event</th><th class="num" scope="col">Round</th>' +
        '<th scope="col">Opponent</th><th scope="col">Result</th><th class="num" scope="col">Elo after</th>',
        rows, 'Matches');
  }

  // ---------- events ----------
  function eventsView() {
    var list = Object.keys(D.events).map(function (k) { return D.events[k]; })
      .sort(function (a, b) { return a.date < b.date ? 1 : -1; });
    var rows = list.map(function (e) {
      var where = [e.store, e.city].filter(Boolean).join(', ');
      var evName = e.name || e.id;
      return '<tr><td>' + fmtDate(e.date) + '</td><td class="txt">' + eventLink(e.id, evName) +
        '</td><td class="txt wide">' + esc(where) +
        '</td><td class="num wide">' + e.players + '</td><td class="num">' + e.matches + '</td></tr>';
    });
    return '<h1>Events</h1><p class="lead">Events at Portuguese stores with results recorded since ' +
      esc(D.meta.since) + '.</p>' + pagedTable('matches',
      '<th scope="col">Date</th><th scope="col">Event</th><th class="wide" scope="col">Store</th>' +
      '<th class="num wide" scope="col">Players</th><th class="num" scope="col">Matches</th>', rows, 'Events');
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
      '<p>Bigger events also count for more: matches at an event with 17\u201332 players move rating 1.25\u00d7 as ' +
      'much as usual, and events with 33 or more players move it 1.5\u00d7. Smaller events use the normal rate.</p>' +
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
    [].slice.call(document.querySelectorAll('nav a')).forEach(function (a) {
      if (a.getAttribute('data-key') === key) a.setAttribute('aria-current', 'page');
      else a.removeAttribute('aria-current');
    });
    wireSearch(wirePagers()['ranking-table']);
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
