// Client-side filtering for topic pages
(function () {
  var activeInstitution = "all";
  var activeDifficulty = "all";
  var activeSubtema = "all";
  var activeAnio = "all";
  var searchQuery = "";

  var instBtns = document.querySelectorAll("#institution-filters .filter-btn");
  var diffBtns = document.querySelectorAll("#difficulty-filters .filter-btn");
  var subBtns = document.querySelectorAll("#subtema-filters .filter-btn");
  var anioBtns = document.querySelectorAll("#anio-filters .filter-btn");
  var searchInput = document.getElementById("search-input");
  var cards = document.querySelectorAll(".exercise-card");
  var noResults = document.getElementById("no-results");

  function applyFilters() {
    var visible = 0;
    var q = searchQuery.toLowerCase();
    cards.forEach(function (card) {
      var matchInst = activeInstitution === "all" || card.dataset.institucion === activeInstitution;
      var matchDiff = activeDifficulty === "all" || card.dataset.dificultad === activeDifficulty;
      var matchSub = activeSubtema === "all" || (card.dataset.subtemas && card.dataset.subtemas.split(",").indexOf(activeSubtema) !== -1);
      var matchAnio = activeAnio === "all" || card.dataset.anio === activeAnio;
      var matchSearch = !q ||
        (card.dataset.id && card.dataset.id.toLowerCase().indexOf(q) !== -1) ||
        (card.dataset.fuente && card.dataset.fuente.toLowerCase().indexOf(q) !== -1) ||
        (card.dataset.subtemas && card.dataset.subtemas.toLowerCase().indexOf(q) !== -1) ||
        (card.dataset.etapa && card.dataset.etapa.toLowerCase().indexOf(q) !== -1) ||
        (card.dataset.anio && card.dataset.anio.indexOf(q) !== -1);
      if (matchInst && matchDiff && matchSub && matchAnio && matchSearch) {
        card.classList.remove("hidden");
        visible++;
      } else {
        card.classList.add("hidden");
      }
    });
    if (noResults) {
      noResults.classList.toggle("hidden", visible > 0);
    }
  }

  function bindGroup(buttons, setter) {
    buttons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        buttons.forEach(function (b) { b.classList.remove("active"); });
        btn.classList.add("active");
        setter(btn.dataset.value);
        applyFilters();
      });
    });
  }

  bindGroup(instBtns, function (v) { activeInstitution = v; });
  bindGroup(diffBtns, function (v) { activeDifficulty = v; });
  bindGroup(subBtns, function (v) { activeSubtema = v; });
  bindGroup(anioBtns, function (v) { activeAnio = v; });

  if (searchInput) {
    searchInput.addEventListener("input", function () {
      searchQuery = searchInput.value;
      applyFilters();
    });
  }
})();
