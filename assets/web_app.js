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
      navMain: 'Main', navRanking: 'Ranking', navIntl: 'International', navAwards: 'Player of the week', navEvents: 'Events',
      navTopCut: 'Top Cut Calculator', navAbout: 'About',
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
      // achievements
      achH: 'Achievements', achSummary: '{n} of {total} unlocked', achNone: 'No achievements unlocked yet.',
      achEarned: 'Earned {date}', achLevelOf: 'Level {l} of {n}', achNext: 'Next: {desc}',
      achLockedH: 'Locked ({n})', achPct: '{pct}% of players',
      rar_common: 'Common', rar_uncommon: 'Uncommon', rar_rare: 'Rare', rar_epic: 'Epic', rar_legendary: 'Legendary',
      achCat_location: 'Stores', achCat_participation: 'Participation', achCat_streak: 'Streaks',
      achCat_rivalry: 'Rivalry', achCat_elo: 'Elo', achCat_events: 'Events', achCat_awards: 'Awards',
      achCat_loyalty: 'Loyalty',
      ach_stores_n: 'Explorer', ach_stores_d: 'Play at {n} different stores',
      ach_home_n: 'Home turf', ach_home_d: 'Play {n} matches at the same store',
      ach_cities_n: 'Road trip', ach_cities_d: 'Play in {n} different cities',
      ach_matches_n: 'Regular', ach_matches_d: 'Play {n} matches',
      ach_events_n: 'Circuit player', ach_events_d: 'Play {n} events',
      ach_wins_n: 'Winner', ach_wins_d: 'Win {n} matches',
      ach_streak_n: 'On a roll', ach_streak_d: 'Win {n} matches in a row',
      ach_opponents_n: 'Social butterfly', ach_opponents_d: 'Play against {n} different opponents',
      ach_rival_n: 'Rivalry', ach_rival_d: 'Play {n} matches against the same opponent',
      ach_heartbreaker_n: 'Heartbreaker', ach_heartbreaker_d: 'Beat the same opponent 3 times',
      ach_slayer_n: 'Nemesis slayer', ach_slayer_d: 'Beat an opponent who had beaten you 3 or more times',
      ach_peak_n: 'Peak Elo', ach_peak_d: 'Reach {n} Elo',
      ach_climb_n: 'Climber', ach_climb_d: 'Gain {n} Elo in one season (with 15+ matches in it)',
      ach_goliath_n: 'David vs Goliath', ach_goliath_d: 'Beat an opponent rated {n}+ Elo above you',
      ach_undefeated_n: 'Flawless', ach_undefeated_d: 'Events finished without losing a match (3+ matches each): {n}',
      ach_debut_n: 'Flawless debut', ach_debut_d: 'Finish your first event without losing a match (3+ matches)',
      ach_bigroom_n: 'Big room', ach_bigroom_d: 'Play an event with 32 or more players',
      ach_comeback_n: 'Comeback kid', ach_comeback_d: 'Win a match after losing 3 in a row',
      ach_rubber_n: 'Rubber match', ach_rubber_d: 'Win a match in the final round of an event (3+ rounds)',
      ach_potw_n: 'Player of the week', ach_potw_d: 'Player of the week: {n}×',
      ach_improved_n: 'Most improved', ach_improved_d: 'Win the Most improved prize of a season',
      ach_podium_n: 'On the podium', ach_podium_d: 'Finish in the top 3 of Most improved in a season',
      ach_founder_n: 'Founding member', ach_founder_d: 'Play in the first season',
      ach_seasons_n: 'Season veteran', ach_seasons_d: 'Play in {n} different seasons',
      awardsTitle: 'Player of the week',
      awardsLead: 'Each week (Monday to Sunday) the title goes to the player who gained the most Elo, with at least {min} matches that week and a positive gain. Each season starts when a new set is released; when the next set comes out, the player who improved the most that season gets the Most improved prize.',
      awardsLast: 'Last week', awardsNow: 'This week so far',
      awardsTileSub: '{gain} Elo · {n} matches · {week}',
      awardsNone: 'No qualifying player', awardsEmpty: 'No player of the week yet.',
      awardsTopH: 'Most player-of-the-week titles',
      colTitles: 'Titles', colLatestTitle: 'Latest title (week of)',
      awardsSeasonsH: 'Most improved player of each season',
      awardsSeasonsNote: 'Improvement is the Elo gained over the season, from before the first match of the season to the last one. To qualify: at least {matches} matches and {events} events in the season. Players who start mid-season count from the starting Elo of {start}.',
      colSeason: 'Season', colMostImproved: 'Most improved', colGain: 'Gain', colFromTo: 'From → to',
      seasonDone: 'Prize awarded', seasonLive: 'In progress', seasonNoWinner: 'No qualifying player',
      awardsLogH: 'Weekly log', colWeek: 'Week', colEloAfterWeek: 'Elo after',
      alsoRunners: 'Also: {list}',
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
      aboutAwardsH: 'Awards',
      aboutAwards: 'The Player of the week page names the player who gained the most Elo each week and the player who improved the most in each season. Seasons follow the release of new sets.',
      aboutAchH: 'Achievements',
      aboutAch: 'Each player page lists the achievements the player has unlocked, such as playing at several stores or winning many matches in a row. Many come in levels. The rarity of each one (Common to Legendary) depends on the share of players who have it.',
      aboutIntlH: 'International Elo',
      aboutIntl: 'Where available, each player page also shows the international Elo from {site}, which rates players worldwide using official Play Hub events. It is a separate rating from the Portugal Elo on this site and is shown for reference only.',
      aboutPrivH: 'Privacy',
      aboutPriv: 'We only show the name that the Play Hub makes publicly available. If you\u2019d rather not appear, contact {contact} and your profile will stop being shown. Your matches still count toward your opponents\u2019 Elo, but your name is replaced with \u201c{anon}\u201d.',
      contactUnset: 'the site contact (to be set)',
      // 404
      notFoundTitle: 'Page not found', notFoundShort: 'Not found',
      notFound: 'This player doesn\u2019t exist or has been removed.', backToRanking: 'Back to ranking',
      // top cut calculator
      topcutTitle: 'Top Cut Calculator',
      topcutLead: 'Will you make the cut? Enter your event\u2019s size and your current record to see, for every possible result in your remaining rounds, the chance it\u2019s enough to make the cut.',
      topcutFieldPlayers: 'Total players', topcutFieldRounds: 'Total Swiss rounds', topcutFieldCut: 'Cut size (top \u2026)',
      topcutFieldRecord: 'Your current record',
      topcutFieldWins: 'Wins', topcutFieldLosses: 'Losses', topcutFieldDraws: 'Draws',
      topcutCalculateBtn: 'Calculate',
      topcutCalculating: 'Calculating\u2026',
      topcutResultsH: 'Results',
      topcutColPoints: 'Points',
      topcutColChance: 'Chance to make top {n}',
      topcutBadInputs: 'Check the fields: total players, rounds and cut size must be positive, and your wins + losses + draws can\u2019t be more than the total rounds.',
      topcutExplain: 'How this is computed: your remaining rounds are turned into every possible final record, and each one\u2019s final points are fixed. What isn\u2019t fixed is the rest of the field, so for every hypothetical this simulates everyone else\u2019s entire tournament (all rounds, at 50% win / 45% loss / 5% draw per round, a generic-opponent assumption) to see how often your total is enough. Ties for the last spot(s) are broken randomly each run, standing in for real tiebreakers (OMW%/GW%/OGW%) that can\u2019t be predicted in advance. It doesn\u2019t know the field\u2019s actual current standings \u2014 only your own record \u2014 so treat this as a general odds estimate, not a live calculation tied to your specific opponents.'
    },
    pt: {
      navMain: 'Principal', navRanking: 'Ranking', navIntl: 'Internacional', navAwards: 'Jogador da semana', navEvents: 'Eventos',
      navTopCut: 'Calculadora Top Cut', navAbout: 'Sobre',
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
      // conquistas
      achH: 'Conquistas', achSummary: '{n} de {total} desbloqueadas', achNone: 'Ainda não há conquistas desbloqueadas.',
      achEarned: 'Conseguida em {date}', achLevelOf: 'Nível {l} de {n}', achNext: 'Seguinte: {desc}',
      achLockedH: 'Por desbloquear ({n})', achPct: '{pct}% dos jogadores',
      rar_common: 'Comum', rar_uncommon: 'Incomum', rar_rare: 'Raro', rar_epic: 'Épico', rar_legendary: 'Lendário',
      achCat_location: 'Lojas', achCat_participation: 'Participação', achCat_streak: 'Sequências',
      achCat_rivalry: 'Rivalidade', achCat_elo: 'Elo', achCat_events: 'Eventos', achCat_awards: 'Prémios',
      achCat_loyalty: 'Fidelidade',
      ach_stores_n: 'Explorador', ach_stores_d: 'Joga em {n} lojas diferentes',
      ach_home_n: 'Em casa', ach_home_d: 'Joga {n} partidas na mesma loja',
      ach_cities_n: 'Em viagem', ach_cities_d: 'Joga em {n} cidades diferentes',
      ach_matches_n: 'Habitual', ach_matches_d: 'Joga {n} partidas',
      ach_events_n: 'Circuito', ach_events_d: 'Joga {n} eventos',
      ach_wins_n: 'Vencedor', ach_wins_d: 'Vence {n} partidas',
      ach_streak_n: 'Em série', ach_streak_d: 'Vence {n} partidas seguidas',
      ach_opponents_n: 'Sociável', ach_opponents_d: 'Joga contra {n} adversários diferentes',
      ach_rival_n: 'Rivalidade', ach_rival_d: 'Joga {n} partidas contra o mesmo adversário',
      ach_heartbreaker_n: 'Quebra-corações', ach_heartbreaker_d: 'Vence 3 vezes o mesmo adversário',
      ach_slayer_n: 'Vingança', ach_slayer_d: 'Vence um adversário que já te tinha vencido 3 ou mais vezes',
      ach_peak_n: 'Elo máximo', ach_peak_d: 'Chega aos {n} de Elo',
      ach_climb_n: 'Escalada', ach_climb_d: 'Ganha {n} de Elo numa época (com 15+ partidas nela)',
      ach_goliath_n: 'David contra Golias', ach_goliath_d: 'Vence um adversário com {n}+ de Elo acima do teu',
      ach_undefeated_n: 'Sem perder', ach_undefeated_d: 'Eventos terminados sem perder uma partida (3+ partidas cada): {n}',
      ach_debut_n: 'Estreia perfeita', ach_debut_d: 'Termina o teu primeiro evento sem perder uma partida (3+ partidas)',
      ach_bigroom_n: 'Sala cheia', ach_bigroom_d: 'Joga um evento com 32 ou mais jogadores',
      ach_comeback_n: 'Recuperação', ach_comeback_d: 'Vence uma partida depois de perderes 3 seguidas',
      ach_rubber_n: 'Decisão', ach_rubber_d: 'Vence uma partida na última ronda de um evento (3+ rondas)',
      ach_potw_n: 'Jogador da semana', ach_potw_d: 'Jogador da semana: {n}×',
      ach_improved_n: 'Mais evoluído', ach_improved_d: 'Ganha o prémio de Mais evoluído de uma época',
      ach_podium_n: 'No pódio', ach_podium_d: 'Fica no top 3 de Mais evoluído numa época',
      ach_founder_n: 'Membro fundador', ach_founder_d: 'Joga na primeira época',
      ach_seasons_n: 'Veterano', ach_seasons_d: 'Joga em {n} épocas diferentes',
      awardsTitle: 'Jogador da semana',
      awardsLead: 'Em cada semana (de segunda a domingo) o título vai para o jogador que mais Elo ganhou, com pelo menos {min} partidas nessa semana e um ganho positivo. Cada época começa quando sai um set novo; quando o set seguinte sai, o jogador que mais evoluiu nessa época recebe o prémio de Mais evoluído.',
      awardsLast: 'Semana passada', awardsNow: 'Esta semana até agora',
      awardsTileSub: '{gain} de Elo · {n} partidas · {week}',
      awardsNone: 'Nenhum jogador elegível', awardsEmpty: 'Ainda não há jogador da semana.',
      awardsTopH: 'Mais títulos de jogador da semana',
      colTitles: 'Títulos', colLatestTitle: 'Último título (semana de)',
      awardsSeasonsH: 'Jogador que mais evoluiu em cada época',
      awardsSeasonsNote: 'A evolução é o Elo ganho ao longo da época, desde antes da primeira partida da época até à última. Para concorrer: pelo menos {matches} partidas e {events} eventos na época. Quem começa a meio da época conta a partir do Elo inicial de {start}.',
      colSeason: 'Época', colMostImproved: 'Mais evoluído', colGain: 'Ganho', colFromTo: 'De → para',
      seasonDone: 'Prémio atribuído', seasonLive: 'Em curso', seasonNoWinner: 'Nenhum jogador elegível',
      awardsLogH: 'Histórico semanal', colWeek: 'Semana', colEloAfterWeek: 'Elo depois',
      alsoRunners: 'Também: {list}',
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
      aboutAwardsH: 'Prémios',
      aboutAwards: 'A página Jogador da semana mostra quem mais Elo ganhou em cada semana e quem mais evoluiu em cada época. As épocas seguem o lançamento de novos sets.',
      aboutAchH: 'Conquistas',
      aboutAch: 'A página de cada jogador mostra as conquistas que desbloqueou, como jogar em várias lojas ou vencer muitas partidas seguidas. Muitas têm níveis. A raridade de cada uma (de Comum a Lendário) depende da percentagem de jogadores que a tem.',
      aboutIntlH: 'Elo internacional',
      aboutIntl: 'Quando existe, a página de cada jogador mostra também o Elo internacional do {site}, que classifica jogadores de todo o mundo com eventos oficiais do Play Hub. É uma classificação à parte do Elo Portugal deste site e serve apenas de referência.',
      aboutPrivH: 'Privacidade',
      aboutPriv: 'S\u00f3 mostramos o nome que o Play Hub disponibiliza publicamente. Se preferires n\u00e3o aparecer, contacta {contact} e o teu perfil deixa de ser mostrado. As tuas partidas continuam a contar para o Elo dos teus advers\u00e1rios, mas o teu nome \u00e9 substitu\u00eddo por \u201c{anon}\u201d.',
      contactUnset: 'quem gere o site (contacto por definir)',
      notFoundTitle: 'P\u00e1gina n\u00e3o encontrada', notFoundShort: 'N\u00e3o encontrado',
      notFound: 'Este jogador n\u00e3o existe ou foi removido.', backToRanking: 'Voltar ao ranking',
      // calculadora top cut
      topcutTitle: 'Calculadora Top Cut',
      topcutLead: 'Vais passar ao corte? Indica o tamanho do teu evento e o teu registo atual para ver, para cada resultado poss\u00edvel nas rondas que faltam, a probabilidade de chegar para o corte.',
      topcutFieldPlayers: 'N\u00famero total de jogadores', topcutFieldRounds: 'Rondas su\u00ed\u00e7as no total', topcutFieldCut: 'Tamanho do corte (top \u2026)',
      topcutFieldRecord: 'O teu registo atual',
      topcutFieldWins: 'Vit\u00f3rias', topcutFieldLosses: 'Derrotas', topcutFieldDraws: 'Empates',
      topcutCalculateBtn: 'Calcular',
      topcutCalculating: 'A calcular\u2026',
      topcutResultsH: 'Resultados',
      topcutColPoints: 'Pontos',
      topcutColChance: 'Probabilidade de fazer top {n}',
      topcutBadInputs: 'Verifica os campos: o n\u00famero de jogadores, as rondas e o tamanho do corte t\u00eam de ser positivos, e vit\u00f3rias + derrotas + empates n\u00e3o pode passar do total de rondas.',
      topcutExplain: 'Como isto \u00e9 calculado: as rondas que te faltam d\u00e3o origem a todos os registos finais poss\u00edveis, e os pontos finais de cada um ficam fixos. O que n\u00e3o fica fixo \u00e9 o resto do campo, por isso cada hip\u00f3tese simula o torneio inteiro de todos os outros jogadores (todas as rondas, a 50% vit\u00f3ria / 45% derrota / 5% empate por ronda, uma hip\u00f3tese gen\u00e9rica de advers\u00e1rio) para ver com que frequ\u00eancia o teu total chega. Os empates no \u00faltimo lugar do corte s\u00e3o desfeitos ao acaso em cada simula\u00e7\u00e3o, como substituto dos crit\u00e9rios de desempate reais (OMW%/GW%/OGW%) que n\u00e3o d\u00e1 para prever de antem\u00e3o. N\u00e3o sabe a classifica\u00e7\u00e3o real e atual do campo \u2014 s\u00f3 o teu pr\u00f3prio registo \u2014 por isso trata isto como uma estimativa geral, n\u00e3o um c\u00e1lculo ao vivo ligado aos teus advers\u00e1rios espec\u00edficos.'
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
      achievementsSection(p) +
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

  // ---------- conquistas (na pagina do jogador) ----------
  var RARITY_RANK = { common: 0, uncommon: 1, rare: 2, epic: 3, legendary: 4 };
  function achPct(x) {
    var s = x < 10 ? x.toFixed(1) : String(Math.round(x));
    return lang === 'pt' ? s.replace('.', ',') : s;      // 1,5 em portugues, 1.5 em ingles
  }

  // e = [valor, nivel conseguido, data do ultimo nivel] ou undefined se nao tem nada
  function achCard(def, e, A) {
    var L = def.levels, value = e ? e[0] : 0, level = e ? e[1] : 0, date = e ? e[2] : null;
    var idx = Math.max(level, 1) - 1;                       // nivel mostrado: o mais alto, ou o primeiro se ainda bloqueada
    var rar = A.rarity[def.id][idx];
    var pct = A.total ? A.holders[def.id][idx] * 100 / A.total : 0;
    var have = level > 0, next = level < L.length ? L[level] : null;
    var pips = L.length > 1 ? '<span class="ach-pips" role="img" aria-label="' + esc(t('achLevelOf', { l: level, n: L.length })) + '">' +
      L.map(function (_, i) { return '<i' + (i < level ? ' class="on"' : '') + '></i>'; }).join('') + '</span>' : '';
    var progress = '';
    if (next !== null && value > 0) {
      var base = def.base || 0, frac = Math.max(0, Math.min(1, (value - base) / (next - base)));
      progress = '<div class="ach-bar" aria-hidden="true"><span style="width:' + Math.round(frac * 100) + '%"></span></div>' +
        '<span class="ach-meta">' + (have ? t('achNext', { desc: t('ach_' + def.id + '_d', { n: next }) }) + ' ' : '') +
        '(' + rnd(value) + ' / ' + next + ')</span>';
    } else if (next !== null && have) {
      progress = '<span class="ach-meta">' + t('achNext', { desc: t('ach_' + def.id + '_d', { n: next }) }) + '</span>';
    }
    return '<div class="ach ach-' + rar + (have ? '' : ' locked') + '">' +
      '<div class="ach-top"><span class="ach-name">' + t('ach_' + def.id + '_n') + '</span>' +
      '<span class="ach-rar">' + t('rar_' + rar) + '</span></div>' +
      '<span class="ach-cat">' + t('achCat_' + def.cat) + '</span>' +
      '<p class="ach-desc">' + t('ach_' + def.id + '_d', { n: L[idx] }) + '</p>' + pips + progress +
      '<span class="ach-meta">' + (have ? t('achEarned', { date: fmtDate(date) }) + ' · ' : '') +
      t('achPct', { pct: achPct(pct) }) + '</span></div>';
  }

  function achievementsSection(p) {
    var A = D.achievements;
    if (!A) return '';
    var mine = p.ach || {}, earned = [], locked = [];
    A.defs.forEach(function (def) {
      var e = mine[def.id];
      (e && e[1] > 0 ? earned : locked).push({ def: def, e: e });
    });
    // as mais raras primeiro; a igualdade decide-se pelo nivel mais alto
    earned.sort(function (a, b) {
      var ra = RARITY_RANK[A.rarity[a.def.id][a.e[1] - 1]], rb = RARITY_RANK[A.rarity[b.def.id][b.e[1] - 1]];
      return rb - ra || b.e[1] - a.e[1];
    });
    function grid(list) {
      return '<div class="ach-grid">' + list.map(function (x) { return achCard(x.def, x.e, A); }).join('') + '</div>';
    }
    return '<h2>' + t('achH') + '</h2><p class="note">' + t('achSummary', { n: earned.length, total: A.defs.length }) + '</p>' +
      (earned.length ? grid(earned) : '<p>' + t('achNone') + '</p>') +
      (locked.length ? '<details class="ach-locked"><summary>' + t('achLockedH', { n: locked.length }) + '</summary>' +
        grid(locked) + '</details>' : '');
  }

  // ---------- awards: jogador da semana e mais evoluido ----------
  // compact = "14/09 – 20/09/2026" (repete o ano so quando a semana muda de ano)
  function weekRange(w, compact) {
    if (compact && w.start.slice(0, 4) === w.end.slice(0, 4)) {
      return fmtDate(w.start).slice(0, 5) + ' – ' + fmtDate(w.end);
    }
    return fmtDate(w.start) + ' – ' + fmtDate(w.end);
  }
  function playerLink(id) {
    var p = byId[id];
    return p ? '<a href="' + link(id) + '">' + esc(p.name) + '</a>' : esc(t('anon'));
  }
  function plus(x) { return '+' + rnd(x); }

  function awardsView() {
    var A = D.awards || { weeks: [], top: [], seasons: [], rules: {} };
    var R = A.rules;
    var head = '<h1>' + t('awardsTitle') + '</h1><p class="lead">' + t('awardsLead', { min: R.weekMin }) + '</p>';
    if (!A.weeks.length && !A.seasons.length) return head + '<p>' + t('awardsEmpty') + '</p>';

    var done = A.weeks.filter(function (w) { return w.final; });
    var live = A.weeks.filter(function (w) { return !w.final; });
    function tile(label, w) {
      return statTile(label, w ? playerLink(w.p) : '–',
        w ? t('awardsTileSub', { gain: plus(w.gain), n: w.n, week: weekRange(w) }) : t('awardsNone'));
    }
    var tiles = '<div class="stat-grid">' + tile(t('awardsLast'), done[done.length - 1]) +
      tile(t('awardsNow'), live[live.length - 1]) + '</div>';

    var topRows = A.top.map(function (r, i) {
      return '<tr><td class="num">' + (i + 1) + '</td><td class="txt">' + playerLink(r.p) + '</td>' +
        '<td class="num elo">' + r.titles + '</td><td class="num wide">' + fmtDate(r.last) + '</td></tr>';
    });
    var top = topRows.length ? '<h2>' + t('awardsTopH') + '</h2>' + pagedTable('ranking',
      '<th class="num" scope="col">' + t('colRank') + '</th><th scope="col">' + t('colPlayer') + '</th>' +
      '<th class="num" scope="col">' + t('colTitles') + '</th><th class="num wide" scope="col">' + t('colLatestTitle') + '</th>',
      topRows, t('awardsTopH'), t('awardsTopH')) : '';

    var seasonRows = A.seasons.slice().reverse().map(function (s) {
      var win = s.top[0], span = fmtDate(s.start) + ' –' + (s.through ? ' ' + fmtDate(s.through) : '');
      var runners = s.top.slice(1).map(function (x, i) {
        return (i + 2) + '. ' + playerLink(x.p) + ' ' + plus(x.gain);
      }).join(' · ');
      var who = win ? '<strong>' + playerLink(win.p) + '</strong>' +
        (runners ? '<br><span class="delta">' + t('alsoRunners', { list: runners }) + '</span>' : '')
        : '<span class="delta">' + t('seasonNoWinner') + '</span>';
      var status = s.done ? (win ? '<span class="tag tag-w">' + t('seasonDone') + '</span>' : '')
        : '<span class="tag">' + t('seasonLive') + '</span>';
      return '<tr><td class="txt">' + esc(s.name) + '<br><span class="delta">' + span + '</span>' +
        (status ? '<br>' + status : '') + '</td>' +
        '<td class="txt">' + who + '</td>' +
        '<td class="num elo">' + (win ? plus(win.gain) : '–') + '</td>' +
        '<td class="num wide">' + (win ? rnd(win.from) + ' → ' + rnd(win.to) : '–') + '</td></tr>';
    });
    var seasons = seasonRows.length ? '<h2>' + t('awardsSeasonsH') + '</h2><p class="note">' +
      t('awardsSeasonsNote', { matches: R.seasonMinMatches, events: R.seasonMinEvents, start: D.consts.start }) + '</p>' +
      pagedTable('matches',
        '<th scope="col">' + t('colSeason') + '</th><th scope="col">' + t('colMostImproved') + '</th>' +
        '<th class="num" scope="col">' + t('colGain') + '</th><th class="num wide" scope="col">' + t('colFromTo') + '</th>',
        seasonRows, t('awardsSeasonsH'), t('awardsSeasonsH')) : '';

    var logRows = done.slice().reverse().map(function (w) {
      return '<tr><td>' + weekRange(w, true) + '</td><td class="txt">' + playerLink(w.p) + '</td>' +
        '<td class="num elo">' + plus(w.gain) + '</td><td class="num wide">' + w.n + '</td>' +
        '<td class="num wide">' + rnd(w.elo) + '</td></tr>';
    });
    var log = logRows.length ? '<h2>' + t('awardsLogH') + '</h2>' + pagedTable('matches',
      '<th scope="col">' + t('colWeek') + '</th><th scope="col">' + t('colPlayer') + '</th>' +
      '<th class="num" scope="col">' + t('colGain') + '</th><th class="num wide" scope="col">' + t('colMatches') + '</th>' +
      '<th class="num wide" scope="col">' + t('colEloAfterWeek') + '</th>', logRows, t('awardsLogH'), t('awardsLogH')) : '';

    return head + tiles + top + seasons + log;
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
      '<h2>' + t('aboutAwardsH') + '</h2><p>' + t('aboutAwards') + '</p>' +
      '<h2>' + t('aboutAchH') + '</h2><p>' + t('aboutAch') + '</p>' +
      (D.meta.intl ? '<h2>' + t('aboutIntlH') + '</h2><p>' + t('aboutIntl', {
        site: '<a href="https://elorcana.com" target="_blank" rel="noopener noreferrer">elorcana.com</a>' }) + '</p>' : '') +
      '<h2>' + t('aboutPrivH') + '</h2><p>' + t('aboutPriv', { contact: contact, anon: t('anon') }) + '</p></div>';
  }

  function notFound() {
    return '<h1>' + t('notFoundTitle') + '</h1><p>' + t('notFound') +
      ' <a href="#/">' + t('backToRanking') + '</a>.</p>';
  }

  // ---------- top cut calculator ----------
  // Enumerates every (win, loss, draw) split of the rounds you have left, from your
  // current record. The rest of the field's actual standings aren't known to this
  // page (Play Hub doesn't let this site fetch them), so for each hypothetical this
  // simulates every other player's whole tournament from a flat per-round win rate
  // to estimate how often your fixed total is good enough. This is a general odds
  // estimate, not a live calculation tied to real opponents.
  var tcState = { players: 30, rounds: 5, cut: 8, wins: 0, losses: 0, draws: 0 };

  function tcEnumerateFinalRecords(wins, losses, draws, remaining) {
    var out = [];
    for (var w = 0; w <= remaining; w++) {
      for (var d = 0; d <= remaining - w; d++) {
        var l = remaining - w - d;
        out.push({ wins: wins + w, losses: losses + l, draws: draws + d, points: 3 * (wins + w) + (draws + d) });
      }
    }
    out.sort(function (a, b) { return (b.wins - a.wins) || (a.losses - b.losses) || (b.draws - a.draws); });
    return out;
  }

  // small seeded PRNG so results are reproducible within a single calculation run
  function tcRng(seed) {
    return function () {
      seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
      var x = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      x = (x + Math.imul(x ^ (x >>> 7), 61 | x)) ^ x;
      return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
    };
  }

  function tcChanceToMakeCut(hypotheticalPoints, otherCount, totalRounds, cutSize, trials, winProb, drawProb, rng) {
    var made = 0;
    var finals = new Array(otherCount + 1);
    for (var tr = 0; tr < trials; tr++) {
      for (var p = 0; p < otherCount; p++) {
        var pts = 0;
        for (var r = 0; r < totalRounds; r++) {
          var x = rng();
          if (x < drawProb) pts += 1;
          else if (x < drawProb + (1 - drawProb) * winProb) pts += 3;
        }
        finals[p] = pts;
      }
      finals[otherCount] = hypotheticalPoints;
      var better = 0, tiedAbove = 0, tiedTotal = 0;
      for (var i = 0; i <= otherCount; i++) {
        if (i === otherCount) continue;
        if (finals[i] > hypotheticalPoints) better++;
        else if (finals[i] === hypotheticalPoints) tiedTotal++;
      }
      // rank if all ties above mine resolve worse-for-me first, i.e. worst case among tied
      // then randomize a placement among the tied group to stand in for real tiebreakers
      var myPlacementAmongTied = Math.floor(rng() * (tiedTotal + 1));
      var rank = better + myPlacementAmongTied + 1;
      if (rank <= cutSize) made++;
    }
    return made / trials;
  }

  function tcOpsBudgetTrials(otherCount, totalRounds) {
    var perTrial = Math.max(1, otherCount * totalRounds);
    return Math.max(2000, Math.min(20000, Math.round(6000000 / perTrial)));
  }

  function tcResultsTable(recs, cutSize) {
    var rows = recs.map(function (r) {
      return '<tr><td>' + r.wins + '–' + r.losses + '–' + r.draws + '</td>' +
        '<td class="num">' + r.points + '</td>' +
        '<td class="num elo">' + (r.chance * 100).toFixed(1) + '%</td></tr>';
    }).join('');
    return '<h2>' + t('topcutResultsH') + '</h2>' +
      '<div class="tablewrap"><table class="ranking"><thead><tr>' +
      '<th scope="col">' + t('wdl') + '</th><th class="num" scope="col">' + t('topcutColPoints') + '</th>' +
      '<th class="num" scope="col">' + t('topcutColChance', { n: cutSize }) + '</th></tr></thead><tbody>' + rows + '</tbody></table></div>';
  }

  function topCutView() {
    return '<h1>' + t('topcutTitle') + '</h1>' +
      '<p class="lead">' + t('topcutLead') + '</p>' +
      '<label class="field"><span>' + t('topcutFieldPlayers') + '</span>' +
        '<input type="number" id="tc-players" min="2" value="' + tcState.players + '"></label>' +
      '<label class="field"><span>' + t('topcutFieldRounds') + '</span>' +
        '<input type="number" id="tc-rounds" min="1" value="' + tcState.rounds + '"></label>' +
      '<label class="field"><span>' + t('topcutFieldCut') + '</span>' +
        '<input type="number" id="tc-cut" min="1" value="' + tcState.cut + '"></label>' +
      '<h2>' + t('topcutFieldRecord') + '</h2>' +
      '<div class="tc-inline-fields">' +
      '<label class="field tc-inline"><span>' + t('topcutFieldWins') + '</span>' +
        '<input type="number" id="tc-wins" min="0" value="' + tcState.wins + '"></label>' +
      '<label class="field tc-inline"><span>' + t('topcutFieldLosses') + '</span>' +
        '<input type="number" id="tc-losses" min="0" value="' + tcState.losses + '"></label>' +
      '<label class="field tc-inline"><span>' + t('topcutFieldDraws') + '</span>' +
        '<input type="number" id="tc-draws" min="0" value="' + tcState.draws + '"></label>' +
      '</div>' +
      '<div class="tc-row-actions"><button type="button" class="btn" id="tc-calculate">' + t('topcutCalculateBtn') + '</button></div>' +
      '<div id="tc-results" aria-live="polite"></div>' +
      '<p class="note">' + t('topcutExplain') + '</p>';
  }

  function wireTopCut() {
    var playersInput = document.getElementById('tc-players');
    if (!playersInput) return;
    var roundsInput = document.getElementById('tc-rounds');
    var cutInput = document.getElementById('tc-cut');
    var winsInput = document.getElementById('tc-wins');
    var lossesInput = document.getElementById('tc-losses');
    var drawsInput = document.getElementById('tc-draws');
    var results = document.getElementById('tc-results');

    [['players', playersInput], ['rounds', roundsInput], ['cut', cutInput],
     ['wins', winsInput], ['losses', lossesInput], ['draws', drawsInput]].forEach(function (pair) {
      pair[1].addEventListener('input', function () { tcState[pair[0]] = parseInt(pair[1].value, 10); });
    });

    document.getElementById('tc-calculate').addEventListener('click', function () {
      var players = parseInt(playersInput.value, 10), rounds = parseInt(roundsInput.value, 10),
        cut = parseInt(cutInput.value, 10), wins = parseInt(winsInput.value, 10),
        losses = parseInt(lossesInput.value, 10), draws = parseInt(drawsInput.value, 10);
      var played = wins + losses + draws;
      if (!(players >= 2) || !(rounds >= 1) || !(cut >= 1) || isNaN(wins) || isNaN(losses) || isNaN(draws) ||
          wins < 0 || losses < 0 || draws < 0 || played > rounds) {
        results.innerHTML = '<p class="empty">' + t('topcutBadInputs') + '</p>';
        return;
      }
      results.innerHTML = '<p class="note">' + t('topcutCalculating') + '</p>';
      setTimeout(function () {
        var remaining = rounds - played;
        var otherCount = players - 1;
        var trials = tcOpsBudgetTrials(otherCount, rounds);
        var rng = tcRng((Date.now() ^ (players * 2654435761)) & 0xffffffff);
        var recs = tcEnumerateFinalRecords(wins, losses, draws, remaining);
        recs.forEach(function (rec) {
          rec.chance = tcChanceToMakeCut(rec.points, otherCount, rounds, cut, trials, 0.5, 0.05, rng);
        });
        results.innerHTML = tcResultsTable(recs, cut);
        markScrollableTables();
      }, 20);
    });
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
    } else if (parts[0] === 'awards') {
      html = awardsView(); key = 'awards'; title = t('navAwards');
    } else if (parts[0] === 'topcut') {
      html = topCutView(); key = 'topcut'; title = t('navTopCut');
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
    wireTopCut();
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
