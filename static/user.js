const HUMAN_RESPONSE_TIMEOUT = 60000; // change here to customize timeout
const chatBox = document.getElementById("chatBox");
const userInput = document.getElementById("userInput");
const sendButton = document.getElementById("sendButton");

const waitingObj = {
  isWaiting: false
};

let waitingProxy = new Proxy({ isWaiting: false }, {
  set(target, prop, isWaiting) {
    target[prop] = isWaiting;

    toggleUserActions(isWaiting);
    return true;
  }
});

let waitingTimeout;

const clientId = Date.now();
const ws = new WebSocket(`ws://localhost:8000/ws/${clientId}`);

const removeWaitingPlaceholder = () => {
  const typingMsg = document.getElementById("typingIndicator");
  if (typingMsg) typingMsg.remove();
}

const toggleUserActions = (enable) => {
  const sendButton = document.getElementById("sendButton");
  const userInput = document.getElementById("userInput");
  if (enable) {
    sendButton.classList.add('disabled');
    userInput.classList.add('disabled');
  } else {
    sendButton.classList.remove('disabled');
    userInput.classList.remove('disabled');
  }
}

const appendMessage = (text, className) => {
  const msg = document.createElement("div");
  if (className === "waiting-for-bot") {
    msg.setAttribute("id", "typingIndicator");
  }
  msg.classList.add("message", className);
  msg.textContent = text;
  chatBox.appendChild(msg);
  chatBox.scrollTop = chatBox.scrollHeight;
}

const handleSend = () => {
  const text = userInput.value.trim();
  if (!text) return;
  appendMessage(text, "user-message");
  appendMessage('', "waiting-for-bot");
  //ws.send(text);
  ws.send(JSON.stringify({clientId: clientId, response: text}));
  userInput.value = "";
  waitingProxy.isWaiting = true;
  waitingTimeout = setTimeout(() => {
    if (waitingProxy.isWaiting) {
      waitingProxy.isWaiting = false;
      clearTimeout(waitingTimeout);
      removeWaitingPlaceholder();
      appendMessage("Sorry, our employees are currently unavailable", "bot-message");
    }
  }, HUMAN_RESPONSE_TIMEOUT);
}

sendButton.addEventListener("click", handleSend);
userInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") handleSend();
});

ws.onmessage = event => {
  removeWaitingPlaceholder();
  waitingProxy.isWaiting = false;
  appendMessage(event.data, "bot-message");
};