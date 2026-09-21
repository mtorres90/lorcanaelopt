// Pesquisa e paginacao no ranking: filtra as linhas enquanto se escreve
// (ignora acentos e maiusculas) e mostra-as em paginas de PAGE_SIZE.
(function () {
  var input = document.getElementById('q');
  if (!input) return;
  var rows = [].slice.call(document.querySelectorAll('tbody tr[data-name]'));
  var empty = document.getElementById('empty');
  var pager = document.getElementById('pager');
  var PAGE_SIZE = 25;
  var page = 1;

  function fold(s) {
    return s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  }

  function apply() {
    var q = fold(input.value.trim());
    var matches = rows.filter(function (row) {
      return !q || row.getAttribute('data-name').indexOf(q) !== -1;
    });
    var totalPages = Math.max(1, Math.ceil(matches.length / PAGE_SIZE));
    if (page > totalPages) page = totalPages;
    var start = (page - 1) * PAGE_SIZE, end = start + PAGE_SIZE;
    rows.forEach(function (row) { row.hidden = true; });
    matches.forEach(function (row, i) { row.hidden = !(i >= start && i < end); });
    empty.hidden = matches.length !== 0;
    if (pager) {
      if (matches.length > PAGE_SIZE) {
        pager.innerHTML =
          '<button type="button" id="prevPage"' + (page <= 1 ? ' disabled' : '') + '>Previous</button>' +
          '<span class="pager-status">Page ' + page + ' of ' + totalPages + '</span>' +
          '<button type="button" id="nextPage"' + (page >= totalPages ? ' disabled' : '') + '>Next</button>';
        var prevBtn = document.getElementById('prevPage');
        var nextBtn = document.getElementById('nextPage');
        if (prevBtn) prevBtn.addEventListener('click', function () { page--; apply(); window.scrollTo(0, 0); });
        if (nextBtn) nextBtn.addEventListener('click', function () { page++; apply(); window.scrollTo(0, 0); });
      } else {
        pager.innerHTML = '';
      }
    }
  }

  input.addEventListener('input', function () { page = 1; apply(); });
  apply();
})();

// Sinaliza tabelas com scroll horizontal (nomes de eventos longos) para mostrar
// o desvanecido do lado direito em vez de parecerem simplesmente cortadas.
(function () {
  function mark() {
    [].slice.call(document.querySelectorAll('.tablewrap')).forEach(function (w) {
      if (w.scrollWidth > w.clientWidth + 1) w.classList.add('scrolls');
      else w.classList.remove('scrolls');
    });
  }
  mark();
  window.addEventListener('resize', mark);
})();
