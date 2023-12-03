Reference: [Plachtaa VALL-E-X](https://github.com/Plachtaa/VALL-E-X)
# How to Run
- Get a virtual environment, python version 3.10
  ```conda create --name x python=3.10```
- Install flask
  ```pip install flask```
- Install requirements for VALL-E-X
  ```pip install -r requirements.txt```
- Install ffmpeg for whisper
  - On MAC, use brew, or conda
  - On Linux, use apt-get -y install ffmpeg
  Note: Whisper fixed as version 20230314, it needs both ffmpeg and ffmpeg-python

- Run ```python app.py -m flask run --host 0.0.0.0 ```