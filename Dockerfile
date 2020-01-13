# Copyright 2019-present SK Telecom
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

FROM centos/python-27-centos7:latest as builder
ENV LD_LIBRARY_PATH=/opt/rh/python27/root/usr/lib64
USER root

RUN curl "https://bootstrap.pypa.io/get-pip.py" -o "get-pip.py"
RUN python get-pip.py
RUN yum install -y build-essential tk
RUN wget https://github.com/upx/upx/releases/download/v3.95/upx-3.95-amd64_linux.tar.xz
RUN tar xvf upx-3.95-amd64_linux.tar.xz -C ./
RUN cp upx-3.95-amd64_linux/upx /bin

RUN mkdir -p /opt/app-root/src
ADD requirements.txt /
ADD sona /opt/app-root/src
ADD config-external.py /opt/app-root/src
ADD master-ip.py /opt/app-root/src
ADD replace-master-ip.py /opt/app-root/src

RUN pip install -r /requirements.txt && \
    pip install pyinstaller

RUN pyinstaller --onefile sona
RUN pyinstaller --onefile config-external.py
RUN pyinstaller --onefile master-ip.py
RUN pyinstaller --onefile replace-master-ip.py

FROM python:2-slim

RUN apt-get -y update && apt-get install -y curl

COPY --from=builder /opt/app-root/src/dist/sona /
COPY --from=builder /opt/app-root/src/dist/config-external /
COPY --from=builder /opt/app-root/src/dist/master-ip /
COPY --from=builder /opt/app-root/src/dist/replace-master-ip /

ADD install-cni-config.sh /
ADD install-sona-config.sh /
ADD install-cni.sh /
ADD check-control-plane.sh /

LABEL name="SONA CNI" \
      vendor="SK Telecom" \
      release="1" \
      summary="SONA CNI" \
      description="SONA CNI includes a CNI networking plugin and a set of configuration scripts" \
      maintainer="gunine@sk.com"

RUN mkdir /licenses
COPY LICENSE /licenses

ENTRYPOINT ["/sona"]
