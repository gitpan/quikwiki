#!/usr/bin/perl
# $Id: ODBCTable.cgi,v 1.1.1.1 2007/06/21 20:01:21 kiesling Exp $
use UnixODBC ':all';
my ($user, $password, $dsn, $sqlquery) = 
    ($ENV{QUERY_STRING} =~ 
     /username\=(.*?)&password\=(.*?)\&dsn\=(.*?)&sqlquery\=(.*?)$/);
$sqlquery =~ s/\+/ /g;
$sqlquery =~ s/%(..)/pack ('c', hex ($1))/ge;


my ($r, $evh, $cnh, $sth);
# SQLGetDiagRec variables
my ($native, $diag_message, $length);
my $maxlength = 65536;
my ($text, $text_length);

my $httpheader =<<ENDHTTP;
Content-type: text/html

ENDHTTP

my $starthtml =<<EOH;
<html><title>$dsn: $sqlquery</title>
<body bgcolor="white">
EOH

print "$httpheader$starthtml";

my $endhtml =<<EOE;
</body>
</html>
EOE

$r = SQLAllocEnv ($evh);
if (($r!=$SQL_SUCCESS)&&($r!=$SQL_NO_DATA)) {
    SQLGetDiagRec ($SQL_HANDLE_ENV, $evh, 1, $sqlstate, 
		   $native, $diag_message, $maxlength, $length);
    print "<tt>[SQLAllocEnv]$diag_message</tt>$endhtml";
    exit 1;
}

$r = SQLSetEnvAttr($evh, $SQL_ATTR_ODBC_VERSION, $SQL_OV_ODBC2, 0);
if (($r!=$SQL_SUCCESS)&&($r!=$SQL_NO_DATA)) {
    SQLGetDiagRec ($SQL_HANDLE_ENV, $evh, 1, $sqlstate, 
		   $native, $diag_message, $maxlength, $length);
    print "<tt>[SQLSetEnvAttr]$diag_message</tt>$endhtml";
    exit 1;
}

$r = SQLAllocConnect ($evh, $cnh);
if (($r!=$SQL_SUCCESS)&&($r!=$SQL_NO_DATA)) {
    SQLGetDiagRec ($SQL_HANDLE_ENV, $evh, 1, $sqlstate, 
		   $native, $diag_message, $maxlength, $length);
    print "<tt>[SQLAllocConnect]$diag_message</tt>$endhtml";
    exit 1;
}

$r = SQLConnect ($cnh, $dsn, $SQL_NTS,
			    $user, $SQL_NTS,
			    $password, $SQL_NTS);
if (($r!=$SQL_SUCCESS)&&($r!=$SQL_NO_DATA)) {
    SQLGetDiagRec ($SQL_HANDLE_DBC, $cnh, 1, $sqlstate, 
		   $native, $diag_message, $maxlength, $length);
    print "<tt>[SQLConnect]$diag_message</tt>$endhtml";
    exit 1;
}

$r = SQLAllocHandle ($SQL_HANDLE_STMT, $cnh, $sth);
if (($r!=$SQL_SUCCESS)&&($r!=$SQL_NO_DATA)) {
    SQLGetDiagRec ($SQL_HANDLE_STMT, $sth, 1, $sqlstate, 
		   $native, $diag_message, $maxlength, $length);
    print "<tt>[SQLAllocHandle]$diag_message</tt>$endhtml";
    exit 1;
}

$r = SQLPrepare ($sth, $sqlquery, length ($sqlquery));
if (($r!=$SQL_SUCCESS)&&($r!=$SQL_NO_DATA)) {
    SQLGetDiagRec ($SQL_HANDLE_STMT, $sth, 1, $sqlstate, 
		   $native, $diag_message, $maxlength, $length);
    print "<tt>[SQLPrepare]$diag_message</tt>$endhtml";
    exit 1;
}

$r = SQLExecute ($sth);
if (($r!=$SQL_SUCCESS)&&($r!=$SQL_NO_DATA)) {
    SQLGetDiagRec ($SQL_HANDLE_STMT, $sth, 1, $sqlstate, 
		   $native, $diag_message, $maxlength, $length);
    print "<tt>[SQLExecute]$diag_message</tt>$endhtml";
    exit 1;
}

