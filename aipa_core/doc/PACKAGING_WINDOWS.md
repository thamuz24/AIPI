# Dong Goi AIPA Thanh App Windows

Tai lieu nay dung cho du an `aipa_core` (Spring Boot) de dong goi thanh app Windows.

## Dieu kien

- Windows
- JDK co `jpackage` (kiem tra: `"%JAVA_HOME%\bin\jpackage.exe" --version`)
- `JAVA_HOME` da tro dung vao JDK
- Neu tao installer `exe/msi`: can cai WiX Toolset va them vao `PATH`

## Lenh nhanh

Tu thu muc goc du an:

```powershell
.\scripts\package-windows.ps1
```

Lenh tren se:

1. Build jar bang Maven wrapper (`mvnw.cmd clean package -DskipTests`)
2. Dong goi bang `jpackage`
3. Tao output tai `release\windows`

Mac dinh script tao dang `app-image`.

## Tao installer EXE

```powershell
.\scripts\package-windows.ps1 -Type exe
```

Neu bi bao loi thieu WiX, cai tai: `https://wixtoolset.org`

## Tao installer MSI

```powershell
.\scripts\package-windows.ps1 -Type msi
```

## Tuy chon hay dung

```powershell
.\scripts\package-windows.ps1 -Type exe -AppName "AIPA" -Vendor "AIPA Team" -AppVersion "1.0.0"
```

Neu muon bo qua buoc build Maven (da co jar san):

```powershell
.\scripts\package-windows.ps1 -SkipBuild
```

Neu co icon `.ico`:

```powershell
.\scripts\package-windows.ps1 -Type exe -IconPath .\assets\aipa.ico
```

## Du lieu DB mac dinh

Ban dong goi dung H2 local voi duong dan mac dinh:

`%USERPROFILE%\.aipa\data\aipa`

Ban van co the doi sang MySQL bang bien moi truong:

- `AIPA_DB_URL`
- `AIPA_DB_DRIVER`
- `AIPA_DB_USERNAME`
- `AIPA_DB_PASSWORD`
