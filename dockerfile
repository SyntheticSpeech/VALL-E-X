# Use an official Python runtime as a parent image
FROM python:3.10.13

# Set the working directory in the container
WORKDIR /app
COPY . /app

#RUN . venv/bin/activate
# Install any needed packages specified in requirements.txt
RUN apt-get update && pip install --upgrade pip 

# RUN apt-get install -y git
# RUN git clone https://github.com/SyntheticSpeech/VALL-E-X.git 
# WORKDIR /VALL-E-X
# RUN git checkout deploy

RUN pip3 install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
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
