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

    switch(type) {
        case 'remove-linebreaks':
            input.value = text.replace(/[\r\n]+/g, ' ');
            break;
        case 'remove-whitespace':
            input.value = text.replace(/\s+/g, ' ');
            break;
        case 'remove-all-spaces':
            input.value = text.replace(/\s+/g, '');
            break;
        case 'trim-lines':
            input.value = text.split('\n')
                .map(line => line.trim())
                .join('\n');
            break;
        case 'remove-empty-lines':
            input.value = text.split('\n')
                .filter(line => line.trim().length > 0)
                .join('\n');
            break;
    }
    updateCounts('modifier');
}

// Update existing functions to handle both tabs
function clearText(type) {
    document.getElementById(`${type}InputText`).value = '';
    updateCounts(type);
}

async function pasteText(type) {
    try {
        const text = await navigator.clipboard.readText();
        document.getElementById(`${type}InputText`).value = text;
        updateCounts(type);
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

function downloadText(type) {
    const text = document.getElementById(`${type}InputText`).value;
    if (!text.trim()) {
        showNotification('Please enter some text to download!', 'error');
        return;
    }
    
    const blob = new Blob([text], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${type}-text.txt`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    showNotification('Text downloaded successfully!');
}

// Update convertCase function to use the new ID
function convertCase(type) {
    const input = document.getElementById('caseInputText');
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
    updateCounts('case');
}