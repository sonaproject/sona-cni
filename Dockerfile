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

FROM python:2-slim as builder

RUN apt-get -y update && apt-get install -y build-essential upx-ucl tk

ADD requirements.txt /
ADD sona /
ADD config-external.py /
ADD master-ip.py /

RUN pip install -r /requirements.txt && \
    pip install pyinstaller

RUN pyinstaller --onefile sona
RUN pyinstaller --onefile config-external.py
RUN pyinstaller --onefile master-ip.py

FROM python:2-slim

RUN apt-get -y update && apt-get install -y curl

COPY --from=builder /dist/sona /
COPY --from=builder /dist/config-external /
COPY --from=builder /dist/master-ip /

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
