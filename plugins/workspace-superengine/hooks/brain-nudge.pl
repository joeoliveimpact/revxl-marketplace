#!/usr/bin/env perl
#
# brain-nudge.pl -- says something when a generating skill started a draft and
# no RevXL Brain call followed.
#
# Subcommands
#   post-skill  PostToolUse(Skill). If the invoked skill is one of the 29
#               generators, stamp ~/.config/revxl/brain-nudge/<session>.json
#               with {skill, ts}. Latest generator wins.
#   pre-write   PreToolUse(Write|Edit). If that stamp exists, the Brain call
#               ledger has no line at or after its ts, and this session has not
#               been nudged yet, emit additionalContext and mark it nudged.
#
# THE ONE RULE THIS FILE EXISTS TO OBEY: it is the belt, not the suspenders.
# The Brain trigger points written into each plugin are the primary mechanism;
# this only catches the case where one was skipped. So it never blocks, never
# returns a permissionDecision, never exits non-zero, and prints NOTHING when
# anything at all goes wrong (no JSON::PP, no home directory, unreadable or
# unparseable ledger). A ledger it cannot parse means it cannot know whether a
# Brain call happened, and an uncertain nudge is worse than no nudge.

use strict;
use warnings;

# Declared with `our` and assigned only inside BEGIN, matching process-ledger.pl:
# a file-scope `my $x = 0` would be re-run at runtime and wipe out what BEGIN
# decided.
our $JSON_OK;
BEGIN {
    $JSON_OK = 0;
    eval { require JSON::PP; JSON::PP->import(qw(encode_json decode_json)); $JSON_OK = 1; 1; };
}
use File::Path qw(make_path);

exit 0 unless $JSON_OK;

# The generating skills, named exactly as the Skill tool names them
# (<plugin>:<skill-directory>). These are the skills that draft client-facing
# work and therefore have a Brain trigger point; analysis, setup, teaching and
# intake skills are deliberately absent.
my %GENERATOR = map { ($_ => 1) } qw(
    meta-ads-superengine:meta-ads-ad-copy
    meta-ads-superengine:meta-ads-campaign-plan
    meta-ads-superengine:meta-ads-creative-strategy
    meta-ads-superengine:meta-ads-hook-writer
    meta-ads-superengine:meta-ads-lead-questions
    meta-ads-superengine:meta-ads-static-ads
    meta-ads-superengine:meta-ads-video-script
    shortform-superengine:reel-scripter
    carousel-superengine:carousel-create
    carousel-superengine:carousel-render
    carousel-superengine:carousel-templates
    email-sequence-superengine:email-follow-up-sequence
    email-sequence-superengine:email-launch-promo-sequence
    email-sequence-superengine:email-no-show-sequence
    email-sequence-superengine:email-onboarding-sequence
    email-sequence-superengine:email-presell-video
    email-sequence-superengine:email-show-up-sequence
    email-sequence-superengine:email-warm-nurture-sequence
    email-sequence-superengine:email-winback-sequence
    lead-magnet-superengine:lm-create
    lead-magnet-superengine:lm-inspired-by
    lead-magnet-superengine:lm-revamp
    profile-optimization-superengine:profile-fb-audit
    profile-optimization-superengine:profile-ig-audit
    offer-architect:build-offer-blueprint
    offer-architect:build-value-stack
    offer-architect:export-roadmap-video
    offer-architect:finalize-offer
    offer-architect:price-matrix
);

# USERPROFILE first: on Windows it is the same folder revxl-brain-search writes
# its key and ledger into, while HOME can be an MSYS-only path set by whichever
# shell launched the hook.
sub home_dir {
    for my $v ($ENV{USERPROFILE}, $ENV{HOME}) {
        return $v if defined $v && length $v;
    }
    return undef;
}

sub revxl_dir {
    my $h = home_dir();
    return undef unless defined $h;
    $h =~ s{\\}{/}g;
    $h =~ s{/+$}{};
    return $h . '/.config/revxl';
}

