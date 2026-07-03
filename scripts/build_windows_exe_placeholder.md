# Windows build target

Future implementation:

```powershell
py -m pip install pyinstaller
pyinstaller --onefile --name Atlas app/main.py
```

Target release layout:

```text
Atlas-v0.x-Windows/
├── Atlas.exe
├── data/
│   └── atlas.db
├── backups/
└── README.txt
```
