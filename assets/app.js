// Pesquisa no ranking: filtra as linhas enquanto se escreve (ignora acentos e maiusculas).
(function () {
  var input = document.getElementById('q');
  if (!input) return;
  var rows = [].slice.call(document.querySelectorAll('tbody tr[data-name]'));
  var empty = document.getElementById('empty');

  function fold(s) {
    return s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  }

  input.addEventListener('input', function () {
    var q = fold(input.value.trim());
    var shown = 0;
    rows.forEach(function (row) {
      var match = !q || row.getAttribute('data-name').indexOf(q) !== -1;
      row.hidden = !match;
      if (match) shown++;
    });
    empty.hidden = shown !== 0;
  });
})();
