const API_BASE = "http://127.0.0.1:8000";

document.addEventListener('DOMContentLoaded', () => {
    // Determine which page logic to run based on existing elements
    if (document.getElementById('videoUrl')) {
        initYoutubePage();
    } else if (document.getElementById('note-topic')) {
        initNotesPage();
    } else if (document.getElementById('messages')) {
        initBotPage();
    }
});


/* =========================================
   PAGE 1: YOUTUBE TRANSCRIPTION (index.html)
   ========================================= */
function initYoutubePage() {
    const askBtn = document.getElementById('askBtn');
    const videoUrlInput = document.getElementById('videoUrl');
    const questionInput = document.getElementById('question');
    const videoPreviewDiv = document.getElementById('video-preview'); // Select the new div
    const container = document.querySelector('.container');

    // 1. LISTEN FOR URL INPUT TO SHOW VIDEO
    videoUrlInput.addEventListener('input', () => {
        const url = videoUrlInput.value.trim();
        const videoId = extractVideoID(url);

        if (videoId) {
            // Embed the YouTube Iframe
            videoPreviewDiv.innerHTML = `
                <iframe 
                    width="100%" 
                    height="350" 
                    src="https://www.youtube.com/embed/${videoId}" 
                    title="YouTube video player" 
                    frameborder="0" 
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                    allowfullscreen>
                </iframe>`;
            videoPreviewDiv.style.display = "block";
        } else {
            // Hide if invalid URL
            videoPreviewDiv.style.display = "none";
            videoPreviewDiv.innerHTML = "";
        }
    });

    // Helper: Extract ID from various YouTube URL formats
    function extractVideoID(url) {
        const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*/;
        const match = url.match(regExp);
        return (match && match[2].length === 11) ? match[2] : null;
    }

    // 2. EXISTING "ASK AI" LOGIC
    // Create result display dynamically
    const resultDiv = document.createElement('div');
    resultDiv.style.marginTop = "20px";
    resultDiv.style.padding = "15px";
    resultDiv.style.background = "#f9f9f9";
    resultDiv.style.border = "1px solid #ddd";
    resultDiv.style.borderRadius = "8px";
    resultDiv.style.display = "none";
    container.appendChild(resultDiv);

    askBtn.addEventListener('click', async () => {
        const videoUrl = videoUrlInput.value.trim();
        const question = questionInput.value.trim();

        if (!videoUrl || !question) {
            alert("Please enter both a Video URL and a Question.");
            return;
        }

        askBtn.textContent = "Processing...";
        askBtn.disabled = true;
        resultDiv.style.display = "none";

        try {
            const response = await fetch(`${API_BASE}/main`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ video_url: videoUrl, question: question })
            });

            if (!response.ok) throw new Error("Backend Error");

            const data = await response.json();
            
            resultDiv.innerHTML = `<strong>Answer:</strong><br><br>${data.answer.replace(/\n/g, '<br>')}`;
            resultDiv.style.display = "block";
        } catch (error) {
            alert("Error: " + error.message);
        } finally {
            askBtn.textContent = "Ask AI";
            askBtn.disabled = false;
        }
    });
}

/* =========================================
   PAGE 2: NOTES (notes.html)
   ========================================= */
function initNotesPage() {
    const topicInput = document.getElementById('note-topic');
    const addBtn = document.getElementById('add-btn');
    const notesContainer = document.getElementById('notes-container');

    // Load saved notes on startup
    renderNotes();

    addBtn.addEventListener('click', async () => {
        const topic = topicInput.value.trim();
        if (!topic) {
            alert("Please enter a topic.");
            return;
        }

        addBtn.textContent = "Generating...";
        addBtn.disabled = true;

        try {
            const response = await fetch(`${API_BASE}/generate_notes_only`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ topic: topic })
            });

            const data = await response.json();

            const newNote = {
                id: Date.now(),
                topic: data.topic,
                content: data.notes
            };

            saveNote(newNote);
            topicInput.value = ''; // Clear input
            renderNotes();
            
        } catch (error) {
            alert("Failed to generate notes: " + error.message);
        } finally {
            addBtn.textContent = "Generate notes";
            addBtn.disabled = false;
        }
    });

    // Helper: Save to LocalStorage
    function saveNote(note) {
        const notes = JSON.parse(localStorage.getItem('userNotes') || '[]');
        notes.push(note);
        localStorage.setItem('userNotes', JSON.stringify(notes));
    }

    // Helper: Render Notes to Grid
    function renderNotes() {
        notesContainer.innerHTML = '';
        const notes = JSON.parse(localStorage.getItem('userNotes') || '[]');
        
        notes.forEach(note => {
            const card = document.createElement('div');
            card.className = 'note-card';
            card.innerHTML = `
                <h3>${note.topic}</h3>
                <p>${formatText(note.content)}</p>
                <button class="delete-btn" data-id="${note.id}">X</button>
            `;
            notesContainer.appendChild(card);
        });

        // Attach delete listeners
        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = Number(e.target.dataset.id);
                const updatedNotes = notes.filter(n => n.id !== id);
                localStorage.setItem('userNotes', JSON.stringify(updatedNotes));
                renderNotes();
            });
        });
    }

    // Helper: Convert newlines to HTML breaks for display
    function formatText(text) {
        return text.replace(/\n/g, '<br>');
    }
}

