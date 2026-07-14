// API Base URL
const API_URL = '';

// Conversation History Memory
let conversationHistory = [];
let currentDocumentsList = [];

// DOM Elements
const uploadZone = document.getElementById('upload-zone');
const fileInput = document.getElementById('file-input');
const uploadProgress = document.getElementById('upload-progress');
const documentList = document.getElementById('document-list');
const docCountBadge = document.getElementById('doc-count');
const btnClear = document.getElementById('btn-clear');
const chatHistory = document.getElementById('chat-history');
const chatForm = document.getElementById('chat-form');
const userInput = document.getElementById('user-input');
const btnSend = document.getElementById('btn-send');
const systemStatus = document.getElementById('system-status');
const apiKeyBadge = document.getElementById('api-key-badge');

// Workspace Mode Switcher elements
const modeRag = document.getElementById('mode-rag');
const modeResearch = document.getElementById('mode-research');
const engineSelect = document.getElementById('engine-select');
const chatViewContainer = document.getElementById('chat-view-container');
const researchViewContainer = document.getElementById('research-view-container');
const panelTitleText = document.getElementById('panel-title-text');

// Research Assistant specific elements
const paperSelectDropdown = document.getElementById('paper-select-dropdown');
const insightDisplayCard = document.getElementById('insight-display-card');
const emptyInsights = document.getElementById('empty-insights');
const insightsScrollContent = document.getElementById('insights-scroll-content');
const insightTitle = document.getElementById('insight-title');
const insightProblem = document.getElementById('insight-problem');
const insightMethodology = document.getElementById('insight-methodology');
const insightResults = document.getElementById('insight-results');
const insightContributions = document.getElementById('insight-contributions');

const btnCompareAll = document.getElementById('btn-compare-all');
const comparisonDisplayCard = document.getElementById('comparison-display-card');
const emptyComparison = document.getElementById('empty-comparison');
const comparisonScrollContent = document.getElementById('comparison-scroll-content');
const synthesizedMarkdown = document.getElementById('synthesized-markdown');

// Pipeline Steps
const stepRoute = document.getElementById('step-route');
const stepRetrieve = document.getElementById('step-retrieve');
const stepRerank = document.getElementById('step-rerank');
const stepGenerate = document.getElementById('step-generate');

// Inspection Panel Elements
const intentBadge = document.getElementById('intent-badge');
const retrievalMetric = document.getElementById('retrieval-metric');
const routingReason = document.getElementById('routing-reason');
const routingCard = document.getElementById('routing-card');
const citationsContainer = document.getElementById('citations-container');
const inspectorContainer = document.getElementById('inspector-container');

// Initialize App
document.addEventListener('DOMContentLoaded', () => {
    fetchDocuments();
    setupUploadHandlers();
    setupResearchAssistantHandlers();
    
    // Form submission
    chatForm.addEventListener('submit', handleChatSubmit);
    
    // Clear Database button
    btnClear.addEventListener('click', handleClearDatabase);
});

// Setup File Upload Event Handlers
function setupUploadHandlers() {
    // Click upload zone to select file
    uploadZone.addEventListener('click', () => fileInput.click());
    
    // File input change
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            uploadFiles(fileInput.files);
        }
    });
    
    // Drag and Drop
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        }, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        uploadZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
        }, false);
    });
    
    uploadZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            uploadFiles(files);
        }
    }, false);
}

// Fetch Indexed Documents
async function fetchDocuments() {
    try {
        const response = await fetch(`${API_URL}/documents`);
        const documents = await response.json();
        renderDocumentList(documents);
    } catch (error) {
        console.error('Error fetching documents:', error);
    }
}

