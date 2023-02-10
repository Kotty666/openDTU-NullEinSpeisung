#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}"  )" &> /dev/null && pwd  )
SERVICE_NAME=$(basename $SCRIPT_DIR)

# Set permissions
chmod +x $SCRIPT_DIR/nulleinspeisung.py

echo 'Installing Needed packages'
sudo apt update
sudo apt -y install python3-pip
sudo pip install pyyaml requests

# create serviceFile
cat << EOF | sudo tee /usr/lib/systemd/system/nulleinspeisung.service
[Unit]
Description=Nulleinspeisung Service
After=multi-user.target
[Service]
Type=simple
Restart=always
ExecStart=/usr/bin/python3 $SCRIPT_DIR/nulleinspeisung.py
[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable nulleinspeisung.service
sudo systemctl start nulleinspeisung.service
sudo systemctl status nulleinspeisung.service

echo "Installation Done"
