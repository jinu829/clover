param(
    [Parameter(Mandatory = $true)]
    [string]$GarmentCodeRoot
)

$target = (Resolve-Path -LiteralPath $GarmentCodeRoot).Path
if (-not (Test-Path -LiteralPath (Join-Path $target 'assets\design_params\t-shirt.yaml'))) {
    throw "GarmentCodeRoot must be the root of a GarmentCode checkout."
}

$source = $PSScriptRoot
Copy-Item -LiteralPath (Join-Path $source 'generate_from_product_images.py') -Destination (Join-Path $target 'generate_from_product_images.py') -Force
Copy-Item -LiteralPath (Join-Path $source 'assets\product_catalog.json') -Destination (Join-Path $target 'assets\product_catalog.json') -Force

Write-Host "Installed adapter files into $target"
