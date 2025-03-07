document.getElementById('queryForm').addEventListener('submit', async (event) => {
    event.preventDefault();

    const question = document.getElementById('question').value.trim();
    const fiqh = document.getElementById('fiqh').value;
    const responseDiv = document.getElementById('response');

    if (!question || !fiqh) {
        responseDiv.innerHTML = "<p>Please enter a question and select a Fiqh.</p>";
        return;
    }

    responseDiv.innerHTML = "<p>Loading...</p>";

    try {
        const response = await fetch('/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question, fiqh })
        });

        if (!response.ok) {
            throw new Error('Failed to fetch response from server.');
        }

        const data = await response.json();
        responseDiv.innerHTML = data.response;
    } catch (error) {
        responseDiv.innerHTML = `<p>Error: ${error.message}</p>`;
    }
});