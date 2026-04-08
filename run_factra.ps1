# Factra Launch Script
# This script starts the Flask API and the Deep Analysis Dashboard.

Write-Host "🚀 Launching Factra (Fake News Detection Suite)..." -ForegroundColor Cyan
Write-Host "----------------------------------------------------"

# Check if Python is installed
if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python not found. Please install Python and add it to your PATH."
    exit 1
}

# Check if the model directory exists
$modelDir = "model/artifacts/fakenews_bert"
if (!(Test-Path $modelDir)) {
    Write-Warning "Model directory not found at $modelDir."
    Write-Host "Please ensure you have trained the model or extracted the artifacts to that location."
    exit 1
}

# Start the Flask API
Write-Host "Starting Flask API... (http://127.0.0.1:5000)" -ForegroundColor Green
python -m api.app --model_dir $modelDir
