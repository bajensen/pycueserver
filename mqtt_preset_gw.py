import paho.mqtt.client as mqtt
import urllib2
import urllib
import struct
from collections import namedtuple
import ConfigParser

config = ConfigParser.SafeConfigParser({
    'host': 'localhost',
    'port': 1883,
    'username': None,
    'password': None,
    'keepalive': 60,
    'state_set_topic': 'living/state/set',
    'state_status_topic': 'living/state/status',
    'rgb_set_topic': 'living/rgb/set',
    'rgb_status_topic': 'living/rgb/status',
    'brightness_set_topic': 'living/brightness/set',
    'brightness_status_topic': 'living/brightness/status',
    'url': 'http://127.0.0.1:8080',
    'get_path': '/get.cgi',
    'exe_path': '/exe.cgi',

    'mode_set_topic': 'living/mode/set/',
    'mode_status_topic': 'living/mode/status/',
    'modes': 'fade backlight',
    'mode_fade_on': 'start p 1',
    'mode_fade_off': 'stop p 1',
    'mode_backlight_on': '"_backlight"=FL',
    'mode_backlight_off': '"_backlight"=1',

    'preset_set_topic': 'living/preset/set/',
    'preset_status_topic': 'living/preset/status/',
    'presets': 'white red green blue yellow purple cyan cycle',
    'preset_default_on': 'b1>8@0;',
    'preset_default_off': 'c1>3@0; b1>8@0;',
    'preset_white_on': 'q4g; b1@fl',
    'preset_white_off': '',
    'preset_red_on': 'q1g; b2@fl',
    'preset_red_off': '',
    'preset_green_on': 'q2g; b3@fl',
    'preset_green_off': '',
    'preset_blue_on': 'q3g; b4@fl',
    'preset_blue_off': '',
    'preset_yellow_on': 'q6g; b5@fl',
    'preset_yellow_off': '',
    'preset_purple_on': 'q5g; b6@fl',
    'preset_purple_off': '',
    'preset_cyan_on': 'q7g; b7@fl',
    'preset_cyan_off': '',
    'preset_cycle_on': 'q10g; b8@fl',
    'preset_cycle_off': ''
})

config.read('config.ini')

modes = config.get('Modes', 'modes').split()
presets = config.get('Presets', 'presets').split()

light_preset = None
light_color = {'red': 0, 'green': 0, 'blue': 0}
light_is_on = False


def server_get(params, fields, packer):
    """
    Call an HTTP GET to retrieve data, then unpack
    :param params: dictionary of parameters
    :param fields: string representing the variable names in order
    :param packer: packing definition
    :return:
    """

    base_url = config.get('CueServer', 'url')
    base_url += config.get('CueServer', 'get_path')

    if len(params):
        base_url += '?' + urllib.urlencode(params)

    result = urllib2.urlopen(base_url).read()

    Data = namedtuple('Data', fields)

    d = Data(*struct.unpack(packer, result))

    return d


def server_exe(cmd):
    """
    Execute a command on the server
    :param cmd:
    :return:
    """

    base_url = config.get('CueServer', 'url')
    base_url += config.get('CueServer', 'exe_path')

    params = {'cmd': cmd}

    base_url += '?' + urllib.urlencode(params)

    return urllib2.urlopen(base_url).read()


def set_preset(prev_preset, cur_preset, status):
    set_preset_int(cur_preset, status)


def set_preset_int(preset, status):
    state = status.lower()

    cmd = ''
    cmd += config.get('MQTT', 'preset_default_' + state) + ' '
    cmd += config.get('MQTT', 'preset_' + preset + '_' + state)

    server_exe(cmd)


def set_mode(mode, status):
    state = status.lower()

    cmd = ''
    cmd += config.get('MQTT', 'mode_' + mode + '_' + state)

    server_exe(cmd)


def update_pub_rgb():
    # Retrieve the color from the CueServer
    # rgb = get_output_levels()

    # Publish the new color
    # publish_rgb(rgb.red, rgb.green, rgb/.blue)
    # publish_state(rgb.red > 0 and rgb.green > 0 and rgb.blue > 0)

    publish_rgb(light_color['red'], light_color['green'], light_color['blue'])
    publish_state(light_is_on)


def update_pub_preset(previous, current, status):
    if previous is not None:
        topic = config.get('MQTT', 'preset_status_topic') + previous
        mqtt_client.publish(topic, 'OFF')

    if current is not None:
        topic = config.get('MQTT', 'preset_status_topic') + current
        mqtt_client.publish(topic, status)


def update_pub_mode(mode, state):
    topic = config.get('MQTT', 'mode_status_topic') + mode
    mqtt_client.publish(topic, state)


