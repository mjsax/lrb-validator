#!/usr/bin/perl -w
#
#  Copyright (C) 2004 - 2015
#  %
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

# Please consider the following "Modified history" a legacy revision management
# which has been taken over by git
####################################################################
# Author    :   Nga Tran
# Date      :   Aug, 2004
# Purposes  :
#   . Drop/Create tables and Indexes
# Modified history :
#      Name        Date           Comment
#      -------     -----------    ---------------------------------
#      Nga         8/24/04        Generate for only 1 expresss way
####################################################################


use strict;
use DBI qw(:sql_types);
use FileHandle;
use Log::Log4perl qw(:easy);

Log::Log4perl->easy_init($DEBUG);
my $logger = Log::Log4perl->get_logger('lrb_validator.import');

#BEGIN {
#    open (STDERR, ">>execution.log");
#}

# Process arguments
my @arguments = @ARGV;
my $dbname = shift(@arguments);
my $dbhost = shift(@arguments);
my $dbuser = shift(@arguments);
my $dbpassword = shift(@arguments);
my $logFile = shift(@arguments);
my $logVar = shift(@arguments);

$logger->info("runDdl in progress ...");

# Connect to test Postgres database
my $dbh  = DBI->connect(
            "DBI:Pg:dbname=$dbname;host=$dbhost", "$dbuser", "$dbpassword",
            {PrintError => 1}
          ) || $logger->logdie("Could not connect to database:  $DBI::errstr");

eval
{
   my $startTime = time;

   createAccidentTable($dbh);
   createStatisticsTable($dbh);
   createTollAccAlertsTable($dbh);
   createComparedTables($dbh);

   my $runningTime = time - $startTime;
   $logger->info( "Total runDdl running time: $runningTime seconds");
};
print $@;

$dbh->disconnect;

exit(0);

#----------------------------------------------------------------

sub createAccidentTable
{
   my ($dbh) = @_;

   $dbh->do("DROP TABLE accident;");

#   $dbh->do("CREATE TABLE accident(
#               carid1 integer,
#               carid2 integer,
#               firstMinute integer,
#               lastMinute integer,
#               xway integer,
#               dir integer,
#               seg integer,
#               pos integer,
#               PRIMARY KEY (xway, dir, pos, firstMinute)
#              );");

   $dbh->do("CREATE TABLE accident(
               carid1 integer,
               carid2 integer,
               firstMinute integer,
               lastMinute integer,
               dir integer,
               seg integer,
               pos integer,
               PRIMARY KEY ( dir, pos, firstMinute)
              );");
}

#----------------------------------------------------------------

sub createStatisticsTable
{
   my ($dbh) = @_;

   $dbh->do("DROP TABLE statistics;");

#   $dbh->do("CREATE TABLE statistics(
#             xway integer,
#             dir  integer,
#             seg  integer,
#             minute integer,
#             numvehicles  integer,
#             lav   integer,
#                 toll  integer,
#                 accident integer,
#                 accidentSeg integer);");

   $dbh->do("CREATE TABLE statistics(
              dir  integer,
              seg  integer,
              minute integer,
              numvehicles  integer,
              lav   integer,
                  toll  integer,
                  accident integer,
                  accidentSeg integer);");

}

#----------------------------------------------------------------

sub createTollAccAlertsTable
{
   my ($dbh) = @_;

   $dbh->do("DROP TABLE tollAccAlerts;");

#   $dbh->do("CREATE TABLE TollAccAlerts(
#             time   INTEGER,
#             carid  INTEGER,
#             xway   INTEGER,
#             dir    INTEGER,
#             seg    INTEGER,
#             lav    INTEGER,
#             toll   INTEGER,
#             accidentSeg INTEGER);");

   $dbh->do("CREATE TABLE TollAccAlerts(
              time   INTEGER,
              carid  INTEGER,
              dir    INTEGER,
              seg    INTEGER,
              lav    INTEGER,
              toll   INTEGER,
              accidentSeg INTEGER);");

}

#----------------------------------------------------------------

sub createComparedTables
{
   my ($dbh) = @_;

   $dbh->do("DROP TABLE accAlertNotInValidator;");
   $dbh->do("DROP TABLE accAlertNotInOriginal;");
   $dbh->do("DROP TABLE tollAlertNotInValidator;");
   $dbh->do("DROP TABLE tollAlertNotInOriginal;");

   $dbh->do("CREATE TABLE accAlertNotInValidator(
               time  INTEGER,
               carid INTEGER,
               seg   INTEGER);");

   $dbh->do("CREATE TABLE accAlertNotInOriginal(
               time  INTEGER,
               carid INTEGER,
               seg   INTEGER);");

   $dbh->do("CREATE TABLE tollAlertNotInValidator(
               time  INTEGER,
               carid INTEGER);");

   $dbh->do("CREATE TABLE tollAlertNotInOriginal(
               time  INTEGER,
               carid INTEGER);");
}
