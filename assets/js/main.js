document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("global-search-reset-button")?.addEventListener("click", () => {
        const resultElement = document.getElementById("global-search-result")
        if(resultElement) {
            resultElement.innerHTML = "";
        }
    });
});

function replaceQuestions(question) {
    const queryElem = document.querySelector("input[name=query]")
    if(!!queryElem) {
        queryElem.value = question.replace(/\-\s/, "");
    }
    return false;
}