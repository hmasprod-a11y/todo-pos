# MSIX packaging for Microsoft Store

ToDo POS keeps the tested ZIP and Setup installer for direct distribution. The
Store package is built from the same PyInstaller portable output and therefore
does not create another runtime or database location.

## Required publisher inputs

Do not replace these with guessed values. Get them from Partner Center after the
Store product is reserved:

- Store identity name
- Publisher subject (for example `CN=...`) matching that identity
- Publisher display name
- Official PNG assets: `StoreLogo.png`, `Square150x150Logo.png`, and
  `Square44x44Logo.png`

## Build

On a Windows machine with the Windows SDK (`MakeAppx.exe`) installed, first
run the normal Windows build so `dist\ToDo` exists. Then run:

```powershell
./packaging/msix/build_msix.ps1 \
  -PortableAppPath dist\ToDo \
  -IdentityName "<Partner Center identity>" \
  -Publisher "<Partner Center publisher>" \
  -PublisherDisplayName "<publisher name>" \
  -AssetsPath <official-assets-folder> \
  -OutputPath dist\ToDo-POS.msix
```

The script fails before packaging if the executable, identity inputs, SDK or
official assets are missing. Sign the output according to the Store submission
workflow; never put a private certificate in the repository.
