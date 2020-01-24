FROM kernsuite/base:5

################################
# install latest masters
################################
RUN echo "deb-src http://ppa.launchpad.net/kernsuite/kern-5/ubuntu bionic main" > /etc/apt/sources.list.d/kernsuite-ubuntu-kern-5-bionic.list
RUN apt-get update
RUN apt-get update
RUN docker-apt-install \
    python3 \
    python-pip python3-pip \
    virtualenv \
    python3-numpy \
    python3-scipy \
    libcfitsio-dev \
    wcslib-dev \
    git \
    nodejs \
    phantomjs \
    ghostscript \
    ipython python3-aplpy python3-astropy \
    python3-matplotlib python3-pil python3-casacore \
    wget lsof iproute2
##    libfuse2 libnss3 libgtk-3-0 libx11-xcb1 libasound2 xvfb
## last one was for carta desktop version

#    python-notebook jupyter-notebook jupyter-nbextension-jupyter-js-widgets \

#RUN pip install astropy==2.0.10  # monkeypatch
RUN pip3 install git+https://github.com/ratt-ru/CubiCal

RUN ldconfig
RUN mkdir /radiopadre
ADD . /radiopadre

# download CARTA
RUN if [ ! -f radiopadre/CARTA-v1.2.1-remote.tgz ]; then cd radiopadre; wget https://github.com/CARTAvis/carta-releases/releases/download/v1.2.1/CARTA-v1.2.1-remote.tgz; fi
RUN tar zxvf radiopadre/CARTA-v1.2.1-remote.tgz
RUN chmod -R a+rX CARTA-v1.2.1-remote
RUN ln -s CARTA-v1.2.1-remote carta
RUN rm radiopadre/CARTA-v1.2.1-remote.tgz


#RUN git clone https://github.com/ratt-ru/radiopadre
RUN rm -fr /radiopadre/.git /radiopadre/js9/.git
RUN cd /radiopadre && if [ ! -d js9 ]; then git clone https://github.com/ericmandel/js9; fi
RUN cd /radiopadre/js9 && make clean
RUN radiopadre/bin/install-radiopadre --inside-container

#RUN git clone https://github.com/ratt-ru/radiopadre-client
RUN git clone -b 1.0-pre1 https://github.com/ratt-ru/radiopadre-client.git
RUN pip3 install -e radiopadre-client

#RUN if [ ! -f radiopadre/CARTA-v1.1-ubuntu.AppImage ]; then cd radiopadre; wget https://github.com/CARTAvis/carta-releases/releases/download/v1.1/CARTA-v1.1-ubuntu.AppImage; fi
#RUN radiopadre/CARTA-v1.1-ubuntu.AppImage --appimage-extract
#RUN chmod -R a+rX squashfs-root
#RUN rm radiopadre/CARTA-v1.1-ubuntu.AppImage

CMD sleep infinity
