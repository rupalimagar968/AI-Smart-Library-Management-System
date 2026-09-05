(function () {
    const token = sessionStorage.getItem("library_token") ||
        localStorage.getItem("library_token") ||
        localStorage.getItem("token");

    document.querySelectorAll(".nav-login").forEach(link => {
        if (!token) return;
        link.textContent = "Logout";
        link.href = "#";
        link.addEventListener("click", event => {
            event.preventDefault();
            [
                "library_token", "token", "library_name", "library_username",
                "library_email", "email", "is_admin", "username"
            ].forEach(key => {
                localStorage.removeItem(key);
                sessionStorage.removeItem(key);
            });
            window.location.replace("/");
        });
    });
})();
