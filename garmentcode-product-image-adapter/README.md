# GarmentCode Product-Image Adapter

This repository contains the code added on top of the upstream
[GarmentCode](https://github.com/maria-korosteleva/GarmentCode) project. It is
deliberately a small adapter repository, not a re-upload of GarmentCode.

The adapter accepts front/back product reference images and a size-chart image,
creates a reviewable parsed size table, maps flat chest width to GarmentCode
panels, and exports one validated pattern for every detected size row.

## What this repository does not include

- The upstream GarmentCode source. Clone and install it separately.
- Product photographs or size-chart images. Do not publish them unless you own
  the rights to redistribute them.
- A fabricated 3D mesh. GarmentCode's Warp simulator is an optional separate
  dependency; without it the adapter exports 2D patterns and 3D panel
  placement only.

## Install into a local GarmentCode clone

```powershell
git clone https://github.com/maria-korosteleva/GarmentCode.git GarmentCode-main
cd garmentcode-product-image-adapter
.\install_into_garmentcode.ps1 -GarmentCodeRoot ..\GarmentCode-main
```

Then follow GarmentCode's own Python and simulator installation instructions,
and install the adapter extras:

```powershell
cd ..\GarmentCode-main
python -m pip install -r ..\garmentcode-product-image-adapter\requirements.txt
```

## Run a reviewed local item

```powershell
python generate_from_product_images.py `
  --catalog-id A `
  --catalog-root "../옷 파일/옷 파일" `
  --output outputs/A
```

`assets/product_catalog.json` is a visual review of the local A--T product
sets. It rejects unsupported construction (for example, raglan sleeves sent to
a set-in-sleeve template) rather than silently generating the wrong garment.

## Before publishing

Add the licence you want for your adapter code and verify that the remote
repository's description clearly states that it depends on GarmentCode.
Upstream GarmentCode is MIT-licensed; retain its licence and attribution when
using or distributing upstream files.
