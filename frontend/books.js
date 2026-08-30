const API_URL = "http://localhost:5000";

async function loadBooks() {
    const grid = document.getElementById("booksGrid");
    const message = document.getElementById("message");

    grid.innerHTML = `
        <div class="loading-card">
            <div class="spinner"></div>
            <p>Loading library collection...</p>
        </div>
    `;

    message.textContent = "";

    try {
        const response = await fetch(`${API_URL}/api/books`);

        if (!response.ok) {
            throw new Error("Unable to load books");
        }

        const data = await response.json();

        displayBooks(data.books || []);

    } catch (error) {
        console.error(error);

        grid.innerHTML = "";
        message.textContent =
            "Unable to connect to the library API.";
        message.className = "error-message";
    }
}

async function applyFilters() {

    const search = document
        .getElementById("searchInput")
        .value
        .trim();

    const category =
        document.getElementById("categoryFilter").value;

    const language =
        document.getElementById("languageFilter").value;

    const params = new URLSearchParams();

    if (search) params.append("q", search);
    if (category) params.append("category", category);
    if (language) params.append("language", language);

    const grid = document.getElementById("booksGrid");

    grid.innerHTML = `
        <div class="loading-card">
            <div class="spinner"></div>
            <p>Searching books...</p>
        </div>
    `;

    try {

        const url = params.toString()
            ? `${API_URL}/api/books?${params.toString()}`
            : `${API_URL}/api/books`;

        const response = await fetch(url);

        if (!response.ok) {
            throw new Error("Search failed");
        }

        const data = await response.json();

        displayBooks(data.books || []);

    } catch (error) {

        console.error(error);

        grid.innerHTML =
            `<p class="error-message">Unable to search books.</p>`;
    }
}

function displayBooks(books) {

    const grid = document.getElementById("booksGrid");
    const count = document.getElementById("booksCount");

    grid.innerHTML = "";

    count.textContent =
        `${books.length} ${books.length === 1 ? "book" : "books"} found`;

    if (!books.length) {
        grid.innerHTML = `
            <div class="no-books">
                <div>📚</div>
                <h3>No books found</h3>
                <p>Try changing your search or filters.</p>
            </div>
        `;
        return;
    }

    books.forEach((book, index) => {

        const card = document.createElement("article");

        card.className = "book-card";

        const available = Number(book.available_quantity || 0);

        card.innerHTML = `
            <div class="book-cover-large cover-${index % 5}">
                <span>📖</span>
                <small>${escapeHtml(book.category || "BOOK")}</small>
            </div>

            <div class="book-card-body">

                <div class="book-tag">
                    ${available > 0 ? "● AVAILABLE" : "● UNAVAILABLE"}
                </div>

                <h2>${escapeHtml(book.title)}</h2>

                <p class="book-author">
                    by ${escapeHtml(book.author)}
                </p>

                <p class="book-description">
                    ${escapeHtml(
                        book.description ||
                        "Explore this book from the Smart Digital Library collection."
                    )}
                </p>

                <div class="book-meta">
                    <span>📚 ${escapeHtml(book.category || "General")}</span>
                    <span>🔖 ${escapeHtml(book.isbn || "N/A")}</span>
                </div>

                <div class="book-footer">
                    <span>
                        <strong>${book.quantity || 0}</strong> total
                    </span>

                    <span class="${
                        available > 0 ? "stock-ok" : "stock-no"
                    }">
                        ${available} available
                    </span>
                </div>

            </div>
        `;

        grid.appendChild(card);
    });
}

function clearFilters() {
    document.getElementById("searchInput").value = "";
    document.getElementById("categoryFilter").value = "";
    document.getElementById("languageFilter").value = "";
    loadBooks();
}

function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value ?? "";
    return div.innerHTML;
}

document
    .getElementById("searchInput")
    .addEventListener("keypress", function(event) {
        if (event.key === "Enter") {
            applyFilters();
        }
    });

loadBooks();