// Render Document List in Sidebar
function renderDocumentList(documents) {
    docCountBadge.textContent = documents.length;
    currentDocumentsList = documents;
    
    // Populate paper select dropdown for research workbench
    if (paperSelectDropdown) {
        const currentSelection = paperSelectDropdown.value;
        paperSelectDropdown.innerHTML = '<option value="">-- Choose an indexed paper --</option>';
        documents.forEach(docName => {
            const opt = document.createElement('option');
            opt.value = docName;
            opt.textContent = docName;
            paperSelectDropdown.appendChild(opt);
        });
        
        if (documents.includes(currentSelection)) {
            paperSelectDropdown.value = currentSelection;
        } else {
            resetInsightsDisplay();
        }
    }
    
    if (documents.length === 0) {
        documentList.innerHTML = `
            <div class="empty-docs-message">
                <i class="fa-solid fa-database"></i>
                <p>No documents uploaded yet</p>
            </div>
        `;
        return;
    }
    
    documentList.innerHTML = '';
    documents.forEach(docName => {
        const chip = document.createElement('div');
        chip.className = 'doc-chip';
        chip.innerHTML = `
            <div class="doc-chip-left">
                <i class="fa-regular fa-file-pdf"></i>
                <span class="doc-name" title="${docName}">${docName}</span>
            </div>
        `;
        documentList.appendChild(chip);
    });
}

// Upload Files to Backend
async function uploadFiles(files) {
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }
    
    // Update UI progress
    const progressBar = uploadZone.querySelector('.upload-progress-bar');
    progressBar.style.display = 'block';
    uploadProgress.style.width = '30%';
    systemStatus.innerHTML = '<span class="status-dot loading"></span> Uploading & Indexing...';
    
    try {
        uploadProgress.style.width = '60%';
        const response = await fetch(`${API_URL}/upload`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Upload failed');
        }
        
        uploadProgress.style.width = '100%';
        const result = await response.json();
        
        // Show success notification in status bar
        systemStatus.innerHTML = '<span class="status-dot online"></span> System Ready';
        
        // Refresh documents list
        fetchDocuments();
        
        // Append small system message to chat history
        appendMessage('assistant', `Successfully processed: ${files.length} document(s). Generated vector embeddings and parsed layout contents.`, true);
        
        setTimeout(() => {
            progressBar.style.display = 'none';
            uploadProgress.style.width = '0%';
        }, 1500);
        
    } catch (error) {
        console.error('Error uploading files:', error);
        systemStatus.innerHTML = '<span class="status-dot online"></span> Upload Error';
        appendMessage('assistant', `Failed to upload documents. Please check console logs.`, true);
        progressBar.style.display = 'none';
    }
}

