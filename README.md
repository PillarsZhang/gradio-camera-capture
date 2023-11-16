# Gradio Camera Capture Simple Demo

## Usage

```powershell
pip install -r requirements.txt
```

---

Launch app (Gradio)

```powershell
python .\main.py app
```

---

Capture image

```powershell
python .\main.py image ./temp/default.jpg
python .\main.py image ./temp/1080p.jpg 0,CAP_DSHOW,1920,1080,30.0
```

---

Capture Video

```powershell
python .\main.py video ./temp/default.mp4
python .\main.py video ./temp/1080p.mp4 0,CAP_DSHOW,1920,1080,30.0
```

## Package

**TL;DR**

```powershell
pip install pyinstaller
pyinstaller .\gradio-camera-capture.spec
```

---

**Tip: How to Package Gradio with PyInstaller?**

1. Generate a spec file (same as pyinstaller). [Reference](https://pyinstaller.org/en/stable/spec-files.html#using-spec-files)

   ```powershell
   pyi-makespec --collect-data=gradio_client --collect-data=gradio name.py
   ```

2. Completely bypass PYZ for gradio. [Reference](https://github.com/pyinstaller/pyinstaller/issues/8108#issuecomment-1814076207)

   ```python
   a = Analysis(
       ...
       module_collection_mode={
           'gradio': 'py',  # Collect gradio package as source .py files
       },
   )
   ```

3. Finally, generate the executable.

   ```powershell
   pyinstaller name.spec
   ```
