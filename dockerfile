# Use an official Python runtime as a parent image
FROM python:3.10.11

# Set the working directory in the container
WORKDIR /valle_app
COPY . .

#RUN . venv/bin/activate
# Install any needed packages specified in requirements.txt
#RUN pip3 uninstall ffmpeg
#RUN pip3 uninstall ffmpeg-python
RUN apt-get update && pip3 install --upgrade pip 
RUN pip3 install flask
RUN apt-get -y install ffmpeg
RUN pip3 install -r requirements.txt

# Make port 80 available to the world outside this container
EXPOSE 5000
# Define environment variable
ENV NAME World
# Run app.py when the container launches
ENTRYPOINT ["python3"]
CMD ["app.py", "-m", "flask", "run", "--host=0.0.0.0"]
#CMD ["python3", "-m", "flask", "run", "--host=0.0.0.0"]
