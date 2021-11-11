FROM python

RUN pip3 install netifaces
COPY ./G1.py /
COPY ./system_network_library.py /

#Give reply_port by command line
ENTRYPOINT ["python","-u","./G1.py"]
