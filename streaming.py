import cv2
from flask import Response
from flask import Flask
from flask import render_template
import threading
import numpy as np
import keras
import tensorflow as tf
from tensorflow.keras.models import load_model
from skimage.transform import resize
from PIL import Image
import tensorflow as tf
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
ip_address = s.getsockname()[0]

import paho.mqtt.client as mqtt
import requests
import json
model_weight = load_model("public_assault_weight.h5")
def on_message(client, userdata, message):
    print("li")
    data1 =[]
    receivedstring = str(message.payload.decode("utf-8"))
    data1=receivedstring.split(",")
    print(data1)
    with open('config.json', 'w') as json_file:
        json.dump(data1, json_file)

broker_address="broker.hivemq.com"
client = mqtt.Client("PROJECT")
client.connect(broker_address) 
client.on_message=on_message 
client.subscribe("NOTIF-NS")
response = 0

with open('config.json') as f:
    data = json.load(f)


serverToken = 'AAAA9myXIrY:APA91bHsrnPMm8TUAk7lfPCdXzdTZdz0riWCQlaoTpWVTCGMiWakwWWEoAFdERvk6LQ8esGb-rRJvFTTY9NRTcVc-O9WrNS_MaE3GNmoJ7tbRrqt46RRXlzIPVO4NBo21LFEA8lRMtSD'
deviceToken = data[0]
headers = {
        'Content-Type': 'application/json',
        'Authorization': 'key=' + serverToken,
      }

body = {
          'notification': {'title': 'Sending push form python script',
                            'body': 'New Message'
                            },
          'to':
              deviceToken,
          'priority': 'high',
        }

outputFrame = None
lock = threading.Lock()

# initialize a flask object
app = Flask(__name__)

@app.route("/")
def index():
    # return the rendered template
    return render_template("index.html")

