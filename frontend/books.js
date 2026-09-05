const API_URL = window.location.port === "5000" ? "" : "http://localhost:5000";
const token = () => sessionStorage.getItem("library_token") ||
    localStorage.getItem("library_token") ||
    localStorage.getItem("token");
let searchTimer;
let searchCatalog = [];

async function requireValidSession() {
    const currentToken = token();
    if (!currentToken) {
        window.location.replace("/");
        return false;
    }
    const response = await fetch(`${API_URL}/api/my-loans`, {
        headers: { Authorization: `Bearer ${currentToken}` }
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
        const response = await fetch(`${API_URL}/api/books`, {
            headers: { Authorization: `Bearer ${token()}` }
        });

        if (!response.ok) {
            throw new Error("Unable to load books");
        }

        const data = await response.json();

        searchCatalog = data.books || [];
        updateSearchSuggestions(searchCatalog);
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

        const response = await fetch(url, {
            headers: { Authorization: `Bearer ${token()}` }
        });

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
    updateSearchHint();

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
                <button class="btn btn-primary borrow-btn" ${available < 1 ? "disabled" : ""}
                    onclick="borrowBook(${book.id})">Borrow</button>

            </div>
        `;

        grid.appendChild(card);
    });
}

async function borrowBook(bookId) {
    if (!token()) {
        openLoginPrompt();
        return;
    }
    const value = prompt("Borrow for how many days? (2-10)", "7");
    if (value === null) return;
    const days = Number(value);
    if (!Number.isInteger(days) || days < 2 || days > 10) {
        showMessage("Choose a whole number of days between 2 and 10.", "error"); return;
    }

    try {
        const response = await fetch(`${API_URL}/api/borrow`, {
            method: "POST", headers: {"Content-Type": "application/json", Authorization: `Bearer ${token()}`},
            body: JSON.stringify({book_id: bookId, duration_days: days})
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || "Unable to borrow book");
        showMessage(`Borrowed successfully. Due ${data.due_date}.`, "success");
        await Promise.all([loadBooks(), loadLoans()]);
    } catch (error) { showMessage(error.message, "error"); }
}

async function loadLoans() {
    const list = document.getElementById("loansList");
    const panel = document.getElementById("myLoansPanel");
    if (!list || !panel) return;
    if (!token()) {
        panel.hidden = true;
        return;
    }
    panel.hidden = false;
    try {
        const response = await fetch(`${API_URL}/api/my-loans`, {headers: {Authorization: `Bearer ${token()}`}});
        if (!response.ok) return;
        const data = await response.json();
        document.getElementById("loansCount").textContent = ` (${data.active_count}/4 active)`;
        document.getElementById("loansQuota").textContent = `${data.active_count}/4`;
        list.innerHTML = data.loans.length ? data.loans.map(loan => `
            <div class="loan-row">
                <div class="loan-book-cell">
                    <span class="loan-book-icon">📖</span>
                    <div><strong>${escapeHtml(loan.title)}</strong>
                    <small>${escapeHtml(loan.author || "Library book")}</small></div>
                </div>
                <div class="loan-date-cell">
                    <small>Borrowed</small>
                    <strong>${loan.borrowed_at.slice(0, 10)}</strong>
                </div>
                <div class="loan-date-cell">
                    <small>Due date</small>
                    <strong>${loan.due_date}</strong>
                </div>
                <div class="loan-status-cell">
                    <span class="loan-status ${loan.remaining_days > 0 ? "on-time" : "overdue"}">
                        ${loan.remaining_days > 0 ? `${loan.remaining_days} days left` : `${loan.overdue_days} days overdue`}
                    </span>
                    <small>${loan.duration_days} day loan · Fine ₹${loan.fine_inr}</small>
                </div>
            <div class="fine-payment">
                    <strong>Fine payment</strong>
                    <img alt="UPI payment QR code"
                        src="https://api.qrserver.com/v1/create-qr-code/?size=140x140&data=${encodeURIComponent(`upi://pay?pa=mayurmagar702-2@okicici&pn=Smart%20Library&am=${loan.fine_inr}&cu=INR`)}">
                    <small>UPI: mayurmagar702-2@okicici · Amount: ₹${loan.fine_inr}</small>
                    <small>Offline option: pay cash at the library counter and enter the receipt number.</small>
                    <select id="paymentMethod-${loan.loan_id}">
                        <option value="UPI">UPI / QR payment</option>
                        <option value="CASH">Offline cash payment</option>
                    </select>
                    <input id="paymentRef-${loan.loan_id}" placeholder="UPI reference / UTR">
                    <button class="btn btn-secondary" ${loan.fine_inr < 1 ? "disabled" : ""}
                        onclick="submitFinePayment(${loan.loan_id}, ${loan.fine_inr})">Submit Payment</button>
                </div>
            </div>
            <button class="btn btn-secondary loan-return-btn" onclick="returnBook(${loan.loan_id})">Return</button></div>`).join("")
            : "<p class='muted'>You have no active borrowed books.</p>";
    } catch (error) { list.innerHTML = "<p class='error-message'>Unable to load borrowed books.</p>"; }
}

async function submitFinePayment(loanId, amount) {
    const paymentMethod = document.getElementById(`paymentMethod-${loanId}`).value;
    try {
        const response = await fetch(`${API_URL}/api/fine-payments`, {
            method: "POST",
            headers: {"Content-Type": "application/json", Authorization: `Bearer ${token()}`},
            body: JSON.stringify({loan_id: loanId, amount, payment_method: paymentMethod})
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || "Unable to submit payment");
        showMessage(`${data.message}. Fine cleared.`, "success");
        const payment = document.querySelector(`#paymentMethod-${loanId}`).closest(".fine-payment");
        payment.innerHTML = `<strong>Payment completed — fine cleared</strong>
            <button class="btn btn-primary" onclick="downloadReceipt(${data.receipt_id})">
                Download PDF receipt
            </button>`;
        const row = payment.closest(".loan-row");
        const fineText = row && row.querySelector(".loan-status-cell small");
        if (fineText) fineText.textContent = "Payment cleared · Fine ₹0";
    } catch (error) {
        showMessage(error.message, "error");
    }
}

async function downloadReceipt(paymentId) {
    try {
        const response = await fetch(`${API_URL}/api/fine-payments/${paymentId}/receipt`, {
            headers: { Authorization: `Bearer ${token()}` }
        });
        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.message || "Unable to download receipt");
        }
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `library-receipt-${paymentId}.pdf`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
    } catch (error) {
        showMessage(error.message, "error");
    }
}

