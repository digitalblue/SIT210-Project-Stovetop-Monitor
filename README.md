# SIT210 Project - Stovetop Monitor

# Overview
The Stovetop Monitor project is a collection of embedded systems to monitor a gas stovetop and provide alarm status if stovetop temperature is detected to be over a set threshold and time frame.

The system makes use of Google Cloud Platform (GCP) Pubsub topic integrated into the Particle environment, along with a Raspberry Pi to handle the processing.

Highlevel system flow:
* Particle Argon publishes sensor event data to a Pubsub topic on GCP
* Raspberry Pi subscribes to this topic and consumes sensor event data
* The Pi handles event processing and alarm status logic
* The Pi also provides a http server with dashboard to user. This provides realtime rolling metrics and video streaming of stovetop

![alt text](Stovetop_monitor_dashboard.png "Dashboard")

## Components
Hardware
* Particle Argon
* DHT22 Temperature/Humidity sensor
* HC-SR04 Ultrasonic range/distance sensor
* Raspberry Pi
* PiCamera
* Green and Red LEDs
* Buzzer

Software - This repository contains source code for
* Particle Argon `.ino` file and `.properties`
* Python and html code for Raspberry Pi

Additional services
* Particle Console Integration environment
* Google Cloud Platform - PubSub

## Run application

Hardware setup
1. Connect DHT22 and Ultrasonic sensor to Particle Argon - refer to `stovetop-monitor.ino` file for pin connections
2. Connect Green, Red LEDs and buzzer to Raspberry Pi - refer to `main.py` file for pin connections
3. Connect PiCamera to Raspberry Pi

Google Cloud Platform (GCP)
1. Log into GCP and create project, topic and topic subscription - check this link for more info https://cloud.google.com/pubsub/docs/quickstart-console
2. Create service account with permissions to subscribe to the topic
3. Download service account credentials file - this should be in JSON format

Particle
1. Log into Particle Console
2. Create Google Cloud Platform integration using Google Project Id and Pubsub topic name
3. Upload Particle code into Particle online IDE
4. Flash to Particle device

Raspberry Pi
1. Clone this repo onto Raspberry Pi
2. Copy GCP service account credentials file to Raspberry Pi
3. Create and activate python virtual environment - use `requirements.txt` for dependencies
4. Export GCP project id, topic subcription and credentials into environment variables
```
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credential/my-project-1234.json"
export GCP_PROJECT_ID="my-project"
export GCP_TOPIC_SUB_ID="my-topic-sub"
```
5. Change directory and run application
```
cd stovetop_monitor
python main.py
```
6. Open dashboard in browser at `127.0.0.1:8000` 


## Tests
Run unit tests from root directory
```
python -m unittest test.stove_metrics_test
```

On GCP Console
* Confirm events are published to topic from Paricle Argon
* Confirm events are acknowledged and consumed in topic subscription from Raspberry Pi
