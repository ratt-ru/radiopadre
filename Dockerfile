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
    python-matplotlib python-pil python-casacore
#    python-notebook jupyter-notebook jupyter-nbextension-jupyter-js-widgets \

RUN pip install astropy==2.0.10  # monkeypatch

RUN mkdir /radiopadre
ADD . /radiopadre
#RUN git clone https://github.com/ratt-ru/radiopadre
RUN rm -fr /radiopadre/.git /radiopadre/js9/.git
RUN cd /radiopadre && if [ ! -d js9 ]; then git clone https://github.com/ericmandel/js9; fi
RUN radiopadre/bin/install-radiopadre --inside-container
