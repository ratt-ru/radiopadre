FROM kernsuite/base:5

################################
# install latest masters
################################
RUN echo "deb-src http://ppa.launchpad.net/kernsuite/kern-5/ubuntu bionic main" > /etc/apt/sources.list.d/kernsuite-ubuntu-kern-5-bionic.list
RUN apt-get update
RUN apt-get update
RUN docker-apt-install \
    python3 \
    python-pip python3-pip python3-virtualenv \
    virtualenv \
    python3-numpy \
    python3-scipy \
    libcfitsio-dev \
    libboost-python-dev \
    wcslib-dev \
    git \
    nodejs \
    phantomjs \
    ghostscript \
    ipython python3-aplpy python3-astropy \
    python3-matplotlib python3-pil python3-casacore \
    wget lsof iproute2

RUN ldconfig

# Setup a virtual env
ENV VIRTUAL_ENV=/.radiopadre/venv
RUN virtualenv -p python3 $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip3 install -U pip setuptools

#RUN pip3 install git+https://github.com/ratt-ru/CubiCal

ADD . /radiopadre

ARG CLIENT_BRANCH=b1.0-pre9
ARG CARTA_VERSION=1.3

RUN git clone -b $CLIENT_BRANCH https://github.com/ratt-ru/radiopadre-client.git
RUN pip3 install -e /radiopadre-client
ENV RADIOPADRE_CARTA_VERSION=$CARTA_VERSION
RUN pip3 install -e /radiopadre

CMD sleep infinity
