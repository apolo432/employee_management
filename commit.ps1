# Git Commit Helper PowerShell Script

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    Git Commit Helper" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Current status:" -ForegroundColor Yellow
git status --short
Write-Host ""

$commitType = Read-Host "Type (feat/fix/style/refactor)"
$commitMsg = Read-Host "Message"

Write-Host ""
Write-Host "Creating commit..." -ForegroundColor Green
git add .
git commit -m "$commitType`: $commitMsg"

Write-Host ""
Write-Host "Commit created successfully!" -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to continue"
