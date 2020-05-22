FROM kernsuite/base:5

################################
# install latest masters
################################
RUN echo "deb-src http://ppa.launchpad.net/kernsuite/kern-5/ubuntu bionic main" > /etc/apt/sources.list.d/kernsuite-ubuntu-kern-5-bionic.list
RUN apt-get update
RUN docker-apt-install --no-install-recommends \
    python3 gcc make \
    python-pip python3-pip python3-virtualenv \
    virtualenv \
    python3-numpy \
    python3-scipy \
    libcfitsio-dev \
    libboost-python-dev \
    wcslib-dev \
    git \
    nodejs npm libxcomposite1 \
    phantomjs \
    ghostscript \
    ipython python3-aplpy python3-astropy \
    python3-matplotlib python3-pil python3-casacore \
    wget lsof iproute2 \
    npm nodejs \
    libxcomposite1 \
    firefox \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libgdk-pixbuf2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libxcursor1 \
    libxrandr2 \
    libxss1 \
    libxtst6 \
    thunderbird \
    && rm -rf /var/lib/apt/lists/*

# crazy list starting with npm needed for chromium within puppeteer. Don't ask me why.

RUN ldconfig

# Setup a virtual env
ENV VIRTUAL_ENV=/.radiopadre/venv
RUN virtualenv -p python3 $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip3 install --no-cache-dir -U pip setuptools

# RUN pip3 install git+https://github.com/ratt-ru/CubiCal

ADD . /radiopadre

ARG CLIENT_BRANCH=b1.0-pre12

#ARG CARTA_VERSION=1.3.1
#ENV RADIOPADRE_CARTA_VERSION=$CARTA_VERSION

RUN git clone -b $CLIENT_BRANCH https://github.com/ratt-ru/radiopadre-client.git
RUN pip3 install --no-cache-dir  -e /radiopadre-client
RUN pip3 install --no-cache-dir  -e /radiopadre

RUN echo 'kernel.unprivileged_userns_clone=1' > /etc/sysctl.d/userns.conf

ENTRYPOINT ["/.radiopadre/venv/bin/run-radiopadre"]

