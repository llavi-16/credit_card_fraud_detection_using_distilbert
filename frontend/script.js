document.addEventListener("DOMContentLoaded", () => {
    // --- Element References ---
    const analyzeButton = document.getElementById('analyzeButton');
    const urlInput = document.getElementById('videoUrlInput');
    const errorMessage = document.getElementById('errorMessage');
    const resultsContainer = document.getElementById('resultsContainer');
    const chartCanvas = document.getElementById('sentimentChart');
    const summaryContainer = document.getElementById('summary');
    const menuIcon = document.getElementById('menu-icon');
    const navBar = document.getElementById('navigation-bar');

    let sentimentChart = null; // To hold the chart instance

    // --- Event Listeners ---
    analyzeButton.addEventListener('click', handleAnalysis);
    menuIcon.addEventListener('click', () => navBar.classList.toggle('responsive'));

    /**
     * Main function to trigger the sentiment analysis process.
     */
    async function handleAnalysis() {
        const url = urlInput.value.trim();
        if (!url) {
            showError("Please paste a YouTube video URL.");
            return;
        }

        setLoadingState(true);
        clearResults();

        try {
            // The backend is running on port 8000 as per uvicorn default
            const response = await fetch("http://127.0.0.1:8000/analyze", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url: url }),
            });

            const data = await response.json();

            if (!response.ok) {
                // Use the 'detail' field from FastAPI's HTTPException
                throw new Error(data.detail || "An unknown error occurred.");
            }

            displayResults(data);

        } catch (error) {
            console.error("Analysis failed:", error);
            showError(`Error: ${error.message}`);
        } finally {
            setLoadingState(false);
        }
    }

    /**
     * Updates the UI to show results.
     * @param {object} data - The analysis data, e.g., { positive: 10, negative: 5 }.
     */
    function displayResults(data) {
        resultsContainer.style.display = 'flex';
        const { positive, negative } = data;
        const total = positive + negative;

        if (total === 0) {
            summaryContainer.innerHTML = '<h3>No comments were analyzed.</h3><p>The video may have no comments, or they could not be processed.</p>';
            return;
        }

        // Display summary stats
        summaryContainer.innerHTML = `
            <h3>Analysis Summary</h3>
            <div class="stat">
                <i class="fa-solid fa-thumbs-up stat-icon positive"></i>
                <span><strong>${positive}</strong> Positive Comments</span>
            </div>
            <div class="stat">
                <i class="fa-solid fa-thumbs-down stat-icon negative"></i>
                <span><strong>${negative}</strong> Negative Comments</span>
            </div>
             <div class="stat">
                <i class="fa-solid fa-comments stat-icon"></i>
                <span><strong>${total}</strong> Total Comments Analyzed</span>
            </div>
        `;

        // Create or update the chart
        createOrUpdateChart(data);
    }

    /**
     * Renders the pie chart using Chart.js.
     * @param {object} data - The analysis data.
     */
    function createOrUpdateChart(data) {
        if (sentimentChart) {
            sentimentChart.destroy(); // Clear previous chart
        }

        sentimentChart = new Chart(chartCanvas.getContext('2d'), {
            type: 'pie',
            data: {
                labels: ['Positive', 'Negative'],
                datasets: [{
                    data: [data.positive, data.negative],
                    backgroundColor: ['#28a745', '#dc3545'],
                    borderColor: '#ffffff',
                    borderWidth: 2,
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.raw;
                                const total = context.chart.getDatasetMeta(0).total;
                                const percentage = ((value / total) * 100).toFixed(1) + '%';
                                return `${label}: ${value} (${percentage})`;
                            }
                        }
                    }
                }
            }
        });
    }

    // --- UI Helper Functions ---
    function setLoadingState(isLoading) {
        analyzeButton.disabled = isLoading;
        analyzeButton.innerHTML = isLoading ? '<i class="fa-solid fa-spinner fa-spin"></i> Analyzing...' : 'Analyze';
    }

    function showError(message) {
        errorMessage.textContent = message;
    }

    function clearResults() {
        errorMessage.textContent = '';
        resultsContainer.style.display = 'none';
        summaryContainer.innerHTML = '';
        if (sentimentChart) {
            sentimentChart.destroy();
        }
    }
});
