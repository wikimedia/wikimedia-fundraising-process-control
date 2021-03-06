from email.mime.text import MIMEText
import smtplib
import socket


class Mailer(object):
    def __init__(self, job):
        self.job = job
        self.from_address = job.config.get("failmail/from_address")
        self.to_address = job.config.get("failmail/to_address")
        # FIXME: this is set to ensure one failmail per instance. Should
        # do something more sophisticated to collect all calls and send
        # the mail before exiting.
        self.sent_fail_mail = False

    def fail_mail(self, subject, logfile=None):
        if logfile is not None:
            body = "See the logs for more information: {logfile}".format(logfile=logfile)
        else:
            body = "No details available."
        if self.sent_fail_mail:
            return

        msg = MIMEText(body)

        msg["Subject"] = "Fail Mail ({host}) run-job: {subject}".format(
            host=socket.gethostname(),  # Why not os.gethostname?
            subject=subject
        )
        msg["From"] = self.from_address
        msg["To"] = self.to_address

        mailer = smtplib.SMTP("localhost")
        mailer.sendmail(
            self.from_address,
            self.to_address,
            msg.as_string()
        )
        mailer.quit()
        # only send one failmail per instance
        self.sent_fail_mail = True
