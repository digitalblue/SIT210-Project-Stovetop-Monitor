# Web streaming example
# Source code from the official PiCamera package
# http://picamera.readthedocs.io/en/latest/recipes2.html#web-streaming

import random
import io
import picamera
import logging
import socketserver
from threading import Condition
from http import server
from pathlib import Path
from concurrent.futures import TimeoutError
from google.cloud import pubsub_v1
import json
from datetime import datetime
import time
import threading

# TODO(developer)
project_id = "edras-project"
subscription_id = "stovetop-metrics-topic-sub"
# Number of seconds the subscriber should listen for messages
timeout = 5.0

subscriber = pubsub_v1.SubscriberClient()
# The `subscription_path` method creates a fully qualified identifier
# in the form `projects/{project_id}/subscriptions/{subscription_id}`
subscription_path = subscriber.subscription_path(project_id, subscription_id)

PAGE = Path('index.html').read_text()

topic_values = "loading...".encode('utf-8')

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
        elif self.path == '/temp':
#             content = str(random.randrange(1,10)).encode('utf-8')
#             response = subscriber.pull(
#                 request={
#                     "subscription": subscription_path,
#                     "max_messages": 1
#                 }
#             )
#                         
#             if not response.received_messages:
#                 print("nothing")
#                 return
#             content = response.received_messages[0].message.data
#             
#             pub_time = response.received_messages[0].message.publish_time
#             
#             # print(pub_time)
# 
#             now_timestamp = time.time()
#             offset = datetime.fromtimestamp(now_timestamp) - datetime.utcfromtimestamp(now_timestamp)
#             
#             now_time = pub_time + offset
#             
#             print(now_time)
#             
#             ack_id = response.received_messages[0].ack_id
#             print(ack_id)
#             ack_ids = [ack_id]
#             
#             subscriber.acknowledge(
#                 request={
#                     "subscription": subscription_path,
#                     "ack_ids": ack_ids
#                 }
#             )
            content = topic_values
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
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
    
def callback(message):
    print(f"Received {message}.")
    if message.data:
        print(type(message.data))
        msg = json.loads(message.data)
        print("Humidity: "+ str(msg['hum']))
        print("Temp :" + str(msg['temp']))
    if message.attributes:
        print('Attributes')
        for key in message.attributes:
            value = message.attributes.get(key)
            print(f"{key}: {value}")
    message.ack()
    global topic_values
    topic_values = message.data
    print(topic_values)
    

streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
print(f"Listening for messages on {subscription_path}..\n")

def start_consuming():
    print("in consumer")
    # Wrap subscriber in a 'with' block to automatically call close() when done.
    with subscriber:
        try:
            # When `timeout` is not set, result() will block indefinitely,
            # unless an exception is encountered first.
            #streaming_pull_future.result(timeout=timeout)
            streaming_pull_future.result()
        except TimeoutError:
            streaming_pull_future.cancel()
            
consumer = threading.Thread(target=start_consuming)
            

with picamera.PiCamera(resolution='640x480', framerate=24) as camera:
    output = StreamingOutput()
    #Uncomment the next line to change your Pi's Camera rotation (in degrees)
    #camera.rotation = 90
    camera.start_recording(output, format='mjpeg')
    consumer.start()
    
#     # Wrap subscriber in a 'with' block to automatically call close() when done.
#     with subscriber:
#         try:
#             # When `timeout` is not set, result() will block indefinitely,
#             # unless an exception is encountered first.
#             streaming_pull_future.result(timeout=timeout)
#             #streaming_pull_future.result()
#         except TimeoutError:
#             streaming_pull_future.cancel()
    
    try:
        address = ('', 8000)
        server = StreamingServer(address, StreamingHandler)
        server.serve_forever()
    finally:
        camera.stop_recording()



# Wrap subscriber in a 'with' block to automatically call close() when done.
# with subscriber:
#     try:
#         # When `timeout` is not set, result() will block indefinitely,
#         # unless an exception is encountered first.
#         streaming_pull_future.result(timeout=timeout)
#         #streaming_pull_future.result()
#     except TimeoutError:
#         streaming_pull_future.cancel()