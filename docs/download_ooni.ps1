# FAST + RESUME OONI Kenya Download (Optimized)
$BaseDir = "C:\ooni-kenya-censorship"
New-Item -ItemType Directory -Force -Path $BaseDir | Out-Null

$ResumeFromDate = "2025-06-29"     # ←←← CHANGE THIS to resume

Write-Host "🚀 Faster OONI Kenya Download - Resume from $ResumeFromDate" -ForegroundColor Green

$env:AWS_S3_MAX_CONCURRENT_REQUESTS = "80"

$startDate = Get-Date $ResumeFromDate
$endDate = Get-Date "2025-06-30"
$current = $startDate

while ($current -le $endDate) {
    $dateStr = $current.ToString("yyyyMMdd")
    Write-Host "→ $dateStr" -ForegroundColor Cyan

    aws s3 sync --no-sign-request `
        "s3://ooni-data-eu-fra/raw/$dateStr/" $BaseDir `
        --exclude "*" `
        --include "*/KE/web_connectivity/*.jsonl.gz" `
        --include "*/KE/whatsapp/*.jsonl.gz" `
        --include "*/KE/telegram/*.jsonl.gz" `
        --include "*/KE/facebook_messenger/*.jsonl.gz" `
        --include "*/KE/signal/*.jsonl.gz" `
        --include "*/KE/tor/*.jsonl.gz" `
        --include "*/KE/psiphon/*.jsonl.gz" `
        --include "*/KE/dnscheck/*.jsonl.gz" | Out-Null

    $current = $current.AddDays(1)
}

Write-Host "`nSession finished. Resume by changing the date and running again." -ForegroundColor Green
pause