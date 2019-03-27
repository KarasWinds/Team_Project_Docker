
#!/bin/bash

yum update -y

username="gcp-user"

yum -y install git wget
yum install -y nano vim
adduser $username
usermod -a -G wheel $username

## install docker
curl -fsSL get.docker.com -o get-docker.sh
sudo sh get-docker.sh

sudo systemctl start docker.service
sudo systemctl enable docker.service

sudo usermod -aG docker $username

curl -L "https://github.com/docker/compose/releases/download/1.23.1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

## pull line chatbot from github
cd /home/$username/
git clone https://github.com/KarasWinds/Team_Project_Docker.git
sleep 5
docker-compose -f /home/$username/Team_Project_Docker/docker-compose.yml up -d

# create secret_key
sleep 5
curl -s "localhost:4040/api/tunnels" | awk -F',' '{print $3}' | awk -F'"' '{print $4}' | awk -F'//' '{print $2}' > NURL 
NURL=`cat ./NURL`
cat << EOF > /home/$username/Team_Project_Docker/py_code/material/line_secret_key
{
 "channel_access_token":"",
  "secret_key":"",
  "self_user_id":"",
  "rich_menu_id":"",
  "server_url":"$NURL"
}
EOF
rm -f ./NURL

chown -R $username Team_Project_Docker/
chmod 777 -R Team_Project_Docker/*