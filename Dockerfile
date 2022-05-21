
FROM python:3.8-buster

RUN apt-get update && apt-get install -y git

RUN git clone https://github.com/nirbarazida/ANPR-AWS.git && cd ANPR-AWS && pip3 install --upgrade pip && pip install -r requirements.txt

CMD ["sh","-c","cd ANPR-AWS && export FLASK_APP=app/app.py && python3 -m flask run --host=0.0.0.0"]


sudo snap install docker
sudo docker run nirbarazida/anpr


sudo snap install docker         
sudo apt  install docker.io      
sudo apt  install podman-docke