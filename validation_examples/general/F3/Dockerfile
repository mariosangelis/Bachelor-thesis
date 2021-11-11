FROM python:3.8
WORKDIR ./

RUN /usr/local/bin/python3.8 -m pip install --upgrade pip && apt-get update \
&& apt-get install ffmpeg libsm6 libxext6  -y \
&& pip3 install opencv-python 

RUN pip3 install scikit-image==0.17.1
RUN pip3 install netifaces

COPY ./F3.py /
COPY ./system_network_library.py /
COPY ./images /images


#Give reply_port by command line
ENTRYPOINT ["python","-u","./F3.py"]



