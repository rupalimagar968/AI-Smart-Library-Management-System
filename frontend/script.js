const API_URL = "http://localhost:5000";
const authToken = sessionStorage.getItem("library_token") ||
    localStorage.getItem("library_token") ||
    localStorage.getItem("token");

function clearSession() {
    ["library_token", "token", "library_name", "library_username",
        "library_email", "email", "is_admin", "username"].forEach(key => {
        localStorage.removeItem(key);
        sessionStorage.removeItem(key);
    });
}

async function requireValidSession() {
    if (!authToken) {
        window.location.replace("/");
        return false;
    }
    const response = await fetch(`${API_URL}/api/my-loans`, {
        headers: { Authorization: "Bearer " + authToken }
    });
    if (!response.ok) {
        clearSession();
        window.location.replace("/");
        return false;
    }
    return true;
}

const currentName = localStorage.getItem("library_name") ||
    sessionStorage.getItem("library_name") || "Library member";

document.querySelectorAll("[data-user-name]").forEach(element => {
    element.textContent = `Welcome, ${currentName}`;
});

async function loadLibraryStats() {
    const response = await fetch(`${API_URL}/api/books`, {
        headers: { Authorization: "Bearer " + authToken }
    });
    if (!response.ok) throw new Error("Unable to load books");
    const data = await response.json();
    const count = data.count ?? (data.books || []).length;
    document.getElementById("totalBooks").textContent = count;
    document.getElementById("heroBooks").textContent = count;
}

async function loadAccountLoans() {
    const list = document.getElementById("accountLoans");
    const summary = document.getElementById("accountSummary");
    const response = await fetch(`${API_URL}/api/my-loans`, {
        headers: { Authorization: "Bearer " + authToken }
    });
    if (!response.ok) throw new Error("Unable to load account");
    const data = await response.json();
    summary.textContent = `${data.active_count} of ${data.quota} borrowing slots in use`;
    list.innerHTML = data.loans.length
        ? `<div class="account-loan-head">
            <span>BOOK</span><span>BORROWED</span><span>DUE DATE</span>
            <span>LOAN PERIOD</span><span>STATUS</span><span>FINE</span>
          </div>${data.loans.map(loan => `
            <div class="account-loan-entry" data-loan-id="${loan.loan_id}">
              <div class="account-loan-row">
                <div class="account-book"><span class="account-book-icon">📖</span>
                  <strong>${escapeHtml(loan.title)}</strong></div>
                <span>${loan.borrowed_at.slice(0, 10)}</span>
                <span>${loan.due_date}</span>
                <span>${loan.duration_days} days</span>
                <span class="account-loan-status ${loan.remaining_days > 0 ? "on-time" : "overdue"}">
                  ${loan.remaining_days > 0 ? loan.remaining_days + " days left" : loan.overdue_days + " days overdue"}
                </span>
                <strong class="account-fine-value ${loan.fine_inr > 0 ? "fine-due" : "fine-clear"}">₹${loan.fine_inr}</strong>
              </div>
              <div class="account-payment-actions">
                <button class="btn btn-secondary" ${loan.fine_inr < 1 ? "disabled" : ""}
                    onclick="toggleAccountPayment(${loan.loan_id}, ${loan.fine_inr})">
                    ${loan.fine_inr > 0 ? "💳 Pay Fine" : "No Fine Due"}
                </button>
              </div>
              <div id="accountPayment-${loan.loan_id}" class="account-payment-panel" hidden></div>
            </div>`).join("")}`
        : "<p class='muted'>You have no active borrowed books.</p>";
}

function toggleAccountPayment(loanId, amount) {
    const panel = document.getElementById(`accountPayment-${loanId}`);
    panel.hidden = !panel.hidden;
    if (!panel.hidden) {
        panel.innerHTML = `<strong>Choose payment mode for ₹${amount}</strong>
            <div class="account-payment-choice">
              <button class="btn btn-primary" onclick="showAccountOnlinePayment(${loanId}, ${amount})">Online UPI / QR</button>
              <button class="btn btn-secondary" onclick="showAccountOfflinePayment(${loanId}, ${amount})">Offline Cash</button>
            </div>`;
    }
}

function showAccountOnlinePayment(loanId, amount) {
    const panel = document.getElementById(`accountPayment-${loanId}`);
    const upi = `upi://pay?pa=mayurmagar702-2@okicici&pn=Smart%20Library&am=${amount}&cu=INR`;
    panel.innerHTML = `<strong>Scan to pay ₹${amount} online</strong>
        <img class="account-payment-qr" alt="UPI payment QR code"
          src="https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${encodeURIComponent(upi)}">
        <small>UPI ID: mayurmagar702-2@okicici</small>
        <input id="accountPaymentRef-${loanId}" placeholder="Enter UPI reference / UTR">
        <button class="btn btn-primary" onclick="submitAccountPayment(${loanId}, ${amount}, 'UPI')">Submit Online Payment</button>`;
}

function showAccountOfflinePayment(loanId, amount) {
    const panel = document.getElementById(`accountPayment-${loanId}`);
    panel.innerHTML = `<strong>Offline cash clearance — ₹${amount}</strong>
        <small>Pay at the library counter and enter the receipt number below.</small>
        <input id="accountPaymentRef-${loanId}" placeholder="Cash receipt number">
        <button class="btn btn-primary" onclick="submitAccountPayment(${loanId}, ${amount}, 'CASH')">Submit Cash Clearance</button>`;
}

async function submitAccountPayment(loanId, amount, paymentMethod) {
    const response = await fetch(`${API_URL}/api/fine-payments`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: "Bearer " + authToken
        },
        body: JSON.stringify({ loan_id: loanId, amount, payment_method: paymentMethod })
    });
    const data = await response.json();
    if (!response.ok) {
        alert(data.message || "Unable to submit payment");
        return;
    }
    const panel = document.getElementById(`accountPayment-${loanId}`);
    panel.innerHTML = `<strong>Payment completed — fine cleared</strong>
        <small>Payment mode: ${paymentMethod} · Amount: ₹${amount}</small>
        <button class="btn btn-primary" onclick="downloadReceipt(${data.receipt_id})">
            Download PDF receipt
        </button>`;
    const entry = document.querySelector(`[data-loan-id="${loanId}"]`);
    if (entry) {
        const fine = entry.querySelector(".account-fine-value");
        const button = entry.querySelector(".account-payment-actions button");
        if (fine) {
            fine.textContent = "₹0";
            fine.className = "account-fine-value fine-clear";
        }
        if (button) {
            button.textContent = "No Fine Due";
            button.disabled = true;
        }
    }
}

async function downloadReceipt(paymentId) {
    try {
        const response = await fetch(`${API_URL}/api/fine-payments/${paymentId}/receipt`, {
            headers: { Authorization: "Bearer " + authToken }
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
        alert(error.message);
    }
}

function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value ?? "";
    return div.innerHTML;
}

requireValidSession().then(async valid => {
    if (!valid) return;
    try {
        await Promise.all([loadLibraryStats(), loadAccountLoans()]);
    } catch (error) {
        document.getElementById("accountSummary").textContent = error.message;
        console.error("Dashboard loading error:", error);
    }
});
