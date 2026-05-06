document.addEventListener("DOMContentLoaded", () => {
  const button = document.getElementById("show-more-photos-button");
  const hiddenGrid = document.getElementById("hidden-photos-grid");

  if (!button || !hiddenGrid) {
    return;
  }

  button.addEventListener("click", () => {
    hiddenGrid.classList.add("is-visible");
    button.remove();
  });
});
