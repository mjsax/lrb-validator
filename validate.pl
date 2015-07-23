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
# Author	:	Igor Pendan
# Date  	:	2004
# Purposes	:
# Modified history :
#      Name        Date           Comment
#      -------     -----------    ---------------------------------
#      Nga         8/27/04        Split expressways
####################################################################
use DBI;
use strict;
use FileHandle;
use Getopt::Long;

my $verbose = 'Print verbose informtion';	# option variable with default value (false)
my $debug = 'Print debug information (implies verbose)';	# option variable with default value (false)
my $propertyfile = ''; # Path to properties file

# somehow declaring sub arguments fails because the argument names are not declared (-> sense?)
sub properties_file_arg { 
    $propertyfile = $_[0]; 
}

# apparently non-option arguments can only be specified using subroutine being
# associated with '<>'<ref>http://perldoc.perl.org/Getopt/Long.html</ref>
GetOptions ('verbose' => \$verbose, 'debug' => \$debug, '<>' => \&properties_file_arg)
or die("Option parsing failed due to previously indicated error"); # GetOptions writes error messages
    # with warn() and die(), so they should be definitely displayed

if ( $propertyfile eq '' ) {
    die "A path to a properties file has to be specified as non-option argument";
}

my $currLine;
my @currProp;

my $dbname;
my $dbuser;
my $dbpassword;
my $logfile;
my $logvar;

#BEGIN {
#	open (STDERR, ">execution.log");
#}

#******************** Import properties
open( PROPERTIES , "$propertyfile") || die("Could not open file: $!");
while (  $currLine = <PROPERTIES>){
	chomp ( $currLine );

        if (!$currLine){
	    next;
	}

	@currProp=split( /=/, $currLine  );

	if ( $currProp[0] eq "keeplog") {
		$logvar=$currProp[1];
	}
	if ( $currProp[0] eq "logfile") {
		$logfile=$currProp[1];
	}
	if ( $currProp[0] eq "databasename") {
		$dbname=$currProp[1];
	}	
	if ( $currProp[0] eq "databaseusername") {
		$dbuser=$currProp[1];
	}
	if ( $currProp[0] eq "databasepassword") {
		$dbpassword=$currProp[1];
	}

}
close ( PROPERTIES );

#print "$dbname\n";
#print "$dbuser\n";
#print "$dbpassword\n";
#print "$logfile\n";
#print "$logvar\n";
#print "$carDataInput\n";
#print "$accountbalance\n";
#print "$dailyexpenditure\n";
#print "$completeHistory\n";
#print "$tollAlerts\n";
#print "$accidentalerts\n";

my $startTime = time;

system ("perl dropalltables.pl $dbname $dbuser $dbpassword $logfile $logvar");
print "Drop table done\n";

system ("perl import.pl $propertyfile");
print "Import done\n";

system ("perl indexes.pl $dbname $dbuser $dbpassword $logfile $logvar");
print "Indexes done\n";

# Generate alerts
system ("perl xwayLoop.pl $dbname $dbuser $dbpassword $logfile $logvar");
print "Loop done\n";

#--> IGOR:  All this stuff should move to xwayLoop.pl if you want to split, otherwise it is OK
# Split types
system("perl splitbytype.pl $dbname $dbuser $dbpassword $logfile $logvar");
print "split by type done\n";

system ("perl accountBalanceAnswer.pl $dbname $dbuser $dbpassword $logfile $logvar");
print "account Balance done\n";

system ("perl dailyExpenditureAnswer.pl $dbname $dbuser $dbpassword $logfile $logvar");
print "Daily expenditure done\n";


# Validation
system("perl compareAlerts.pl  $dbname $dbuser $dbpassword $logfile $logvar");
print "compare alerts table done\n";

system ("perl accountBalanceValidation.pl $dbname $dbuser $dbpassword $logfile $logvar");
print "accountBalanceValidation.pl done\n";

system ("perl dailyExpenditureValidation.pl $dbname $dbuser $dbpassword $logfile $logvar");
print "dailyExpenditureValidation.pl done\n";


my $runningTime = time - $startTime;
print "Total running time: $runningTime\n";


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
