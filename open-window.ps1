param(
    [Parameter(Mandatory=$true)][int]$BrowserProcessId,
    [Parameter(Mandatory=$true)][long]$WindowHandle
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
Write-Output ("Foreground window before Ctrl+N: " + [CanaryWindow]::GetForegroundWindow().ToInt64())
$shell.SendKeys('^n')
Write-Output 'Sent native Windows Ctrl+N to the disposable Zen process'