def publish_state(state):
    topic = config.get('MQTT', 'state_status_topic')
    msg = '{"state":' + ('true' if state else 'false') + ')'

    mqtt_client.publish(topic, msg)


def publish_rgb(red, green, blue):
    topic = config.get('MQTT', 'rgb_status_topic')
    msg = '{"rgb":"' + str(red) + ',' + str(green) + ',' + str(blue) + '")'

    mqtt_client.publish(topic, msg)


def get_playback_details():
    return server_get({
        'req': 'PI',
        'id': 1
    }, 'playback '
       'run_mode '
       'output_level '
       'combine_mode '
       'fade_timer '
       'follow_timer '
       'stream_timer '
       'current_cue '
       'next_cue '
       'fade_times '
       'follow_time '
       'link_cue '
       'reserved '
       'current_name '
       'next_name', 'BBBBHHLHHLHH8s32s32s')


def get_system_info():
    return server_get({
        'req': 'SI'
    }, 'serial '
       'device_name '
       'firmware_version '
       'time_str '
       'model '
       'has_password', '16s24s12s24sBB')


def get_button_level():
    return server_get({
        'req': 'BV'
    }, 'b1 b2 b3 b4 b5 b6 b7 b8', '8B504x')


def get_output_levels():
    d = server_get({
        'req': 'OUT'
    }, 'red blue green', '3B509x')

    return d


def set_rgb(red, green, blue):
    global light_is_on
    global light_color

    red = int(red)
    green = int(green)
    blue = int(blue)

    light_color['red'] = red
    light_color['green'] = green
    light_color['blue'] = blue

    light_is_on = (red > 0 or green > 0 or blue > 0)

    red = str(red * 100 / 255)
    green = str(green * 100 / 255)
    blue = str(blue * 100 / 255)

    cmd = ''
    cmd += 'c1@' + red + '; '
    cmd += 'c3@' + green + '; '  # Because Backwards
    cmd += 'c2@' + blue + '; '  # Because Backwards

    server_exe(cmd)


def on_connect(client, user_data, flags, result_code):
    print('Connected to MQTT with result code: ' + str(result_code))

    update_pub_rgb()

    mqtt_client.subscribe(config.get('MQTT', 'state_set_topic'))
    mqtt_client.subscribe(config.get('MQTT', 'rgb_set_topic'))

    # Subscribe to all mode set topics
    for mode in modes:
        topic = config.get('Modes', 'mode_set_topic') + mode
        mqtt_client.subscribe(topic)

    # Subscribe to all preset set topics
    for preset in presets:
        topic = config.get('Presets', 'preset_set_topic') + preset
        mqtt_client.subscribe(topic)


def on_message(client, user_data, msg):
    topic = msg.topic
    payload = str(msg.payload)

    if topic == config.get('MQTT', 'state_set_topic'):
        on_msg_state(payload)

    elif topic == config.get('MQTT', 'rgb_set_topic'):
        on_msg_rgb(payload)

    elif topic == config.get('MQTT', 'brightness_set_topic'):
        pass

    else:
        # Check mode set topics
        for mode in modes:
            if topic == config.get('Modes', 'mode_set_topic') + mode:
                on_msg_mode(mode, payload)

        # Check all preset set topics
        for preset in presets:
            if topic == config.get('Presets', 'preset_set_topic') + preset:
                on_msg_preset(preset, payload)


def on_msg_preset(preset, payload):
    global light_preset

    if payload == 'ON' or payload == 'OFF':
        set_preset(light_preset, preset, payload)
        update_pub_preset(light_preset, preset, payload)
        light_preset = preset


def on_msg_mode(mode, payload):
    if payload == 'ON' or payload == 'OFF':
        set_mode(mode, payload)
        update_pub_mode(mode, payload)


def on_msg_state(payload):
    global light_is_on

    if payload == 'ON':
        if not light_is_on:
            set_rgb(255, 255, 255)
    elif payload == 'OFF':
        if light_is_on:
            set_rgb(0, 0, 0)

    update_pub_rgb()


def on_msg_rgb(payload):
    global light_color

    # Parse the color values
    values = payload.split(',')
    RGB = namedtuple('RGB', 'red green blue')
    rgb_values = RGB(*values)

    # Set the color on the CueServer
    set_rgb(rgb_values.red, rgb_values.green, rgb_values.blue)

    update_pub_rgb()


def on_msg_brightness(payload):
    pass


mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

username = config.get('MQTT', 'username')
password = config.get('MQTT', 'password')

if username and password:
    mqtt_client.username_pw_set(username, password)

print "Attempting connection..."

mqtt_client.connect(
    config.get('MQTT', 'host'),
    config.getint('MQTT', 'port'),
    config.getint('MQTT', 'keepalive')
)

mqtt_client.loop_forever()
