# Team_Project_Docker
---
## ---version->0327-v1---<br>

### 1.docker安裝程序在install_Docker資料夾中<br>
### 2.jupyter工作目錄檔案請放至py_code資料夾中<br>
### 3.jupyter預設安裝套件如下:<br>
    (1)Flask(0.12)
    (2)requests
    (3)line-bot-sdk
    (4)kafka-python
    (5)sklearn
    (6)pandas
    (7)numpy
    (8)mysql-connector
    (9)urllib3
    (10)bs4
    (11)pymongo
    (12)logstash
    (13)elasticsearch
    (14)redis
    (15)python-dotenv

#### GCP-Auto-Start.sh
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
