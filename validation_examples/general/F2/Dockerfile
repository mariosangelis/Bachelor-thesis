FROM python
WORKDIR ./


RUN /usr/local/bin/python3.9 -m pip install --upgrade pip && apt-get update \
&& apt-get install ffmpeg libsm6 libxext6  -y \
&& pip3 install opencv-python \
&& apt-get install python3-dev python3-numpy -y \
&& pip3 install numpy && pip3 install --upgrade numpy \
&& apt-get install python3-pil python3-pil.imagetk -y 

RUN pip install pillow
RUN pip3 install netifaces

COPY ./F2.py /
COPY ./system_network_library.py /
COPY ./haarcascade_frontalface_default.xml /

#Give reply_port by command line
ENTRYPOINT ["python","-u","./F2.py"]


