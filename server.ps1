$baseDir = $PSScriptRoot
if ([string]::IsNullOrEmpty($baseDir)) { $baseDir = $PWD }

$port = 8080
$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://+:$port/")

try {
    $listener.Start()
} catch {
    Write-Host "========================== WARNING ==========================" -ForegroundColor Red
    Write-Host " IP バインディングに失敗しました (Access Denied)" -ForegroundColor Yellow
    Write-Host " サーバーの外部IPからアクセスするには、管理者権限が必要です。" -ForegroundColor Yellow
    Write-Host " 'start.bat' を右クリックし、「管理者として実行」してください。" -ForegroundColor Yellow
    Write-Host "=============================================================" -ForegroundColor Red
    Read-Host "Enterキーを押して終了します..."
    exit
}

Write-Host "================================================="
Write-Host " EnvPortal - Environment & RDP Navigation Server"
Write-Host " Server is running on http://localhost:$port/"
Write-Host " Press Ctrl+C to stop."
Write-Host "================================================="

Start-Process "http://localhost:$port/index.html"

# Ignore SSL errors for ping functionality
[System.Net.ServicePointManager]::ServerCertificateValidationCallback = {$true}

try {
    while ($listener.IsListening) {
        $context = $listener.GetContext()
        $request = $context.Request
        $response = $context.Response
        $response.Headers.Add("Cache-Control", "no-store, no-cache, must-revalidate")

        $localPath = $request.Url.LocalPath

        if ($request.HttpMethod -eq "POST") {
            $reader = New-Object IO.StreamReader($request.InputStream)
            $body = $reader.ReadToEnd()
            $reader.Close()

            if ($localPath -eq "/auth.jsp") {
                $parts = $body.Split('=')
                $pwd = if ($parts.Length -gt 1) { [uri]::UnescapeDataString($parts[1]) } else { "" }
                $outStr = if ($pwd -eq "nho1234567") { "OK" } else { "NG" }
                $buffer = [System.Text.Encoding]::UTF8.GetBytes($outStr)
                $response.ContentType = "text/plain; charset=utf-8"
            }
            elseif ($localPath -eq "/update_csv.jsp" -or $localPath -eq "/update_rdp.jsp") {
                $file = if ($localPath -eq "/update_csv.jsp") { "data.csv" } else { "rdp.csv" }
                $filePath = Join-Path $baseDir $file
                
                # Write file with UTF-8 BOM representation
                $utf8NoBom = New-Object System.Text.UTF8Encoding $true
                [System.IO.File]::WriteAllText($filePath, $body, $utf8NoBom)
                
                $buffer = [System.Text.Encoding]::UTF8.GetBytes("success")
                $response.ContentType = "text/plain; charset=utf-8"
            }
            else {
                $response.StatusCode = 404
                $buffer = [System.Text.Encoding]::UTF8.GetBytes("Not Found")
            }
        }
        elseif ($request.HttpMethod -eq "GET") {
            if ($localPath -eq "/ping.jsp") {
                $target_url = $request.QueryString["url"]
                
                if ([string]::IsNullOrWhiteSpace($target_url)) {
                    $code = "ERROR"
                } else {
                    try {
                        $webreq = [System.Net.WebRequest]::Create($target_url)
                        $webreq.Method = "GET"
                        $webreq.Timeout = 3000
                        $webres = $webreq.GetResponse()
                        $code = [int]($webres.StatusCode)
                        $webres.Close()
                    } catch [System.Net.WebException] {
                        if ($_.Response) {
                            $code = [int]$_.Response.StatusCode
                        } else {
                            $code = "ERROR"
                        }
                    } catch {
                        $code = "ERROR"
                    }
                }
                $buffer = [System.Text.Encoding]::UTF8.GetBytes([string]$code)
                $response.ContentType = "text/plain; charset=utf-8"
            }
            else {
                $filePath = Join-Path $baseDir ($localPath.TrimStart('/'))
                if ($localPath -eq "/") { $filePath = Join-Path $baseDir "index.html" }
                
                if (Test-Path $filePath -PathType Leaf) {
                    $buffer = [System.IO.File]::ReadAllBytes($filePath)
                    $ext = [System.IO.Path]::GetExtension($filePath).ToLower()
                    if ($ext -eq ".css") { $response.ContentType = "text/css" }
                    elseif ($ext -eq ".js") { $response.ContentType = "application/javascript" }
                    elseif ($ext -eq ".html") { $response.ContentType = "text/html; charset=utf-8" }
                    elseif ($ext -eq ".csv") { $response.ContentType = "text/csv; charset=utf-8" }
                } else {
                    $response.StatusCode = 404
                    $buffer = [System.Text.Encoding]::UTF8.GetBytes("File Not Found: " + $filePath)
                }
            }
        }
        
        $response.ContentLength64 = $buffer.Length
        $response.OutputStream.Write($buffer, 0, $buffer.Length)
        $response.Close()
    }
} finally {
    $listener.Stop()
}
