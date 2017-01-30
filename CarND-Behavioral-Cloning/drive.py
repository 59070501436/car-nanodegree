import argparse
import base64
import json

import numpy as np
import socketio
import eventlet
import eventlet.wsgi
import time
from PIL import Image
from PIL import ImageOps
from flask import Flask, render_template
from io import BytesIO

from keras.models import model_from_json
from keras.preprocessing.image import ImageDataGenerator, array_to_img, img_to_array

import cv2
from skimage.filters.rank import entropy
from skimage.morphology import disk
import curses

# Fix error with Keras and TensorFlow
import tensorflow as tf
tf.python.control_flow_ops = tf


sio = socketio.Server()
app = Flask(__name__)
model = None
prev_image_array = None
last_frame = None
last_key = 0
repeat_key = 0

@sio.on('telemetry')
def telemetry(sid, data, prev_frame=last_frame):
    # The current steering angle of the car
    steering_angle = float(data["steering_angle"])/25.
    # The current throttle of the car
    throttle = data["throttle"]
    # The current speed of the car
    speed = data["speed"]
    # The current image from the center camera of the car
    imgString = data["image"]
    image = Image.open(BytesIO(base64.b64decode(imgString)))
    image_array = np.asarray(image)

    #global last_frame

    #if prev_frame:
    #    image_array = image_array - prev_frame

    #last_frame = image_array

    gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
    #ent_img = entropy(gray, disk(5))
    # softmax
    #ent_img = np.exp(ent_img - np.max(ent_img))
    #ent_img = (ent_img / np.max(ent_img))
    cv2.imshow('frame', gray)
    key = cv2.waitKey(1)

    print('Before:', steering_angle, throttle)

    global last_key
    global repeat_key

    if key >= 0 or repeat_key > 0:
        print("key:", key)

        if repeat_key <= 0:
            repeat_key = 1

        if last_key == 63234 and steering_angle > -.7:
            steering_angle -= 0.05 * abs(repeat_key)
        elif last_key == 63235 and steering_angle < .7:
            steering_angle += 0.05 * abs(repeat_key)

        if key >= 0 and repeat_key < 3:
            repeat_key += 1
        elif repeat_key > 0:
            repeat_key -= 1

        if key >= 0:
            last_key = key

    elif repeat_key < -3:

        if steering_angle < 0:
            steering_angle += 0.2

        elif steering_angle > 0:
            steering_angle -= 0.2

        if abs(steering_angle) < 0.2:
            steering_angle = 0
    else:
        repeat_key -= 1

    transformed_image_array = image_array[None, :, :, :]
    # This model currently assumes that the features of the model are just the images. Feel free to change this.
    #steering_angle = float(model.predict(transformed_image_array, batch_size=1))
    #steering_angle = 0.0

    # The driving model currently just outputs a constant throttle. Feel free to edit this.
    throttle = 0.1
    print('After:', steering_angle, throttle, last_key)
    send_control(steering_angle, throttle)


@sio.on('connect')
def connect(sid, environ):
    print("connect ", sid)
    send_control(0, 0)


def send_control(steering_angle, throttle):
    sio.emit("steer", data={
    'steering_angle': steering_angle.__str__(),
    'throttle': throttle.__str__()
    }, skip_sid=True)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Remote Driving')
    parser.add_argument('model', type=str,
    help='Path to model definition json. Model weights should be on the same path.')
    args = parser.parse_args()
    #with open(args.model, 'r') as jfile:
        # NOTE: if you saved the file by calling json.dump(model.to_json(), ...)
        # then you will have to call:
        #
        #   model = model_from_json(json.loads(jfile.read()))\
        #
        # instead.
        #model = model_from_json(jfile.read())


    #model.compile("adam", "mse")
    #weights_file = args.model.replace('json', 'h5')
    #model.load_weights(weights_file)

    #stdscr.nodelay(1)

    # wrap Flask application with engineio's middleware
    app = socketio.Middleware(sio, app)

    # deploy as an eventlet WSGI server
    eventlet.wsgi.server(eventlet.listen(('', 4567)), app)
