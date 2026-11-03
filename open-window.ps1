param([Parameter(Mandatory=$true)][int]$BrowserProcessId)
$ErrorActionPreference = 'Stop'
$shell = New-Object -ComObject WScript.Shell
if (-not $shell.AppActivate($BrowserProcessId)) {
    throw 'Could not activate the disposable Zen process'
}
Start-Sleep -Milliseconds 300
$shell.SendKeys('^n')
Write-Output 'Sent native Windows Ctrl+N to the disposable Zen process'
