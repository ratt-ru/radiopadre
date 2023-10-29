# Largely borrowed from https://github.com/corbinu/ssh-server

FROM quay.io/osmirnov/radiopadre:1.2.2

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /var/run/sshd \
  && mkdir /root/.ssh \
  && chmod 700 /root/.ssh \
  && touch /root/.ssh/authorized_keys

COPY sshd_config /etc/ssh/sshd_config

EXPOSE 22

# RUN ssh-keygen -t rsa -f /etc/ssh/ssh_host_rsa_key
RUN chmod 600 /etc/ssh/ssh_host_rsa_key

ENTRYPOINT ["/usr/sbin/sshd", "-D"]
