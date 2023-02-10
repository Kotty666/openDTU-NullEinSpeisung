#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}"  )" &> /dev/null && pwd  )
SERVICE_NAME=$(basename $SCRIPT_DIR)

# Set permissions
chmod +x $SCRIPT_DIR/nulleinspeisung.py

PIP3=$(which pip3)
ME=$(whoami)

echo 'Installing Needed packages'
if [ -z $PIP3 ]; then
  sudo apt update
  sudo apt -y install python3-pip
fi
sudo pip install pyyaml requests

# create serviceFile
cat << EOF | sudo tee /usr/lib/systemd/system/nulleinspeisung.service
[Unit]
Description=Nulleinspeisung Service
After=multi-user.target

[Service]
Type=simple
Restart=always
ExecStart=/usr/bin/python3 ${SCRIPT_DIR}/nulleinspeisung.py
WorkingDirectory=${SCRIPT_DIR}
User=${ME}

[Install]
WantedBy=multi-user.target
EOF
sudo chmod 644 /usr/lib/systemd/system/nulleinspeisung.service
sudo systemctl daemon-reload
sudo systemctl enable nulleinspeisung.service
sudo systemctl start nulleinspeisung.service
sudo systemctl status nulleinspeisung.service

echo "Installation Done"
