const REGION = 'us-east-1'; // AWS Region
const BOT_NAME = 'AV5JRISRPL'; // Lex Bot ID
const BOT_ALIAS = 'TSTALIASID'; // Lex Bot Alias Id
const IDENTITY_POOL_ID = 'us-east-1:d6ebaa41-c466-442e-9042-5d9b82d83a62'; // Cognito Identity Pool ID

AWS.config.region = REGION;
AWS.config.credentials = new AWS.CognitoIdentityCredentials({
  IdentityPoolId: IDENTITY_POOL_ID
});

//Create custom session id
let session_id = localStorage.getItem('session_id');
if (!session_id) {
  session_id = uuid.v4().replace(/-/g, '').slice(0, 8);
  localStorage.setItem('session_id', session_id);
}

const lexRuntime = new AWS.LexRuntimeV2();
const chatWindow = document.getElementById('chat-window');
const chatForm = document.getElementById('chat-form');
const userInput = document.getElementById('user-input');

const pdfUpload = document.getElementById('pdf-upload');
const uploadBtn = document.getElementById('upload-btn');

// Initial bot message
window.addEventListener('DOMContentLoaded', function() {
  appendMessage(
    'I am MediCure, your triage assistant. I am here to help you with your health concerns.',
    'bot'
  );
});

function appendMessage(text, sender) {
  const msgDiv = document.createElement('div');
  msgDiv.className = sender === 'user' ? 'user-msg' : 'bot-msg';
  msgDiv.textContent = text;
  chatWindow.appendChild(msgDiv);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

chatForm.addEventListener('submit', function(e) {
  e.preventDefault();
  const text = userInput.value.trim();
  if (!text) return;
  appendMessage(text, 'user');
  userInput.value = '';
  sendToLex(text);
});

uploadBtn.addEventListener('click', function() {
  pdfUpload.click();
});

// Lambda function URL
const LAMBDA_URL = 'https://sotod7dnz64klaympl2w3lfy3u0jyuxd.lambda-url.us-east-1.on.aws/';
// Upload PDF
pdfUpload.addEventListener('change', function() {
  const file = pdfUpload.files[0];
  if (file && file.type === 'application/pdf') {
    const reader = new FileReader();
    reader.onload = function(e) {
      fetch(LAMBDA_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/pdf',
          'file-name': file.name,
          'session-id': session_id
        },
        body: e.target.result
      })
      .then(res => res.text())
      .then(msg => appendMessage(msg, 'bot'))
      .catch(err => appendMessage('Upload failed: ' + err, 'bot'));
    };
    reader.readAsArrayBuffer(file);
  } else {
    appendMessage('Please select a valid PDF file.', 'bot');
  }
  pdfUpload.value = '';
});

//Lex configuration
function sendToLex(text) {
  const params = {
    botId: BOT_NAME,
    botAliasId: BOT_ALIAS,
    localeId: 'en_US',
    sessionId: session_id,
    text: text,
    sessionState: {
      sessionAttributes: {
        session_id: session_id 
      }
    }
  };
  lexRuntime.recognizeText(params, function(err, data) {
    if (err) {
      appendMessage('Error: ' + err.message, 'bot');
    } else {
      const messages = data.messages || [];
      messages.forEach(msg => appendMessage(msg.content, 'bot'));
    }
  });
}
