#!/usr/bin/perl -w

# $Id: quikwiki.cgi,v 1.4 2003/07/28 23:17:59 kiesling Exp $

my $httpheader =<<ENDHTTP;
Content-type: text/html

ENDHTTP

my $starthtml =<<ENDTITLE;
<html><head><title>QuikWiki!</title></head><body bgcolor="white">
ENDTITLE

my $endhtml=<<ENDENDHTML;
</body></html>
ENDENDHTML

my $rcs_ok = (-d 'RCS') && length (`which rcs`) ? 1 : 0;

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
<form method="post" action="$scriptname">
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
    w_pre (join '<br>', @files);
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
    `ci -u -m'Revised by wiki.cgi' $name` if $rcs_ok;
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
    w_eval ($word) if $page =~ s/\<\%|\%\>//gm;
    print qq|$page<p>|;
    w_eval ('WikiFooter') if -f 'WikiFooter';
    print $endhtml;
    exit 0;
}

sub w_eval {
    my $file = $_[0];
    my $script = w_read ($file);
    $script =~ s/\<\%|\%\>//gm;
    eval $script;
    print ('<br>'. $@.'<br>') if $@;
}

sub words {
    $page = $_[0];
    my @p_words = split /\s|\r?\n/, $page;    
    foreach my $st (split /\s|\r?\n|\'|\\|\"|\?|\.|\:|,/, $page) {
	next if $st !~ /^[A-Z]/;
	$page =~ s/([^"<])$st([^"])/$1<a href="?$st">$st<\/a>$2/ 
	    if (filetype ($st) =~ /text/);
	$page =~ s/([^"<])$st([^"])/$1<img src="$st" alt="$st">$2/ 
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
	# Blank line.
	if (substr ($l, 0, 1) eq ' ') {
	    $l =~ s/ /\&nbsp\;/g;
	    $newpage .= "<tt>$l</tt><br>\n";
	} elsif ($l =~ /^----/) {
	    $newpage .= '<hr>';
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


  # View pages

  http://<host>/quikwiki/quikwiki.cgi?HomePage   # View HomePage
  http://<host>/quikwiki/?HomePage               # Same as above.


  # Edit pages

  http://<host>/quikwiki/quikwiki.cgi?&action=edit       # Edit HomePage

  http://<host>/quikwiki/quikwiki.cgi?MyPage&action=edit # Edit MyPage


  # Create and edit page named "NewPage."

  http://<host>/quikwiki/quikwiki.cgi?NewPage&action=new

  http://<host>/quikwiki/?NewPage                # Same as above


=head1 DESCRIPTION

QuikWiki outputs HTML of pages formatted with Wiki markup tags (see
"L<"Text Markup">"), with embedded links to Wiki "words."  The names
of files that contains Wiki pages are words in QuikWiki.

Words start with uppercase letters and contain mixed-case alphanumeric
characters.  These are valid words.

  HomePage
  AreaCode916
  TableOfContents
  Addresses

If no word is given, wiki.cgi uses "HomePage." 

To display a list of the words that QuikWiki knows about, use the
"L<"words">" document option, below.

QuikWiki displays JPEG and PNG images in-line.

=head2 Page Headers and Footers

QuikWiki uses the file <tt>WikiHeader</tt> for page headers and
<tt>WikiFooter</tt> as the page footer.  These files contain Perl code
and are evaluated instead of displayed.  Refer to the section
L<"Embedding Perl Programs"> below.

=head2 Self-Documentation

These are the documentation commands that wiki.cgi recognizes.

=head3 self

Output the wiki.cgi source code.  Best done with 

  lynx -dump -width 100 http://<server>/?self >wiki.cgi

=head3 doc | pod

Print the POD documentation.

=head3 words

Print a list of QuikWiki words.

  http://<server>/?words

=head2 Actions

These are the actions that QuikWiki recognizes.

=head3 view 

Display the page - this is the default.

=head3 new

Open the editor to create a new page.

=head3 save

Save a page, with backup or revision.  See the section
"Backups and Revisions," below.

=head3 edit

Open the editor form and edit the page text.

=head2 Text Markup

=head3 Paragraphs

Do not indent paragraphs.  Separate paragraphs with a blank line.

=head3 Character Emphasis

B<Bold> text begins and ends with three single quotes (''').
I<Emphasized> (italic) text begins and ends with two single quotes
('').

=head3 Preformatted Text

Lines that begin with one or more spaces maintain their
formatting and are printed in a monospaced <tt> font.

=head3 Horizontal Rules

Lines that begin with four or more hyphens are formatted as
horizontal rules.

=head2 Backups and Revisions

QuikWiki uses RCS for revisions if you have B<rcs> and B<ci> programs,
and you've created a B<RCS> subdirectory under wiki.cgi's directory.
Make sure that the Web server can write to the RCS subdirectory.

At the moment, RCS uses non-strict locking.

If you don't want to use RCS, don't make a RCS subdirectory, and
wiki.cgi will rename the previous version of the page with a .bak
extension.

=head2 Embedding Perl

If a page contains "<%" and "%>", it gets eval'd
instead of displayed.  You can embed Perl code in a page, and
wiki.cgi will output the results.

For examples of embedded Perl, look at the files "WikiHeader"
and "WikiFooter."

=head1 VERSION

Current Version: $Revision: 1.4 $

=head1 CREDITS

The idea for wiki.cgi, and a few of the coding tricks, came from Scott
Walter's tinywiki, but the code in wiki.cgi is (slightly) less
obfuscated.  Most of the Wiki conventions are derived from
WikiWiki.

Written by Robert Kiesling <rkiesling@earthlink.net>.

=cut

__DATA__
