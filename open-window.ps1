param(
    [Parameter(Mandatory=$true)][int]$BrowserProcessId,
    [long]$WindowHandle = 0,
    [string]$NavigateNewTab = '',
    [switch]$NewTabOnly
)
$ErrorActionPreference = 'Stop'
$shell = New-Object -ComObject WScript.Shell
if (-not $shell.AppActivate($BrowserProcessId)) {
    throw 'Could not activate the disposable Zen process'
}
Start-Sleep -Milliseconds 300
if ($WindowHandle -ne 0) {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class CanaryWindow {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr handle);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
}
'@
    [CanaryWindow]::SetForegroundWindow([IntPtr]$WindowHandle) | Out-Null
    Start-Sleep -Milliseconds 200
    if ([CanaryWindow]::GetForegroundWindow().ToInt64() -ne $WindowHandle) {
        throw 'Could not focus the requested disposable Zen window'
    }
}
if ($NewTabOnly) {
    $shell.SendKeys('^t')
    Write-Output 'Sent native New Tab shortcut to the requested Zen window'
    exit 0
}
if ($NavigateNewTab) {
    if ($NavigateNewTab -notmatch '^http://127\.0\.0\.1:[0-9]+/[a-z-]+$') {
        throw 'Only a simple loopback fixture URL is allowed'
    }
    $shell.SendKeys('^t')
    $shell.SendKeys('^l')
    $shell.SendKeys($NavigateNewTab)
    $shell.SendKeys('{ENTER}')
    Write-Output "Opened fixture through native New Tab and address bar: $NavigateNewTab"
    exit 0
}
$shell.SendKeys('^n')
Write-Output 'Sent native Windows Ctrl+N to the disposable Zen process'
