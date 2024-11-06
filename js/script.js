// Add history stacks at the beginning of the file
const textHistory = {
    case: {
        stack: [],
        currentIndex: -1
    },
    modifier: {
        stack: [],
        currentIndex: -1
    },
    analyzer: {
        stack: [],
        currentIndex: -1
    }
};

// Add these constants at the top of the file
const MAX_CHARS = 100000;
const WARN_THRESHOLD = 0.8; // Show warning at 80% of limit

// Add these variables at the top of the file
const fontSizes = {
    case: 16,
    modifier: 16,
    analyzer: 16
};

// Function to save state to history
function saveToHistory(type, text) {
    const history = textHistory[type];
    
    // Don't save if the text is identical to the current state
    if (history.stack[history.currentIndex] === text) {
        return;
    }
    
    // Remove any future states if we're in the middle of the history
    if (history.currentIndex < history.stack.length - 1) {
        history.stack = history.stack.slice(0, history.currentIndex + 1);
    }
    
    // Add new state
    history.stack.push(text);
    history.currentIndex++;
    
    // Limit history size
    if (history.stack.length > 50) {
        history.stack.shift();
        history.currentIndex--;
    }
    
    // Enable/disable undo button
    updateUndoButton(type);
}

// Function to undo
function undo(type) {
    const history = textHistory[type];
    if (history.currentIndex > 0) {
        history.currentIndex--;
        const previousState = history.stack[history.currentIndex];
        
        // Update the text area
        const textarea = document.getElementById(`${type}InputText`);
        textarea.value = previousState;
        
        // Update counts and undo button state
        updateCounts(type);
        updateUndoButton(type);
    }
}

// Function to update undo button state
function updateUndoButton(type) {
    const undoButton = document.getElementById(`${type}Undo`);
    if (undoButton) {
        undoButton.disabled = textHistory[type].currentIndex <= 0;
    }
}

// Tab Switching
document.addEventListener('DOMContentLoaded', function() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Remove active class from all buttons and contents
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));

            // Add active class to clicked button and corresponding content
            button.classList.add('active');
            document.getElementById(button.dataset.tab).classList.add('active');
        });
    });

    // Add input listeners for all textareas
    ['case', 'modifier', 'analyzer'].forEach(type => {
        const textarea = document.getElementById(`${type}InputText`);
        if (textarea) {
            textarea.addEventListener('input', () => {
                updateCounts(type);
                updateCharLimit(type);
                if (textHistory[type].stack.length === 0) {
                    saveToHistory(type, '');
                }
                saveToHistory(type, textarea.value);
            });
            
            // Initialize character limit display
            updateCharLimit(type);
        }
    });

    // Initialize theme
    initTheme();
    document.getElementById('themeToggle').addEventListener('click', toggleTheme);
    
    // Load saved text
    loadFromLocalStorage();
});

// Text Modification Functions
function modifyText(type) {
    const input = document.getElementById('modifierInputText');
    let text = input.value;
    
    // Save current state before modification
    if (text !== textHistory.modifier.stack[textHistory.modifier.currentIndex]) {
        saveToHistory('modifier', text);
    }
    
    let newText = text;
    switch(type) {
        case 'remove-linebreaks':
            newText = text.replace(/[\r\n]+/g, ' ');
            break;
        case 'remove-whitespace':
            newText = text.replace(/\s+/g, ' ');
            break;
        case 'remove-all-spaces':
            newText = text.replace(/\s+/g, '');
            break;
        case 'trim-lines':
            newText = text.split('\n')
                .map(line => line.trim())
                .join('\n');
            break;
        case 'remove-empty-lines':
            newText = text.split('\n')
                .filter(line => line.trim().length > 0)
                .join('\n');
            break;
        case 'format-json':
            try {
                // First try to parse the JSON to validate it
                const jsonObj = JSON.parse(text);
                // Format with 2 spaces indentation and proper sorting
                newText = JSON.stringify(jsonObj, null, 2);
                showNotification('JSON formatted successfully!', 'success');
            } catch (err) {
                showNotification('Invalid JSON format: ' + err.message, 'error');
                return;
            }
            break;
    }
    
    if (newText !== text) {
        input.value = newText;
        saveToHistory('modifier', newText);
        updateCounts('modifier');
    }
}

