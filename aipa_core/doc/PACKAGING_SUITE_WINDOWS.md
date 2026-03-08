# Dong Goi AIPA All-In-One (core + client + controll)

Tai lieu nay dong goi mot app image Windows gom:

- `aipa_core` (Spring Boot)
- `aipa_client` (frontend build)
- `aipa_controll` (FastAPI service)

## Dieu kien

- Windows
- `JAVA_HOME` tro dung JDK co `jpackage`
- Python 3 tren may dich (de `aipa_controll\run_aipa_all.bat` tao `.venv` lan dau)
- Internet lan dau chay de pip cai dependencies cho `aipa_controll` (neu chua co san)
- Neu muon build lai frontend: Node.js + npm

## Dong goi nhanh

Tu thu muc `aipa_core`:

```powershell
.\scripts\package-suite-windows.ps1
```

Lenh tren se:

1. Dong goi `aipa_core` thanh `release\windows\AIPA`
2. Copy `..\aipa_client\build` vao `release\windows\AIPA\app\client`
3. Copy `..\aipa_controll` vao `release\windows\AIPA\app\controll` (bo qua `.venv`, `tmp`, `__pycache__`)
4. Bat desktop mode trong `AIPA.exe` (tu khoi dong `aipa_controll`, mo cua so app va tu tat khi dong cua so)
5. Xuat bo cai doc lap ra thu muc `..\AIPA_App` (ngoai `aipa_core`)

## Build lai frontend truoc khi dong goi

```powershell
.\scripts\package-suite-windows.ps1 -BuildClient
```

## Cach chay ban dong goi

```powershell
cd ..\AIPA_App
.\AIPA.exe
```

Khi dong cua so app, backend se tu dung.

## Doi thu muc output

```powershell
.\scripts\package-suite-windows.ps1 -OutputDir "D:\dist\AIPA_App"
```

## Ghi chu ky thuat

- `aipa_core` phuc vu static frontend tu `./app/client`.
- Script dong goi patch `chat_server.py` trong ban copy de cho phep origin `http://localhost:8080` va `http://127.0.0.1:8080`.
