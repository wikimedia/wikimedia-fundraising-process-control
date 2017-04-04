import copy
import logging
import logging.config
import os
import sys
import yaml


CONFIG_PATH = "/etc/process-control.yaml"

# FIXME: Offload responsibility for logging.
log = None


def setup_logging(global_config=None):
    global log

    if log is not None:
        # Already initialized.
        return

    if global_config is None:
        global_config = GlobalConfiguration()

    if global_config.has("logging"):
        # Configure from global config.
        log_config = global_config.get("logging")
        logging.config.dictConfig(log_config)
        log = logging.getLogger("process-control")
        log.info("Configured logging.")
        log.debug(log_config)
    else:
        # Set to the root logger.
        log = logging.getLogger()

    if sys.stdout.isatty():
        log.addHandler(logging.StreamHandler(sys.stdout))


class Configuration():

    def __init__(self, defaults={}):
        self.values = defaults

    def get(self, path):
        """Get a value from configuration.
        You can get a nested property by using a path delimited by
        forward slashes (/), for example "failmail/from-address".

        Trying to get a missing property raises a MissingKeyException.
        """
        parts = path.split("/")
        current = self.values

        for part in parts:
            if part not in current:
                raise MissingKeyException(path)
            current = current[part]
        return current

    def has(self, path):
        """Test for existance of a property.
        As with get(), use forward slashes to represent nested properties.
        """
        try:
            self.get(path)
        except MissingKeyException:
            return False
        return True


class MissingKeyException(Exception):

    def __init__(self, path):
        message = "Missing configuration key '" + path + "'"
        super(MissingKeyException, self).__init__(message)


class GlobalConfiguration(Configuration):
    def __init__(self):
        Configuration.__init__(self)
        self.load_global_config()

        # Semi-opportunistic place to initialize logging.
        setup_logging(self)

    def load_global_config(self):
        """Load configuration from global config paths.
        Later entries override earlier entries.
        """
        if os.access(CONFIG_PATH, os.R_OK):
            with open(CONFIG_PATH, "r") as f:
                config = yaml.safe_load(f)
            self.values.update(config)

        self.validate_global_config()

    def validate_global_config(self):
        assert "cron_template" in self.values
        assert "job_directory" in self.values
        assert "output_crontab" in self.values
        assert "output_directory" in self.values
        assert "runner_path" in self.values
        assert "user" in self.values


class JobConfiguration(Configuration):

    def __init__(self, global_config, config_path):
        if global_config.has("default_job_config"):
            defaults = copy.deepcopy(global_config.get("default_job_config"))
        else:
            defaults = {}
        Configuration.__init__(self, defaults)

        with open(config_path, "r") as f:
            self.values.update(yaml.safe_load(f))

        # TODO: Catch and interpret errors.
        self.validate_job_config()

    def validate_job_config(self):
        assert "name" in self.values

        assert "command" in self.values
        assert "\n" not in self.values["command"]

        if "schedule" in self.values:
            # No tricky assignments.
            assert "=" not in self.values["schedule"]
            # Legal cron, but I don't want to deal with it.
            assert "@" not in self.values["schedule"]
            # No line breaks
            assert "\n" not in self.values["schedule"]

            # Be sure the schedule is valid.
            terms = self.values["schedule"].split()
            assert len(terms) == 5
