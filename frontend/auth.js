const API_URL = "";

function showMessage(message, type = "") {
    const element = document.getElementById("message");

    if (!element) return;

    element.textContent = message;
    element.className = `auth-message ${type}`;
}


function togglePassword(id, button) {
    const input = document.getElementById(id);

    if (!input) return;

    if (input.type === "password") {
        input.type = "text";
        button.textContent = "🙈";
    } else {
        input.type = "password";
        button.textContent = "👁";
    }
}


/* ================= LOGIN ================= */

const loginForm = document.getElementById("loginForm");

if (loginForm) {

    loginForm.addEventListener("submit", async function(event) {

        event.preventDefault();

        const username =
            document.getElementById("username").value.trim();

        const password =
            document.getElementById("password").value;

        if (!username || !password) {
            showMessage(
                "Name and password are required.",
                "error"
            );
            return;
        }

        showMessage("Signing you in...", "loading");

        try {

            const response = await fetch(
                `${API_URL}/api/login`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        username,
                        password
                    })
                }
            );

            const data = await response.json();

            if (!response.ok) {
                showMessage(
                    data.message || "Login failed.",
                    "error"
                );
                return;
            }

            localStorage.setItem("token", data.token);
            localStorage.setItem("username", data.username);
            localStorage.setItem("library_token", data.token);
            localStorage.setItem("library_name", data.name || data.username);
            localStorage.setItem("library_username", data.username);
            localStorage.setItem("is_admin", data.is_admin ? "true" : "false");

            if (data.email) {
                localStorage.setItem("email", data.email);
                localStorage.setItem("library_email", data.email);
            }

            showMessage(
                "Login successful! Redirecting...",
                "success"
            );

            setTimeout(() => {
                window.location.href = "index.html";
            }, 700);

        } catch (error) {

            console.error(error);

            showMessage(
                "Unable to connect to backend.",
                "error"
            );
        }

    });
}


/* ================= REGISTER ================= */

const registerForm =
    document.getElementById("registerForm");

if (registerForm) {

    registerForm.addEventListener(
        "submit",
        async function(event) {

            event.preventDefault();

            const username =
                document.getElementById("username")
                    .value.trim();

            const email =
                document.getElementById("email")
                    .value.trim();

            const password =
                document.getElementById("password")
                    .value;

            const confirmPassword =
                document.getElementById("confirmPassword")
                    .value;


            if (!username || !password || !confirmPassword) {

                showMessage(
                    "Name, password and confirmation are required.",
                    "error"
                );

                return;
            }


            if (username.length < 2) {

                showMessage(
                    "Name must be at least 2 characters.",
                    "error"
                );

                return;
            }


            if (password.length < 6) {

                showMessage(
                    "Password must be at least 6 characters.",
                    "error"
                );

                return;
            }


            if (password !== confirmPassword) {

                showMessage(
                    "Passwords do not match.",
                    "error"
                );

                return;
            }


            showMessage(
                "Creating your account...",
                "loading"
            );


            try {

                const response = await fetch(
                    `${API_URL}/api/register`,
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({
                            username,
                            email: email || null,
                            password
                        })
                    }
                );


                const data = await response.json();


                if (!response.ok) {

                    showMessage(
                        data.message || "Registration failed.",
                        "error"
                    );

                    return;
                }


                showMessage(
                    "Account created successfully! Redirecting to login...",
                    "success"
                );


                setTimeout(() => {
                    window.location.href = "login.html";
                }, 1000);


            } catch (error) {

                console.error(error);

                showMessage(
                    "Unable to connect to backend.",
                    "error"
                );
            }

        }
    );
}


/* ================= FORGOT PASSWORD ================= */

const forgotForm =
    document.getElementById("forgotForm");

if (forgotForm) {

    forgotForm.addEventListener(
        "submit",
        async function(event) {

            event.preventDefault();

            const username =
                document.getElementById("username")
                    .value.trim();

            const newPassword =
                document.getElementById("newPassword")
                    .value;

            const confirmPassword =
                document.getElementById("confirmPassword")
                    .value;


            if (!username || !newPassword || !confirmPassword) {

                showMessage(
                    "All required fields must be completed.",
                    "error"
                );

                return;
            }


            if (newPassword.length < 6) {

                showMessage(
                    "Password must be at least 6 characters.",
                    "error"
                );

                return;
            }


            if (newPassword !== confirmPassword) {

                showMessage(
                    "Passwords do not match.",
                    "error"
                );

                return;
            }


            showMessage(
                "Resetting password...",
                "loading"
            );


            try {

                const response = await fetch(
                    `${API_URL}/api/forgot-password`,
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({
                            username,
                            new_password: newPassword
                        })
                    }
                );


                const data = await response.json();


                if (!response.ok) {

                    showMessage(
                        data.message || "Password reset failed.",
                        "error"
                    );

                    return;
                }


                showMessage(
                    "Password reset successfully! Redirecting to login...",
                    "success"
                );


                setTimeout(() => {
                    window.location.href = "login.html";
                }, 1200);


            } catch (error) {

                console.error(error);

                showMessage(
                    "Unable to connect to backend.",
                    "error"
                );
            }

        }
    );
}
