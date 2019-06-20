FROM kernsuite/base:4

################################
# install latest masters
################################
RUN echo "deb-src http://ppa.launchpad.net/kernsuite/kern-4/ubuntu bionic main" > /etc/apt/sources.list.d/kernsuite-ubuntu-kern-4-bionic.list
RUN apt-get update
RUN apt-get update
RUN docker-apt-install \
    python-pip \
    virtualenv \
    python-numpy \
    python-scipy \
    libcfitsio-dev \
    wcslib-dev \
    git \
    nodejs \
    ipython python-aplpy python-astropy \
    python-matplotlib python-pil python-casacore \
    wget lsof iproute2
##    libfuse2 libnss3 libgtk-3-0 libx11-xcb1 libasound2 xvfb
## last one was for carta desktop version

#    python-notebook jupyter-notebook jupyter-nbextension-jupyter-js-widgets \

RUN pip install astropy==2.0.10  # monkeypatch

RUN ldconfig
RUN mkdir /radiopadre
ADD . /radiopadre
#RUN git clone https://github.com/ratt-ru/radiopadre
RUN rm -fr /radiopadre/.git /radiopadre/js9/.git
RUN cd /radiopadre && if [ ! -d js9 ]; then git clone https://github.com/ericmandel/js9; fi
RUN cd /radiopadre/js9 && make clean
RUN radiopadre/bin/install-radiopadre --inside-container

RUN if [ ! -f radiopadre/CARTA-v1.1-remote.tar.gz ]; then cd radiopadre; wget https://github.com/CARTAvis/carta-releases/releases/download/v1.1/CARTA-v1.1-remote.tar.gz; fi
RUN tar zxvf radiopadre/CARTA-v1.1-remote.tar.gz
RUN chmod -R a+rX CARTA-v1.1-remote
RUN ln -s CARTA-v1.1-remote carta
RUN rm radiopadre/CARTA-v1.1-remote.tar.gz

#RUN if [ ! -f radiopadre/CARTA-v1.1-ubuntu.AppImage ]; then cd radiopadre; wget https://github.com/CARTAvis/carta-releases/releases/download/v1.1/CARTA-v1.1-ubuntu.AppImage; fi
#RUN radiopadre/CARTA-v1.1-ubuntu.AppImage --appimage-extract
#RUN chmod -R a+rX squashfs-root
#RUN rm radiopadre/CARTA-v1.1-ubuntu.AppImage

CMD sleep infinity