// Update existing functions to handle both tabs
function clearText(type) {
    const input = document.getElementById(`${type}InputText`);
    if (input.value) {
        saveToHistory(type, input.value);
        input.value = '';
        updateCounts(type);
        updateCharLimit(type);
    }
}

async function pasteText(type) {
    try {
        const text = await navigator.clipboard.readText();
        const textarea = document.getElementById(`${type}InputText`);
        const currentText = textarea.value;
        
        if (text !== currentText) {
            saveToHistory(type, currentText);
            textarea.value = text;
            updateCounts(type);
            updateCharLimit(type);
        }
    } catch (err) {
        showNotification('Failed to read clipboard. Please check browser permissions.', 'error');
    }
}

function updateCounts(type) {
    const text = document.getElementById(`${type}InputText`).value;
    
    // Character count
    document.getElementById(`${type}CharCount`).textContent = text.length;
    
    // Word count
    document.getElementById(`${type}WordCount`).textContent = 
        text.trim() === '' ? 0 : text.trim().split(/\s+/).length;
    
    // Line count
    const lines = text.split(/\r\n|\r|\n/);
    document.getElementById(`${type}LineCount`).textContent = 
        text.trim() === '' ? 0 : lines.length;
    
    // Sentence count
    const sentences = text.trim().split(/[.!?]+\s*/)
        .filter(sentence => sentence.length > 0);
    document.getElementById(`${type}SentenceCount`).textContent = 
        text.trim() === '' ? 0 : sentences.length;
}

async function copyToClipboard(type) {
    const text = document.getElementById(`${type}InputText`).value;
    try {
        await navigator.clipboard.writeText(text);
        showNotification('Text copied to clipboard!');
    } catch (err) {
        showNotification('Failed to copy text!', 'error');
    }
}

