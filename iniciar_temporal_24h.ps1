# Prende el servidor local + un tunel publico temporal (Cloudflare Quick
# Tunnel, sin necesidad de cuenta) por 24 horas, y despues cierra todo solo.
# Variante de iniciar_temporal_2h.ps1 (misma logica, solo cambia la
# duracion) -- pedido explicito del usuario para compartir acceso desde
# cualquier dispositivo/lugar por un dia entero. No es parte de la app --
# es un script de un solo uso, no pensado para dejar corriendo mas alla de
# esas 24 horas.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$logTunel = "$PSScriptRoot\tunel_temporal.log"
$urlFile = "$PSScriptRoot\tunel_temporal_url.txt"
Remove-Item $logTunel, $urlFile -ErrorAction SilentlyContinue

# 1) Servidor local (si no hay uno corriendo ya en el 5000).
$yaCorriendo = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue
if (-not $yaCorriendo) {
    Start-Process -FilePath ".\venv\Scripts\python.exe" -ArgumentList "app.py" -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

# 2) Tunel publico temporal apuntando al servidor local.
$tunel = Start-Process -FilePath "$PSScriptRoot\cloudflared.exe" `
    -ArgumentList "tunnel", "--url", "http://localhost:5000" `
    -RedirectStandardError $logTunel -PassThru -WindowStyle Hidden

# Cloudflared tarda unos segundos en asignar la URL publica -- se espera a
# que aparezca en el log en vez de un tiempo fijo a ciegas.
$url = $null
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 1
    if (Test-Path $logTunel) {
        $match = Select-String -Path $logTunel -Pattern "https://[a-zA-Z0-9\-]+\.trycloudflare\.com" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($match) {
            $url = $match.Matches[0].Value
            break
        }
    }
}
if ($url) {
    Set-Content -Path $urlFile -Value $url -Encoding utf8
} else {
    Set-Content -Path $urlFile -Value "ERROR: no se pudo obtener la URL" -Encoding utf8
}

# 3) Cierra el tunel solo despues de 24 horas (el servidor local se deja
# corriendo -- eso lo sigue manejando iniciar.bat como siempre).
Start-Sleep -Seconds 86400
Stop-Process -Id $tunel.Id -Force -ErrorAction SilentlyContinue
Set-Content -Path $urlFile -Value "EXPIRADO" -Encoding utf8
