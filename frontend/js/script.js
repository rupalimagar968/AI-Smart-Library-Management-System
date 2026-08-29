function exploreBooks() {
document
.getElementById("books")
.scrollIntoView({
behavior: "smooth"
});
}

function openLogin() {
document
.getElementById("loginModal")
.style.display = "flex";
}

function closeLogin() {
document
.getElementById("loginModal")
.style.display = "none";
}

function login() {

const email =
    document.getElementById("email").value;

if (!email) {
    alert("Please enter your email.");
    return;
}

alert("Frontend login demo. Backend authentication will be added later.");

closeLogin();

}

function openChatbot() {

document
    .getElementById("chatbot")
    .style.display = "block";

}

function closeChatbot() {

document
    .getElementById("chatbot")
    .style.display = "none";

}

function sendMessage() {

const input =
    document.getElementById("chatInput");

const message =
    input.value.trim();

if (!message) {
    return;
}

const chat =
    document.getElementById("chatMessages");


const userMessage =
    document.createElement("div");

userMessage.className =
    "user-message";

userMessage.textContent =
    message;

chat.appendChild(userMessage);


const botMessage =
    document.createElement("div");

botMessage.className =
    "bot-message";

botMessage.textContent =
    "AI service will be connected in Phase 3. 🤖";

chat.appendChild(botMessage);


input.value = "";

chat.scrollTop =
    chat.scrollHeight;

}
