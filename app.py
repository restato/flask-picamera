import Adafruit_DHT
import RPi.GPIO as GPIO
import time

from flask import Flask, render_template, Response, request, jsonify
from camera_pi import Camera
from functools import wraps

app = Flask(__name__)

# Enter the sensor details
sensor = Adafruit_DHT.DHT22
sensor_gpio = 21

def support_jsonp(f):
    """Wraps JSONified output for JSONP"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        callback = request.args.get("callback", False)
        if callback:
            content = str(callback) + "(" + str(f(*args,**kwargs)) + ")"
            return current_app.response_class(content, mimetype="application/javascript")
        else:
            return f(*args, **kwargs)
    return decorated_function


@app.route('/index.html')
@app.route('/')
def index():
    """Home Page"""
    humidity, temperature = raw_dht()
    return render_template('index.html', humidity=humidity, temperature=temperature)


def gen(camera):
    """Video streaming generator function."""
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen(Camera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


GPIO.setmode(GPIO.BOARD)

PIN_TRIGGER = 35
PIN_ECHO = 37

GPIO.setup(PIN_TRIGGER,GPIO.OUT)
GPIO.setup(PIN_ECHO,GPIO.IN)
GPIO.output(PIN_TRIGGER, GPIO.LOW)
print("Calibrating.....")
time.sleep(2)
print("Place the object......")

@app.route("/ultrasonic")
@support_jsonp
def api_ultrasonic():
    return jsonify({'distance': int(raw_ultrasonic())})


def raw_ultrasonic():
    try:
        GPIO.output(PIN_TRIGGER, GPIO.HIGH)
        time.sleep(0.00001)
        GPIO.output(PIN_TRIGGER, GPIO.LOW)

        while GPIO.input(PIN_ECHO)==0:
            pulse_start = time.time()

        while GPIO.input(PIN_ECHO)==1:
            pulse_end = time.time()

        pulse_duration = pulse_end - pulse_start
        distance = round(pulse_duration * 17150, 2)
        print(f'distance: {distance}')
        return distance
        # distance = round(distance+1.15, 2)
    except KeyboardInterrupt:
        GPIO.cleanup()


@app.route("/dht")
@support_jsonp
def api_dht():
    humidity, temperature = raw_dht()
    return jsonify({'humidity': humidity, 'temperature': temperature})
    '''
    if humidity is not None and temperature is not None:
        return "{ temperature: '" + "{0:0.0f}".format(temperature) +  "', humidity: '" + "{0:0.0f}".format(humidity) + "' }"
    else:
        return "Failed to get reading. Try again!", 500
    '''


def raw_dht():
    """Read the sensor using the configured driver and gpio"""
    humidity, temperature = Adafruit_DHT.read_retry(sensor, sensor_gpio)
    humidity = round(humidity, 2)
    temperature = round(temperature, 2)
    return humidity, temperature


if __name__ == '__main__':
    app.run(host='0.0.0.0', port =8000, debug=True, threaded=True)
