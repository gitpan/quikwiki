#!/usr/bin/perl 

# $Id: quikwiki.cgi,v 1.28 2004/05/29 10:19:37 kiesling Exp $

use warnings;

my $httpheader =<<ENDHTTP;
Content-type: text/html

ENDHTTP

my $starthtml =<<ENDTITLE;
<html><head><title>QuikWiki!</title>
<style type="text/css">
BODY {font-family: sans-serif; font-size: 11 px; } 
</style>
</head><body bgcolor="white">
ENDTITLE

my $endhtml=<<ENDENDHTML;
</body></html>
ENDENDHTML

my $rcs_path = `which rcs`;
my $rcs_ok = ((-d 'RCS') && (length($rcs_path) && $rcs_path !~ /no rcs/))?1:0;

my $s = $ENV{SERVER_NAME};
my $q = $ENV{QUERY_STRING};
my $scriptname = $ENV{SCRIPT_NAME};
my $method = $ENV{REQUEST_METHOD};
my ($pboundary, $content, $content_length);
my $referer = $ENV{HTTP_REFERER};
if ($method =~ /POST/) {
    ($pboundary) = ($ENV{CONTENT_TYPE} =~ /boundary=(.*)/);
    $content_length = $ENV{CONTENT_LENGTH};
    binmode STDIN, ':crlf';
    read STDIN, $content, $content_length;
    w_save ($content);
}

my ($word, $action, $data) = split '&', $q, 3;
$word = 'HomePage' if ! $word;

$action = ($action and -f $word) ? $action : ((! -f $word ) ? 'edit' : 'view');

my $page =  (-f $word) ? w_read ($word) : "Describe $word here.";

my $editor = <<ENDEDIT;
<form method="post" action="?$word">
<input type="hidden" name="newname" value="$word">
<textarea name="text" cols="80" rows="30">$page</textarea>
<input type="hidden" name="action" value="save">
<input type="submit" value="Save Page">
</form>
ENDEDIT

if ($word =~ /doc|pod/) {
    print $httpheader . $starthtml;
    w_eval ('WikiHeader') if -f 'WikiHeader';
    seek DATA, 0, 0;
    $d = join "", (<DATA>);
    open POD, "|pod2html" or do {w_pre ("doc: $!"); return; };
    print POD $d; 
    close POD;
    w_eval ('WikiFooter') if -f 'WikiFooter';
    print $endhtml;
    unlink <pod2htm*>;
    exit 0;
}

if ($word =~ /self/) {
    seek DATA, 0, 0; 
    w_pre( join "", (<DATA>));
    exit 0;
}

if ($word =~ /words/) { 
    opendir DIR, '.' or do {w_pre ("words: $!"); return;};
    my @files = grep {/^[A-Z]/ && ! -d $_} readdir DIR;
    closedir DIR;
    @sortedwords = sort @files;
    $wordspage = '';
    foreach (@sortedwords) {
	if (filetype ($_) =~ /text/) {
	    $wordspage .= qq{<a href="?$_">$_</a><br>};
	} else {
	    $wordspage .= qq{<a href="?image&$_">$_</a><br>};
	}
    }
    w_pre ($wordspage);
    exit 0;
}

# ?image&<image_name>
if ($word =~ /image/) {
    no warnings;
    ($imword, $imname) = split /&/, $q;
    no warnings;
    $impage = qq{<p><img src="$imname" alt="$imname">};
    w_out ($impage);
    exit 0;
}

if ($action =~ /view/) {
    w_out ($page);
    exit 0;
}

if ($action =~ /edit/) {
    print $httpheader . $starthtml;
    print qq{<font size="3"><b>Edit "$word"</b></font><br><hr>};
    print $editor . $endhtml;
    exit 0;
} 

sub w_save {
    my $content = $_[0];
    my ($newname) = ($content =~ /name=(.*?)&/);
    my ($text) = ($content =~ /.*?&text=(.*)&action=.*$/);
    $text =~ s/\+/ /g;
    $text =~ s/%(..)/pack ('c', hex ($1))/ge;
    $word=$newname;
    w_write ($newname, $text);
    w_out ($text);
    exit 0;
}

sub w_read {
    my $w = $_[0];
    open WORD, $w or do {return "$w: $!"};
    my $s = '';
    while (defined ($l = <WORD>)) { $s .= $l }
    close WORD;
    return $s;
}