// Clear Database
async function handleClearDatabase() {
    if (!confirm('Are you sure you want to clear all indexed documents from the vector database?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/clear`, { method: 'POST' });
        const result = await response.json();
        
        // Reset local variables
        conversationHistory = [];
        
        // Reset UI
        chatHistory.innerHTML = `
            <div class="message assistant-message welcome-message">
                <div class="message-avatar">
                    <i class="fa-solid fa-robot"></i>
                </div>
                <div class="message-content">
                    <h3>Corpus Cleared</h3>
                    <p>The vector database and uploaded files have been deleted. Please upload new PDFs to start querying again.</p>
                </div>
            </div>
        `;
        
        fetchDocuments();
        resetInspectionPanel();
        resetPipelineSteps();
        
        appendMessage('assistant', 'Database cleared successfully.', true);
    } catch (error) {
        console.error('Error clearing database:', error);
    }
}

// Reset pipeline visual indicator states
function resetPipelineSteps() {
    [stepRoute, stepRetrieve, stepRerank, stepGenerate].forEach(step => {
        step.className = 'pipeline-step';
    });
    const connectors = document.querySelectorAll('.pipeline-connector');
    connectors.forEach(conn => conn.classList.remove('active'));
}

// Reset explainability side panel
function resetInspectionPanel() {
    intentBadge.className = 'badge';
    intentBadge.textContent = 'None';
    retrievalMetric.className = 'routing-metric inactive';
    retrievalMetric.innerHTML = '<i class="fa-solid fa-ban"></i> Retrieval Inactive';
    routingReason.textContent = 'No query run yet. Ask a question to trigger the router.';
    
    citationsContainer.innerHTML = `
        <div class="empty-explain-state">
            <i class="fa-solid fa-book-bookmark"></i>
            <p>Citations and page extracts will appear here when an answer is generated.</p>
        </div>
    `;
    
    inspectorContainer.innerHTML = `
        <div class="empty-explain-state">
            <i class="fa-solid fa-bars-staged"></i>
            <p>Similarity vs. Rerank confidence scores.</p>
        </div>
    `;
}

// Handle Chat Message Submit
async function handleChatSubmit(e) {
    e.preventDefault();
    const queryText = userInput.value.trim();
    if (!queryText) return;
    
    // Add user message to chat UI
    appendMessage('user', queryText);
    userInput.value = '';
    
    // Set UI loading state
    btnSend.disabled = true;
    btnSend.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    systemStatus.innerHTML = '<span class="status-dot loading"></span> Analyzing Query...';
    
    // Reset pipeline steps visual
    resetPipelineSteps();
    
    try {
        // Step 1: Active routing visual
        stepRoute.classList.add('active');
        
        const response = await fetch(`${API_URL}/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: queryText,
                history: conversationHistory
            })
        });
        
        if (!response.ok) {
            throw new Error('Query failed');
        }
        
        const result = await response.json();
        
        // Step 2 & 3: Retrieval & Reranking visuals if retrieval was active
        stepRoute.classList.add('completed');
        
        if (result.retrieve) {
            document.querySelector('.pipeline-connector').classList.add('active');
            stepRetrieve.classList.add('active', 'completed');
            
            // Connect to reranking
            document.querySelectorAll('.pipeline-connector')[1].classList.add('active');
            stepRerank.classList.add('active', 'completed');
            
            document.querySelectorAll('.pipeline-connector')[2].classList.add('active');
        }
        
        stepGenerate.classList.add('active', 'completed');
        
        // Append response to UI
        appendMessage('assistant', result.answer, false, result.citations);
        
        // Save to conversational memory
        conversationHistory.push({ role: 'user', text: queryText });
        conversationHistory.push({ role: 'model', text: result.answer });
        
        // Update Explainability / Inspection Panels
        renderInspectionPanel(result);
        
        // Update Live badge dynamically if Gemini key is active
        if (!result.answer.includes('[Demo Mode - Set GEMINI_API_KEY')) {
            apiKeyBadge.className = 'api-key-badge live';
            apiKeyBadge.innerHTML = '<i class="fa-solid fa-bolt"></i> Gemini Live Mode';
        } else {
            apiKeyBadge.className = 'api-key-badge';
            apiKeyBadge.innerHTML = '<i class="fa-solid fa-key"></i> Gemini Demo Mode';
        }
        
    } catch (error) {
        console.error('Error querying backend:', error);
        appendMessage('assistant', 'Sorry, I encountered an error while processing your request. Please ensure the backend server is running.');
        resetPipelineSteps();
    } finally {
        btnSend.disabled = false;
        btnSend.innerHTML = '<i class="fa-solid fa-paper-plane"></i>';
        systemStatus.innerHTML = '<span class="status-dot online"></span> System Ready';
    }
}

// Render values inside Inspection Panel
function renderInspectionPanel(result) {
    // 1. Intent Route
    intentBadge.textContent = result.intent;
    intentBadge.className = `badge badge-${result.intent}`;
    
    if (result.retrieve) {
        retrievalMetric.className = 'routing-metric';
        retrievalMetric.innerHTML = '<i class="fa-solid fa-circle-check"></i> Retrieval Active';
    } else {
        retrievalMetric.className = 'routing-metric inactive';
        retrievalMetric.innerHTML = '<i class="fa-solid fa-ban"></i> Retrieval Inactive';
    }
    
    routingReason.textContent = result.reasoning;
    
    // 2. Render Citations
    if (!result.citations || result.citations.length === 0) {
        citationsContainer.innerHTML = `
            <div class="empty-explain-state">
                <i class="fa-solid fa-circle-info"></i>
                <p>No citations extracted. The query was resolved without referencing documents.</p>
            </div>
        `;
    } else {
        citationsContainer.innerHTML = '';
        result.citations.forEach((cit, idx) => {
            const card = document.createElement('div');
            card.className = 'citation-card';
            card.addEventListener('click', () => highlightCitationText(cit.text));
            card.innerHTML = `
                <div class="citation-card-header">
                    <span class="citation-card-source" title="${cit.source}">${cit.source}</span>
                    <span class="citation-card-page">Page ${cit.page}</span>
                </div>
                <div class="citation-card-text">"${cit.text}"</div>
            `;
            citationsContainer.appendChild(card);
        });
    }
    
    // 3. Render Chunk Score Inspector
    if (!result.retrieved_chunks || result.retrieved_chunks.length === 0) {
        inspectorContainer.innerHTML = `
            <div class="empty-explain-state">
                <i class="fa-solid fa-ban"></i>
                <p>No vector search occurred.</p>
            </div>
        `;
    } else {
        inspectorContainer.innerHTML = '';
        result.retrieved_chunks.forEach((chunk, idx) => {
            const biScore = chunk.score ? (chunk.score * 100).toFixed(0) : 0;
            // Cross encoder outputs logit scores, convert sigmoid confidence value to percent
            const crossScore = chunk.confidence ? (chunk.confidence * 100).toFixed(0) : 0;
            
            const card = document.createElement('div');
            card.className = 'score-card';
            card.innerHTML = `
                <div class="score-card-header">
                    <span>Chunk #${idx + 1} (Page ${chunk.metadata.page})</span>
                    <span style="color: var(--accent-blue)">Type: ${chunk.metadata.type}</span>
                </div>
                <div class="score-bars">
                    <div class="score-bar-group">
                        <span class="score-label">Bi-Encoder</span>
                        <div class="score-track">
                            <div class="score-fill bi-fill" style="width: ${biScore}%"></div>
                        </div>
                        <span class="score-val">${biScore}%</span>
                    </div>
                    <div class="score-bar-group">
                        <span class="score-label">Cross-Enc</span>
                        <div class="score-track">
                            <div class="score-fill cross-fill" style="width: ${crossScore}%"></div>
                        </div>
                        <span class="score-val">${crossScore}%</span>
                    </div>
                </div>
            `;
            inspectorContainer.appendChild(card);
        });
    }
}

// Highlight Citation Text inside a Modal or Alert
function highlightCitationText(text) {
    alert(`Evidence Reference:\n\n"${text}"`);
}

// Helper to Append Messages to Chat History UI
function appendMessage(role, text, isSystem = false, citations = []) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message ${isSystem ? 'system-message' : ''}`;
    
    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar';
    avatarDiv.innerHTML = role === 'user' ? '<i class="fa-regular fa-user"></i>' : '<i class="fa-solid fa-robot"></i>';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // If it is from assistant, we highlight the citations in the body
    if (role === 'assistant' && !isSystem && citations.length > 0) {
        let formattedText = formatMarkdown(text);
        
        // Find citation tags like [report.pdf: Page 4] and convert to interactive links
        citations.forEach(cit => {
            const tagStr = `[${cit.source}: Page ${cit.page}]`;
            // Escape special regex chars
            const escapedTag = tagStr.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
            const regex = new RegExp(escapedTag, 'g');
            
            formattedText = formattedText.replace(regex, `
                <span class="citation-link" onclick="highlightCitationText(\`${cit.text.replace(/`/g, '\\`').replace(/"/g, '&quot;')}\`)">
                    <i class="fa-solid fa-circle-info"></i> Page ${cit.page}
                </span>
            `);
        });
        
        contentDiv.innerHTML = formattedText;
    } else {
        contentDiv.innerHTML = isSystem ? `<p><i>${text}</i></p>` : formatMarkdown(text);
    }
    
    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);
    chatHistory.appendChild(messageDiv);
    
    // Auto Scroll to bottom
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

// Simple markdown formatter
function formatMarkdown(text) {
    // Escape HTML to prevent injection
    let clean = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
        
    // Bold **text**
    clean = clean.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Italics *text*
    clean = clean.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    // Inline code `code`
    clean = clean.replace(/`(.*?)`/g, '<code>$1</code>');
    
    // Line breaks
    clean = clean.replace(/\n/g, '<br>');
    
    return clean;
}

// --- RESEARCH ASSISTANT HANDLERS & ROUTINES ---

function setupResearchAssistantHandlers() {
    // Mode toggle: Chat RAG
    if (modeRag) {
        modeRag.addEventListener('click', () => {
            modeRag.classList.add('active');
            modeResearch.classList.remove('active');
            chatViewContainer.classList.remove('hidden');
            researchViewContainer.classList.add('hidden');
            panelTitleText.textContent = "Conversational AI Reasoning";
        });
    }
    
    // Mode toggle: Research Assistant
    if (modeResearch) {
        modeResearch.addEventListener('click', () => {
            modeResearch.classList.add('active');
            modeRag.classList.remove('active');
            chatViewContainer.classList.add('hidden');
            researchViewContainer.classList.remove('hidden');
            panelTitleText.textContent = "Research & Scientific Analysis";
        });
    }
    
    // Engine select change
    if (engineSelect) {
        engineSelect.addEventListener('change', handleEngineChange);
    }
    
    // Paper select dropdown change
    if (paperSelectDropdown) {
        paperSelectDropdown.addEventListener('change', handlePaperSelectChange);
    }
    
    // Compare papers button
    if (btnCompareAll) {
        btnCompareAll.addEventListener('click', handleComparePapers);
    }
}

// Reset Insights Display to initial empty state
function resetInsightsDisplay() {
    if (emptyInsights && insightsScrollContent) {
        emptyInsights.classList.remove('hidden');
        insightsScrollContent.classList.add('hidden');
    }
}

// Handle switching embedding models
async function handleEngineChange() {
    const selectedModel = engineSelect.value;
    systemStatus.innerHTML = `<span class="status-dot loading"></span> Switching to ${selectedModel}...`;
    
    try {
        const response = await fetch(`${API_URL}/set-model`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model_name: selectedModel })
        });
        
        if (!response.ok) {
            throw new Error('Failed to switch embeddings model');
        }
        
        const result = await response.json();
        systemStatus.innerHTML = '<span class="status-dot online"></span> System Ready';
        appendMessage('assistant', `Embeddings Engine switched to <strong>${selectedModel}</strong>. Vector index automatically rebuilt with layout-aware parsing.`, true);
        fetchDocuments();
    } catch (error) {
        console.error('Error switching model:', error);
        systemStatus.innerHTML = '<span class="status-dot online"></span> Engine Swap Failed';
        alert('Failed to switch embeddings engine. Please check if backend is running.');
    }
}

// Handle paper selection and metrics extraction
async function handlePaperSelectChange() {
    const filename = paperSelectDropdown.value;
    if (!filename) {
        resetInsightsDisplay();
        return;
    }
    
    // Show spinner inside the display card
    emptyInsights.classList.add('hidden');
    insightsScrollContent.classList.add('hidden');
    
    // Create temporary loader message
    const loader = document.createElement('div');
    loader.id = 'temp-insights-loader';
    loader.className = 'empty-insights';
    loader.innerHTML = `
        <i class="fa-solid fa-spinner fa-spin"></i>
        <p>Extracting scientific metrics and contributions using layout analysis...</p>
    `;
    insightDisplayCard.appendChild(loader);
    
    try {
        const response = await fetch(`${API_URL}/extract-insights`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: filename })
        });
        
        if (!response.ok) {
            throw new Error('Failed to extract insights');
        }
        
        const result = await response.json();
        
        // Remove loader
        const tempLoader = document.getElementById('temp-insights-loader');
        if (tempLoader) tempLoader.remove();
        
        // Set content
        insightTitle.textContent = result.title || filename;
        insightProblem.textContent = result.problem_statement || "No problem statement found.";
        insightMethodology.textContent = result.methodology || "No methodology found.";
        insightResults.textContent = result.results || "No results found.";
        
        // Key contributions list
        insightContributions.innerHTML = '';
        const contributions = result.key_contributions || [];
        if (contributions.length === 0) {
            insightContributions.innerHTML = '<li>No key contributions specified.</li>';
        } else {
            contributions.forEach(contrib => {
                const li = document.createElement('li');
                li.textContent = contrib;
                insightContributions.appendChild(li);
            });
        }
        
        insightsScrollContent.classList.remove('hidden');
    } catch (error) {
        console.error('Error extracting insights:', error);
        const tempLoader = document.getElementById('temp-insights-loader');
        if (tempLoader) tempLoader.remove();
        emptyInsights.classList.remove('hidden');
        alert('Failed to extract insights from this paper.');
    }
}

// Compare all uploaded documents and render the comparison matrix
async function handleComparePapers() {
    if (!currentDocumentsList || currentDocumentsList.length === 0) {
        alert('Please upload some scientific papers (PDFs) before running the comparison.');
        return;
    }
    
    // Show loading spinner
    emptyComparison.classList.add('hidden');
    comparisonScrollContent.classList.add('hidden');
    
    const loader = document.createElement('div');
    loader.id = 'temp-comparison-loader';
    loader.className = 'empty-comparison';
    loader.innerHTML = `
        <i class="fa-solid fa-spinner fa-spin"></i>
        <p>Running comparative analysis and synthesizing literature review...</p>
    `;
    comparisonDisplayCard.appendChild(loader);
    
    try {
        const response = await fetch(`${API_URL}/compare-papers`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filenames: currentDocumentsList })
        });
        
        if (!response.ok) {
            throw new Error('Comparison request failed');
        }
        
        const result = await response.json();
        
        const tempLoader = document.getElementById('temp-comparison-loader');
        if (tempLoader) tempLoader.remove();
        
        // Parse markdown table and review into HTML
        const html = parseMarkdownToHTML(result.comparison_markdown);
        synthesizedMarkdown.innerHTML = html;
        
        comparisonScrollContent.classList.remove('hidden');
    } catch (error) {
        console.error('Error running comparison:', error);
        const tempLoader = document.getElementById('temp-comparison-loader');
        if (tempLoader) tempLoader.remove();
        emptyComparison.classList.remove('hidden');
        alert('Failed to complete literature comparison analysis.');
    }
}

// High-fidelity Markdown compiler for headers, lists, and tables
function parseMarkdownToHTML(text) {
    let lines = text.split('\n');
    let inTable = false;
    let tableHTML = '';
    let resultHTML = [];
    
    for (let i = 0; i < lines.length; i++) {
        let line = lines[i].trim();
        
        if (line.startsWith('|') && line.endsWith('|')) {
            if (line.includes('---') || line.includes(':---')) {
                continue;
            }
            
            let cells = line.split('|').map(c => c.trim()).filter((c, idx, arr) => idx > 0 && idx < arr.length - 1);
            
            if (!inTable) {
                inTable = true;
                tableHTML = '<table class="markdown-table"><thead><tr>';
                cells.forEach(cell => {
                    tableHTML += `<th>${formatMarkdown(cell)}</th>`;
                });
                tableHTML += '</tr></thead><tbody>';
            } else {
                tableHTML += '<tr>';
                cells.forEach(cell => {
                    tableHTML += `<td>${formatMarkdown(cell)}</td>`;
                });
                tableHTML += '</tr>';
            }
            continue;
        } else {
            if (inTable) {
                inTable = false;
                tableHTML += '</tbody></table>';
                resultHTML.push(tableHTML);
                tableHTML = '';
            }
        }
        
        if (line.startsWith('### ')) {
            resultHTML.push(`<h3>${formatMarkdown(line.substring(4))}</h3>`);
        } else if (line.startsWith('## ')) {
            resultHTML.push(`<h2>${formatMarkdown(line.substring(3))}</h2>`);
        } else if (line.startsWith('# ')) {
            resultHTML.push(`<h1>${formatMarkdown(line.substring(2))}</h1>`);
        } else if (line.startsWith('* ') || line.startsWith('- ')) {
            resultHTML.push(`<ul><li>${formatMarkdown(line.substring(2))}</li></ul>`);
        } else if (line === '') {
            // Keep spacing clean
        } else {
            resultHTML.push(`<p>${formatMarkdown(line)}</p>`);
        }
    }
    
    if (inTable) {
        tableHTML += '</tbody></table>';
        resultHTML.push(tableHTML);
    }
    
    let finalHTML = resultHTML.join('\n');
    finalHTML = finalHTML.replace(/<\/ul>\n<ul>/g, '');
    return finalHTML;
}
