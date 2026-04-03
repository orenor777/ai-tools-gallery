const toolGrid = document.querySelector("#tool-grid");
const featuredGrid = document.querySelector("#featured-grid");
const searchInput = document.querySelector("#search-input");
const categorySelect = document.querySelector("#category-select");
const resultsCount = document.querySelector("#results-count");
const cardTemplate = document.querySelector("#tool-card-template");

let allTools = [];

function formatMetric(label, value) {
  if (!value) return "";
  return `${label}: ${new Intl.NumberFormat().format(value)}`;
}

function createCard(tool) {
  const fragment = cardTemplate.content.cloneNode(true);
  fragment.querySelector(".tool-category").textContent = tool.category;
  fragment.querySelector(".tool-name").textContent = tool.name;
  fragment.querySelector(".tool-pricing").textContent = tool.pricing;
  fragment.querySelector(".tool-description").textContent = tool.tagline || tool.description;
  fragment.querySelector(".metric.saves").textContent = formatMetric("Saves", tool.saves) || "Dataset pick";
  fragment.querySelector(".metric.domain").textContent = tool.domain || "Unknown domain";
  const link = fragment.querySelector(".tool-link");
  link.href = tool.url;
  return fragment;
}

function renderFeatured(tools) {
  featuredGrid.replaceChildren();
  tools.slice(0, 6).forEach((tool) => {
    featuredGrid.appendChild(createCard(tool));
  });
}

function renderTools(tools) {
  toolGrid.replaceChildren();
  const visible = tools.slice(0, 120);
  visible.forEach((tool) => {
    toolGrid.appendChild(createCard(tool));
  });
  resultsCount.textContent = `${tools.length} matching tools`;
}

function currentFilters() {
  return {
    query: searchInput.value.trim().toLowerCase(),
    category: categorySelect.value,
  };
}

function applyFilters() {
  const { query, category } = currentFilters();
  const filtered = allTools.filter((tool) => {
    const matchesCategory = category === "all" || tool.category === category;
    if (!matchesCategory) return false;
    if (!query) return true;
    return [tool.name, tool.category, tool.domain, tool.description]
      .filter(Boolean)
      .some((field) => field.toLowerCase().includes(query));
  });
  renderTools(filtered);
}

function populateCategories(tools) {
  const categories = [...new Set(tools.map((tool) => tool.category).filter(Boolean))].sort();
  categories.forEach((category) => {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = category;
    categorySelect.appendChild(option);
  });
  document.querySelector("#stat-categories").textContent = categories.length.toString();
}

async function init() {
  const response = await fetch("./data/tools.json");
  const payload = await response.json();
  allTools = payload.tools || [];
  document.querySelector("#stat-count").textContent = String(allTools.length);
  populateCategories(allTools);
  renderFeatured(allTools.filter((tool) => tool.featured));
  renderTools(allTools);
}

searchInput.addEventListener("input", applyFilters);
categorySelect.addEventListener("change", applyFilters);

init().catch((error) => {
  console.error(error);
  resultsCount.textContent = "Failed to load tools";
});
