apt-get update --allow-releaseinfo-change
apt-get install git -y
apt-get install python3-pip -y
apt-get install build-essential -y
git config --global user.name "NorwegianGoat"
git config --global user.email riccardomioli@gmail.com
git clone https://NorwegianGoat@github.com/NorwegianGoat/edge_utils.git
cd edge_utils
pip3 install -r requirements.txt
python3 helper.py init
git config credential.helper store
git pull
