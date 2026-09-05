const API_URL = "http://localhost:5000";
const aiToken = sessionStorage.getItem("library_token") ||
    localStorage.getItem("library_token") ||
    localStorage.getItem("token");

async function requireValidSession() {
    if (!aiToken) {
        window.location.replace("/");
        return false;
    }
    const response = await fetch(`${API_URL}/api/my-loans`, {
        headers: { Authorization: `Bearer ${aiToken}` }
    });
    if (response.status === 401 || response.status === 403) {
        localStorage.removeItem("library_token");
        sessionStorage.removeItem("library_token");
        localStorage.removeItem("token");
        window.location.replace("/");
        return false;
    }
    return response.ok;
}

const chatMessages = document.getElementById("chatMessages");
const chatInput = document.getElementById("chatInput");

async function sendMessage() {

    const question = chatInput.value.trim();

    if (!question) return;

    addMessage(question, "user");

    chatInput.value = "";

    addTyping();

    try {

        const response = await fetch(`${API_URL}/api/books`);

        if (!response.ok) {
            throw new Error("Books API failed");
        }

        const data = await response.json();

        removeTyping();

        const books = data.books || [];

        const answer = generateLibraryAnswer(question, books);

        addMessage(answer, "ai");

    } catch (error) {

        console.error(error);

        removeTyping();

        addMessage(
            "I couldn't connect to the library service right now. Please try again.",
            "ai"
        );
    }
}

function generateLibraryAnswer(question, books) {

    const q = question.toLowerCase();

    if (!books.length) {
        return "The library currently has no books available.";
    }

    let matches = books.filter(book =>
        `${book.title} ${book.author} ${book.category} ${book.isbn}`
            .toLowerCase()
            .includes(q)
    );

    if (
        q.includes("python") ||
        q.includes("programming")
    ) {
        matches = books.filter(book =>
            `${book.title} ${book.author} ${book.category} ${book.description}`
                .toLowerCase()
                .includes("python")
        );
    }

    if (
        q.includes("computer science") ||
        q.includes("computer")
    ) {
        matches = books.filter(book =>
            `${book.category} ${book.title} ${book.description}`
                .toLowerCase()
                .includes("computer science")
        );
    }

    if (
        q.includes("ai") ||
        q.includes("artificial intelligence")
    ) {
        matches = books.filter(book =>
            `${book.title} ${book.description} ${book.category}`
                .toLowerCase()
                .includes("artificial intelligence")
        );
    }

    if (
        q.includes("recommend") ||
        q.includes("suggest")
    ) {
        matches = books.filter(book =>
            Number(book.available_quantity || 0) > 0
        ).slice(0, 3);
    }

    if (!matches.length) {
        return `I found ${books.length} books in the library, but none matched "${question}". Try asking about Python, AI, Computer Science, authors or a specific book title.`;
    }

    const list = matches.slice(0, 5)
        .map(book =>
            `• ${book.title} — ${book.author} (${book.available_quantity || 0} available)`
        )
        .join("\n");

    return `I found these books for you:\n\n${list}`;
}

function askSuggestion(question) {
    chatInput.value = question;
    sendMessage();
}

function addMessage(text, type) {

    const message = document.createElement("div");

    message.className =
        `message ${type === "user" ? "user-message" : "ai-message"}`;

    const avatar = type === "user" ? "👤" : "🤖";
    const name = type === "user" ? "You" : "Library AI";

    const formatted = escapeHtml(text).replace(/\n/g, "<br>");

    message.innerHTML = `
        <div class="message-avatar">${avatar}</div>

        <div class="message-content">
            <strong>${name}</strong>
            <p>${formatted}</p>
        </div>
    `;

    chatMessages.appendChild(message);

    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addTyping() {

    const typing = document.createElement("div");

    typing.id = "typingIndicator";
    typing.className = "message ai-message";

    typing.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="typing">
            <span></span>
            <span></span>
            <span></span>
        </div>
    `;

    chatMessages.appendChild(typing);

    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeTyping() {

    const typing =
        document.getElementById("typingIndicator");

    if (typing) typing.remove();
}

function clearChat() {

    chatMessages.innerHTML = `
        <div class="message ai-message">
            <div class="message-avatar">🤖</div>
            <div class="message-content">
                <strong>Library AI</strong>
                <p>
                    New conversation started. How can I help you?
                </p>
            </div>
        </div>
    `;
}

function escapeHtml(value) {

    const div = document.createElement("div");

    div.textContent = value ?? "";

    return div.innerHTML;
}

chatInput.addEventListener("keypress", event => {

    if (event.key === "Enter") {
        sendMessage();
    }

});

requireValidSession();
