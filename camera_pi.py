#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import io
import threading
import picamera
import datetime as dt

class StreamingOutput(object):
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = threading.Condition()

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
            camera.annotate_background = picamera.Color('black')
            camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d')
            camera.hflip = False
            camera.vflip = False

            output = StreamingOutput()
            camera.start_recording(output, format='mjpeg')

            try:
                while True:
                    with output.condition:
                        cls.frame = output.frame
            except Exception as e:
                logging.warning(
                    'Removed streaming client %s', str(e))

        cls.thread = None

