// Client-side filtering for topic pages
(function () {
  var activeInstitution = "all";
  var activeDifficulty = "all";
  var activeSubtema = "all";

  var instBtns = document.querySelectorAll("#institution-filters .filter-btn");
  var diffBtns = document.querySelectorAll("#difficulty-filters .filter-btn");
  var subBtns = document.querySelectorAll("#subtema-filters .filter-btn");
  var cards = document.querySelectorAll(".exercise-card");
  var noResults = document.getElementById("no-results");

  function applyFilters() {
    var visible = 0;
    cards.forEach(function (card) {
      var matchInst = activeInstitution === "all" || card.dataset.institucion === activeInstitution;
      var matchDiff = activeDifficulty === "all" || card.dataset.dificultad === activeDifficulty;
      var matchSub = activeSubtema === "all" || (card.dataset.subtemas && card.dataset.subtemas.split(",").indexOf(activeSubtema) !== -1);
      if (matchInst && matchDiff && matchSub) {
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
})();
