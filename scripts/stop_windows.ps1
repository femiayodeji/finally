<#
.SYNOPSIS
    FinAlly — stop script (Windows PowerShell).
.DESCRIPTION
    Stops and removes the running container. Does NOT remove the data
    volume, so the portfolio/watchlist persist across restarts. Idempotent.
#>

$ContainerName = "finally-app"

$existing = docker ps -a --format "{{.Names}}" | Select-String -Pattern "^$ContainerName$" -Quiet
if ($existing) {
    Write-Host "Stopping $ContainerName..."
    docker stop $ContainerName *> $null
    docker rm $ContainerName *> $null
    Write-Host "Stopped. Data volume 'finally-data' preserved."
} else {
    Write-Host "$ContainerName is not running."
}
