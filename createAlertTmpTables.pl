#!/usr/bin/perl -w

####################################################################
# Author	:	Nga Tran
# Date   	:       Aug 24, 2004
# Purposes	:
#	. Create alerts temporary tables
# Modified history :
#      Name        Date           Comment
#      -------     -----------    ---------------------------------
####################################################################


use strict;
use DBI qw(:sql_types);
use FileHandle;

#BEGIN {
#    open (STDERR, ">>execution.log");
#}

# Process arguments
my @arguments = @ARGV;
my $dbName = shift(@arguments);
my $userName = shift(@arguments);
my $password = shift(@arguments);
my $logFile = shift(@arguments);
my $logVar = shift(@arguments);

writeToLog($logFile, $logVar, "createAlertTmpTables in progress ...\n");

# Connect to test Postgres database
my $dbh = DBI->connect(
            "DBI:PgPP:$dbName", "$userName", "$password",
            {PrintError => 0, AutoCommit => 1}
          ) || die "Could not connect to database:  $DBI::errstr";

eval
{
   my $startTime = time;

   createTollAccAlertsTmpTable($dbh);

   my $runningTime = time - $startTime;
   writeToLog($logFile, $logVar,  "Total createAlertTmpTables running time: $runningTime seconds\n\n");
};
print $@;

$dbh->disconnect;

exit(0);

#----------------------------------------------------------------


sub createTollAccAlertsTmpTable
{
   my ($dbh) = @_; 

   $dbh->do("DROP TABLE tollAccAlertsTmp;");

#   $dbh->do("CREATE TABLE TollAccAlertsTmp(   
#  	          time   INTEGER,
#  	          carid  INTEGER,
#      	          xway   INTEGER,
#  	          dir    INTEGER,
#  	          seg    INTEGER,
#  	          lav    INTEGER,
#  	          toll   INTEGER,
#  	          accidentSeg INTEGER);");

   $dbh->do("CREATE TABLE TollAccAlertsTmp(   
  	          time   INTEGER,
  	          carid  INTEGER,
  	          dir    INTEGER,
  	          seg    INTEGER,
  	          lav    INTEGER,
  	          toll   INTEGER,
  	          accidentSeg INTEGER);");
}

#--------------------------------------------------------------------------------

sub logTime {
	my ($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst)=localtime(time);
	return ( ($mon+1)."-".$mday."-".($year+1900)." ".$hour.":".$min.":".$sec );
}


sub writeToLog {
	my ( $logfile, $logvar, $logmessage ) = @_;
	if ($logvar eq "yes") {
		open( LOGFILE1, ">>$logfile")  || die("Could not open file: $!");
		LOGFILE1->autoflush(1);
		print LOGFILE1 ( logTime()."> $logmessage"."\n");
		close (LOGFILE1);
	}
}