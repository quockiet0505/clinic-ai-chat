$ErrorActionPreference = "Stop"

Write-Host "=================================================="
Write-Host "STEP 1: ACTIVATE VENV AND INSTALL DEPENDENCIES"
Write-Host "=================================================="
if (Test-Path "..\venv\Scripts\Activate.ps1") {
    . "..\venv\Scripts\Activate.ps1"
} else {
    Write-Host "Venv not found, using system Python." -ForegroundColor Yellow
}

Write-Host "Installing required Python packages for merging..."
pip install torch transformers peft accelerate
if ($LASTEXITCODE -ne 0) {
    Write-Error "Error installing python dependencies."
    exit $LASTEXITCODE
}

Write-Host "`n=================================================="
Write-Host "STEP 2: MERGE MODEL"
Write-Host "=================================================="
Write-Host "Merging model with Python..."
python merge_adapter.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "Error during Python model merge."
    exit $LASTEXITCODE
}

Write-Host "`n=================================================="
Write-Host "STEP 3: CLONE LLAMA.CPP AND CONVERT TO GGUF F16"
Write-Host "=================================================="
cd ..
if (-not (Test-Path "llama.cpp")) {
    Write-Host "Cloning llama.cpp..."
    git clone https://github.com/ggerganov/llama.cpp.git
}

Write-Host "Installing llama.cpp requirements..."
pip install -r llama.cpp/requirements.txt

Write-Host "Converting HF to GGUF F16..."
python llama.cpp/convert_hf_to_gguf.py models/clinic-ai-merged --outfile models/clinic-ai-F16.gguf --outtype f16
if ($LASTEXITCODE -ne 0) {
    Write-Error "Error converting HF to GGUF."
    exit $LASTEXITCODE
}

Write-Host "`n=================================================="
Write-Host "STEP 4: DOWNLOAD QUANTIZE TOOL AND QUANTIZE TO Q4_K_M"
Write-Host "=================================================="
if (-not (Test-Path "llama-bin\llama-quantize.exe")) {
    Write-Host "Fetching latest llama.cpp release for Windows..."
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $release = Invoke-RestMethod -Uri "https://api.github.com/repos/ggerganov/llama.cpp/releases/latest"
    
    $asset = $release.assets | Where-Object { $_.name -match "-bin-win-.*x64.zip$" -and $_.name -notmatch "cu[0-9]" -and $_.name -notmatch "vulkan" } | Select-Object -First 1
    
    if ($asset) {
        Write-Host "Downloading: $($asset.name)"
        Invoke-WebRequest -Uri $asset.browser_download_url -OutFile "llama-bin.zip"
        Write-Host "Extracting..."
        Expand-Archive -Path "llama-bin.zip" -DestinationPath "llama-bin" -Force
        Remove-Item "llama-bin.zip"
    } else {
        Write-Warning "Could not automatically download llama-quantize."
    }
}

if (Test-Path "llama-bin\llama-quantize.exe") {
    Write-Host "Quantizing model to Q4_K_M..."
    .\llama-bin\llama-quantize.exe models/clinic-ai-F16.gguf models/clinic-ai-Q4_K_M.gguf Q4_K_M
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Error running llama-quantize."
        exit $LASTEXITCODE
    }
    Write-Host "`n✅ SUCCESS!" -ForegroundColor Green
    Write-Host "Optimized model saved to: models/clinic-ai-Q4_K_M.gguf" -ForegroundColor Green
} else {
    Write-Host "llama-quantize.exe not found. Stopped at F16 version." -ForegroundColor Yellow
}
