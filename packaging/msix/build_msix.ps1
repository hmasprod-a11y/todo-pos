[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$PortableAppPath,
  [Parameter(Mandatory=$true)][string]$IdentityName,
  [Parameter(Mandatory=$true)][string]$Publisher,
  [Parameter(Mandatory=$true)][string]$PublisherDisplayName,
  [Parameter(Mandatory=$true)][string]$AssetsPath,
  [string]$DisplayName = "ToDo POS",
  [string]$Description = "Offline Point of Sale for Retail & Grocery",
  [string]$Version = "1.1.0.0",
  [string]$OutputPath = "dist\ToDo-POS.msix"
)
$ErrorActionPreference='Stop'
$required=@('StoreLogo.png','Square150x150Logo.png','Square44x44Logo.png')
if(-not (Test-Path (Join-Path $PortableAppPath 'ToDo.exe'))){throw "Portable app must contain ToDo.exe: $PortableAppPath"}
foreach($asset in $required){if(-not (Test-Path (Join-Path $AssetsPath $asset))){throw "Missing required Store asset: $asset"}}
$makeAppx=(Get-Command MakeAppx.exe -ErrorAction SilentlyContinue)
if(-not $makeAppx){throw "MakeAppx.exe was not found. Install the Windows SDK before building MSIX."}
$stage=Join-Path ([IO.Path]::GetTempPath()) ("todo-msix-"+[guid]::NewGuid())
try {
  New-Item -ItemType Directory -Path $stage | Out-Null
  Copy-Item (Join-Path $PortableAppPath '*') $stage -Recurse -Force
  New-Item -ItemType Directory -Path (Join-Path $stage 'Assets') | Out-Null
  Copy-Item (Join-Path $AssetsPath '*') (Join-Path $stage 'Assets') -Force
  $template=Get-Content (Join-Path $PSScriptRoot 'AppxManifest.xml.template') -Raw
  $manifest=$template.Replace('{{IDENTITY_NAME}}',$IdentityName).Replace('{{PUBLISHER}}',$Publisher).Replace('{{PUBLISHER_DISPLAY_NAME}}',$PublisherDisplayName).Replace('{{DISPLAY_NAME}}',$DisplayName).Replace('{{DESCRIPTION}}',$Description).Replace('{{VERSION}}',$Version)
  Set-Content (Join-Path $stage 'AppxManifest.xml') $manifest -Encoding utf8
  $output=Resolve-Path -LiteralPath (Split-Path $OutputPath -Parent) -ErrorAction SilentlyContinue
  if(-not $output){$null=New-Item -ItemType Directory -Path (Split-Path $OutputPath -Parent) -Force}
  & $makeAppx.Source pack /d $stage /p $OutputPath /o
  if($LASTEXITCODE -ne 0){throw "MakeAppx failed with exit code $LASTEXITCODE"}
} finally { if(Test-Path $stage){Remove-Item -LiteralPath $stage -Recurse -Force} }
