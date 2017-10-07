FROM centos:latest

RUN yum -y update

RUN yum -y install epel-release && \
    yum -y install python2-pip && \
    yum -y clean all && \
    pip install --upgrade pip && \
    pip install paho-mqtt

COPY config.ini /opt/pycueserver
COPY mqtt_preset_gw.py /opt/pycueserver
COPY mqtt_rgb_gw.py /opt/pycueserver

WORKDIR /opt/pycueserver

CMD ["python", "/opt/pycueserver/mqtt_preset_gw.py"]