def web_stream(frameCount):
    # grab global references to the video stream, output frame, and
    # lock variables
    global outputFrame, lock,model_weight

    count = 0
    cond = 0

    # global notification_flag
    notification_flag = 0
    normalflag = 0
    cap = cv2.VideoCapture(1)
    farneback_params = dict(
    winsize=20, iterations=1,
    flags=cv2.OPTFLOW_FARNEBACK_GAUSSIAN, levels=1,
    pyr_scale=0.5, poly_n=5, poly_sigma=1.1, flow=None)
    IMG_W = 60
    IMG_H = 80
    prev_frame = None
    frames_list = []
    optical_flow_x = []
    optical_flow_y = []

    # loop over frames from the video stream
    while True:

        client.loop_start()
        has_frame, show = cap.read()
        if has_frame:
                # Boolean flag to check if current frame contains human.
            frame = cv2.resize(show, (120, 160))
            frame = Image.fromarray(np.array(frame))
            frame = frame.convert("L")
            frame = np.array(frame.getdata(),
                        dtype=np.float32).reshape((120, 160))
            frame = resize(frame, (60, 80))
            frames_list.append(frame)
            if len(frames_list) > 30:
                frames_list.pop(0)
            if prev_frame is not None:
                # Calculate optical flow.
                flows = cv2.calcOpticalFlowFarneback(prev_frame, frame,
                                                    **farneback_params)    
                # Subsampling optical flow by half (due to memory usage problems).
                subsampled_x = np.zeros((IMG_W//2, IMG_H//2), dtype=np.float32)
                subsampled_y = np.zeros((IMG_W//2, IMG_H//2), dtype=np.float32)
                for r in range(IMG_W//2):
                    for c in range(IMG_H//2):
                        subsampled_x[r, c] = flows[r*2, c*2, 0]
                        subsampled_y[r, c] = flows[r*2, c*2, 1]
                optical_flow_x.append(subsampled_x)
                optical_flow_y.append(subsampled_y)
                if len(optical_flow_x) > 29:
                    optical_flow_x.pop(0)
                    optical_flow_y.pop(0)
            prev_frame = frame
            if len(frames_list)==30:
                pixel_feature = np.array(frames_list)
                pixel_feature = pixel_feature.reshape(1,pixel_feature.shape[0],pixel_feature.shape[1],pixel_feature.shape[2],1)
                # print(pixel_feature)
                # print("pixel_feature",pixel_feature.shape)
                optical_feature_x_data = np.array(optical_flow_x)
                optical_feature_x_data = optical_feature_x_data.reshape(1,optical_feature_x_data.shape[0],optical_feature_x_data.shape[1],optical_feature_x_data.shape[2],1)
                # print("optical_feature_x_data",optical_feature_x_data.shape)
                optical_feature_y_data = np.array(optical_flow_y)
                optical_feature_y_data = optical_feature_y_data.reshape(1,optical_feature_y_data.shape[0],optical_feature_y_data.shape[1],optical_feature_y_data.shape[2],1)
                # print("optical_feature_y_data",optical_feature_y_data.shape)
                temporal_feature = np.concatenate((optical_feature_x_data, optical_feature_y_data), axis=1)
                prediction = model_weight.predict([pixel_feature,temporal_feature], verbose=1)
                CATEGORIES = ["violence","non violence"]
                print("predicted labels is ",CATEGORIES[prediction.argmax()])
                # print(prediction[prediction.argmax(axis=1)])
                predicted_class = CATEGORIES[prediction.argmax()]

                if  predicted_class=="violence":
    
                    print("***ABNORMAL***")
                    if notification_flag == 0:
                        normalflag=0
                        client.publish("NOTIF-NA","1"+","+str(ip_address))
                        with open('config.json') as f:
                            data = json.load(f)
                        serverToken = 'AAAA9myXIrY:APA91bHsrnPMm8TUAk7lfPCdXzdTZdz0riWCQlaoTpWVTCGMiWakwWWEoAFdERvk6LQ8esGb-rRJvFTTY9NRTcVc-O9WrNS_MaE3GNmoJ7tbRrqt46RRXlzIPVO4NBo21LFEA8lRMtSD'
                        deviceToken = data[0]
                        headers = {
                                'Content-Type': 'application/json',
                                'Authorization': 'key=' + serverToken,
                            }

                        body = {
                                'notification': {'title': 'Sending push form python script',
                                                    'body': 'New Message'
                                                    },
                                'to':
                                    deviceToken,
                                'priority': 'high',
                                }
                        response = requests.post("https://fcm.googleapis.com/fcm/send",headers = headers, data=json.dumps(body))
                        print(response.status_code)
                        print(response.json())
                        notification_flag=1
                else:
                    if normalflag==0:
                        client.publish("NOTIF-NA","0")
                        notification_flag=0
                        normalflag=1

                cv2.imshow("Assault detection", show)

            with lock:
                outputFrame = show.copy()
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

def generate():
    # grab global references to the output frame and lock variables
    global outputFrame, lock

    # loop over frames from the output stream
    while True:
        # wait until the lock is acquired
        with lock:
            # check if the output frame is available, otherwise skip
            # the iteration of the loop
            if outputFrame is None:
                continue

            # encode the frame in JPEG format
            (flag, encodedImage) = cv2.imencode(".jpg", outputFrame)

            # ensure the frame was successfully encoded
            if not flag:
                continue

        # yield the output frame in the byte format
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
            bytearray(encodedImage) + b'\r\n')
        
@app.route("/video_feed")
def video_feed():
    # return the response generated along with the specific media
    # type (mime type)
    return Response(generate(),
        mimetype = "multipart/x-mixed-replace; boundary=frame")

# check to see if this is the main thread of execution
if __name__ == '__main__':

    # start a thread that will perform motion detection
    t = threading.Thread(target=web_stream, args=(32,))
    t.daemon = True
    t.start()

    # start the flask app
    app.run(host="0.0.0.0", port="8000", threaded=True, use_reloader=False)
