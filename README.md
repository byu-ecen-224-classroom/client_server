# Client Lab Server

This is the server that the students' clients connect to in the Client Lab for ECEn 224.

## Setup

```bash
python3 -m venv ./.venv         # Create virtual environment
source .venv/bin/activate       # Activate virtual environment
pip install -r requirements.txt # Install dependencies
mkdir photos                    # Make the folder for photos
python app.py                   # Run the server
```

This create two servers:

  - The image server that the clients connect to to upload their images. This runs on port 2240.
    
  - The web server that students can view their images. This runs on port 2241.

The web server stores students' images based on their homework IDs (as reported in LS). For example, if a student's homework ID was ABC123456, then they would navigate to `http://ecen224.byu.edu:2241/ABC123456` (assuming the host is ecen224.byu.edu).

Between semesters, you might need to delete the photos folder, except for `photos/123456789`.

## Running in the Background

You can install a systemd service to have the server run on start up and restart automatically if it crashes. The file is `client_lab_server.service` and can be installed running the following commands:

```bash
sudo cp client_lab_server.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start client_lab_server.service   # Start service
sudo systemctl enable client_lab_server.service  # Have service run on boot

```
