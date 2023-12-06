# CPU version, just use python base image
# FROM python:3.10.13

# GPU version, use a torch cuda driver base image
FROM pytorch/pytorch:2.1.1-cuda12.1-cudnn8-runtime

# Set the working directory in the container
WORKDIR /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN apt-get update && pip install --upgrade pip 

# Needed it if using the repository from github
# RUN apt-get install -y git
# RUN git clone https://github.com/SyntheticSpeech/VALL-E-X.git 
# WORKDIR /VALL-E-X
# RUN git checkout deploy

# CPU version of torch and torchaudio
# RUN pip3 install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
# GPU version of torch and torchaudio
RUN pip3 install torch torchaudio

RUN pip3 install -r requirements_light.txt
RUN pip3 install flask
RUN apt-get -y install ffmpeg

# Make port 80 available to the world outside this container
EXPOSE 5000
# Define environment variable
ENV NAME World
# Run app.py when the container launches
ENTRYPOINT ["python3"] 
CMD ["app.py", "-m", "flask", "run"]
#CMD ["app.py", "-m", "flask", "run", "--host=0.0.0.0"]
