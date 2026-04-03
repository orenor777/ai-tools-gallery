const searchInput = document.querySelector("#search-input");
const categorySelect = document.querySelector("#category-select");
const resultsCount = document.querySelector("#results-count");
const cards = [...document.querySelectorAll("#tool-grid .tool-card")];

function applyFilters() {
  const query = searchInput.value.trim().toLowerCase();
  const category = categorySelect.value;
  let visibleCount = 0;

  cards.forEach((card) => {
    const matchesCategory = category === "all" || card.dataset.category === category;
    const matchesQuery = !query || (card.dataset.search || "").includes(query);
    const visible = matchesCategory && matchesQuery;
    card.hidden = !visible;
    if (visible) visibleCount += 1;
  });

  resultsCount.textContent = `${visibleCount} matching tools`;
}

searchInput.addEventListener("input", applyFilters);
categorySelect.addEventListener("change", applyFilters);
applyFilters();
