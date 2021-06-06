#####################################################
# SIT210 Project - Stovetop Monitor
# SID: 215279167
#
# main.py
#
# Streaming http server source code and classes
# utilised from official PiCamera package
# http://picamera.readthedocs.io/en/latest/recipes2.html#web-streaming
#
#####################################################

from stove_metrics import StoveMetrics

import picamera
import os
import io
import json
import logging
import socketserver
import time
import threading
import RPi.GPIO as GPIO
from google.cloud import pubsub_v1
from datetime import datetime
from time import sleep
from gpiozero import LED
from pathlib import Path
from threading import Condition
from http import server


logging.basicConfig(level=logging.INFO)

PAGE = Path('index.html').read_text()
TEMP_THRESHOLD = 30 # degrees 
ALARM_DURATION_THRESHOLD = 10 # minutes

# define leds and buzzer pin
led_green = LED(4)
led_red = LED(27)
buzzer = 17

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(buzzer, GPIO.OUT, initial=GPIO.LOW)

# set GCP project setting and create pubsub client
project_id = os.getenv('GCP_PROJECT_ID')
subscription_id = os.getenv('GCP_TOPIC_SUB_ID')
subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(project_id, subscription_id)

# create single instance of StoveMetrics class
metrics = StoveMetrics()

class StreamingOutput(object):
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            # New frame, copy the existing buffer's content and notify all
            # clients it's available
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()
            self.buffer.seek(0)
        return self.buffer.write(buf)

class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/metrics':
            metrics_list = metrics.get_rolling_metrics()            
            payload = json.dumps(metrics_list)
            content = payload.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
        else:
            self.send_error(404)
            self.end_headers()

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

def event_callback(message):  
    if message.data:
        logging.info('Event received: %s', message.data)
        msg = json.loads(message.data)
        
        # convert published time from UTC to local time
        pub_time = message.publish_time
        now_timestamp = time.time()
        offset = datetime.fromtimestamp(now_timestamp) - datetime.utcfromtimestamp(now_timestamp)      
        event_time = pub_time + offset
        
        metrics.set_metrics(msg['temp'], msg['hum'], msg['dist'], event_time.replace(tzinfo=None))
    message.ack()

def event_subscriber():
    with subscriber:
        try:
            future.result()
        except KeyboardInterrupt:
            future.cancel()
               
def alarm_status_processor():
    # trigger metric holds initial event greater than threshold
    trigger_metric = [0, 0, 0, datetime.now()]
    alarm_level_1_on = False
    alarm_level_2_on = False
    while True:
        latest_metric = metrics.get_avg_metrics()
        temp = latest_metric[0]
        evt_time = latest_metric[3]

        # determine alarm level
        if temp > TEMP_THRESHOLD:
            if alarm_level_1_on:
                diff = evt_time - trigger_metric[3]
                diff_min = diff.total_seconds() / 60
                if diff_min > ALARM_DURATION_THRESHOLD:
                    alarm_level_2_on = True
                else:
                    alarm_level_2_on = False
            else:
                trigger_metric = latest_metric
                alarm_level_1_on = True            
        else:
            trigger_metric = [0, 0, 0, datetime.now()]
            alarm_level_1_on = False
            alarm_level_2_on = False
            
        # set led, buzzer and UI status based on determined alarm level
        if alarm_level_1_on:
            led_green.off()
            led_red.on()
            if alarm_level_2_on:
                GPIO.output(buzzer, GPIO.HIGH)
                metrics.set_health_status(2)
            else:
                GPIO.output(buzzer, GPIO.LOW)
                metrics.set_health_status(1)
        else:
            led_green.on()
            led_red.off()
            metrics.set_health_status(0)
        sleep(0.1)
        
        # pause to flash off
        led_green.off()
        led_red.off()
        GPIO.output(buzzer, GPIO.LOW)
        sleep(0.9)        


if __name__=="__main__":    
    future = subscriber.subscribe(subscription_path, callback=event_callback)
    event_consumer = threading.Thread(target=event_subscriber)
    alarm_status_monitor = threading.Thread(target=alarm_status_processor)
    
    # start event consumer and alarm status processing on different threads
    event_consumer.start()
    alarm_status_monitor.start()
    
    # start http server with streaming video
    with picamera.PiCamera() as camera:
        camera.resolution = (640, 480)
        camera.framerate = 24
        output = StreamingOutput()
        camera.start_recording(output, format='mjpeg')        
        try:
            address = ('', 8000)
            server = StreamingServer(address, StreamingHandler)
            server.serve_forever()
        finally:
            camera.stop_recording()
