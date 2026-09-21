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
  function delta(x) {
    var r = Math.round(x);
    if (r === 0) return '0';
    return (r > 0 ? '+' : '\u2212') + Math.abs(r);
  }
  function chip(score) {
    if (score === 1) return '<span class="chip chip-w" title="Vit\u00f3ria">V</span>';
    if (score === 0) return '<span class="chip chip-l" title="Derrota">D</span>';
    return '<span class="chip chip-d" title="Empate">E</span>';
  }
  function link(id) { return '#/jogador/' + encodeURIComponent(id); }
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
      return '<tr' + (p.rank ? '' : ' class="prov"') + ' data-name="' + esc(fold(p.name)) + '">' +
        '<td class="num">' + (p.rank || '\u2013') + '</td>' +
        '<td><a href="' + link(p.id) + '">' + esc(p.name) + '</a></td>' +
        '<td class="num elo">' + rnd(p.rating) + '</td>' +
        '<td class="num">' + p.games + '</td>' +
        '<td class="num wide">' + p.wins + '\u2013' + p.draws + '\u2013' + p.losses + '</td>' +
        '<td class="wide">' + form + '</td></tr>';
    }).join('');
    var provNote = D.players.length > ranked.length
      ? ' Quem tem menos de ' + m.minGames + ' partidas aparece no fim, sem posi\u00e7\u00e3o.' : '';
    return '<h1>Ranking Elo de Lorcana em Portugal</h1>' +
      '<p class="lead">' + D.players.length + ' jogadores, ' + m.matches + ' partidas e ' + m.events +
      ' eventos desde ' + esc(m.since) + '.' + provNote + '</p>' +
      '<div class="search"><label class="sr-only" for="q">Procurar jogador</label>' +
      '<input id="q" type="search" placeholder="Procura um jogador" autocomplete="off"></div>' +
      '<div class="tablewrap"><table class="ranking"><caption class="sr-only">Classifica\u00e7\u00e3o por Elo</caption>' +
      '<thead><tr><th class="num" scope="col">Pos.</th><th scope="col">Jogador</th><th class="num" scope="col">Elo</th>' +
      '<th class="num" scope="col">Jogos</th><th class="num wide" scope="col">V\u2013E\u2013D</th>' +
      '<th class="wide" scope="col">\u00daltimos 5</th></tr></thead><tbody>' + rows + '</tbody></table></div>' +
      '<p id="empty" class="empty" hidden>Nenhum jogador encontrado. Confirma a grafia do nome.</p>';
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

  function playerView(id) {
    var p = byId[id];
    if (!p) return notFound();
    var ratings = [D.consts.start].concat(p.h.map(function (h) { return h[5]; }));
    var standing = p.rank
      ? p.rank + '.\u00ba entre ' + D.meta.ranked + ' jogadores classificados.'
      : 'Ainda sem posi\u00e7\u00e3o: precisa de ' + D.meta.minGames + ' partidas e tem ' + p.games + '.';
    var pct = p.games ? Math.round(((p.wins + 0.5 * p.draws) / p.games) * 100) : 0;
    var rows = p.h.slice().reverse().map(function (h) {
      var ev = D.events[h[1]] || {};
      var opp = h[3] && byId[h[3]]
        ? '<a href="' + link(h[3]) + '">' + esc(byId[h[3]].name) + '</a>' : 'Jogador an\u00f3nimo';
      var evName = ev.name || h[1];
      return '<tr><td>' + fmtDate(h[0]) + '</td><td title="' + esc(evName) + '">' + esc(evName) + '</td><td class="num">' + h[2] +
        '</td><td>' + opp + '</td><td>' + chip(h[4]) + '</td><td class="num">' + rnd(h[5]) +
        ' <span class="delta">(' + delta(h[6]) + ')</span></td></tr>';
    }).join('');
    return '<p class="crumb"><a href="#/">Ranking</a></p><h1>' + esc(p.name) + '</h1>' +
      '<div class="hero"><p class="bignum" aria-label="Elo atual">' + rnd(p.rating) + '</p>' +
      '<p class="hero-text">' + standing + '<br>M\u00e1ximo de ' + rnd(p.peak) + '. ' + p.wins + ' vit\u00f3rias, ' +
      p.draws + ' empates e ' + p.losses + ' derrotas (' + pct + ' % de aproveitamento).</p></div>' +
      '<h2>Evolu\u00e7\u00e3o do Elo</h2>' + chart(p.name, ratings) +
      '<h2>Partidas</h2><div class="tablewrap"><table class="matches"><thead><tr><th scope="col">Data</th>' +
      '<th scope="col">Evento</th><th class="num" scope="col">Ronda</th><th scope="col">Advers\u00e1rio</th>' +
      '<th scope="col">Resultado</th><th class="num" scope="col">Elo depois</th></tr></thead><tbody>' +
      rows + '</tbody></table></div>';
  }

  // ---------- eventos ----------
  function eventsView() {
    var list = Object.keys(D.events).map(function (k) { return D.events[k]; })
      .sort(function (a, b) { return a.date < b.date ? 1 : -1; });
    var rows = list.map(function (e) {
      var where = [e.store, e.city].filter(Boolean).join(', ');
      var evName = e.name || e.id;
      return '<tr><td>' + fmtDate(e.date) + '</td><td title="' + esc(evName) + '">' + esc(evName) + '</td><td>' + esc(where) +
        '</td><td class="num">' + e.players + '</td><td class="num">' + e.matches + '</td></tr>';
    }).join('');
    return '<h1>Eventos</h1><p class="lead">Eventos em lojas portuguesas com resultados registados desde ' +
      esc(D.meta.since) + '.</p><div class="tablewrap"><table class="matches"><thead><tr><th scope="col">Data</th>' +
      '<th scope="col">Evento</th><th scope="col">Loja</th><th class="num" scope="col">Jogadores</th>' +
      '<th class="num" scope="col">Partidas</th></tr></thead><tbody>' + rows + '</tbody></table></div>';
  }

  // ---------- sobre ----------
  function aboutView() {
    var c = D.consts, m = D.meta;
    var contact = m.contact
      ? '<a href="mailto:' + esc(m.contact) + '">' + esc(m.contact) + '</a>'
      : 'o contacto do respons\u00e1vel (por definir)';
    return '<h1>Sobre o ranking</h1>' +
      '<h2>O que \u00e9</h2><p>Uma classifica\u00e7\u00e3o Elo dos jogadores de Disney Lorcana em Portugal, calculada a partir ' +
      'dos resultados de torneios e ligas registados no Ravensburger Play Hub. S\u00f3 contam eventos em lojas ' +
      'portuguesas, realizados desde ' + esc(m.since) + '.</p>' +
      '<h2>Como o Elo funciona</h2><p>Todos come\u00e7am com ' + c.start + ' pontos. Depois de cada partida, quem ganha ' +
      'recebe pontos e quem perde cede-os. Ganhar a um advers\u00e1rio com Elo mais alto vale mais do que ganhar a um ' +
      'mais baixo. Um empate conta como meia vit\u00f3ria.</p>' +
      '<p>Nas primeiras ' + c.prov + ' partidas as varia\u00e7\u00f5es s\u00e3o maiores (K = ' + c.k1 + '), para o Elo chegar ' +
      'depressa ao n\u00edvel certo. Depois passa a K = ' + c.k2 + '. As partidas de uma mesma ronda s\u00e3o calculadas ' +
      'com o Elo que cada jogador tinha antes dessa ronda. Byes n\u00e3o contam.</p>' +
      '<h2>Quem aparece com posi\u00e7\u00e3o</h2><p>Jogadores com pelo menos ' + m.minGames + ' partidas. Os outros ' +
      'aparecem no fim da tabela, sem posi\u00e7\u00e3o.</p>' +
      '<h2>Privacidade</h2><p>Mostramos apenas o nome que o Play Hub disponibiliza publicamente. Se preferires n\u00e3o ' +
      'aparecer, contacta ' + contact + ' e o teu perfil deixa de ser mostrado. As tuas partidas continuam a contar ' +
      'para o Elo dos advers\u00e1rios, mas o teu nome \u00e9 substitu\u00eddo por \u201cJogador an\u00f3nimo\u201d.</p>';
  }

  function notFound() {
    return '<h1>P\u00e1gina n\u00e3o encontrada</h1><p>Este jogador n\u00e3o existe ou foi removido. ' +
      '<a href="#/">Voltar ao ranking</a>.</p>';
  }

  // ---------- router ----------
  var first = true;
  function route() {
    var h = location.hash.replace(/^#\/?/, '');
    var parts = h.split('/');
    var html, key = 'ranking', title = 'Ranking';
    if (parts[0] === 'jogador' && parts[1]) {
      var id = decodeURIComponent(parts.slice(1).join('/'));
      html = playerView(id);
      title = byId[id] ? byId[id].name : 'N\u00e3o encontrado';
    } else if (parts[0] === 'eventos') {
      html = eventsView(); key = 'eventos'; title = 'Eventos';
    } else if (parts[0] === 'sobre') {
      html = aboutView(); key = 'sobre'; title = 'Sobre';
    } else {
      html = rankingView();
    }
    app.innerHTML = html;
    document.title = title + ' \u00b7 Elo Lorcana Portugal';
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