sub safe_name {
    my ($s) = @_;
    $s = '' unless defined $s;
    $s =~ s/[^A-Za-z0-9._-]/_/g;
    $s = 'unknown' if $s eq '';
    return substr($s, 0, 80);
}

sub read_stdin {
    local $/;
    my $in = <STDIN>;
    return defined $in ? $in : '';
}

# The ledger's ts is written by `date -u +%Y-%m-%dT%H:%M:%SZ` inside the same
# command that made the call (revxl-brain-search step 3), so it is always UTC.
sub iso_epoch {
    my ($s) = @_;
    return undef unless defined $s && !ref($s);
    return undef unless $s =~ /^(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)Z$/;
    require Time::Local;
    my $e = eval { Time::Local::timegm($6, $5, $4, $3, $2 - 1, $1) };
    return $e;
}

my $mode = defined $ARGV[0] ? $ARGV[0] : '';
exit 0 unless $mode eq 'post-skill' || $mode eq 'pre-write';

my $payload = eval { decode_json(read_stdin()) };
exit 0 unless ref($payload) eq 'HASH';

my $session = $payload->{session_id};
$session = $ENV{CLAUDE_CODE_SESSION_ID}
    unless defined $session && !ref($session) && length $session;
exit 0 unless defined $session && !ref($session) && length $session;

my $dir = revxl_dir();
exit 0 unless defined $dir;
my $stamp = $dir . '/brain-nudge/' . safe_name($session) . '.json';

if ($mode eq 'post-skill') {
    my $ti = $payload->{tool_input};
    my $skill = (ref($ti) eq 'HASH') ? $ti->{skill} : undef;
    exit 0 unless defined $skill && !ref($skill) && $GENERATOR{$skill};

    eval { make_path($dir . '/brain-nudge'); 1 } or exit 0;
    my $line = eval { encode_json({ skill => $skill, ts => time }) };
    exit 0 unless defined $line;
    open my $out, '>', $stamp or exit 0;
    print {$out} $line, "\n";
    close $out;
    exit 0;
}

# pre-write
exit 0 unless -f $stamp;
open my $in, '<', $stamp or exit 0;
my $rec = eval { local $/; decode_json(scalar <$in>) };
close $in;
exit 0 unless ref($rec) eq 'HASH';
exit 0 if $rec->{nudged};

my $since = $rec->{ts};
exit 0 unless defined $since && !ref($since) && $since =~ /^\d+$/;

# A failed Brain call is still a Brain check: revxl-brain-search logs one line
# per call, success or failure, so any line at or after the stamp answers this.
my $ledger = $dir . '/brain-calls.jsonl';
if (-e $ledger) {
    open my $lg, '<', $ledger or exit 0;
    while (my $line = <$lg>) {
        $line =~ s/^\s+//;
        $line =~ s/\s+$//;
        next unless length $line;
        my $r = eval { decode_json($line) };
        exit 0 unless ref($r) eq 'HASH';
        my $e = iso_epoch($r->{ts});
        exit 0 unless defined $e;
        exit 0 if $e >= $since;
    }
    close $lg;
}

$rec->{nudged} = 1;
if (open my $out, '>', $stamp) {
    my $line = eval { encode_json($rec) };
    print {$out} $line, "\n" if defined $line;
    close $out;
}

my $skill = (defined $rec->{skill} && !ref($rec->{skill})) ? $rec->{skill} : 'a generating skill';
my $msg = "No Brain check since `" . $skill . "` started. Invoke "
        . "`workspace-superengine:revxl-brain-search` before this draft "
        . "(depth med, the plugin's recipe), or print `Brain: skipped (...)` "
        . "with the reason.";
my $json = eval {
    encode_json({
        hookSpecificOutput => {
            hookEventName    => 'PreToolUse',
            additionalContext => $msg,
        },
    });
};
exit 0 unless defined $json;
print STDOUT $json, "\n";
exit 0;
