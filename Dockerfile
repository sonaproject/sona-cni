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

FROM registry.access.redhat.com/ubi8/ubi-minimal:latest

LABEL name="SONA CNI" \
      vendor="SK Telecom" \
      release="1" \
      summary="SONA CNI" \
      description="SONA CNI includes a CNI networking plugin and a set of configuration scripts" \
      maintainer="gunine@sk.com"

ADD /dist/sona /opt/cni/bin/
ADD /dist/config-route /config-route
ADD /dist/config-external /config-external

RUN mkdir /licenses
COPY LICENSE /licenses

ENV PATH=$PATH:/opt/cni/bin
WORKDIR /opt/cni/bin
CMD ["/opt/cni/bin/sona"]