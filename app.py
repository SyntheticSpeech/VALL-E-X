import os
import time
from flask import Flask, render_template, request, send_file, redirect, send_from_directory
from werkzeug.utils import secure_filename
from scipy.io.wavfile import write as write_wav

from utils.generation import preload_models, generate_audio, generate_audio_from_long_text
from utils.prompt_making import make_prompt, download_whisper

saved_prompts = set()

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

app.config['UPLOAD_FOLDER'] = 'uploads'
ALLOWED_EXTENSIONS = {'wav'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'audioPrompt' not in request.files:
        print(f"Uploaded file was not found. Please check the path of the uploaded file")
        return redirect(request.url)

    name = request.form.get('name')
    text_prompt = request.form.get('textPrompt')
    file = request.files['audioPrompt']

    if name == "":
        print("Name not found.")
        return redirect(request.url)

    if text_prompt == "":
        print("Text not found.")
        return redirect(request.url)

    print(f"name: {name}, text: {text_prompt}, file: {file}")

    if file.filename == '':
        # Handle the case where the file has no selected file
        print(f"the file directory is empty")
        return redirect(request.url)

    if not (file and allowed_file(file.filename)):
        # Handle the case where the file has an invalid extension
        return redirect(request.url)

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    print(filepath)
    t1 = time.perf_counter(), time.process_time()
    if name not in saved_prompts:
        t_m_s = time.perf_counter(), time.process_time()
        make_prompt(name=name, audio_prompt_path=filepath)
        saved_prompts.add(name)
        t_m_e = time.perf_counter(), time.process_time()
        print(f"[make_prompt] Real time: {t_m_e[0] - t_m_s[0]:.2f} seconds")
        print(f"[make_prompt] CPU time: {t_m_e[1] - t_m_s[1]:.2f} seconds")

    t_g_s = time.perf_counter(), time.process_time()
    audio_array = generate_audio(text_prompt, prompt=name)
    t_g_e = time.perf_counter(), time.process_time()
    print(f"[generate_audio] Real time: {t_g_e[0] - t_g_s[0]:.2f} seconds")
    print(f"[generate_audio] CPU time: {t_g_e[1] - t_g_s[1]:.2f} seconds")

    t_w_s = time.perf_counter(), time.process_time()
    write_wav("cloned.wav", 24000, audio_array)
    synthetic_audio_path = os.path.abspath("cloned.wav")
    t_w_e = time.perf_counter(), time.process_time()
    print(f"[write_wav] Real time: {t_w_e[0] - t_w_s[0]:.2f} seconds")
    print(f"[write_wav] CPU time: {t_w_e[1] - t_w_s[1]:.2f} seconds")

    t2 = time.perf_counter(), time.process_time()
    print(f"[Inference] Real time: {t2[0] - t1[0]:.2f} seconds")
    print(f"[Inference] CPU time: {t2[1] - t1[1]:.2f} seconds")
    print(f"Generated audio file path: {synthetic_audio_path}")
    
    # Extract the directory and filename separately
    directory, filename = os.path.split(synthetic_audio_path)

    # Use send_from_directory to send the file without the full path
    return send_from_directory(directory, filename, as_attachment=True)


def init():
    t1 = time.perf_counter(), time.process_time()
    preload_models()
    download_whisper()
    t2 = time.perf_counter(), time.process_time()
    print(f"[Init] Real time: {t2[0] - t1[0]:.2f} seconds")
    print(f"[Init] CPU time: {t2[1] - t1[1]:.2f} seconds")

if __name__ == "__main__":
    init()
    app.run(port=int(os.environ.get("PORT", 5000))) #debug=True