// Update the downloadText function
function downloadText(type) {
    const text = document.getElementById(`${type}InputText`).value;
    if (!text.trim()) {
        showNotification('Please enter some text to download!', 'error');
        return;
    }
    
    try {
        const blob = new Blob([text], { type: 'text/plain' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'converted-text.txt';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        showNotification('Text downloaded successfully!');
    } catch (err) {
        console.error('Download error:', err);
        showNotification('Failed to download text!', 'error');
    }
}

// Update convertCase function to use the new ID
function convertCase(type) {
    const input = document.getElementById('caseInputText');
    let text = input.value;
    
    // Save current state before modification
    if (text !== textHistory.case.stack[textHistory.case.currentIndex]) {
        saveToHistory('case', text);
    }
    
    let newText = text;
    switch(type) {
        case 'lower':
            newText = text.toLowerCase();
            break;
        case 'upper':
            newText = text.toUpperCase();
            break;
        case 'title':
            newText = text.toLowerCase().split(' ')
                .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                .join(' ');
            break;
        case 'sentence':
            newText = text.toLowerCase().replace(/(^\w|\.\s+\w)/gm, 
                letter => letter.toUpperCase());
            break;
        case 'alternate':
            newText = text.split('').map((char, i) => 
                i % 2 === 0 ? char.toLowerCase() : char.toUpperCase()).join('');
            break;
    }
    
    if (newText !== text) {
        input.value = newText;
        saveToHistory('case', newText);
        updateCounts('case');
    }
}

// Initialize history when text is first entered
document.addEventListener('DOMContentLoaded', function() {
    ['case', 'modifier'].forEach(type => {
        const textarea = document.getElementById(`${type}InputText`);
        if (textarea) {
            textarea.addEventListener('input', (e) => {
                // Save initial state if history is empty
                if (textHistory[type].stack.length === 0) {
                    saveToHistory(type, '');
                }
                saveToHistory(type, e.target.value);
                updateCounts(type);
            });
        }
    });
});

// Theme Toggle
function initTheme() {
    const theme = localStorage.getItem('theme') || 'light';
    document.body.classList.toggle('dark-theme', theme === 'dark');
    updateThemeIcon();
}

function toggleTheme() {
    document.body.classList.toggle('dark-theme');
    const isDark = document.body.classList.contains('dark-theme');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    updateThemeIcon();
}

function updateThemeIcon() {
    const icon = document.querySelector('#themeToggle i');
    const isDark = document.body.classList.contains('dark-theme');
    icon.className = isDark ? 'fas fa-sun' : 'fas fa-moon';
}

// Text Size Controls
function adjustTextSize(action, type) {
    const minSize = 12;
    const maxSize = 24;
    const step = 2;
    
    if (action === 'increase' && fontSizes[type] < maxSize) {
        fontSizes[type] += step;
    } else if (action === 'decrease' && fontSizes[type] > minSize) {
        fontSizes[type] -= step;
    }
    
    // Update the textarea font size
    document.getElementById(`${type}InputText`).style.fontSize = `${fontSizes[type]}px`;
    
    // Update the display
    document.getElementById(`${type}FontSizeDisplay`).textContent = `${fontSizes[type]}px`;
    
    // Save to localStorage
    localStorage.setItem(`${type}FontSize`, fontSizes[type]);
}

// Export functionality
async function exportText(format) {
    const activeTab = document.querySelector('.tab-content.active');
    const textarea = activeTab.querySelector('textarea');
    const text = textarea.value;
    
    if (!text.trim()) {
        showNotification('Please enter some text to export!', 'error');
        return;
    }
    
    try {
        if (format === 'pdf') {
            const { jsPDF } = window.jspdf;
            const doc = new jsPDF();
            
            // Set font size and line height
            doc.setFontSize(12);
            const lineHeight = 7;
            
            // Split text into lines
            const pageWidth = doc.internal.pageSize.getWidth();
            const pageHeight = doc.internal.pageSize.getHeight();
            const margin = 20;
            const maxWidth = pageWidth - (margin * 2);
            
            // Function to handle text wrapping
            const splitLines = doc.splitTextToSize(text, maxWidth);
            
            // Calculate how many lines can fit on one page
            const linesPerPage = Math.floor((pageHeight - (margin * 2)) / lineHeight);
            
            // Add pages and text
            let currentPage = 1;
            for (let i = 0; i < splitLines.length; i += linesPerPage) {
                if (i > 0) {
                    doc.addPage();
                    currentPage++;
                }
                
                // Get lines for current page
                const pageLines = splitLines.slice(i, i + linesPerPage);
                
                // Add text to page
                doc.text(pageLines, margin, margin + lineHeight);
            }
            
            doc.save('converted-text.pdf');
        } else if (format === 'doc') {
            const blob = new Blob([text], { type: 'application/msword' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'converted-text.doc';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        }
        showNotification(`Text exported as ${format.toUpperCase()}!`);
    } catch (err) {
        console.error('Export error:', err);
        showNotification('Failed to export text!', 'error');
    }
}

// Share functionality
async function shareText(platform) {
    const activeTab = document.querySelector('.tab-content.active');
    const textarea = activeTab.querySelector('textarea');
    const text = textarea.value;
    
    if (!text.trim()) {
        showNotification('Please enter some text to share!', 'error');
        return;
    }
    
    // Create a shorter hash from the text
    const hash = await createShortHash(text);
    const shortUrl = `${window.location.origin}/?t=${hash}`;
    
    switch(platform) {
        case 'copy':
            await navigator.clipboard.writeText(shortUrl);
            showNotification('Share link copied to clipboard!');
            break;
        case 'twitter':
            window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(shortUrl)}`);
            break;
        case 'facebook':
            window.open(`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shortUrl)}`);
            break;
    }
}

// Add these new functions
async function createShortHash(text) {
    // Create a hash of the text
    const msgBuffer = new TextEncoder().encode(text);
    const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    
    // Take first 8 characters of the hash
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('').substring(0, 8);
}

// Add this to handle incoming short URLs
document.addEventListener('DOMContentLoaded', function() {
    // Check if there's a text hash in the URL
    const urlParams = new URLSearchParams(window.location.search);
    const textHash = urlParams.get('t');
    
    if (textHash) {
        // Here you would typically fetch the text from localStorage or your preferred storage
        const savedText = localStorage.getItem(textHash);
        if (savedText) {
            document.getElementById('caseInputText').value = savedText;
            updateCounts('case');
        }
    }
});

// Local Storage
function saveToLocalStorage(type) {
    const textarea = document.getElementById(`${type}InputText`);
    const text = textarea.value;
    localStorage.setItem(`${type}Text`, text);
    
    // Also save with hash for sharing
    if (text.trim()) {
        createShortHash(text).then(hash => {
            localStorage.setItem(hash, text);
            // Optionally cleanup old hashes here
        });
    }
}

function loadFromLocalStorage() {
    ['case', 'modifier'].forEach(type => {
        const savedText = localStorage.getItem(`${type}Text`);
        if (savedText) {
            const textarea = document.getElementById(`${type}InputText`);
            textarea.value = savedText;
            updateCounts(type);
        }
    });
}

// Initialize everything when the document loads
document.addEventListener('DOMContentLoaded', function() {
    // Existing initialization code...
    
    // Initialize theme
    initTheme();
    document.getElementById('themeToggle').addEventListener('click', toggleTheme);
    
    // Initialize font sizes from localStorage
    ['case', 'modifier'].forEach(type => {
        const savedSize = localStorage.getItem(`${type}FontSize`);
        if (savedSize) {
            fontSizes[type] = parseInt(savedSize);
            document.getElementById(`${type}InputText`).style.fontSize = `${fontSizes[type]}px`;
            document.getElementById(`${type}FontSizeDisplay`).textContent = `${fontSizes[type]}px`;
        }
    });
    
    // Load saved text
    loadFromLocalStorage();
    
    // Add auto-save functionality
    ['case', 'modifier'].forEach(type => {
        const textarea = document.getElementById(`${type}InputText`);
        textarea.addEventListener('input', () => saveToLocalStorage(type));
    });
});

// Add this function to create and update character limit indicator
function updateCharLimit(type) {
    const textarea = document.getElementById(`${type}InputText`);
    let charLimitDiv = document.getElementById(`${type}CharLimit`);
    
    if (!charLimitDiv) {
        charLimitDiv = document.createElement('div');
        charLimitDiv.id = `${type}CharLimit`;
        charLimitDiv.className = 'char-limit';
        textarea.parentElement.appendChild(charLimitDiv);
    }
    
    const charCount = textarea.value.length;
    const percentUsed = charCount / MAX_CHARS;
    
    charLimitDiv.textContent = `${charCount.toLocaleString()} / ${MAX_CHARS.toLocaleString()}`;
    
    // Update classes based on usage
    charLimitDiv.classList.remove('near-limit', 'at-limit');
    if (percentUsed >= 1) {
        charLimitDiv.classList.add('at-limit');
    } else if (percentUsed >= WARN_THRESHOLD) {
        charLimitDiv.classList.add('near-limit');
    }
}

// Update the textarea input event listeners
document.addEventListener('DOMContentLoaded', function() {
    ['case', 'modifier'].forEach(type => {
        const textarea = document.getElementById(`${type}InputText`);
        if (textarea) {
            textarea.addEventListener('input', (e) => {
                // Only save to history if there's actual content
                if (e.target.value.trim()) {
                    if (textHistory[type].stack.length === 0) {
                        saveToHistory(type, e.target.value);
                    }
                } else {
                    // Reset history if textarea is empty
                    textHistory[type].stack = [];
                    textHistory[type].currentIndex = -1;
                    updateUndoButton(type);
                }
                updateCounts(type);
                updateCharLimit(type);
                
                // Prevent input if at limit
                if (e.target.value.length > MAX_CHARS) {
                    e.target.value = e.target.value.substring(0, MAX_CHARS);
                    showNotification('Character limit reached!', 'error');
                }
            });
            
            // Initialize character limit display
            updateCharLimit(type);
        }
    });
});

// Text Analysis Functions
function analyzeText(type) {
    const input = document.getElementById('analyzerInputText');
    const text = input.value;
    const resultsDiv = document.querySelector('.analysis-results');
    const outputDiv = document.getElementById('analysisOutput');
    
    if (!text.trim()) {
        showNotification('Please enter some text to analyze!', 'error');
        return;
    }

    let result = '';
    switch(type) {
        case 'word-frequency':
            result = getWordFrequency(text);
            break;
        case 'reading-time':
            result = getReadingTime(text);
            break;
        case 'keyword-density':
            result = getKeywordDensity(text);
            break;
        case 'readability':
            result = getReadabilityScore(text);
            break;
        case 'char-distribution':
            result = getCharacterDistribution(text);
            break;
    }

    outputDiv.innerHTML = result;
    outputDiv.classList.remove('hidden');
    resultsDiv.style.display = 'block';
}

function getWordFrequency(text) {
    const words = text.toLowerCase().match(/\b\w+\b/g);
    const frequency = {};
    words.forEach(word => {
        frequency[word] = (frequency[word] || 0) + 1;
    });

    const sorted = Object.entries(frequency)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10);

    return `
        <h3>Top 10 Most Frequent Words</h3>
        <table>
            <tr><th>Word</th><th>Frequency</th></tr>
            ${sorted.map(([word, count]) => 
                `<tr><td>${word}</td><td>${count}</td></tr>`
            ).join('')}
        </table>
    `;
}

function getReadingTime(text) {
    const wordsPerMinute = 200;
    const wordCount = text.trim().split(/\s+/).length;
    const minutes = Math.ceil(wordCount / wordsPerMinute);

    return `
        <h3>Estimated Reading Time</h3>
        <p>${minutes} minute${minutes !== 1 ? 's' : ''} (at ${wordsPerMinute} words per minute)</p>
        <p>Total words: ${wordCount}</p>
    `;
}

function getKeywordDensity(text) {
    const words = text.toLowerCase().match(/\b\w+\b/g);
    const totalWords = words.length;
    const frequency = {};
    
    words.forEach(word => {
        frequency[word] = (frequency[word] || 0) + 1;
    });

    const density = Object.entries(frequency)
        .map(([word, count]) => ({
            word,
            count,
            density: ((count / totalWords) * 100).toFixed(2)
        }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 10);

    return `
        <h3>Keyword Density (Top 10)</h3>
        <table>
            <tr><th>Keyword</th><th>Count</th><th>Density (%)</th></tr>
            ${density.map(({word, count, density}) => 
                `<tr><td>${word}</td><td>${count}</td><td>${density}%</td></tr>`
            ).join('')}
        </table>
    `;
}

function getReadabilityScore(text) {
    const sentences = text.split(/[.!?]+/).length;
    const words = text.trim().split(/\s+/).length;
    const syllables = countSyllables(text);
    
    // Flesch Reading Ease score
    const score = 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words);
    const level = getReadingLevel(score);

    return `
        <h3>Readability Analysis</h3>
        <p>Flesch Reading Ease Score: ${Math.round(score)}</p>
        <p>Reading Level: ${level}</p>
        <p>Average words per sentence: ${(words / sentences).toFixed(1)}</p>
        <p>Average syllables per word: ${(syllables / words).toFixed(1)}</p>
    `;
}

function getCharacterDistribution(text) {
    const chars = text.split('');
    const distribution = {};
    
    chars.forEach(char => {
        if (char.match(/[a-z0-9]/i)) {
            distribution[char.toLowerCase()] = (distribution[char.toLowerCase()] || 0) + 1;
        }
    });

    const sorted = Object.entries(distribution)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10);

    return `
        <h3>Character Distribution (Top 10)</h3>
        <table>
            <tr><th>Character</th><th>Count</th></tr>
            ${sorted.map(([char, count]) => 
                `<tr><td>${char}</td><td>${count}</td></tr>`
            ).join('')}
        </table>
    `;
}

// Helper functions
function countSyllables(text) {
    return text.toLowerCase()
        .replace(/[^a-z]/g, '')
        .replace(/[^aeiouy]*[aeiouy]+/g, 'a')
        .length;
}

function getReadingLevel(score) {
    if (score >= 90) return 'Very Easy';
    if (score >= 80) return 'Easy';
    if (score >= 70) return 'Fairly Easy';
    if (score >= 60) return 'Standard';
    if (score >= 50) return 'Fairly Difficult';
    if (score >= 30) return 'Difficult';
    return 'Very Difficult';
}

// Add these new analysis functions

function getLongestWords(text) {
    const words = text.toLowerCase()
        .match(/\b[a-z]+\b/g)
        .sort((a, b) => b.length - a.length)
        .slice(0, 10);

    return `
        <h3>10 Longest Words</h3>
        <table>
            <tr><th>Word</th><th>Length</th></tr>
            ${words.map(word => 
                `<tr><td>${word}</td><td>${word.length} characters</td></tr>`
            ).join('')}
        </table>
    `;
}

function getRepeatedPhrases(text) {
    const phrases = {};
    const words = text.toLowerCase().match(/\b\w+\b/g);
    
    // Look for 2-4 word phrases
    for (let phraseLength = 2; phraseLength <= 4; phraseLength++) {
        for (let i = 0; i <= words.length - phraseLength; i++) {
            const phrase = words.slice(i, i + phraseLength).join(' ');
            phrases[phrase] = (phrases[phrase] || 0) + 1;
        }
    }

    const repeatedPhrases = Object.entries(phrases)
        .filter(([_, count]) => count > 1)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10);

    return `
        <h3>Most Repeated Phrases</h3>
        <table>
            <tr><th>Phrase</th><th>Occurrences</th></tr>
            ${repeatedPhrases.map(([phrase, count]) => 
                `<tr><td>"${phrase}"</td><td>${count}</td></tr>`
            ).join('')}
        </table>
    `;
}

function getSentimentAnalysis(text) {
    // Simple sentiment analysis using keyword matching
    const positiveWords = new Set([
        'good', 'great', 'awesome', 'excellent', 'happy', 'love', 'wonderful',
        'fantastic', 'amazing', 'beautiful', 'best', 'perfect', 'brilliant'
    ]);
    
    const negativeWords = new Set([
        'bad', 'terrible', 'awful', 'horrible', 'sad', 'hate', 'worst',
        'poor', 'disappointing', 'negative', 'wrong', 'difficult', 'failed'
    ]);

    const words = text.toLowerCase().match(/\b\w+\b/g) || [];
    let positiveCount = 0;
    let negativeCount = 0;
    let neutralCount = 0;

    words.forEach(word => {
        if (positiveWords.has(word)) positiveCount++;
        else if (negativeWords.has(word)) negativeCount++;
        else neutralCount++;
    });

    const total = words.length;
    const sentiment = positiveCount > negativeCount ? 'Positive' :
                     positiveCount < negativeCount ? 'Negative' : 'Neutral';
    
    return `
        <h3>Basic Sentiment Analysis</h3>
        <p>Overall Sentiment: <strong>${sentiment}</strong></p>
        <table>
            <tr><th>Type</th><th>Count</th><th>Percentage</th></tr>
            <tr>
                <td>Positive Words</td>
                <td>${positiveCount}</td>
                <td>${((positiveCount/total) * 100).toFixed(1)}%</td>
            </tr>
            <tr>
                <td>Negative Words</td>
                <td>${negativeCount}</td>
                <td>${((negativeCount/total) * 100).toFixed(1)}%</td>
            </tr>
            <tr>
                <td>Neutral Words</td>
                <td>${neutralCount}</td>
                <td>${((neutralCount/total) * 100).toFixed(1)}%</td>
            </tr>
        </table>
    `;
}

function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);

    // Remove notification after 3 seconds
    setTimeout(() => {
        notification.classList.add('fade-out');
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 500);
    }, 3000);
}