$r = SQLNumResultCols ($sth, $ncols);
if (($r!=$SQL_SUCCESS)&&($r!=$SQL_NO_DATA)) {
    SQLGetDiagRec ($SQL_HANDLE_STMT, $sth, 1, $sqlstate, 
		   $native, $diag_message, $maxlength, $length);
    print "<tt>[SQLNumResultCols]$diag_message</tt>$endhtml";
    exit 1;
}

$r = SQLRowCount ($sth, $nrows);
if (($r!=$SQL_SUCCESS)&&($r!=$SQL_NO_DATA)) {
    SQLGetDiagRec ($SQL_HANDLE_STMT, $sth, 1, $sqlstate, 
		   $native, $diag_message, $maxlength, $length);
    print "<tt>[SQLRowCount]$diag_message</tt>$endhtml";
    exit 1;
}


my $clabel = ($ncols == 1) ? 'column' : 'columns';
print qq{<i>$nrows rows, $ncols $clabel in result set.</i><p>\n};

print qq{<table border="1" cellpadding="5">};
print qq{<tr>};

for my $col (1..$ncols) {
    $r = SQLDescribeCol ($sth, $col, $columname, 255, $head_len, 
			 $data_type, $column_size, $decimal_digits, 
			 $nullable);
    if ($r!=$SQL_SUCCESS) {
	SQLGetDiagRec ($SQL_HANDLE_STMT, $sth, 1, $sqlstate, 
		       $native, $diag_message, 255, $length);
	print "<tt>[SQLDescribeCol]$diag_message</tt>$endhtml";
    }
    print qq{<td><b>$columname</b></td>};
    last if $r == $SQL_NO_DATA;
}
print qq{</tr>};

while (1) {
    print qq{<tr>};
    $r = SQLFetch ($sth);
    last if $r == $SQL_NO_DATA;
    if ($r!=$SQL_SUCCESS) {
	SQLGetDiagRec ($SQL_HANDLE_STMT, $sth, 1, $sqlstate, 
		       $native, $diag_message, $maxlength, $length);
	print "<tt>[SQLFetch]$diag_message</tt>$endhtml";
	exit 1;
    }
    for my $col (1..$ncols) {
	$r = SQLGetData ($sth, $col, $SQL_C_CHAR, $text, $maxlength, 
			 $text_length);
	if ($r!=$SQL_SUCCESS) {
	    SQLGetDiagRec ($SQL_HANDLE_STMT, $sth, 1, $sqlstate, 
			   $native, $diag_message, 255, $length);
	    print "<tt>[SQLGetData]$diag_message</tt>$endhtml";
	    exit 1;
	}
	print qq{<td>$text</td>};
	last if $r == $SQL_NO_DATA;
    }
    print qq{<tr>};
}

print qq{</table>$endhtml};

$r = SQLFreeHandle ($SQL_HANDLE_STMT, $sth);
if (($r!=$SQL_SUCCESS)&&($r!=$SQL_NO_DATA)) {
    SQLGetDiagRec ($SQL_HANDLE_STMT, $sth, 1, $sqlstate, 
		   $native, $diag_message, $maxlength, $length);
    print "<tt>[SQLFreeHandle (STMT)]$diag_message</tt>$endhtml";
    &endhtml;
}

$r = SQLDisconnect ($cnh);
if (($r!=$SQL_SUCCESS)&&($r!=$SQL_NO_DATA)) {
    SQLGetDiagRec ($SQL_HANDLE_DBC, $cnh, 1, $sqlstate, 
		   $native, $diag_message, $maxlength, $length);
    print "<tt>[SQLDisconnect]$diag_message</tt>$endhtml";
    exit 1;
}

$r = SQLFreeConnect ($cnh);
if (($r!=$SQL_SUCCESS)&&($r!=$SQL_NO_DATA)) {
    SQLGetDiagRec ($SQL_HANDLE_DBC, $cnh, 1, $sqlstate, 
		   $native, $diag_message, $maxlength, $length);
    print "<tt>[SQLFreeConnect]$diag_message</tt>$endhtml";
    exit 1;
}

$r = SQLFreeHandle ($SQL_HANDLE_ENV, $evh);
if (($r!=$SQL_SUCCESS)&&($r!=$SQL_NO_DATA)) {
    SQLGetDiagRec ($SQL_HANDLE_ENV, $evh, 1, $sqlstate, 
		   $native, $diag_message, $maxlength, $length);
    print "<tt>[SQLFreeHandle (ENV)]$diag_message</tt>$endhtml";
    exit 1;
}




