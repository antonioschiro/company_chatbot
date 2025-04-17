const clientId = Date.now();
let ws = new WebSocket(`ws://localhost:8000/ws/${clientId}-backoffice`);
let selectedClientId;

const handleClick = (e) => {
    selectedClientId = e.value;
    updateMessageInput();
}

const sendMessage = () => {
    let input = document.getElementById("messageInput");
    ws.send(JSON.stringify({response: input.value, clientId: selectedClientId}));
    document.getElementById(`li-${selectedClientId}`).remove();
    input.value = "";
}

const updateMessageInput = () => {
    let input = document.getElementById("responseContainer");
    if (!selectedClientId) {
        input.classList.add('disabled');
    } else {
        input.classList.remove('disabled');
    }
}

const updateSendButton = () => {
    let input = document.getElementById("messageInput");
    let sendButton = document.getElementById("sendButton");
    if (!input.value) {
        sendButton.classList.add('disabled');
    } else {
        sendButton.classList.remove('disabled');
    }
}

updateMessageInput();
updateSendButton();
