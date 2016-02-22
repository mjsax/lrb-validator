#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# Copyright (C) 2014 - 2015 Humboldt-Universität zu Berlin
# %
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# Performs actions which can't be performed as root user (e.g. invoking
# `initdb`). This separation avoid fidling with privileges.

import logging
import validate_globals
import subprocess as sp
import pexpect
import sys
import psycopg2
import threading
import time
import plac
import os
import generate_validate_config
import signal
import ipaddress

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger_stdout_handler = logging.StreamHandler()
logger_stdout_handler.setLevel(logging.DEBUG)
logger_formatter = logging.Formatter('%(asctime)s:%(message)s')
logger_stdout_handler.setFormatter(logger_formatter)
logger.addHandler(logger_stdout_handler)

postgres_version = (9,4)
initdb_default = "/usr/lib/postgresql/9.4/bin/initdb"
postgres_default = "/usr/lib/postgresql/9.4/bin/postgres"
psql_default = "/usr/lib/postgresql/9.4/bin/psql"
createdb_default = "/usr/lib/postgresql/9.4/bin/createdb"

class Bootstrapper():
    """Allows monitoring of the bootstrap progress and control over the database
    process which is very useful to write elegant and small code for callers and
    avoids the need to communicate with signals where python functions can be
    used. Basic signal handling is provided, though.
    """
    def __init__(self, initdb=initdb_default,
        postgres=postgres_default,
        createdb=createdb_default,
        base_dir_path=validate_globals.base_dir_path_default,
        db_name=validate_globals.database_name_default,
        db_host=validate_globals.database_host_default,
        db_user=validate_globals.database_user_default,
        db_pass=validate_globals.database_password_default,
        shutdown_server=False
    ):
        self.initdb=initdb
        self.postgres=postgres
        self.createdb=createdb
        self.base_dir_path=base_dir_path
        self.db_name=db_name
        self.db_host = db_host
        self.db_user=db_user
        self.db_pass=db_pass
        self.shutdown_server=shutdown_server
        self.shutdown_event = threading.Event()

    def stop(self, wait=True):
        """Initializes the shutdown process for the database server. Waits for
        the server to be shut down depending on whether `wait` is `True` or
        `False`."""
        self.shutdown_event.set()
        if wait is True:
            self.waitFor()

    def start(self):
        # generate validate.config
        generate_validate_config.generate_validate_config()

        # generate and start database
        db_dir_path = os.path.join(self.base_dir_path, "database")
        created = False
        if not os.path.exists(db_dir_path):
            logger.debug("creating PostgreSQL database in '%s'" % (db_dir_path,))
            sp.check_call([self.initdb, db_dir_path])
            created = True
        else:
            logger.debug("skipping creation of existing database '%s' (assuming the database is setup correctly which means that remaining rests of a crashed setup need to be removed manually)" % (db_dir_path,))
        db_server_proc = None
        class DBThread(threading.Thread):
            def __init__(self, shutdown_event, postgres, db_host):
                super(DBThread, self).__init__()
                self.shutdown_event = shutdown_event
                self.postgres = postgres
                self.db_host = db_host

            def run(self):
                logger.debug("starting PostgreSQL server")
                try:
                    ipaddress.ip_address(self.db_host)
                except ValueError:
                    # db_host is a socket path
                    if not os.path.exists(self.db_host):
                        logger.info("creating inexisting database host (socket directory) '%s'" % (self.db_host,))
                        os.makedirs(self.db_host)
                    elif not os.path.isdir(self.db_host):
                        raise ValueError("path for database host (socket directory) '%s' points to an existing file or link" % (self.db_host,))
                db_server_proc = sp.Popen([self.postgres, "-D", db_dir_path, "-k", self.db_host,
                    "--checkpoint_segments=48", # avoiding `LOG:  checkpoints are occurring too frequently ([n] seconds apart)` (occured with 24)
                ])
                while not self.shutdown_event.is_set() and db_server_proc.poll() == None:
                    time.sleep(1) # in python 3.x it might be better to use subprocess.Popen.wait with timeout because it used short sleeps of the asyncio module<ref>https://docs.python.org/3.4/library/subprocess.html#subprocess.Popen.wait</ref>
                if not not self.shutdown_event.is_set():
                    logger.debug("server shutdown requested")
                if db_server_proc.poll() == None:
                    db_server_proc.send_signal(signal.SIGINT)
                    try_1_time = 0
                    try_1_time_max = 5
                    try_1_interval = .5
                    while db_server_proc.poll() == None and try_1_time < try_1_time_max:
                        try_1_time += try_1_interval
                        time.sleep(try_1_interval)
                    if db_server_proc.poll() == None:
                        db_server_proc.terminate()
                elif db_server_proc.returncode != 0:
                    raise RuntimeError("server process returned abnormally with code %d" % (db_server_proc.returncode,))
        self.db_thread = DBThread(shutdown_event=self.shutdown_event, postgres=self.postgres, db_host=self.db_host)
        self.db_thread.start()
        conn = None
        try_time = 0
        try_time_max = 10 # time in seconds in which we try to connect to the server
        try_interval = .5
        # wait until the server is up (don't connect as db_user, because initially
        # only the postgres user is available (and linear shouldn't be the
        # maintenance user)
        while try_time < try_time_max:
            try:
                conn = psycopg2.connect(dbname="postgres", host=self.db_host, async=False)
                logger.debug("database connection established successfully")
                break
            except Exception as db_connect_ex:
                logger.debug("waiting another %d s for the server to come up" % (try_time_max-try_time,))
                try_time += try_interval
                time.sleep(try_interval)
        if conn == None:
            self.stop(wait=True)
            raise Exception("Database connection could repeatedly not be created due to (last exception) '%s'" % (str(db_connect_ex),))
        if created:
            cur = conn.cursor()
            logger.debug("creating user %s" % (self.db_user,))
            cur.execute("""create user %s with encrypted password '%s' login""" % (self.db_user, self.db_pass))
            conn.commit()
            logger.debug("creating database %s" % (self.db_name,))
            createdb_proc = pexpect.spawn(str.join(" ", [self.createdb, "--owner=%s" % (self.db_user,), "-W", "--host=%s" % (self.db_host,), "--port=5432", self.db_name]))
            createdb_proc.expect(['Password:', "Passwort:"])
            createdb_proc.sendline(self.db_pass)
            createdb_proc.expect(pexpect.EOF) # wait for termination
            #conn = psycopg2.connect(dbname="postgres", host='/tmp', async=False)
            #cur = conn.cursor()
            logger.debug("granting permissions")
            cur.execute("""grant all on database "%s" to %s""" % (self.db_name, self.db_user))
            #cur.close()
            #conn.close()
            conn.commit()
        success_message = "Setup successful :)"
        logger.info("""
    %s
    %s
    %s""" % ("*"*(len(success_message)+4), "* %s *" % success_message, "*"*(len(success_message)+4)))
        logger.info("database is still running and can (and should) be used for LRB validator's validate.pl")
        if self.shutdown_server:
            if self.db_thread != None:
                self.shutdown_event.set()
                logger.debug("waiting for server to terminate")
            self.stop(wait=True)
        else:
            logger.info("registering signal handler for SIGINT to shutdown database cleanly")
            def __handler__(signum, frame):
                logger.info("received SIGINT, terminating database process")
                self.shutdown_event.set()
            signal.signal(signal.SIGINT, __handler__)

    def waitFor(self):
        while self.db_thread.is_alive():
            self.db_thread.join(timeout=0.1)


def bootstrap_unprivileged(initdb=initdb_default,
    postgres=postgres_default,
    createdb=createdb_default,
    base_dir_path=validate_globals.base_dir_path_default,
    db_name=validate_globals.database_name_default,
    db_host = validate_globals.database_host_default,
    db_user=validate_globals.database_user_default,
    db_pass=validate_globals.database_password_default,
    shutdown_server=False
):
    """creates, starts and returns a `Bootstrapper`"""
    ret_value = Bootstrapper(initdb=initdb,
        postgres=postgres,
        createdb=createdb,
        base_dir_path=base_dir_path,
        db_name=db_name,
        db_host=db_host,
        db_user=db_user,
        db_pass=db_pass,
        shutdown_server=shutdown_server
    )
    ret_value.start()
    return ret_value

def main():
    plac.call(bootstrap_unprivileged)

if __name__ == "__main__":
    main()
