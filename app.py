import os
import time
from flask import Flask, render_template, request, send_file, redirect, send_from_directory, url_for
from werkzeug.utils import secure_filename
from scipy.io.wavfile import write as write_wav

from utils.generation import download_models, generate_audio, generate_audio_from_long_text, load_model
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

@app.route('/generate', methods=['POST'])
def upload_file():
    if 'audioPrompt' not in request.files:
        print(f"Uploaded file was not found. Please check the path of the uploaded file")
        return redirect(request.url)

    name = request.form.get('name')
    text_prompt = request.form.get('textPrompt')
    file = request.files['audioPrompt']
    model_option = request.form.get('modelOption')

    if name == "":
        return render_template('error.html', error_message="Name not found.")

    if text_prompt == "":
        return render_template('error.html', error_message="Text not found.")

    if model_option == "":
        model_option = "pretrain"

    print(f"name: {name}, text: {text_prompt}, file: {file}, model : {model_option}")
    load_model(model_option=model_option)

    t1 = time.perf_counter(), time.process_time()
    if file.filename != '':
        if name in saved_prompts:
            return render_template('error.html', error_message="Speaker name exists.")
        if not (file and allowed_file(file.filename)):
            return render_template('error.html', error_message="Audio prompt file extension not supported")

        t_m_s = time.perf_counter(), time.process_time()
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        print(filepath)
        make_prompt(name=name, audio_prompt_path=filepath)
        saved_prompts.add(name)
        t_m_e = time.perf_counter(), time.process_time()
        print(f"[make_prompt] Real time: {t_m_e[0] - t_m_s[0]:.2f} seconds")
        print(f"[make_prompt] CPU time: {t_m_e[1] - t_m_s[1]:.2f} seconds")
    else:
        print(f"Using preset speaker prompt {name}")

    t_g_s = time.perf_counter(), time.process_time()
    audio_array = generate_audio(text_prompt, prompt=name)
    t_g_e = time.perf_counter(), time.process_time()
    print(f"[generate_audio] Real time: {t_g_e[0] - t_g_s[0]:.2f} seconds")
    print(f"[generate_audio] CPU time: {t_g_e[1] - t_g_s[1]:.2f} seconds")

    t_w_s = time.perf_counter(), time.process_time()
    write_wav("static/cloned.wav", 24000, audio_array)
    # synthetic_audio_path = os.path.abspath("cloned.wav")
    t_w_e = time.perf_counter(), time.process_time()
    print(f"[write_wav] Real time: {t_w_e[0] - t_w_s[0]:.2f} seconds")
    print(f"[write_wav] CPU time: {t_w_e[1] - t_w_s[1]:.2f} seconds")

    t2 = time.perf_counter(), time.process_time()
    print(f"[Inference] Real time: {t2[0] - t1[0]:.2f} seconds")
    print(f"[Inference] CPU time: {t2[1] - t1[1]:.2f} seconds")
    # print(f"Generated audio file path: {synthetic_audio_path}")
    
    # Extract the directory and filename separately
    # directory, filename = os.path.split(synthetic_audio_path)
    synthetic_audio_path = "cloned.wav"

    # Use send_from_directory to send the file without the full path
    # return send_from_directory(directory, filename, as_attachment=True)
    return redirect(url_for('play_audio', audio_path=synthetic_audio_path))

@app.route('/play')
def play_audio():
    audio_path = request.args.get('audio_path')
    return render_template('play_audio.html', audio_path=audio_path)


@app.route('/back')
def back_to_home():
    return render_template('index.html')

def init():
    # read all preset prompts
    for filename in os.listdir("./presets"):
        if os.path.isfile(os.path.join("./presets", filename)):
            saved_prompts.add(os.path.splitext(os.path.basename(filename))[0])

    t1 = time.perf_counter(), time.process_time()
    download_models()
    download_whisper()
    t2 = time.perf_counter(), time.process_time()
    print(f"[Init] Real time: {t2[0] - t1[0]:.2f} seconds")
    print(f"[Init] CPU time: {t2[1] - t1[1]:.2f} seconds")

if __name__ == "__main__":
    init()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000))) #debug=True
