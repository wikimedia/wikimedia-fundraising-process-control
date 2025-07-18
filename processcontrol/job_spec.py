import glob
import os

from . import config


# TODO: uh has no raison d'etre now other than to demonstrate factoryness.
def load(job_name):
    return Job(slug=job_name)


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


class Job(object):
    def __init__(self, slug=None):
        self.global_config = config.GlobalConfiguration()
        self.config_path = job_path_for_slug(slug)

        # Validate that we're not allowing directory traversal.
        job_directory = os.path.abspath(self.global_config.get("job_directory"))
        assert os.path.dirname(os.path.realpath(self.config_path)) == job_directory, \
            "You may only run jobs with configuration files in '{path}'".format(path=job_directory)

        self.config = config.JobConfiguration(self.global_config, self.config_path)

        self.name = self.config.get("name")
        self.slug = slug
        if self.config.has("timeout"):
            self.timeout = self.config.get("timeout")
        else:
            self.timeout = 0

        if self.config.has("disabled") and self.config.get("disabled") is True:
            self.enabled = False
        else:
            self.enabled = True

        if not self.config.has("schedule"):
            self.enabled = False

        self.environment = os.environ.copy()
        if self.config.has("environment"):
            # Force all values to string
            str_env = {k: str(v) for k, v in self.config.get("environment").items()}
            self.environment.update(str_env)

        self.commands = self.config.get_as_list("command")

        if self.config.has("slow_start_command"):
            self.slow_start_command = self.config.get_as_list("slow_start_command")
        else:
            self.slow_start_command = False

        if self.config.has("tag"):
            self.tags = self.config.get_as_list("tag")
        else:
            self.tags = []

        if self.config.has("description"):
            self.description = self.config.get("description")
        else:
            self.description = None

        if self.config.has("allow_overtime"):
            self.allow_overtime = self.config.get("allow_overtime")
        else:
            self.allow_overtime = False

        if self.config.has("failure_threshold_for_mail"):
            self.failure_threshold_for_mail = self.config.get("failure_threshold_for_mail")
        else:
            self.failure_threshold_for_mail = 1
