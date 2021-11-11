FROM python
WORKDIR ./


RUN /usr/local/bin/python3.9 -m pip install --upgrade pip && apt-get update \
&& apt-get install ffmpeg libsm6 libxext6  -y 


RUN pip3 install opencv-python \
&& apt-get install python3-dev python3-numpy -y \
&& pip3 install numpy && pip3 install --upgrade numpy

RUN pip3 install netifaces

COPY ./F1.py /
COPY ./system_network_library.py /

#Give reply_port by command line
ENTRYPOINT ["python","-u","./F1.py"]
