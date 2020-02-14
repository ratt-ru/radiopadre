FROM kernsuite/base:5

ARG CLIENT_BRANCH=b1.0-pre2
ARG CARTA_VERSION=v1.2.1
ARG CARTA_BASE=CARTA-$CARTA_VERSION-remote
ARG CARTA_TGZ=$CARTA_BASE.tgz
ARG CARTA_URL=https://github.com/CARTAvis/carta-releases/releases/download/$CARTA_VERSION/$CARTA_TGZ

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

RUN pip3 install git+https://github.com/ratt-ru/CubiCal

RUN ldconfig
RUN mkdir /radiopadre
ADD . /radiopadre

# download CARTA
#RUN if [ ! -f radiopadre/$CARTA_TGZ ]; then cd radiopadre; wget $CARTA_URL; fi
#RUN tar zxvf radiopadre/$CARTA_TGZ
#RUN chmod -R a+rX $CARTA_BASE
#RUN ln -s $CARTA_BASE carta
#RUN rm radiopadre/$CARTA_TGZ

RUN rm -fr /radiopadre/.git /radiopadre/js9/.git
RUN cd /radiopadre && if [ ! -d js9 ]; then git clone https://github.com/ericmandel/js9; fi
RUN cd /radiopadre/js9 && make clean
RUN git clone -b $CLIENT_BRANCH https://github.com/ratt-ru/radiopadre-client.git
RUN pip3 install -e /radiopadre-client
RUN /radiopadre/bin/bootstrap-radiopadre-install --inside-container --client-path /radiopadre-client

CMD sleep infinity
