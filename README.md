# Gradio Camera Capture Simple Demo

## Usage

Launch app (Gradio)

```powershell
python .\main.py app
```

Capture image

```powershell
python .\main.py image ./temp/default.jpg
python .\main.py image ./temp/1080p.jpg 0,CAP_DSHOW,1920,1080,30.0
```

Capture Video

```powershell
python .\main.py video ./temp/default.mp4
python .\main.py video ./temp/1080p.mp4 0,CAP_DSHOW,1920,1080,30.0
```
