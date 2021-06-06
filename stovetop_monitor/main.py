from stove_metrics import StoveMetrics

import picamera
from concurrent.futures import TimeoutError
from google.cloud import pubsub_v1
import json
from datetime import datetime
import time
from time import sleep
import threading
from gpiozero import LED
import RPi.GPIO as GPIO
import os
from pathlib import Path
import io
import logging
import socketserver
from threading import Condition
from http import server

metrics = StoveMetrics()

PAGE = Path('index.html').read_text()

buzzer_on = False
temp_threshold = 30
alarm_duration_threshold = 2

logging.basicConfig(level=logging.ERROR)

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
    
    def set_output(output):
        self.output = output

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


project_id = os.getenv('GCP_PROJECT_ID')
subscription_id = os.getenv('GCP_TOPIC_SUB_ID')

# The `subscription_path` method creates a fully qualified identifier
# in the form `projects/{project_id}/subscriptions/{subscription_id}`
subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(project_id, subscription_id)


led_green = LED(4)
led_red = LED(27)
buzzer = 17

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(buzzer, GPIO.OUT, initial=GPIO.LOW)


    
def clear_all_leds():
    led_green.off()
    led_red.off()
    
def callback(message):  
    if message.data:
        logging.info('Event received: %s', message.data)
        msg = json.loads(message.data)
        pub_time = message.publish_time
        # convert from UTC to local time
        now_timestamp = time.time()
        offset = datetime.fromtimestamp(now_timestamp) - datetime.utcfromtimestamp(now_timestamp)      
        event_time = pub_time + offset
        metrics.set_metrics(msg['temp'], msg['hum'], msg['dist'], event_time.replace(tzinfo=None))
    message.ack()
   

future = subscriber.subscribe(subscription_path, callback=callback)
clear_all_leds()

def start_consuming():
    with subscriber:
        try:
            future.result()
        except KeyboardInterrupt:
            future.cancel()
               
def alarm_monitor():
    trigger_metric = [0, 0, 0, datetime.now()]
    alarm_level_1_on = False
    alarm_level_2_on = False
    while True:
        latest_metric = metrics.get_avg_metrics()
        temp = latest_metric[0]
        evt_time = latest_metric[3]
        
        if buzzer_on:
            GPIO.output(buzzer, GPIO.HIGH)
        if temp > temp_threshold:
            if alarm_level_1_on:
                diff = evt_time - trigger_metric[3]
                diff_min = diff.total_seconds() / 60
                if diff_min > alarm_duration_threshold:
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
        
        led_green.off()
        led_red.off()
        GPIO.output(buzzer, GPIO.LOW)
        sleep(0.9)        


if __name__=="__main__":
    consumer = threading.Thread(target=start_consuming)
    monitor = threading.Thread(target=alarm_monitor)
    
    consumer.start()
    monitor.start()
    
    with picamera.PiCamera() as camera:
        camera.resolution = (640, 480)
        camera.framerate = 24
        output = StreamingOutput()
        #Uncomment the next line to change your Pi's Camera rotation (in degrees)
        #camera.rotation = 90
        camera.start_recording(output, format='mjpeg')
        
        try:
            address = ('', 8000)
            server = StreamingServer(address, StreamingHandler)
            server.serve_forever()
        finally:
            camera.stop_recording()