sub w_write {
    my ($name, $text) = @_;
    if ($rcs_ok and ((! -f $name) or (! -f "RCS/$name,v"))) {
	`rcs -i -U -t-"Wiki Page $name." $name`;
    }
    rename $name, "$name.bak" if (-f $name && ! $rcs_ok);
    open OUT, ">$name" or do {w_pre ("Save $name: $!\n"); return 1; };
    print OUT $text;
    print OUT "\n" if $text !~ /\n$/;
    close OUT;
    `ci -u -m'User revision.' $name` if $rcs_ok;
}

sub w_pre {
    my $page = $_[0];
    print $httpheader . $starthtml;
    w_eval ('WikiHeader') if -f 'WikiHeader';
    print qq{<pre>$page</pre>};
    w_eval ('WikiFooter') if -f 'WikiFooter';
    print $endhtml;
}

sub w_out {
    my $page = $_[0];
    $page = words($page);
    $page = lines($page);
    print $httpheader . $starthtml;
    w_eval ('WikiHeader') if -f 'WikiHeader';
    if ($page =~ s/\<\%|\%\>//gm) {w_eval($word); } else {print qq|$page<p>|;}
    w_eval ('WikiFooter') if -f 'WikiFooter';
    print $endhtml;
    exit 0;
}

sub w_eval {
    my $file = $_[0];
    my $script = w_read ($file);
    while ($script =~ /\<\%.*?\%\>/s) {
	my ($text, $expr, $rest) = 
	    ($script =~ /^(.*?)\<\%(.*?)\%\>(.*)$/s);
	my $l = lines ($text); print $l;
	eval $expr;
	print ('<br>'. $@.'<br>') if $@;
	$script = $rest;
    }
    print lines( $script);
}

sub words {
    $page = $_[0];
    foreach my $st (split /\s|\r?\n|\'|\\|\"|\?|\.|\:|,|\*/, $page) {
	next if $st !~ /^[A-Z]/ || ! -f $st;
	$page =~ s/([^\w"<])$st([^\w"])/$1<a href="?$st">$st<\/a>$2/ 
	    if (filetype ($st) =~ /text/);
	$page =~ s/([^\w"<])$st([^\w"])/$1<img src="$st" alt="$st">$2/g
	    if (filetype ($st) =~ /png|jpeg/);
    }
    return $page;
}

sub filetype {
    my $s = $_[0];
    return 0 if ! -f $s;
    my $c = w_read($s);
    return 'png' if (substr ($c, 1, 3) =~ /PNG/);
    return 'jpeg' if (substr ($c, 6, 4) =~ /JFIF/);
    return 'text';
}

sub lines {
    my $page = $_[0];
    # Replace blank lines with paragraph tags.
    # If line is indented, wrap in <tt> tags and <br>.
    $page =~ s/\n\s*?\n|\r\n\s*?\r\n/\n<p>\n/smg;
    # Bold and Italic
    $page =~ s/\'\'\'(.*?)\'\'\'/<b>$1<\/b>/smg;
    $page =~ s/\'\'(.*?)\'\'/<i>$1<\/i>/smg;
    my $newpage = '';
    foreach my $l (split /(\n)/, $page) {
	if ($l =~ /^(\t|        )\*/) {
	    $l =~ s/^(\t|        )\*/<li>/;
	    $newpage .= $l;
	} elsif (substr ($l, 0, 1) eq ' ') {
	    local $i = 0;
	    while ( substr($l, $i, 1) eq ' ') {
		substr($l, $i++, 1, '&nbsp;');
	    }
	    $newpage .= "<tt>$l</tt><br>\n";
	} elsif ($l =~ /^----/) {
	    $l =~ s/^----//;
	    $newpage .= ('<hr>' . $l);
	} else {
	    $newpage .= "$l";
	} 
    }
    return $newpage;
}


__END__

=head1 NAME

quikwiki.cgi - Simple Perl/CGI Wiki.

=head1 SYNOPSIS

  # View the page named, "HomePage."
  http://<host>/quikwiki/quikwiki.cgi?HomePage   

  # Edit the page, "HomePage."
  http://<host>/quikwiki/quikwiki.cgi?&action=edit

  # Create and edit page named, "NewPage."
  http://<host>/quikwiki/quikwiki.cgi?NewPage&action=new

  # View the QuikReference page.
  http://<host>/quikwiki/quikwiki.cgi?QuikReference


  # If quickwiki.cgi is renamed or symlinked to index.cgi:

  http://<host>/quikwiki/?HomePage

  # Edit the page named, "MyPage."  
  http://<host>/quikwiki/?MyPage&action=edit 

  # Create and edit page named, "NewPage."
  http://<host>/quikwiki/?NewPage

=head1 DESCRIPTION

QuikWiki outputs HTML of text files ("pages") that contain Wiki markup
tags (see, "L<"Text Markup">") and references to other pages and
images ("words").  QuikWiki's words correspond to page and image
files.  When displayed, word references appear in HTML B<E<lt>a
hrefE<gt>> tags.

By convention Wiki words start with uppercase letters and contain
mixed-case alphanumeric characters.  These are valid words.

  HomePage
  AreaCode916
  TableOfContents
  Addresses

"L<"Documentation Words">" and "L<"Action Words">," tell QuikWiki
which action to take when displaying pages.

URL parameters provide page and action words. If the URL does not
contain arguments, B<HomePage> is the default page and B<view> is the
default action word.  Refer to "L<"SYNOPSIS">," above.

To display a list of the words that QuikWiki knows about, use the,
"L<"words">," word.

QuikWiki replaces JPEG and PNG words with the images and can display
images separately with the L<"image"> word. 

Optionally, Revision Control System, if installed, can store page
revisions. (See, "L<"Backups and Revisions">").

The template files, "WikiHeader," and, "WikiFooter," format page
headers and footers.  These files contain Perl code and are evaluated
instead of displayed.  (See, L<"Embedding Perl">.)

=head2 Documentation Words

These are the documentation words that QuikWiki recognizes.

=head3 self

Output the QuikWiki source code.  To save in a text file, use a 
shell command similar to the following.

  lynx -dump -width 100 http://<server>/?self >quikwiki.cgi

=head3 doc | pod

Print the POD documentation.

=head3 words

Display sorted list of words and links to pages.

  http://<server>/?words

=head2 Action Words

These are the action words that QuikWiki recognizes.

=head3 edit

Display the editor form and edit a page.

=head3 image

Display an image on a separate page. 

  http://<server>/?image&<image_name>

=head3 new

Create and edit a new page.

=head3 view 

Display the page - this is the default.

=head2 Text Markup

=head3 Paragraphs

Do not indent paragraphs.  Separate paragraphs with a blank line.

=head3 Character Emphasis

B<Bold> text begins and ends with three single quotes (''').
I<Emphasized> (italic) text begins and ends with two single quotes
('').

=head3 Preformatted Text

Lines that begin with one or more spaces maintain their
formatting and are printed in monospaced <tt> font.

=head3 Horizontal Rules

Lines that begin with four or more hyphens are displayed as rules.

=head3 List Items

List items begin with a tab and an asterisk, or eight spaces and 
an asterisk.

=head2 Backups and Revisions

QuikWiki uses RCS for revisions if the system has the B<rcs> and B<ci>
programs, and the document directory contains a B<RCS> subdirectory.
Make sure that the Web server can write to the RCS subdirectory and
archive.

QuikWiki uses non-strict locking for RCS revisions.

Without RCS or a RCS subdirectory, QuikWiki renames previous versions
of the page with a B<.bak> extension.

=head2 Embedding Perl

Pages that contain, "<%" and "%>", get evaluated instead of displayed.
Pages with embedded Perl code can generate dynamic content.  Here is
a page that displays, "Hello, World!" and the date and time in bold type.

Hello, world!  The data and time is:
<%
  $t=localtime ();
  $s = qq{'''$t'''.};
  print lines ($s);
%>

Values and operations are accessible via internal variables and
functions.  The variable B<$word>, for example, is the name of the
currently displayed page, and B<$s> is the name of the HTTP server.
The function B<line($pagetext)> performs markup formatting.  Scripts
can also define their own variables.

The templates, "WikiHeader," and, "WikiFooter," use embedded Perl to
format page Headers and Footers.

=head1 VERSION

$Id: quikwiki.cgi,v 1.28 2004/05/29 10:19:37 kiesling Exp $

=head1 CREDITS

The idea for QuikWiki, and a few of the coding tricks, came from Scott
Walter's tinywiki, although the code is (slightly) less obfuscated.  

The text markup conventions come from WikiWiki.

Written by Robert Kiesling, rkies@cpan.org.

Copyright © 2003-2004 by Robert Kiesling.  QuikWiki is licensed under
the same terms as Perl.  Refer to the file, "Artistic," for details.

=cut

__DATA__
