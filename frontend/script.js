document.addEventListener("DOMContentLoaded", function () {

    /* ================= MOBILE MENU ================= */

    const mobileMenu = document.getElementById("mobileMenu");
    const navLinks = document.querySelector(".nav-links");

    if (mobileMenu) {
        mobileMenu.addEventListener("click", function () {

            if (navLinks.style.display === "flex") {
                navLinks.style.display = "none";
            } else {
                navLinks.style.display = "flex";
                navLinks.style.flexDirection = "column";
                navLinks.style.position = "absolute";
                navLinks.style.top = "78px";
                navLinks.style.left = "0";
                navLinks.style.width = "100%";
                navLinks.style.padding = "20px";
                navLinks.style.background = "#071126";
            }

        });
    }


    /* ================= NAV SEARCH ================= */

    const search = document.getElementById("navSearch");

    if (search) {

        search.addEventListener("keypress", function (event) {

            if (event.key === "Enter") {

                const query = search.value.trim();

                if (query !== "") {

                    window.location.href =
                        "#books";

                }

            }

        });

    }


    /* ================= AI INPUT ================= */

    const aiInput = document.getElementById("aiInput");

    if (aiInput) {

        aiInput.addEventListener("keypress", function (event) {

            if (event.key === "Enter") {
                sendMessage();
            }

        });

    }


    /* ================= SCROLL ANIMATION ================= */

    const observer = new IntersectionObserver(
        function (entries) {

            entries.forEach(function (entry) {

                if (entry.isIntersecting) {
                    entry.target.classList.add("show");
                }

            });

        },
        {
            threshold: 0.1
        }
    );


    document
        .querySelectorAll(".feature-card, .book-card")
        .forEach(function (element) {

            element.style.opacity = "0";
            element.style.transform = "translateY(20px)";
            element.style.transition = "0.6s ease";

            observer.observe(element);

        });

});


/* ================= AI ================= */

function openAI() {

    const aiSection = document.getElementById("ai");

    if (aiSection) {
        aiSection.scrollIntoView({
            behavior: "smooth"
        });
    }

}


function sendMessage() {

    const input = document.getElementById("aiInput");

    if (!input) {
        return;
    }

    const message = input.value.trim();

    if (message === "") {
        return;
    }

    const chatBody = document.querySelector(".chat-body");

    const userMessage = document.createElement("div");

    userMessage.className = "message user";

    userMessage.textContent = message;

    chatBody.appendChild(userMessage);

    input.value = "";

    setTimeout(function () {

        const botMessage = document.createElement("div");

        botMessage.className = "message bot";

        botMessage.innerHTML =
            "That's a great question! 🤖<br><br>" +
            "Our AI library assistant can help you " +
            "find books and learning resources.";

        chatBody.appendChild(botMessage);

        chatBody.scrollTop = chatBody.scrollHeight;

    }, 700);

}
