FROM kernsuite/base:7

################################
# install latest masters
################################
RUN echo "deb-src http://ppa.launchpad.net/kernsuite/kern-7/ubuntu focal main" > /etc/apt/sources.list.d/kernsuite-ubuntu-kern-7-focal.list
RUN add-apt-repository ppa:cartavis-team/carta
RUN add-apt-repository ppa:saiarcot895/chromium-beta
RUN apt-get update
RUN docker-apt-install --no-install-recommends \
    gcc g++ make carta-backend carta-frontend casacore-data \
    python3-pip python3-virtualenv chromium-browser \
    virtualenv \
    python3-numpy \
    python3-scipy \
    libcfitsio-dev \
    libboost-python-dev \
    wcslib-dev \
    git \
    nodejs npm libxcomposite1 \
    phantomjs libqt5core5a \
    ghostscript \
    ipython3 python3-aplpy python3-astropy \
    python3-matplotlib python3-pil python3-casacore \
    wget lsof iproute2 \
    npm nodejs nodeenv \
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
    && apt-get clean && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives 


# crazy list starting with npm needed for chromium within puppeteer. Don't ask me why.

RUN ldconfig


# Setup a virtual env
ENV VIRTUAL_ENV=/.radiopadre/venv
RUN virtualenv -p python3 $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip3 install --no-cache-dir -U pip setuptools numpy wheel

ADD . /radiopadre

### override the override -- CARTA 2.0 installed from PPA above
## override due to problems with 1.4 in containers
#ARG RADIOPADRE_CARTA_VERSION=1.3.1  

ARG CLIENT_BRANCH=b1.2.2

RUN git clone -b $CLIENT_BRANCH https://github.com/ratt-ru/radiopadre-client.git
RUN pip3 install --no-cache-dir -e /radiopadre-client

RUN pip3 install --no-cache-dir -e /radiopadre

RUN echo 'kernel.unprivileged_userns_clone=1' > /etc/sysctl.d/userns.conf

# stupid phantomjs problem, see here:
# https://stackoverflow.com/questions/63627955/cant-load-shared-library-libqt5core-so-5
RUN strip --remove-section=.note.ABI-tag /usr/lib/x86_64-linux-gnu/libQt5Core.so.5         


ENTRYPOINT ["/.radiopadre/venv/bin/run-radiopadre"]

