const ADMIN_API = "";

const adminToken =
    localStorage.getItem("library_token") ||
    sessionStorage.getItem("library_token") ||
    localStorage.getItem("token");

const isAdmin =
    localStorage.getItem("is_admin") === "true" ||
    sessionStorage.getItem("is_admin") === "true";

if (!adminToken || !isAdmin) {
    window.location.replace("index.html");
}


function adminHeaders() {
    return {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${adminToken}`
    };
}


function showAdminMessage(message, type = "success") {

    const element = document.getElementById("adminMessage");

    element.textContent = message;
    element.className = `admin-message ${type}`;

    setTimeout(() => {
        element.textContent = "";
        element.className = "admin-message";
    }, 3500);
}


async function apiRequest(url, options = {}) {

    const response = await fetch(
        `${ADMIN_API}${url}`,
        {
            ...options,
            headers: {
                ...adminHeaders(),
                ...(options.headers || {})
            }
        }
    );

    const data = await response.json().catch(() => ({}));

    if (response.status === 401 || response.status === 403) {
        localStorage.removeItem("token");
        localStorage.removeItem("library_token");

        showAdminMessage(
            data.message || "Admin access denied",
            "error"
        );

        setTimeout(() => {
            window.location.href = "login.html";
        }, 1000);

        throw new Error(data.message || "Unauthorized");
    }

    if (!response.ok) {
        throw new Error(
            data.message || "Request failed"
        );
    }

    return data;
}


async function loadDashboard() {

    try {

        const data =
            await apiRequest("/api/admin/dashboard");

        const stats = data.stats;

        document.getElementById("statUsers")
            .textContent = stats.users;

        document.getElementById("statBooks")
            .textContent = stats.books;

        document.getElementById("statCopies")
            .textContent = stats.total_copies;

        document.getElementById("statAvailable")
            .textContent = stats.available_copies;


        renderRecentUsers(data.recent_users || []);
        renderRecentBooks(data.recent_books || []);
        renderActivities(data.activities || []);

    } catch (error) {

        console.error(error);

        showAdminMessage(
            error.message,
            "error"
        );
    }
}


function renderRecentUsers(users) {

    const container =
        document.getElementById("recentUsers");

    if (!users.length) {
        container.innerHTML =
            `<div class="empty-state">No users found.</div>`;
        return;
    }

    container.innerHTML = users.map(user => `

        <div class="admin-list-row">

            <div class="list-avatar">
                ${(user.name || user.username || "U")
                    .charAt(0)
                    .toUpperCase()}
            </div>

            <div class="list-main">

                <strong>
                    ${escapeHtml(user.name || user.username)}
                </strong>

                <small>
                    @${escapeHtml(user.username)}
                </small>

            </div>

            <span class="list-date">
                ${formatDate(user.created_at)}
            </span>

        </div>

    `).join("");
}


function renderRecentBooks(books) {

    const container =
        document.getElementById("recentBooks");

    if (!books.length) {
        container.innerHTML =
            `<div class="empty-state">No books found.</div>`;
        return;
    }

    container.innerHTML = books.map(book => `

        <div class="admin-list-row">

            <div class="book-list-icon">
                📖
            </div>

            <div class="list-main">

                <strong>
                    ${escapeHtml(book.title)}
                </strong>

                <small>
                    ${escapeHtml(book.author)}
                </small>

            </div>

            <span class="availability-badge">
                ${book.available_quantity}/${book.quantity}
            </span>

        </div>

    `).join("");
}


async function loadUsers() {

    const search =
        document.getElementById("userSearch")?.value || "";

    try {

        const data =
            await apiRequest(
                `/api/admin/users?q=${encodeURIComponent(search)}`
            );

        const table =
            document.getElementById("usersTable");

        if (!data.users.length) {

            table.innerHTML = `
                <tr>
                    <td colspan="5" class="table-empty">
                        No users found.
                    </td>
                </tr>
            `;

            return;
        }

        table.innerHTML = data.users.map(user => {

            const isAdmin =
                user.username.toLowerCase() === "admin";

            return `
                <tr>

                    <td>#${user.id}</td>

                    <td>
                        <div class="table-user">

                            <div class="table-avatar">
                                ${(user.name ||
                                  user.username ||
                                  "U")
                                  .charAt(0)
                                  .toUpperCase()}
                            </div>

                            <div>
                                <strong>
                                    ${escapeHtml(
                                        user.name ||
                                        user.username
                                    )}
                                </strong>

                                <small>
                                    @${escapeHtml(user.username)}
                                </small>
                            </div>

                        </div>
                    </td>

                    <td>
                        ${escapeHtml(user.email || "—")}
                    </td>

                    <td>
                        ${formatDate(user.created_at)}
                    </td>

                    <td>

                        ${
                            isAdmin

                            ? `<span class="protected-badge">
                                Protected
                               </span>`

                            : `<button
                                class="danger-btn"
                                onclick="deleteUser(${user.id}, '${escapeJs(user.username)}')">
                                Delete
                               </button>`
                        }

                    </td>

                </tr>
            `;

        }).join("");

    } catch (error) {

        console.error(error);

    }
}


async function deleteUser(id, username) {

    const confirmed =
        confirm(
            `Delete user "${username}"?\n\nThis action cannot be undone.`
        );

    if (!confirmed) return;

    try {

        const data =
            await apiRequest(
                `/api/admin/users/${id}`,
                {
                    method: "DELETE"
                }
            );

        showAdminMessage(data.message);

        await loadUsers();
        await loadDashboard();

    } catch (error) {

        showAdminMessage(
            error.message,
            "error"
        );
    }
}


async function loadAdminBooks() {

    const search =
        document.getElementById("bookSearch")?.value || "";

    try {

        const data =
            await apiRequest(
                `/api/admin/books?q=${encodeURIComponent(search)}`
            );

        const table =
            document.getElementById("booksTable");

        if (!data.books.length) {

            table.innerHTML = `
                <tr>
                    <td colspan="7" class="table-empty">
                        No books found.
                    </td>
                </tr>
            `;

            return;
        }

        table.innerHTML = data.books.map(book => `

            <tr>

                <td>#${book.id}</td>

                <td>
                    <div class="book-table-title">
                        <strong>
                            ${escapeHtml(book.title)}
                        </strong>

                        <small>
                            ${escapeHtml(book.isbn || "No ISBN")}
                        </small>
                    </div>
                </td>

                <td>
                    ${escapeHtml(book.author)}
                </td>

                <td>
                    <span class="category-badge">
                        ${escapeHtml(book.category || "General")}
                    </span>
                </td>

                <td>
                    ${book.quantity}
                </td>

                <td>
                    <span class="availability-badge">
                        ${book.available_quantity}
                    </span>
                </td>

                <td>

                    <div class="table-actions">

                        <button
                            class="edit-btn"
                            onclick='editBook(${JSON.stringify(book)})'>
                            Edit
                        </button>

                        <button
                            class="danger-btn"
                            onclick="deleteBook(${book.id}, '${escapeJs(book.title)}')">
                            Delete
                        </button>

                    </div>

                </td>

            </tr>

        `).join("");

    } catch (error) {

        console.error(error);

    }
}


function openBookModal(book = null) {

    const modal =
        document.getElementById("bookModal");

    document.getElementById("bookForm").reset();

    document.getElementById("bookId").value = "";

    document.getElementById("bookLanguage").value =
        "English";

    document.getElementById("bookQuantity").value =
        "1";

    if (book) {

        document.getElementById("bookModalTitle")
            .textContent = "Edit Book";

        document.getElementById("bookId").value =
            book.id;

        document.getElementById("bookTitle").value =
            book.title || "";

        document.getElementById("bookAuthor").value =
            book.author || "";

        document.getElementById("bookCategory").value =
            book.category || "";

        document.getElementById("bookLanguage").value =
            book.language || "English";

        document.getElementById("bookIsbn").value =
            book.isbn || "";

        document.getElementById("bookQuantity").value =
            book.quantity || 1;

        document.getElementById("bookDescription").value =
            book.description || "";

    } else {

        document.getElementById("bookModalTitle")
            .textContent = "Add New Book";
    }

    modal.classList.add("open");
}


function editBook(book) {
    openBookModal(book);
}


function closeBookModal() {

    document
        .getElementById("bookModal")
        .classList.remove("open");
}


document
    .getElementById("bookForm")
    .addEventListener("submit", async event => {

        event.preventDefault();

        const id =
            document.getElementById("bookId").value;

        const payload = {

            title:
                document.getElementById("bookTitle").value.trim(),

            author:
                document.getElementById("bookAuthor").value.trim(),

            category:
                document.getElementById("bookCategory").value.trim(),

            language:
                document.getElementById("bookLanguage").value.trim(),

            isbn:
                document.getElementById("bookIsbn").value.trim(),

            quantity:
                Number(
                    document.getElementById("bookQuantity").value
                ),

            description:
                document.getElementById("bookDescription").value.trim()
        };


        try {

            const data =
                await apiRequest(
                    id
                        ? `/api/admin/books/${id}`
                        : "/api/admin/books",
                    {
                        method: id ? "PUT" : "POST",
                        body: JSON.stringify(payload)
                    }
                );

            closeBookModal();

            showAdminMessage(data.message);

            await loadAdminBooks();
            await loadDashboard();

        } catch (error) {

            showAdminMessage(
                error.message,
                "error"
            );
        }

    });


async function deleteBook(id, title) {

    const confirmed =
        confirm(
            `Delete "${title}"?\n\nThis action cannot be undone.`
        );

    if (!confirmed) return;

    try {

        const data =
            await apiRequest(
                `/api/admin/books/${id}`,
                {
                    method: "DELETE"
                }
            );

        showAdminMessage(data.message);

        await loadAdminBooks();
        await loadDashboard();

    } catch (error) {

        showAdminMessage(
            error.message,
            "error"
        );
    }
}


function renderActivities(activities) {

    const container =
        document.getElementById("activityList");

    if (!activities.length) {

        container.innerHTML = `
            <div class="empty-state">
                No admin activity yet.
            </div>
        `;

        return;
    }

    container.innerHTML =
        activities.map(activity => `

            <div class="activity-row">

                <div class="activity-icon">
                    ${activity.action.includes("USER")
                        ? "👤"
                        : "📚"}
                </div>

                <div class="activity-content">

                    <strong>
                        ${formatActivity(activity.action)}
                    </strong>

                    <p>
                        ${escapeHtml(activity.details || "")}
                    </p>

                    <small>
                        ${escapeHtml(activity.admin_username)}
                        ·
                        ${formatDate(activity.created_at)}
                    </small>

                </div>

            </div>

        `).join("");
}


function formatActivity(action) {

    return action
        .replaceAll("_", " ")
        .toLowerCase()
        .replace(/\b\w/g, char => char.toUpperCase());
}


function showAdminSection(section, button) {

    document
        .querySelectorAll(".admin-section")
        .forEach(element =>
            element.classList.remove("active")
        );

    document
        .getElementById(`${section}Section`)
        .classList.add("active");


    document
        .querySelectorAll(".admin-nav-item")
        .forEach(element =>
            element.classList.remove("active")
        );

    if (button) {
        button.classList.add("active");
    }


    const titles = {

        dashboard: "Dashboard",
        users: "User Management",
        books: "Book Management",
        activity: "Admin Activity"

    };

    document.getElementById("adminPageTitle")
        .textContent = titles[section] || "Dashboard";


    if (section === "users") {
        loadUsers();
    }

    if (section === "books") {
        loadAdminBooks();
    }

    if (section === "activity") {
        loadDashboard();
    }

}


function showAdminSectionByName(section) {

    const button =
        [...document.querySelectorAll(".admin-nav-item")]
            .find(element =>
                element.textContent
                    .toLowerCase()
                    .includes(section)
            );

    showAdminSection(section, button);
}


function adminLogout() {

    const keys = [
        "token",
        "library_token",
        "username",
        "library_name",
        "library_username",
        "library_email",
        "email",
        "is_admin"
    ];

    keys.forEach(key => {
        localStorage.removeItem(key);
        sessionStorage.removeItem(key);
    });

    window.location.replace("login.html");
}


function formatDate(value) {

    if (!value) return "—";

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return value;
    }

    return date.toLocaleDateString(
        "en-IN",
        {
            day: "2-digit",
            month: "short",
            year: "numeric"
        }
    );
}


function escapeHtml(value) {

    const div =
        document.createElement("div");

    div.textContent =
        value ?? "";

    return div.innerHTML;
}


function escapeJs(value) {

    return String(value ?? "")
        .replaceAll("\\", "\\\\")
        .replaceAll("'", "\\'");
}


const adminUsername =
    localStorage.getItem("username") ||
    localStorage.getItem("library_name") ||
    "Administrator";

document.getElementById("adminName")
    .textContent = adminUsername;


loadDashboard();
