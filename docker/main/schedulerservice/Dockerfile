# problem using the current registry (127.0.0.1:5000), apparently due to the ':'
# which Docker thinks is an invalid --from value in the multi-stage copy step
ARG docker_internal_registry
FROM ${docker_internal_registry}/nwmaas-py-sources as sources

FROM python:3.7-alpine
ARG comms_package_name
ARG scheduler_package_dist_name
ARG scheduler_service_package_dist_name

WORKDIR /code

COPY ./entrypoint.sh entrypoint.sh

# Copy custom built packages from external sources image
COPY --from=sources /DIST /DIST
#COPY --chown=mpi:mpi conf/redis.conf /usr/local/etc/redis/redis.conf
#COPY --chown=mpi:mpi nwmaas/scheduler/image_and_domain.yaml /nwm/
COPY ./image_and_domain.yaml /nwm/

RUN apk update \
    && apk add --no-cache openssl bash \
    && rm -rf /var/cache/apk/* \
    && alias python=python3 \
    && pip3 install --no-cache-dir --upgrade pip \
    # Install service package, along with custom and generally available dependencies, which should all be in /DIST \
    && pip3 install --no-cache-dir --find-links=/DIST ${scheduler_service_package_dist_name} \
    # After installing everything needed from /DIST, clean up ... \
    && rm -r /DIST \
    && mkdir -p ~/.ssh \
    && printf "Host *\n        ServerAliveInterval 300\n        ServerAliveCountMax 2\n" >> ~/.ssh/config

ENTRYPOINT ["/code/entrypoint.sh"]
