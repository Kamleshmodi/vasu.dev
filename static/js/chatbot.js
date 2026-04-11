(function () {
    const DEFAULT_API_URL = "/api/chatbot-search/";
    const DEFAULT_PLACEHOLDER_IMAGE = "/static/image/logo/logo-transparent.png";
    let initialized = false;
    let requestInFlight = false;

    function getChatPanel() {
        return document.getElementById("chatPanel");
    }

    function getMessagesBox() {
        return document.getElementById("chatMessages");
    }

    function getChatInput() {
        return document.getElementById("chatInput");
    }

    function getApiUrl() {
        const panel = getChatPanel();
        return panel?.dataset.chatbotApiUrl || DEFAULT_API_URL;
    }

    function getPlaceholderImage() {
        const panel = getChatPanel();
        return panel?.dataset.chatbotPlaceholderImage || DEFAULT_PLACEHOLDER_IMAGE;
    }

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text || "";
        return div.innerHTML;
    }

    function formatMessageHtml(text) {
        return escapeHtml(text).replace(/\n/g, "<br>");
    }

    function appendMessage(sender, text, type = "text") {
        const box = getMessagesBox();
        if (!box) {
            return;
        }

        const msgDiv = document.createElement("div");
        msgDiv.classList.add("message", sender === "You" ? "user-message" : "bot-message");

        if (type === "loading") {
            msgDiv.innerHTML = '<span class="dot-typing"></span> Searching...';
            msgDiv.id = "botLoading";
        } else {
            msgDiv.innerHTML = formatMessageHtml(text);
        }

        box.appendChild(msgDiv);
        box.scrollTop = box.scrollHeight;
    }

    function appendProductCard(product) {
        const box = getMessagesBox();
        if (!box) {
            return;
        }

        const cardDiv = document.createElement("div");
        const imageSrc = product.image || getPlaceholderImage();
        const metaBits = [product.brand, product.category].filter(Boolean).join(" | ");
        const sizeLine = product.sizes ? `Sizes: ${escapeHtml(product.sizes)}` : "";

        cardDiv.classList.add("message", "bot-message", "product-card");
        cardDiv.innerHTML = `
            <div class="prod-layout" style="display:flex;gap:10px;align-items:center;">
                <img src="${escapeHtml(imageSrc)}" alt="${escapeHtml(product.name)}" style="width:60px;height:60px;object-fit:cover;border-radius:5px;">
                <div>
                    <strong style="font-size:14px;display:block;">${escapeHtml(product.name)}</strong>
                    <span style="color:#28a745;font-weight:bold;">${escapeHtml(product.price)}</span>
                    ${metaBits ? `<div style="font-size:11px;color:#666;">${escapeHtml(metaBits)}</div>` : ""}
                    ${sizeLine ? `<div style="font-size:11px;color:#666;">${sizeLine}</div>` : ""}
                </div>
            </div>
            <a href="${escapeHtml(product.link || "#")}" class="view-btn" style="display:block;text-align:center;margin-top:8px;background:#007bff;color:white;padding:5px;text-decoration:none;border-radius:4px;font-size:12px;">
                View Details
            </a>
        `;

        box.appendChild(cardDiv);
        box.scrollTop = box.scrollHeight;
    }

    async function sendMessage() {
        const input = getChatInput();
        if (!input || requestInFlight) {
            return;
        }

        const msg = input.value.trim();
        if (!msg) {
            return;
        }

        requestInFlight = true;
        appendMessage("You", msg);
        input.value = "";
        input.disabled = true;
        appendMessage("Bot", "", "loading");

        try {
            const response = await fetch(`${getApiUrl()}?query=${encodeURIComponent(msg)}`, {
                headers: { Accept: "application/json" },
            });

            let data = {};
            try {
                data = await response.json();
            } catch (error) {
                data = {};
            }

            const loadingMsg = document.getElementById("botLoading");
            if (loadingMsg) {
                loadingMsg.remove();
            }

            if (!response.ok) {
                throw new Error(data.error || "The chatbot service is unavailable right now.");
            }

            appendMessage("Bot", data.message || "I am here to help.");

            if (Array.isArray(data.products) && data.products.length > 0) {
                data.products.forEach((product) => appendProductCard(product));
            }
        } catch (error) {
            const loadingMsg = document.getElementById("botLoading");
            if (loadingMsg) {
                loadingMsg.remove();
            }

            console.error("Chatbot Error:", error);
            appendMessage("Bot", error.message || "Server error. Please try again later.");
        } finally {
            requestInFlight = false;
            input.disabled = false;
            input.focus();
        }
    }

    function toggleChat() {
        const panel = getChatPanel();
        if (!panel) {
            return;
        }

        panel.classList.toggle("open");
        if (panel.classList.contains("open")) {
            getChatInput()?.focus();
        }
    }

    function initChatbot() {
        if (initialized) {
            return;
        }

        const input = getChatInput();
        const panel = getChatPanel();
        if (!input || !panel) {
            return;
        }

        input.addEventListener("keydown", function (event) {
            if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
            }
        });

        initialized = true;
    }

    window.toggleChat = toggleChat;
    window.sendMessage = sendMessage;

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initChatbot);
    } else {
        initChatbot();
    }
})();
