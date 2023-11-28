import os
from flask import Flask, render_template, request, send_file, redirect, send_from_directory
from utils.script import generate_synthetic_audio
from werkzeug.utils import secure_filename

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
    if 'file' not in request.files:
        print(f"Uploaded file was not found. Please check the path of the uploaded file")
        return redirect(request.url)

    file = request.files['file']

    if file.filename == '':
        # Handle the case where the file has no selected file
        print(f"the file directory is empty")
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        text_prompt = """
        Hey, Traveler, Listen to this, This machine has taken my voice, and now it can talk just like me!
        """
        synthetic_audio_path = generate_synthetic_audio(text_prompt, uploaded_file_path=filepath)

        print(f"Generated audio file path: {synthetic_audio_path}")
        
        # Extract the directory and filename separately
        directory, filename = os.path.split(synthetic_audio_path)

        # Use send_from_directory to send the file without the full path
        return send_from_directory(directory, filename, as_attachment=True)
    else:
        # Handle the case where the file has an invalid extension
        return redirect(request.url)

#if __name__ == '__main__':
#    app.run(debug=True)

if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", 5000)))
