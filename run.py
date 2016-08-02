#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# Copyright (C) 2014 - 2016 Humboldt-Universität zu Berlin
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

# Initializes the database if not already initialized (including creation of
# user with appropriate permissions), starts the database server (including
# waiting for the server to be available) and handles its graceful shutdown.
#
# The purpose of the script is to handle the fact that `validate.pl` does
# neither start nor shutdown the database server it needs to run.
#
# Expects `run_once.sh` to have run once.

import bootstrap_unprivileged
import threading
import time
import logging
import subprocess as sp
import plac
import validate_globals

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger_stdout_handler = logging.StreamHandler()
logger_stdout_handler.setLevel(logging.DEBUG)
logger_formatter = logging.Formatter('%(asctime)s:%(message)s')
logger_stdout_handler.setFormatter(logger_formatter)
logger.addHandler(logger_stdout_handler)

@plac.annotations(perl=plac.Annotation("The perl binary to use", "option"),
    server_only=plac.Annotation("A flag which allows to start the database server only", "flag"),
    force_recreate_db=plac.Annotation("A flag which allows to force the recreation of the database scheme (should be used after input data changed and should be unnecessary otherwise)", "flag"),
    base_dir_path=plac.Annotation("The location of the validator input/output data", "option"), # should be fine to expose this since having a database in the data directory makes a lot of sense
    skip_generate_validate_config=plac.Annotation("A flag indicating that the generation of the validate.config file ought to be skipped (e.g. because it has been modified and changes ought not to be overwritten)", "flag"),
    validate_config_file_path=plac.Annotation("The validate.config file to use (will be generated automatically from validate.config.tmpl if the -skip-generate-validate-config flag isn't specified", "option"),
)
def run(perl="perl", server_only=False, base_dir_path=validate_globals.base_dir_path_default, skip_generate_validate_config=False, validate_config_file_path=validate_globals.validate_config_file_path_default, force_recreate_db=False):
    """Runs the relevant perl scripts of the `lrb-validator` and the necessary
    setup and bootstrapping steps before. If the perl scripts fails a
    `subprocess.CalledProcessError` will be raised and the database server will
    be shutdown properly."""
    if server_only is True:
        bootstrapper = bootstrap_unprivileged.bootstrap_unprivileged(base_dir_path=base_dir_path, skip_generate_validate_config=skip_generate_validate_config, validate_config_file_path=validate_config_file_path)
        bootstrapper.startDB(db_dir_path=bootstrapper.generateDBDirPath(), shutdown_server=False)
            # registers SIGINT handler for database process/thread
        bootstrapper.waitFor()
    else:
        bootstrapper = bootstrap_unprivileged.bootstrap_unprivileged(base_dir_path=base_dir_path, skip_generate_validate_config=skip_generate_validate_config, validate_config_file_path=validate_config_file_path)
        bootstrapper.start()
            # registers SIGINT handler for database process/thread
        try:
            logger.info("sleeping 10s to wait for the database server to be available")
            time.sleep(10)

            # `validate.config` has been generated by `bootstrap_unprivileged.py` (if skip_generate_validate_config isn't True), but can
            # be regenerated (e.g. after changes) with `generate_validate_config.py` (see
            # `generate_validate_config.py --help` for usage info)
            try:
                validate_cmds = [perl, "validate.pl"]
                if force_recreate_db is True:
                    validate_cmds += ["-force-recreate-db"]
                validate_cmds += ["validate.config"]
                sp.check_call(validate_cmds)
            except sp.CalledProcessError as ex:
                logger.error("one of the perl scripts failed (see preceeding output for details) with exception '%s', trying to shutdown database server cleanly, then terminating" % (str(ex),))
                if bootstrapper != None:
                    bootstrapper.stop(wait=True)
                return
            logger.info("validation completeted successfully")
            logger.info("terminating python database process")
            bootstrapper.stop(wait=True)
        except Exception as ex:
            logger.error("the unexpected exception '%s' occured, trying to shutdown database server cleanly, then terminating" % (str(ex),))
            if bootstrapper != None:
                bootstrapper.stop(wait=True)

if __name__ == "__main__":
    plac.call(run)
