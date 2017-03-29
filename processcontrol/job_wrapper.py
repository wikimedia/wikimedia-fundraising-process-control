import datetime
import glob
import os
import shlex
import subprocess
import threading

from . import config
from . import lock
from . import mailer
from . import output_streamer


# TODO: uh has no raison d'etre now other than to demonstrate factoryness.
def load(job_name):
    return JobWrapper(slug=job_name)


def list():
    """Return a tuple of all available job names."""
    job_directory = config.GlobalConfiguration().get("job_directory")
    paths = sorted(glob.glob(job_directory + "/*.yaml"))
    file_names = [os.path.basename(p) for p in paths]
    job_names = [f.replace(".yaml", "") for f in file_names]
    return job_names


def job_path_for_slug(slug):
    global_config = config.GlobalConfiguration()
    job_directory = global_config.get("job_directory")
    path = "{root_dir}/{slug}.yaml".format(root_dir=job_directory, slug=slug)
    return path


class JobWrapper(object):
    def __init__(self, slug=None):
        self.global_config = config.GlobalConfiguration()
        self.config_path = job_path_for_slug(slug)
        self.config = config.JobConfiguration(self.global_config, self.config_path)

        self.name = self.config.get("name")
        self.slug = slug
        self.start_time = datetime.datetime.utcnow()
        self.mailer = mailer.Mailer(self.config)
        self.timeout = self.config.get("timeout")

        if self.config.has("disabled") and self.config.get("disabled") is True:
            self.enabled = False
        else:
            self.enabled = True

        if not self.config.has("schedule"):
            self.enabled = False

        if self.config.has("environment"):
            self.environment = self.config.get("environment")
        else:
            self.environment = {}

    def run(self):
        lock.begin(job_tag=self.slug)

        config.log.info("Running job {name} ({slug})".format(name=self.name, slug=self.slug))

        command = shlex.split(self.config.get("command"))

        self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self.environment)
        streamer = output_streamer.OutputStreamer(self.process, self.slug, self.start_time)
        streamer.start()

        timer = threading.Timer(self.timeout, self.fail_timeout)
        timer.start()

        try:
            # should be safe from deadlocks because our OutputStreamer
            # has been consuming stderr and stdout
            self.process.wait()

            stderr_data = streamer.get_errors()
            if len(stderr_data) > 0:
                self.fail_has_stderr(stderr_data)
        finally:
            timer.cancel()
            lock.end()

        return_code = self.process.returncode
        if return_code != 0:
            self.fail_exitcode(return_code)

    def fail_exitcode(self, return_code):
        message = "Job {name} failed with code {code}".format(name=self.name, code=return_code)
        config.log.error(message)
        # TODO: Prevent future jobs according to config.
        self.mailer.fail_mail(message)

    def fail_has_stderr(self, stderr_data):
        message = "Job {name} printed things to stderr:".format(name=self.name)
        config.log.error(message)
        body = stderr_data.decode("utf-8")
        config.log.error(body)
        self.mailer.fail_mail(message, body)

    def fail_timeout(self):
        self.process.kill()
        message = "Job {name} timed out after {timeout} seconds".format(name=self.name, timeout=self.timeout)
        config.log.error(message)
        self.mailer.fail_mail(message)
        # FIXME: Job will return SIGKILL now, fail_exitcode should ignore that signal now?

    def status(self):
        """Check for any running instances of this job, in this process or another.

        Returns a crappy dict, or None if no process is found.

        Do not use this function to gate the workflow, explicitly assert the
        lock instead."""

        # FIXME: DRY--find a good line to cut at to split out lock.read_pid.
        lock_path = lock.path_for_job(self.slug)
        if os.path.exists(lock_path):
            with open(lock_path, "r") as f:
                pid = int(f.read().strip())
                # TODO: encapsulate
                return {"status": "running", "pid": pid}

        return None
