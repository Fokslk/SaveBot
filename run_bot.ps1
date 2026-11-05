Set-Location $PSScriptRoot
Start-Process -FilePath "$PSScriptRoot\.venv\Scripts\pythonw.exe" -ArgumentList "-m","bot.panel" -WorkingDirectory $PSScriptRoot
