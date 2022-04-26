sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt install python3-pip -y
sudo pip3 install --upgrade pip
git clone https://github.com/nirbarazida/ANPR-AWS.git
cd ANPR-AWS
pip3 install -r requirements.txt
export FLASK_APP=app/app.py
python3 -m flask run --host=0.0.0.0
