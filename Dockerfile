FROM archlinux

EXPOSE 8008

WORKDIR /meshchat

RUN set -ex \
	&& buildDeps=' \
		pypy3 \
		python-cryptography \
	' \
	&& pacman --quiet --noconfirm -Sy $buildDeps

ADD ./ /meshchat
COPY ./.peerkey/* /meshchat/.key/

CMD python client.py
# CMD "bash"
