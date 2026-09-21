// Versao web de uma so pagina: ranking, jogador, eventos e sobre.
// Os dados (DATA) sao calculados em Python e embebidos na pagina.
(function () {
  var D = DATA;
  var byId = {};
  D.players.forEach(function (p) { byId[p.id] = p; });
  var app = document.getElementById('app');
  var query = '';
  var chartModel = null;      // pontos do grafico do jogador atual (para o tooltip)
  var hideChartTip = null;

  // ---------- idiomas ----------
  // Todo o texto visivel vive aqui. {nome} e substituido por t(chave, {nome: valor}).
  var T = {
    en: {
      navMain: 'Main', navRanking: 'Ranking', navIntl: 'International', navEvents: 'Events', navAbout: 'About',
      demo: 'Sample data: players and results are made up to test the site.',
      footer: 'Fan project, not affiliated with Ravensburger or Disney. Disney Lorcana is a trademark of its respective owners. Results sourced from the Ravensburger Play Hub. Updated on {date}.',
      win: 'Win', loss: 'Loss', draw: 'Draw', w: 'W', d: 'D', l: 'L', wdl: 'W\u2013D\u2013L',
      anon: 'Anonymous player',
      prev: 'Previous', next: 'Next', pageOf: 'Page {page} of {total}', pagesOf: '{label} pages',
      months: 'Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec',
      // ranking
      rankingTitle: 'Lorcana Portugal Elo Ranking',
      rankingLead: '{players} players, {matches} matches and {events} events since {since}.',
      rankingProv: ' Players with fewer than {min} matches appear at the bottom, unranked.',
      search: 'Search for a player',
      empty: 'No player found. Check the spelling of the name.',
      eloRanking: 'Elo ranking',
      colRank: 'Rank', colPlayer: 'Player', colElo: 'Elo', colMatches: 'Matches', colLast5: 'Last 5',
      // player
      ordinal: function (n) {
        var r = n % 100;
        if (r >= 11 && r <= 13) return n + 'th';
        switch (n % 10) {
          case 1: return n + 'st';
          case 2: return n + 'nd';
          case 3: return n + 'rd';
          default: return n + 'th';
        }
      },
      standingRanked: '{ord} out of {ranked} ranked players.',
      standingUnranked: 'Not yet ranked: needs {min} matches, has {games}.',
      currentElo: 'Current Elo',
      intlElo: 'International Elo', intlOn: 'See {name} on elorcana.com',
      intlTitle: 'International Elo of Portuguese players',
      intlLead: '{n} Portuguese players with an international Elo on elorcana.com, ranked by it. Data updated on {date}.',
      intlNote: 'International Elo comes from elorcana.com and only uses Ravensburger Play Hub results (Melee is left out). elorcana only tracks official events and community events with over 512 players, so players who have never played one are not listed. Players are matched by their Play Hub name; when several Play Hub players share a name we skip them rather than guess.',
      intlEmpty: 'No international Elo data yet.',
      colIntl: 'International Elo', colWorldRank: 'elorcana rank', colPtElo: 'Portugal Elo',
      heroText: 'Peak of {peak}. {w} wins, {d} draws and {l} losses ({pct}% win rate).',
      secProgression: 'Elo progression', secH2h: 'Head-to-head', secEvents: 'Events', secMatches: 'Matches',
      chartLabel: 'Elo progression of {name}: from {from} to {to}',
      chartStart: 'Starting Elo', chartVs: 'vs {opp}',
      statPeak: 'Peak', statLow: 'Low', statEvents: 'Events',
      statWinStreak: 'Best win streak', statLossStreak: 'Worst loss streak',
      statBestGain: 'Biggest single-match gain', statWorstDrop: 'Biggest single-match drop',
      statFavorite: 'As favorite', statUnderdog: 'As underdog', nMatches: '{n} matches',
      tagNemesis: 'toughest rival', tagVictim: 'favorable opponent',
      colOpponent: 'Opponent', colWinPct: 'Win %', colDate: 'Date', colEvent: 'Event',
      colRounds: 'Rounds', colChange: 'Change', colRound: 'Round', colResult: 'Result', colEloAfter: 'Elo after',
      // events
      eventsTitle: 'Events',
      eventsLead: 'Events at Portuguese stores with results recorded since {since}.',
      colStore: 'Store', colPlayers: 'Players',
      // about
      aboutTitle: 'About the ranking',
      aboutWhatH: 'What this is',
      aboutWhat: 'An Elo ranking of Disney Lorcana players in Portugal, calculated from tournament and league results recorded on the Ravensburger Play Hub. Only events at Portuguese stores count, held since {since}.',
      aboutHowH: 'How Elo works',
      aboutHow1: 'Everyone starts with {start} points. After each match, the winner gains points and the loser loses them. Beating a higher-rated opponent is worth more than beating a lower-rated one. A draw counts as half a win.',
      aboutHow2: 'In the first {prov} matches, swings are bigger (K = {k1}), so Elo reaches the right level quickly. After that it switches to K = {k2}. Matches within the same round are calculated using each player\u2019s Elo from before that round. Byes don\u2019t count.',
      aboutHow3: 'Bigger events also count for more: matches at an event with 17\u201332 players move rating 1.25\u00d7 as much as usual, and events with 33 or more players move it 1.5\u00d7. Smaller events use the normal rate.',
      aboutRankH: 'Who gets a rank',
      aboutRank: 'Players with at least {min} matches. Others appear at the bottom of the table, unranked.',
      aboutIntlH: 'International Elo',
      aboutIntl: 'Where available, each player page also shows the international Elo from {site}, which rates players worldwide using official Play Hub events. It is a separate rating from the Portugal Elo on this site and is shown for reference only.',
      aboutPrivH: 'Privacy',
      aboutPriv: 'We only show the name that the Play Hub makes publicly available. If you\u2019d rather not appear, contact {contact} and your profile will stop being shown. Your matches still count toward your opponents\u2019 Elo, but your name is replaced with \u201c{anon}\u201d.',
      contactUnset: 'the site contact (to be set)',
      // 404
      notFoundTitle: 'Page not found', notFoundShort: 'Not found',
      notFound: 'This player doesn\u2019t exist or has been removed.', backToRanking: 'Back to ranking'
    },
    pt: {
      navMain: 'Principal', navRanking: 'Ranking', navIntl: 'Internacional', navEvents: 'Eventos', navAbout: 'Sobre',
      demo: 'Dados de exemplo: os jogadores e os resultados s\u00e3o inventados para testar o site.',
      footer: 'Projeto de f\u00e3s, sem afilia\u00e7\u00e3o \u00e0 Ravensburger ou \u00e0 Disney. Disney Lorcana \u00e9 uma marca registada dos respetivos propriet\u00e1rios. Resultados obtidos do Ravensburger Play Hub. Atualizado em {date}.',
      win: 'Vit\u00f3ria', loss: 'Derrota', draw: 'Empate', w: 'V', d: 'E', l: 'D', wdl: 'V\u2013E\u2013D',
      anon: 'Jogador an\u00f3nimo',
      prev: 'Anterior', next: 'Seguinte', pageOf: 'P\u00e1gina {page} de {total}', pagesOf: 'P\u00e1ginas: {label}',
      months: 'Jan,Fev,Mar,Abr,Mai,Jun,Jul,Ago,Set,Out,Nov,Dez',
      rankingTitle: 'Ranking Elo Lorcana Portugal',
      rankingLead: '{players} jogadores, {matches} partidas e {events} eventos desde {since}.',
      rankingProv: ' Os jogadores com menos de {min} partidas aparecem no fim, sem classifica\u00e7\u00e3o.',
      search: 'Pesquisar jogador',
      empty: 'Nenhum jogador encontrado. Verifica a grafia do nome.',
      eloRanking: 'Ranking Elo',
      colRank: 'Pos.', colPlayer: 'Jogador', colElo: 'Elo', colMatches: 'Partidas', colLast5: '\u00daltimas 5',
      ordinal: function (n) { return n + '.\u00ba'; },
      standingRanked: '{ord} de {ranked} jogadores classificados.',
      standingUnranked: 'Ainda sem classifica\u00e7\u00e3o: precisa de {min} partidas, tem {games}.',
      currentElo: 'Elo atual',
      intlElo: 'Elo internacional', intlOn: 'Ver {name} no elorcana.com',
      intlTitle: 'Elo internacional dos jogadores portugueses',
      intlLead: '{n} jogadores portugueses com Elo internacional no elorcana.com, ordenados por ele. Dados atualizados em {date}.',
      intlNote: 'O Elo internacional vem do elorcana.com e usa apenas resultados do Ravensburger Play Hub (o Melee fica de fora). O elorcana só regista eventos oficiais e eventos de comunidade com mais de 512 jogadores, por isso quem nunca jogou um não aparece. Os jogadores são associados pelo nome no Play Hub; quando vários jogadores do Play Hub têm o mesmo nome, ignoramos em vez de adivinhar.',
      intlEmpty: 'Ainda não há dados de Elo internacional.',
      colIntl: 'Elo internacional', colWorldRank: 'Pos. no elorcana', colPtElo: 'Elo Portugal',
      heroText: 'M\u00e1ximo de {peak}. {w} vit\u00f3rias, {d} empates e {l} derrotas ({pct}% de vit\u00f3rias).',
      secProgression: 'Evolu\u00e7\u00e3o do Elo', secH2h: 'Frente a frente', secEvents: 'Eventos', secMatches: 'Partidas',
      chartLabel: 'Evolu\u00e7\u00e3o do Elo de {name}: de {from} para {to}',
      chartStart: 'Elo inicial', chartVs: 'vs {opp}',
      statPeak: 'M\u00e1ximo', statLow: 'M\u00ednimo', statEvents: 'Eventos',
      statWinStreak: 'Melhor sequ\u00eancia de vit\u00f3rias', statLossStreak: 'Pior sequ\u00eancia de derrotas',
      statBestGain: 'Maior ganho numa partida', statWorstDrop: 'Maior perda numa partida',
      statFavorite: 'Como favorito', statUnderdog: 'Como azar\u00e3o', nMatches: '{n} partidas',
      tagNemesis: 'maior rival', tagVictim: 'oponente favor\u00e1vel',
      colOpponent: 'Advers\u00e1rio', colWinPct: '% vit\u00f3rias', colDate: 'Data', colEvent: 'Evento',
      colRounds: 'Rondas', colChange: 'Varia\u00e7\u00e3o', colRound: 'Ronda', colResult: 'Resultado', colEloAfter: 'Elo depois',
      eventsTitle: 'Eventos',
      eventsLead: 'Eventos em lojas portuguesas com resultados registados desde {since}.',
      colStore: 'Loja', colPlayers: 'Jogadores',
      aboutTitle: 'Sobre o ranking',
      aboutWhatH: 'O que \u00e9',
      aboutWhat: 'Um ranking Elo de jogadores de Disney Lorcana em Portugal, calculado a partir dos resultados de torneios e ligas registados no Ravensburger Play Hub. S\u00f3 contam eventos em lojas portuguesas, realizados desde {since}.',
      aboutHowH: 'Como funciona o Elo',
      aboutHow1: 'Toda a gente come\u00e7a com {start} pontos. Depois de cada partida, o vencedor ganha pontos e o perdedor perde-os. Vencer um advers\u00e1rio com Elo mais alto vale mais do que vencer um com Elo mais baixo. Um empate conta como meia vit\u00f3ria.',
      aboutHow2: 'Nas primeiras {prov} partidas, as oscila\u00e7\u00f5es s\u00e3o maiores (K = {k1}), para o Elo chegar depressa ao n\u00edvel certo. Depois passa a K = {k2}. As partidas da mesma ronda s\u00e3o calculadas com o Elo que cada jogador tinha antes dessa ronda. Os byes n\u00e3o contam.',
      aboutHow3: 'Os eventos maiores tamb\u00e9m valem mais: as partidas num evento com 17\u201332 jogadores movem o Elo 1,25\u00d7 mais do que o normal, e os eventos com 33 ou mais jogadores movem-no 1,5\u00d7. Os eventos mais pequenos usam a taxa normal.',
      aboutRankH: 'Quem tem classifica\u00e7\u00e3o',
      aboutRank: 'Jogadores com pelo menos {min} partidas. Os restantes aparecem no fim da tabela, sem classifica\u00e7\u00e3o.',
      aboutIntlH: 'Elo internacional',
      aboutIntl: 'Quando existe, a página de cada jogador mostra também o Elo internacional do {site}, que classifica jogadores de todo o mundo com eventos oficiais do Play Hub. É uma classificação à parte do Elo Portugal deste site e serve apenas de referência.',
      aboutPrivH: 'Privacidade',
      aboutPriv: 'S\u00f3 mostramos o nome que o Play Hub disponibiliza publicamente. Se preferires n\u00e3o aparecer, contacta {contact} e o teu perfil deixa de ser mostrado. As tuas partidas continuam a contar para o Elo dos teus advers\u00e1rios, mas o teu nome \u00e9 substitu\u00eddo por \u201c{anon}\u201d.',
      contactUnset: 'quem gere o site (contacto por definir)',
      notFoundTitle: 'P\u00e1gina n\u00e3o encontrada', notFoundShort: 'N\u00e3o encontrado',
      notFound: 'Este jogador n\u00e3o existe ou foi removido.', backToRanking: 'Voltar ao ranking'
    }
  };

  // portugues por omissao; a ultima escolha fica guardada no browser (localStorage) e volta na visita seguinte
  var lang = 'pt';
  try {
    var saved = localStorage.getItem('lang');
    if (saved && T[saved]) lang = saved;
  } catch (e) { /* sem armazenamento: fica em portugues */ }

  function t(key, vars) {
    var s = T[lang][key];
    if (s == null) s = T.en[key];
    if (s == null) return key;
    if (typeof s === 'function') return s(vars);
    return s.replace(/\{(\w+)\}/g, function (m, k) { return vars && vars[k] != null ? vars[k] : m; });
  }

  // texto fixo da moldura (cabecalho, rodape, botoes) marcado com data-i18n no HTML
  function applyStatic() {
    document.documentElement.lang = lang === 'pt' ? 'pt-PT' : 'en';
    [].slice.call(document.querySelectorAll('[data-i18n]')).forEach(function (el) {
      el.textContent = t(el.getAttribute('data-i18n'));
    });
    [].slice.call(document.querySelectorAll('[data-i18n-aria]')).forEach(function (el) {
      el.setAttribute('aria-label', t(el.getAttribute('data-i18n-aria')));
    });
    var foot = document.getElementById('foot');
    if (foot) foot.textContent = t('footer', { date: foot.getAttribute('data-updated') });
    [].slice.call(document.querySelectorAll('.lang-btn')).forEach(function (b) {
      b.setAttribute('aria-pressed', b.getAttribute('data-lang') === lang ? 'true' : 'false');
    });
  }

  function setLang(l) {
    if (!T[l] || l === lang) return;
    lang = l;
    try { localStorage.setItem('lang', l); } catch (e) { /* ignora */ }
    applyStatic();
    route(true);
  }

  // ---------- utilitarios ----------
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
    if (score === 1) return '<span class="chip chip-w" title="' + t('win') + '">' + t('w') + '</span>';
    if (score === 0) return '<span class="chip chip-l" title="' + t('loss') + '">' + t('l') + '</span>';
    return '<span class="chip chip-d" title="' + t('draw') + '">' + t('d') + '</span>';
  }
  function link(id) { return '#/player/' + encodeURIComponent(id); }
  function intlUrl(intl) { return 'https://elorcana.com/profile/' + encodeURIComponent(intl.id); }
  function intlLink(p) {
    return '<a href="' + intlUrl(p.intl) + '" target="_blank" rel="noopener noreferrer" title="' +
      esc(t('intlOn', { name: p.name })) + '">' + rnd(p.intl.elo) + '</a>';
  }
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
      '<nav class="pager" aria-label="' + esc(t('pagesOf', { label: label })) + '"></nav>';
  }

  function paginate(wrap, rows, nav) {
    var shown = rows, page = 1, prev, next, status;
    if (nav) {
      nav.innerHTML = '<button type="button" data-dir="-1">' + t('prev') + '</button>' +
        '<span class="pager-status" aria-live="polite"></span>' +
        '<button type="button" data-dir="1">' + t('next') + '</button>';
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
        status.textContent = t('pageOf', { page: page, total: total });
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
    var provNote = D.players.length > ranked.length ? t('rankingProv', { min: m.minGames }) : '';
    return '<h1>' + t('rankingTitle') + '</h1>' +
      '<p class="lead">' + t('rankingLead', { players: D.players.length, matches: m.matches, events: m.events,
        since: esc(m.since) }) + provNote + '</p>' +
      '<div class="search"><label class="sr-only" for="q">' + t('search') + '</label>' +
      '<input id="q" type="search" placeholder="' + esc(t('search')) + '" autocomplete="off"></div>' +
      pagedTable('ranking',
        '<th class="num" scope="col">' + t('colRank') + '</th><th scope="col">' + t('colPlayer') + '</th>' +
        '<th class="num" scope="col">' + t('colElo') + '</th><th class="num" scope="col">' + t('colMatches') + '</th>' +
        '<th class="num wide" scope="col">' + t('wdl') + '</th>' +
        '<th class="wide" scope="col">' + t('colLast5') + '</th>',
        rows, t('navRanking'), t('eloRanking'), 'ranking-table') +
      '<p id="empty" class="empty" hidden>' + t('empty') + '</p>';
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
  function dayNum(iso) { var p = iso.split('-'); return Date.UTC(+p[0], +p[1] - 1, +p[2]) / 86400000; }

  // ratings[0] e o Elo inicial; dates[i] e a data de ratings[i] (dates[0] = data da 1a partida).
  // O eixo x e o tempo: partidas do mesmo dia repartem-se pela largura desse dia.
  function chart(name, ratings, dates, info) {
    var w = 640, h = 220, pl = 44, pr = 14, pt = 14, pb = 38, start = D.consts.start;
    var n = ratings.length;
    var MONTHS = t('months').split(',');
    var peak = Math.max.apply(null, ratings), low = Math.min.apply(null, ratings);
    // margem so na geometria: os rotulos do eixo mostram o pico e o minimo reais
    var lo = low - 10, hi = peak + 10;
    if (hi - lo < 60) { var mid = (hi + lo) / 2; lo = mid - 30; hi = mid + 30; }

    var perDay = {};
    dates.slice(1).forEach(function (d) { perDay[d] = (perDay[d] || 0) + 1; });
    var seen = {}, tm = [dayNum(dates[0])];
    dates.slice(1).forEach(function (d) {
      seen[d] = (seen[d] || 0) + 1;
      tm.push(dayNum(d) + seen[d] / (perDay[d] + 1));
    });
    var t0 = tm[0], t1 = Math.floor(tm[n - 1]) + 1;
    function x(i) { return pl + (w - pl - pr) * (n > 1 ? (tm[i] - t0) / (t1 - t0) : 0.5); }
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

    var xs = ratings.map(function (v, i) { return x(i); });
    var ys = ratings.map(function (v) { return y(v); });
    var pts = ratings.map(function (v, i) { return xs[i].toFixed(1) + ',' + ys[i].toFixed(1); }).join(' ');
    var label = t('chartLabel', { name: name, from: rnd(ratings[0]), to: rnd(ratings[n - 1]) });
    chartModel = { w: w, h: h, xs: xs, ys: ys, ratings: ratings, dates: dates, info: info };
    return '<div class="chart-wrap"><svg class="chart" viewBox="0 0 ' + w + ' ' + h + '" role="img" tabindex="0" aria-label="' +
      esc(label) + '">' +
      months +
      '<line class="chart-base" x1="' + pl + '" x2="' + (w - pr) + '" y1="' + base.toFixed(1) + '" y2="' + base.toFixed(1) + '"/>' +
      '<text class="chart-tick" x="' + (pl - 6) + '" y="' + (base + 4).toFixed(1) + '" text-anchor="end">' + rnd(start) + '</text>' +
      tick(peak) + tick(low) +
      '<polyline class="chart-line" points="' + pts + '"/>' +
      '<circle class="chart-dot" cx="' + xs[n - 1].toFixed(1) + '" cy="' + ys[n - 1].toFixed(1) + '" r="4"/>' +
      '<g class="chart-hover" visibility="hidden"><line class="chart-cursor" y1="' + pt + '" y2="' + (h - pb) + '"/>' +
      '<circle class="chart-hover-dot" r="5"/></g>' +
      '<rect class="chart-hit" x="0" y="0" width="' + w + '" height="' + (h - pb) + '"/></svg>' +
      '<div class="chart-tip" role="status" aria-live="polite" hidden></div></div>';
  }

  // tooltip do grafico: rato, toque e teclado (setas). Mostra o Elo, a data e o resultado da partida.
  function wireChart() {
    var m = chartModel, wrap = app.querySelector('.chart-wrap');
    hideChartTip = null;
    if (!m || !wrap) return;
    var svg = wrap.querySelector('svg'), tip = wrap.querySelector('.chart-tip');
    var g = svg.querySelector('.chart-hover'), cursor = g.querySelector('line'), dot = g.querySelector('circle');
    var hit = svg.querySelector('.chart-hit');
    var cur = -1;

    function nearest(vx) {
      var best = 0, bd = Infinity;
      for (var i = 0; i < m.xs.length; i++) {
        var dd = Math.abs(m.xs[i] - vx);
        if (dd < bd) { bd = dd; best = i; }
      }
      return best;
    }
    function tipHtml(i) {
      var v = '<strong>' + rnd(m.ratings[i]) + '</strong>', inf = m.info[i];
      if (!inf) return v + '<span>' + t('chartStart') + '</span>';
      var opp = inf.opp && byId[inf.opp] ? esc(byId[inf.opp].name) : t('anon');
      var res = inf.score === 1 ? t('win') : inf.score === 0 ? t('loss') : t('draw');
      return v + '<span>' + fmtDate(inf.date) + '</span><span class="muted">' + res + ' ' + delta(inf.delta) +
        ' \u00b7 ' + t('chartVs', { opp: opp }) + '</span>';
    }
    function show(i) {
      cur = i;
      var r = svg.getBoundingClientRect(), sx = r.width / m.w, sy = r.height / m.h;
      var px = m.xs[i] * sx, py = m.ys[i] * sy;
      cursor.setAttribute('x1', m.xs[i].toFixed(1)); cursor.setAttribute('x2', m.xs[i].toFixed(1));
      dot.setAttribute('cx', m.xs[i].toFixed(1)); dot.setAttribute('cy', m.ys[i].toFixed(1));
      g.setAttribute('visibility', 'visible');
      tip.innerHTML = tipHtml(i);
      tip.hidden = false;
      var tw = tip.offsetWidth, th = tip.offsetHeight;
      var left = px + 14;
      if (left + tw > r.width) left = px - tw - 14;
      // nao cabe de nenhum dos lados (grafico estreito): centra por cima/baixo do ponto
      if (left < 0) left = Math.min(Math.max(0, px - tw / 2), r.width - tw);
      var top = py - th - 12;
      if (top < 0) top = py + 14;
      tip.style.left = left + 'px';
      tip.style.top = top + 'px';
    }
    function hide() {
      cur = -1;
      g.setAttribute('visibility', 'hidden');
      tip.hidden = true;
    }
    function fromPointer(ev) {
      var r = svg.getBoundingClientRect();
      show(nearest((ev.clientX - r.left) * (m.w / r.width)));
    }
    hideChartTip = hide;
    hit.addEventListener('pointermove', fromPointer);
    hit.addEventListener('pointerdown', fromPointer);
    hit.addEventListener('pointerleave', function (ev) { if (ev.pointerType === 'mouse') hide(); });
    svg.addEventListener('blur', hide);
    svg.addEventListener('keydown', function (ev) {
      var n = m.xs.length, next;
      if (ev.key === 'ArrowLeft') next = cur < 0 ? n - 1 : cur - 1;
      else if (ev.key === 'ArrowRight') next = cur < 0 ? n - 1 : cur + 1;
      else if (ev.key === 'Home') next = 0;
      else if (ev.key === 'End') next = n - 1;
      else if (ev.key === 'Escape') { hide(); return; }
      else return;
      ev.preventDefault();
      show(Math.max(0, Math.min(n - 1, next)));
    });
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
      statTile(t('statPeak'), rnd(p.peak)) +
      statTile(t('statLow'), rnd(e.low)) +
      statTile(t('statEvents'), e.events) +
      statTile(t('statWinStreak'), e.best_win_streak) +
      statTile(t('statLossStreak'), e.best_loss_streak) +
      statTile(t('statBestGain'), delta(e.best_gain)) +
      statTile(t('statWorstDrop'), delta(e.worst_loss)) +
      statTile(t('statFavorite'), favPct, t('nMatches', { n: e.fav_games })) +
      statTile(t('statUnderdog'), dogPct, t('nMatches', { n: e.dog_games })) +
      '</div>';
  }

  function h2hSection(p) {
    var list = (p.extra && p.extra.h2h) || [];
    if (!list.length) return '';
    var rows = list.map(function (o) {
      var opp = byId[o.id];
      var name = opp ? opp.name : t('anon');
      var cell = opp ? '<a href="' + link(o.id) + '">' + esc(name) + '</a>' : esc(name);
      var pct = Math.round(((o.wins + 0.5 * o.draws) / o.games) * 100);
      var tag = '';
      if (o.id === p.extra.nemesis) tag = ' <span class="tag tag-l">' + t('tagNemesis') + '</span>';
      else if (o.id === p.extra.victim) tag = ' <span class="tag tag-w">' + t('tagVictim') + '</span>';
      return '<tr><td>' + cell + tag + '</td><td class="num">' + o.games + '</td>' +
        '<td class="num wide">' + o.wins + '\u2013' + o.draws + '\u2013' + o.losses + '</td>' +
        '<td class="num">' + pct + ' %</td></tr>';
    });
    return '<h2>' + t('secH2h') + '</h2>' + pagedTable('matches',
      '<th scope="col">' + t('colOpponent') + '</th><th class="num" scope="col">' + t('colMatches') + '</th>' +
      '<th class="num wide" scope="col">' + t('wdl') + '</th><th class="num" scope="col">' + t('colWinPct') + '</th>',
      rows, t('secH2h'));
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
    return '<h2>' + t('secEvents') + '</h2>' + pagedTable('matches',
      '<th scope="col">' + t('colDate') + '</th><th scope="col">' + t('colEvent') + '</th>' +
      '<th class="num" scope="col">' + t('colRounds') + '</th>' +
      '<th class="num wide" scope="col">' + t('wdl') + '</th><th class="num" scope="col">' + t('colChange') + '</th>',
      rows, t('secEvents'));
  }

  function playerView(id) {
    var p = byId[id];
    if (!p) return notFound();
    var ratings = [D.consts.start].concat(p.h.map(function (h) { return h[5]; }));
    var dates = [p.h.length ? p.h[0][0] : '1970-01-01'].concat(p.h.map(function (h) { return h[0]; }));
    var info = [null].concat(p.h.map(function (h) { return { date: h[0], opp: h[3], score: h[4], delta: h[6] }; }));
    var standing = p.rank
      ? t('standingRanked', { ord: t('ordinal', p.rank), ranked: D.meta.ranked })
      : t('standingUnranked', { min: D.meta.minGames, games: p.games });
    var pct = p.games ? Math.round(((p.wins + 0.5 * p.draws) / p.games) * 100) : 0;
    var rows = p.h.slice().reverse().map(function (h) {
      var ev = D.events[h[1]] || {};
      var opp = h[3] && byId[h[3]]
        ? '<a href="' + link(h[3]) + '">' + esc(byId[h[3]].name) + '</a>' : t('anon');
      var evName = ev.name || h[1];
      return '<tr><td>' + fmtDate(h[0]) + '</td><td class="txt">' + eventLink(h[1], evName) + '</td><td class="num">' + h[2] +
        '</td><td>' + opp + '</td><td>' + chip(h[4]) + '</td><td class="num">' + rnd(h[5]) +
        ' <span class="delta">(' + delta(h[6]) + ')</span></td></tr>';
    });
    var realNameLine = p.realName ? '<p class="crumb-sub">' + esc(p.realName) + '</p>' : '';
    return '<p class="crumb"><a href="#/">' + t('navRanking') + '</a></p><h1>' + esc(p.name) + '</h1>' + realNameLine +
      '<div class="hero"><p class="bignum" aria-label="' + esc(t('currentElo')) + '">' + rnd(p.rating) + '</p>' +
      '<p class="hero-text">' + standing + '<br>' + t('heroText', { peak: rnd(p.peak), w: p.wins, d: p.draws,
        l: p.losses, pct: pct }) +
        (p.intl ? '<br>' + t('intlElo') + ': <strong>' + intlLink(p) + '</strong>' : '') + '</p></div>' +
      '<h2>' + t('secProgression') + '</h2>' + chart(p.name, ratings, dates, info) +
      statGrid(p) +
      h2hSection(p) +
      eventsSection(p) +
      '<h2>' + t('secMatches') + '</h2>' + pagedTable('matches',
        '<th scope="col">' + t('colDate') + '</th><th scope="col">' + t('colEvent') + '</th>' +
        '<th class="num" scope="col">' + t('colRound') + '</th><th scope="col">' + t('colOpponent') + '</th>' +
        '<th scope="col">' + t('colResult') + '</th><th class="num" scope="col">' + t('colEloAfter') + '</th>',
        rows, t('secMatches'));
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
    return '<h1>' + t('eventsTitle') + '</h1><p class="lead">' + t('eventsLead', { since: esc(D.meta.since) }) +
      '</p>' + pagedTable('matches',
      '<th scope="col">' + t('colDate') + '</th><th scope="col">' + t('colEvent') + '</th>' +
      '<th class="wide" scope="col">' + t('colStore') + '</th>' +
      '<th class="num wide" scope="col">' + t('colPlayers') + '</th><th class="num" scope="col">' + t('colMatches') + '</th>',
      rows, t('eventsTitle'));
  }

  // ---------- international ----------
  function intlView() {
    var list = D.players.filter(function (p) { return p.intl; })
      .sort(function (a, b) { return b.intl.elo - a.intl.elo || a.name.localeCompare(b.name); });
    var head = '<h1>' + t('intlTitle') + '</h1>';
    if (!list.length) return head + '<p class="lead">' + t('intlEmpty') + '</p>';
    var rows = list.map(function (p, i) {
      return '<tr data-name="' + esc(fold(p.name)) + '"><td class="num">' + (i + 1) + '</td>' +
        '<td class="txt"><a href="' + link(p.id) + '">' + esc(p.name) + '</a></td>' +
        '<td class="num elo">' + intlLink(p) + '</td>' +
        '<td class="num wide">' + (p.intl.rank ? '#' + p.intl.rank : '–') + '</td>' +
        '<td class="num">' + rnd(p.rating) + '</td></tr>';
    });
    return head + '<p class="lead">' + t('intlLead', { n: list.length, date: esc(D.meta.intlUpdated || '') }) + '</p>' +
      pagedTable('ranking',
        '<th class="num" scope="col">' + t('colRank') + '</th><th scope="col">' + t('colPlayer') + '</th>' +
        '<th class="num" scope="col">' + t('colIntl') + '</th>' +
        '<th class="num wide" scope="col">' + t('colWorldRank') + '</th>' +
        '<th class="num" scope="col">' + t('colPtElo') + '</th>',
        rows, t('navIntl'), t('intlTitle')) +
      '<p class="note">' + t('intlNote') + '</p>';
  }

  // ---------- about ----------
  function aboutView() {
    var c = D.consts, m = D.meta;
    var contact = m.contact
      ? '<a href="mailto:' + esc(m.contact) + '">' + esc(m.contact) + '</a>'
      : t('contactUnset');
    return '<div class="about"><h1>' + t('aboutTitle') + '</h1>' +
      '<h2>' + t('aboutWhatH') + '</h2><p>' + t('aboutWhat', { since: esc(m.since) }) + '</p>' +
      '<h2>' + t('aboutHowH') + '</h2><p>' + t('aboutHow1', { start: c.start }) + '</p>' +
      '<p>' + t('aboutHow2', { prov: c.prov, k1: c.k1, k2: c.k2 }) + '</p>' +
      '<p>' + t('aboutHow3') + '</p>' +
      '<h2>' + t('aboutRankH') + '</h2><p>' + t('aboutRank', { min: m.minGames }) + '</p>' +
      (D.meta.intl ? '<h2>' + t('aboutIntlH') + '</h2><p>' + t('aboutIntl', {
        site: '<a href="https://elorcana.com" target="_blank" rel="noopener noreferrer">elorcana.com</a>' }) + '</p>' : '') +
      '<h2>' + t('aboutPrivH') + '</h2><p>' + t('aboutPriv', { contact: contact, anon: t('anon') }) + '</p></div>';
  }

  function notFound() {
    return '<h1>' + t('notFoundTitle') + '</h1><p>' + t('notFound') +
      ' <a href="#/">' + t('backToRanking') + '</a>.</p>';
  }

  // ---------- router ----------
  var first = true;
  // keep = true quando so mudou o idioma: volta a desenhar sem saltar para o topo
  function route(keep) {
    keep = keep === true;
    var h = location.hash.replace(/^#\/?/, '');
    var parts = h.split('/');
    chartModel = null;
    var html, key = 'ranking', title = t('navRanking');
    if (parts[0] === 'player' && parts[1]) {
      var id = decodeURIComponent(parts.slice(1).join('/'));
      html = playerView(id);
      title = byId[id] ? byId[id].name : t('notFoundShort');
    } else if (parts[0] === 'events') {
      html = eventsView(); key = 'events'; title = t('navEvents');
    } else if (parts[0] === 'international') {
      html = intlView(); key = 'international'; title = t('navIntl');
    } else if (parts[0] === 'about') {
      html = aboutView(); key = 'about'; title = t('navAbout');
    } else {
      html = rankingView();
    }
    app.innerHTML = html;
    document.title = title + ' \u00b7 Lorcana Portugal Elo';
    [].slice.call(document.querySelectorAll('nav a')).forEach(function (a) {
      if (a.getAttribute('data-key') === key) a.setAttribute('aria-current', 'page');
      else a.removeAttribute('aria-current');
    });
    wireChart();
    wireSearch(wirePagers()['ranking-table']);
    if (!first && !keep) {
      window.scrollTo(0, 0);
      var h1 = app.querySelector('h1');
      if (h1) { h1.setAttribute('tabindex', '-1'); h1.focus({ preventScroll: true }); }
    }
    first = false;
  }
  [].slice.call(document.querySelectorAll('.lang-btn')).forEach(function (b) {
    b.addEventListener('click', function () { setLang(b.getAttribute('data-lang')); });
  });
  document.addEventListener('pointerdown', function (ev) {
    if (hideChartTip && !ev.target.closest('.chart-wrap')) hideChartTip();
  });
  window.addEventListener('hashchange', route);
  window.addEventListener('resize', markScrollableTables);
  applyStatic();
  route();
})();