/* =========================================
   PAGE 3: EXAM BOT (bot.html)
   ========================================= */
function initBotPage() {
    const messagesDiv = document.getElementById('messages');
    const inputField = document.getElementById('input');
    const sendBtn = document.querySelector('.input-area button');

    // State for the exam session
    let state = {
        mode: 'TOPIC_SELECTION', // TOPIC_SELECTION, EXAM, FINISHED
        topic: '',
        questions: [],
        currentQIndex: 0,
        historyLog: [] // Stores conversation for final eval
    };

    // Event Listeners
    sendBtn.addEventListener('click', handleUserMessage);
    inputField.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleUserMessage();
    });

    async function handleUserMessage() {
        const text = inputField.value.trim();
        if (!text) return;

        appendMessage(text, 'user');
        inputField.value = '';

        if (state.mode === 'TOPIC_SELECTION') {
            await startSession(text);
        } else if (state.mode === 'EXAM') {
            await processAnswer(text);
        }
    }

    async function startSession(topic) {
        appendMessage(`Generating exam questions for "${topic}"... Please wait.`, 'bot');
        state.topic = topic;

        try {
            const response = await fetch(`${API_BASE}/startsession`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_topics: topic })
            });
            const data = await response.json();
            
            state.questions = data.questions;
            state.mode = 'EXAM';
            
            appendMessage(`I have prepared ${state.questions.length} questions. Let's begin!`, 'bot');
            askNextQuestion();

        } catch (e) {
            appendMessage("Error starting session. Please try again.", 'bot');
        }
    }

    function askNextQuestion() {
        if (state.currentQIndex < state.questions.length) {
            const q = state.questions[state.currentQIndex];
            appendMessage(`<strong>Question ${state.currentQIndex + 1}:</strong> ${q}`, 'bot');
            // Log for history
            state.historyLog.push(`Q: ${q}`);
        } else {
            finishExam();
        }
    }

    async function processAnswer(answer) {
        const currentQ = state.questions[state.currentQIndex];
        
        appendMessage("Evaluating answer...", 'bot');

        // Log answer
        state.historyLog.push(`A: ${answer}`);

        try {
            const response = await fetch(`${API_BASE}/submitanswer`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question_text: currentQ,
                    answer_text: answer,
                    topic: state.topic
                })
            });
            const data = await response.json();
            
            // Show short feedback
            appendMessage(`<strong>Feedback:</strong> ${formatFeedback(data.evaluation)}`, 'bot');
            
            // Log evaluation
            state.historyLog.push(`Eval: ${data.evaluation}`);

            // Move to next
            state.currentQIndex++;
            askNextQuestion();

        } catch (e) {
            appendMessage("Error evaluating answer.", 'bot');
        }
    }

    async function finishExam() {
        state.mode = 'FINISHED';
        appendMessage("Exam finished! Generating your final performance report and study notes...", 'bot');

        try {
            const fullConv = state.historyLog.join("\n");
            const response = await fetch(`${API_BASE}/finalevaluation`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    topics: state.topic,
                    full_conversation: fullConv
                })
            });
            const data = await response.json();

            appendMessage(`<h3>Final Report</h3>${data.total_evaluation.replace(/\n/g, '<br>')}`, 'bot');
            
            appendMessage(`<h3>Recommended Study Notes</h3>${data.notes.replace(/\n/g, '<br>')}`, 'bot');

            appendMessage("Refresh the page to start a new session.", 'bot');

        } catch (e) {
            appendMessage("Error generating final report.", 'bot');
        }
    }

    // UI Helper: Add message to chat
    function appendMessage(htmlContent, sender) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${sender}`;
        msgDiv.innerHTML = htmlContent;
        messagesDiv.appendChild(msgDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight; // Auto scroll to bottom
    }

    // Helper: Clean up backend Markdown/Text for chat display
    function formatFeedback(text) {
        // Simple formatting to make backend text look okay in HTML
        return text.replace(/\n/g, '<br>');
    }
}