$ErrorActionPreference = 'Stop'
$privateKey = Read-Host 'DeepSeek API Key (hidden; this service only)' -AsSecureString
$keyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($privateKey)
try {
    $env:DEEPSEEK_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPointer)
    Push-Location $PSScriptRoot
    try {
        & '.\.venv\Scripts\python.exe' control-plane-python/run_console.py --provider deepseek --port 8767
    } finally {
        Pop-Location
    }
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer)
    Remove-Item Env:DEEPSEEK_API_KEY -ErrorAction SilentlyContinue
    $privateKey.Dispose()
}
