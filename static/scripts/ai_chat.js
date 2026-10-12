document.addEventListener("DOMContentLoaded", () => {
  const chatBtn = document.getElementById("aiChatBtn");
  const chatWindow = document.getElementById("aiChatWindow");
  const chatCloseBtn = document.getElementById("aiChatCloseBtn");
  const chatForm = document.getElementById("aiChatForm");
  const chatInput = document.getElementById("aiChatInput");
  const chatMessages = document.getElementById("aiChatMessages");

  if (!chatBtn || !chatWindow || !chatForm) return;

  const toggleChat = () => {
    chatWindow.classList.toggle("hidden");
    if (!chatWindow.classList.contains("hidden")) {
      setTimeout(() => chatInput.focus(), 150);
    }
  };

  chatBtn.addEventListener("click", toggleChat);
  chatCloseBtn.addEventListener("click", toggleChat);

  const appendMessage = (sender, text) => {
    const msgDiv = document.createElement("div");
    msgDiv.className = `ai-msg ai-msg-${sender}`;

    // Clean up rogue prompt leaks or trailing asterisks
    let cleanText = text
      .replace(/\*+\s*Concise\?\s*Yes\..*?\*\s*/gi, '')
      .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
      .trim();

    if (window.marked && typeof window.marked.parse === 'function') {
      try {
        msgDiv.innerHTML = window.marked.parse(cleanText, { breaks: true, gfm: true });
      } catch (e) {
        msgDiv.innerHTML = fallbackFormat(cleanText);
      }
    } else {
      msgDiv.innerHTML = fallbackFormat(cleanText);
    }

    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return msgDiv;
  };

  const fallbackFormat = (str) => {
    return str
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.*?)\*/g, "<em>$1</em>")
      .replace(/^[\*\-]\s+(.*)$/gm, "• $1")
      .replace(/`([^`]+)`/g, "<code class='px-1 bg-dark text-white rounded'>$1</code>")
      .replace(/\n/g, "<br>");
  };

  const showTypingIndicator = () => {
    const indicator = document.createElement("div");
    indicator.className = "ai-msg ai-msg-assistant ai-typing-indicator";
    indicator.id = "aiTypingIndicator";
    indicator.innerHTML = `
      <span class="ai-typing-dot"></span>
      <span class="ai-typing-dot"></span>
      <span class="ai-typing-dot"></span>
    `;
    chatMessages.appendChild(indicator);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return indicator;
  };

  const removeTypingIndicator = () => {
    const indicator = document.getElementById("aiTypingIndicator");
    if (indicator) indicator.remove();
  };

  chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = chatInput.value.trim();
    if (!query) return;

    appendMessage("user", query);
    chatInput.value = "";
    chatInput.disabled = true;

    showTypingIndicator();

    try {
      const response = await fetch("/api/ai/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: query }),
      });

      removeTypingIndicator();

      if (response.ok) {
        const data = await response.json();
        appendMessage("assistant", data.reply || "Sorry, I could not process that.");

        // If booking or release action succeeded, reload user dashboard/booking page to reflect updated status
        if (data.action === "booking_success" || data.action === "release_success") {
          setTimeout(() => {
            if (
              window.location.pathname.includes("/user/dashboard") ||
              window.location.pathname.includes("/user/book") ||
              window.location.pathname.includes("/user/summary")
            ) {
              window.location.reload();
            }
          }, 2000);
        }
      } else {
        appendMessage("assistant", "⚠️ Unable to contact AI assistant. Please check your session or network.");
      }
    } catch (err) {
      removeTypingIndicator();
      appendMessage("assistant", "⚠️ An error occurred while communicating with the assistant.");
    } finally {
      chatInput.disabled = false;
      chatInput.focus();
    }
  });
});
