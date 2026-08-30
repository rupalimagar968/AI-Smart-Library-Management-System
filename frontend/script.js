const API_URL = "http://localhost:5000";

async function loadLibraryStats() {

    try {

        const response =
            await fetch(`${API_URL}/api/books`);

        if (!response.ok) return;

        const data = await response.json();

        const count = data.count ?? (data.books || []).length;

        const totalBooks =
            document.getElementById("totalBooks");

        const heroBooks =
            document.getElementById("heroBooks");

        if (totalBooks) totalBooks.textContent = count;
        if (heroBooks) heroBooks.textContent = count;

    } catch (error) {

        console.error("Library statistics error:", error);

    }
}

loadLibraryStats();
