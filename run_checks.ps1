# Run Ruff lint, Ruff format, and mypy type checking for the whole project

Write-Host "Running Ruff lint..."
.venv\Scripts\ruff.exe check .

Write-Host "Running Ruff format..."
.venv\Scripts\ruff.exe format .

Write-Host "Running mypy type checking..."
.venv\Scripts\mypy.exe .

Write-Host "All checks complete."
