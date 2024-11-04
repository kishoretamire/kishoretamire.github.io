// Add history stacks at the beginning of the file
const textHistory = {
    case: {
        stack: [],
        currentIndex: -1
    },
    modifier: {
        stack: [],
        currentIndex: -1
    }
};

// Function to save state to history
function saveToHistory(type, text) {
    const history = textHistory[type];
    
    // Remove any future states if we're in the middle of the history
    if (history.currentIndex < history.stack.length - 1) {
        history.stack = history.stack.slice(0, history.currentIndex + 1);
    }
    
    // Add new state
    history.stack.push(text);
    history.currentIndex++;
    
    // Limit history size (optional)
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
        const text = history.stack[history.currentIndex];
        document.getElementById(`${type}InputText`).value = text;
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

    // Add input listeners for both textareas
    document.getElementById('caseInputText')?.addEventListener('input', () => updateCounts('case'));
    document.getElementById('modifierInputText')?.addEventListener('input', () => updateCounts('modifier'));
});

// Text Modification Functions
function modifyText(type) {
    const input = document.getElementById('modifierInputText');
    let text = input.value;
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
    }
    
    if (newText !== text) {
        saveToHistory('modifier', text);
        input.value = newText;
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
    }
}

async function pasteText(type) {
    try {
        const text = await navigator.clipboard.readText();
        const currentText = document.getElementById(`${type}InputText`).value;
        if (text !== currentText) {
            saveToHistory(type, currentText);
            document.getElementById(`${type}InputText`).value = text;
            updateCounts(type);
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
        saveToHistory('case', text);
        input.value = newText;
        updateCounts('case');
    }
}

// Initialize history when text is first entered
document.addEventListener('DOMContentLoaded', function() {
    ['case', 'modifier'].forEach(type => {
        const textarea = document.getElementById(`${type}InputText`);
        if (textarea) {
            textarea.addEventListener('input', (e) => {
                if (textHistory[type].stack.length === 0) {
                    saveToHistory(type, e.target.value);
                }
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
let currentFontSize = 16;

function adjustTextSize(action) {
    const minSize = 12;
    const maxSize = 24;
    const step = 2;
    
    if (action === 'increase' && currentFontSize < maxSize) {
        currentFontSize += step;
    } else if (action === 'decrease' && currentFontSize > minSize) {
        currentFontSize -= step;
    }
    
    document.querySelectorAll('textarea').forEach(textarea => {
        textarea.style.fontSize = `${currentFontSize}px`;
    });
    
    document.getElementById('fontSizeDisplay').textContent = `${currentFontSize}px`;
    localStorage.setItem('fontSize', currentFontSize);
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
    
    // Initialize font size
    const savedFontSize = localStorage.getItem('fontSize');
    if (savedFontSize) {
        currentFontSize = parseInt(savedFontSize);
        document.querySelectorAll('textarea').forEach(textarea => {
            textarea.style.fontSize = `${currentFontSize}px`;
        });
        document.getElementById('fontSizeDisplay').textContent = `${currentFontSize}px`;
    }
    
    // Load saved text
    loadFromLocalStorage();
    
    // Add auto-save functionality
    ['case', 'modifier'].forEach(type => {
        const textarea = document.getElementById(`${type}InputText`);
        textarea.addEventListener('input', () => saveToLocalStorage(type));
    });
});