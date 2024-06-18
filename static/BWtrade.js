document.addEventListener('DOMContentLoaded', function () {
    document.getElementById('updateConfig').addEventListener('submit', function (e) {
        e.preventDefault();
        let currencyPairs = document.getElementById('currencyPairs').value;
        let tradeVolume = document.getElementById('tradeVolume').value;
        let stopLoss = document.getElementById('stopLoss').value;
        let takeProfit = document.getElementById('takeProfit').value;

        fetch('/configure', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                currencyPairs: currencyPairs,
                tradeVolume: tradeVolume,
                stopLoss: stopLoss,
                takeProfit: takeProfit
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'Configuration updated successfully') {
                alert('Configuration updated successfully');
            } else {
                alert('Error updating configuration');
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
    });
});
