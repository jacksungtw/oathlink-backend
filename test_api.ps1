# test_api.ps1  — 最小可執行版

$ErrorActionPreference = 'Stop'

# 1) 寫入記憶
$writeBody = @{ content = "師父說要穩定保活"; tags = @("todo","important") } | ConvertTo-Json -Depth 5
$writeRes  = Invoke-RestMethod -Uri "https://oathlink-backend-production.up.railway.app/memory/write" `
                               -Method POST `
                               -Headers @{ "Content-Type" = "application/json" } `
                               -Body $writeBody
"=== 寫入成功 ==="
$writeRes

# 2) 搜尋記憶
$searchRes = Invoke-RestMethod -Uri "https://oathlink-backend-production.up.railway.app/memory/search?q=師父&top_k=3" -Method GET
"=== 搜尋結果 ==="
$searchRes

# 3) 健康檢查
$health = Invoke-RestMethod -Uri "https://oathlink-backend-production.up.railway.app/health" -Method GET
"=== 健康檢查 ==="
$health