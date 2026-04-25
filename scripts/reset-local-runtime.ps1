Set-Location "$PSScriptRoot\..\backend"

if (Test-Path ".\town_warden.db") {
    Remove-Item ".\town_warden.db"
    Write-Host "Removed local SQLite database. It will be recreated on backend startup."
} else {
    Write-Host "No local database found."
}
