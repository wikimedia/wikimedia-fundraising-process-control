FROM python:buster

# Install mailutils for inspecting failmail
RUN apt update && apt install -y \
mailutils

# Create the directories that process-control uses (as set in process-control.yaml config)
RUN mkdir -p /var/log/process-control
RUN mkdir -p /var/run/process-control/state
RUN mkdir -p /var/run/process-control/run
RUN mkdir -p /etc/cron.d

# Copy in app src and config
COPY . /srv/process-control
COPY ./examples/process-control.example.docker.yaml /etc/process-control.yaml
COPY ./examples/job.example.docker.yaml /srv/jobs/example_job.yaml

# Add 'pc-user' and set permissions
RUN useradd -m pc-user
RUN chmod -R o+rwx /var/run/process-control
RUN chmod -R o+rw /srv
RUN chmod -R o+rw /var/log
RUN chmod o+rw /etc/cron.d

# Set cwd to app src directory and install process-control
WORKDIR /srv/process-control
RUN pip3 install -r requirements.txt
RUN pip3 install -e .