function openLoginPrompt() {
    document.getElementById("loginPrompt").classList.add("open");
}

function closeLoginPrompt() {
    document.getElementById("loginPrompt").classList.remove("open");
}

function continueToLogin() {
    window.location.href = "login.html?next=books.html";
}

async function returnBook(loanId) {
    try {
        const response = await fetch(`${API_URL}/api/loans/${loanId}/return`, {
            method: "POST", headers: {Authorization: `Bearer ${token()}`}
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || "Unable to return book");
        showMessage(`Book returned. Fine: ₹${data.fine_inr || 0}.`, "success");
        await Promise.all([loadBooks(), loadLoans()]);
    } catch (error) { showMessage(error.message, "error"); }
}

function clearFilters() {
    document.getElementById("searchInput").value = "";
    document.getElementById("categoryFilter").value = "";
    document.getElementById("languageFilter").value = "";
    applyFilters();
}

function updateSearchSuggestions(books) {
    const suggestions = document.getElementById("bookSearchSuggestions");
    if (!suggestions) return;
    const values = new Set();
    books.forEach(book => {
        [book.title, book.author, book.category, book.isbn]
            .filter(Boolean)
            .forEach(value => values.add(String(value)));
    });
    suggestions.innerHTML = [...values]
        .sort((a, b) => a.localeCompare(b))
        .slice(0, 100)
        .map(value => `<option value="${escapeHtml(value)}"></option>`)
        .join("");
}

function updateSearchHint() {
    const hint = document.getElementById("searchHint");
    if (!hint) return;
    const query = document.getElementById("searchInput").value.trim();
    const category = document.getElementById("categoryFilter").value;
    const language = document.getElementById("languageFilter").value;
    const active = [query && `"${query}"`, category, language].filter(Boolean);
    hint.textContent = active.length
        ? `Smart search active: ${active.join(" · ")}`
        : "Smart search checks title, author, category, language and ISBN.";
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

document
    .getElementById("searchInput")
    .addEventListener("input", function() {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(applyFilters, 350);
    });

["categoryFilter", "languageFilter"].forEach(id => {
    document.getElementById(id).addEventListener("change", applyFilters);
});

requireValidSession().then(isValid => {
    if (isValid) {
        loadBooks();
        loadLoans();
    }
});
