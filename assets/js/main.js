document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("global-search-reset-button")?.addEventListener("click", () => {
        const resultElement = document.getElementById("global-search-result")
        if(resultElement) {
            resultElement.innerHTML = "";
        }
    });
});
