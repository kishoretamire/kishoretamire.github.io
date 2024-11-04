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
    document.getElementById('charCount').textContent = text.length;
    document.getElementById('wordCount').textContent = 
        text.trim() === '' ? 0 : text.trim().split(/\s+/).length;
}

// Add event listener for input changes
document.getElementById('inputText').addEventListener('input', updateCounts); 