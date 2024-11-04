function convertCase(type) {
    const input = document.getElementById('inputText');
    let text = input.value;

    switch(type) {
        case 'lower':
            input.value = text.toLowerCase();
            break;
        case 'upper':
            input.value = text.toUpperCase();
            break;
        case 'title':
            input.value = text.toLowerCase().split(' ')
                .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                .join(' ');
            break;
        case 'sentence':
            input.value = text.toLowerCase().replace(/(^\w|\.\s+\w)/gm, 
                letter => letter.toUpperCase());
            break;
        case 'alternate':
            input.value = text.split('').map((char, i) => 
                i % 2 === 0 ? char.toLowerCase() : char.toUpperCase()).join('');
            break;
    }
    updateCounts();
}

function clearText() {
    document.getElementById('inputText').value = '';
    updateCounts();
}

async function pasteText() {
    try {
        const text = await navigator.clipboard.readText();
        document.getElementById('inputText').value = text;
        updateCounts();
    } catch (err) {
        alert('Failed to read clipboard. Please check browser permissions.');
    }
}

function updateCounts() {
    const text = document.getElementById('inputText').value;
    
    // Character count
    document.getElementById('charCount').textContent = text.length;
    
    // Word count
    document.getElementById('wordCount').textContent = 
        text.trim() === '' ? 0 : text.trim().split(/\s+/).length;
    
    // Line count
    const lines = text.split(/\r\n|\r|\n/);
    document.getElementById('lineCount').textContent = 
        text.trim() === '' ? 0 : lines.length;
    
    // Sentence count
    const sentences = text.trim().split(/[.!?]+\s*/)
        .filter(sentence => sentence.length > 0);
    document.getElementById('sentenceCount').textContent = 
        text.trim() === '' ? 0 : sentences.length;
}

async function copyToClipboard() {
    const text = document.getElementById('inputText').value;
    try {
        await navigator.clipboard.writeText(text);
        showNotification('Text copied to clipboard!');
    } catch (err) {
        showNotification('Failed to copy text!', 'error');
    }
}

function downloadText() {
    const text = document.getElementById('inputText').value;
    if (!text.trim()) {
        showNotification('Please enter some text to download!', 'error');
        return;
    }
    
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
}

function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.classList.add('fade-out');
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 500);
    }, 2000);
}

// Add event listeners when document loads
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('inputText')?.addEventListener('input', updateCounts);
});