# Download OONI raw measurements for Kenya from OONI's public S3 bucket (no account needed).
# Requires the AWS CLI. Afterwards, move the files into data/dev/ooni/ooni-kenya-censorship/.
#
# Bucket layout: s3://ooni-data-eu-fra/raw/<YYYYMMDD>/<HH>/<CC>/<folder>/<file>.jsonl.gz
# Folder names drop the underscore that each record's test_name keeps
# (webconnectivity, facebookmessenger), so the patterns below use the folder names.
# Re-running resumes: aws s3 sync skips files already downloaded.

$BaseDir   = "C:\ooni-kenya-censorship"
$StartDate = "2023-06-01"
$EndDate   = "2025-06-30"

# Web Connectivity is large: about 115 MB a day for Kenya, roughly 90 GB for
# 2023-06-01 to 2025-06-30 (OONI file listings sampled 2026-11-05).
# Off by default. Set to $true only after planning disk space, storage and cost.
$IncludeWebConnectivity = $false

$Tests = @("whatsapp", "telegram", "facebookmessenger", "signal", "tor", "psiphon", "dnscheck")
if ($IncludeWebConnectivity) { $Tests += "webconnectivity" }

$includes = @()
foreach ($t in $Tests) { $includes += "--include"; $includes += "*/KE/$t/*.jsonl.gz" }

New-Item -ItemType Directory -Force -Path $BaseDir | Out-Null
$env:AWS_S3_MAX_CONCURRENT_REQUESTS = "80"

Write-Host "OONI Kenya download: $StartDate to $EndDate; tests: $($Tests -join ', ')" -ForegroundColor Green

$current = Get-Date $StartDate
$end = Get-Date $EndDate
while ($current -le $end) {
    $dateStr = $current.ToString("yyyyMMdd")
    Write-Host "-> $dateStr" -ForegroundColor Cyan
    aws s3 sync --no-sign-request "s3://ooni-data-eu-fra/raw/$dateStr/" $BaseDir --exclude "*" @includes | Out-Null
    $current = $current.AddDays(1)
}

# A requested test with no files usually means its folder name is wrong. Say so.
foreach ($t in $Tests) {
    $n = (Get-ChildItem -Path $BaseDir -Recurse -Filter "*_KE_$t.*.jsonl.gz" -ErrorAction SilentlyContinue | Measure-Object).Count
    if ($n -eq 0) {
        Write-Warning "No files for '$t' under $BaseDir. Check the folder name in the bucket."
    } else {
        Write-Host "${t}: $n files"
    }
}

Write-Host "`nDone. Re-run to resume; files already downloaded are skipped." -ForegroundColor Green
