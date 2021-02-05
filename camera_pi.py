#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import io
import threading
import picamera
import datetime as dt

from picamera.array import PiRGBArray

class StreamingOutput(object):
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            # New frame, copy the existing buffer's content and notify all
            # clients it's available
            self.buffer.seek(0)
            self.frame = self.buffer.read()
            
            self.buffer.seek(0)
            self.buffer.truncate()
        return self.buffer.write(buf)


class Camera(object):
    thread = None  # background thread that reads frames from camera
    frame = None  # current frame is stored here by background thread
    last_access = 0  # time of last client access to the camera

    def initialize(self):
        if Camera.thread is None:
            # start background frame thread
            Camera.thread = threading.Thread(target=self._thread)
            Camera.thread.start()

            # wait until frames start to be available
            while self.frame is None:
                time.sleep(0)

    def get_frame(self):
        Camera.last_access = time.time()
        self.initialize()
        return self.frame

    @classmethod
    def _thread(cls):
        with picamera.PiCamera(framerate=24) as camera:
            # camera setup
            # camera.resolution = (640, 480)
            # camera.resolution = (735*3, 812*3)
            camera.resolution = (735, 812)
            # camera.image_effect = 'colorbalance'
            # camera.image_effect = 'cartoon'
            # camera.awb_mode = 'auto'
            camera.annotate_background = picamera.Color('black')
            camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d')
            camera.hflip = False
            camera.vflip = False

            # let camera warm up
            camera.start_preview()
            # time.sleep(2)

            stream = io.BytesIO()
            for foo in camera.capture_continuous(stream, 'jpeg',
                                                 use_video_port=True):
                # store frame
                stream.seek(0)
                cls.frame = stream.read()

                # reset stream for next frame
                stream.seek(0)
                stream.truncate()

                # if there hasn't been any clients asking for frames in
                # the last 10 seconds stop the thread
                if time.time() - cls.last_access > 10:
                    break
        cls.thread = None

