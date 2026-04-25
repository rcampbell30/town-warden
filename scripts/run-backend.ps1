Set-Location "$PSScriptRoot\..\backend"

if (!(Test-Path ".\venv\Scripts\Activate.ps1")) {
    py -m venv venv
}

. .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
