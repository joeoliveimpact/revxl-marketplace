#!/usr/bin/env perl
#
# process-ledger.pl -- background process ledger for workspace-superengine.
#
# THE ONE RULE THIS FILE EXISTS TO ENFORCE:
#   the process table may VERIFY a ledger entry, it may never SELECT a target.
#
# Why: the process table cannot identify an orphan.
#   * Parent-PID lies. MCP servers launch through npx, so their parent is
#     cmd.exe, not claude. A "no live claude parent" filter flagged around 30
#     actively-in-use MCP servers as orphans.
#   * Name lies catastrophically. Claude Code IS node. Stopping processes by
#     the name "node" kills the running harness mid-command plus every other
#     open Claude window.
#   * Age lies. A three-day-old server can be legitimately in use; a
#     ten-minute-old one can belong to another live session.
#
# So: record on start, close from the ledger, and re-verify the full identity
# (pid + started_at + cmd) immediately before stopping anything. Any mismatch
# means SKIP, never kill. Anything not in the ledger is reported, never
# stopped.
#
# Subcommands
#   pre            PreToolUse(Bash) hook. Stamps the start of the tool call.
#   post           PostToolUse(Bash) hook. Captures survivors, writes entries.
#   session-start  SessionStart hook. Sweeps entries left by dead sessions.
#   list           Human-readable state + consent token. Never stops anything.
#   stop           Verified, consent-gated stop. Skips on any mismatch.
#   paths          Print where everything lives (discovery / debugging).
#
# Hook subcommands ALWAYS exit 0. A ledger problem must never break a session.
# They record a "degraded" line instead, which list/session-start then report
# out loud. A silent no-op is the failure mode this whole feature is designed
# against, so every branch here has something readable to say.

use strict;
use warnings;

# Declared with `our` and assigned only inside BEGIN. A file-scope `my $x = 0`
# would be re-run at runtime and would wipe out what BEGIN just decided.
our $JSON_OK;
BEGIN {
    $JSON_OK = 0;
    eval { require JSON::PP; JSON::PP->import(qw(encode_json decode_json)); $JSON_OK = 1; 1; };
}
use Digest::MD5 qw(md5_hex);
use File::Path qw(make_path);
use File::Basename qw(basename dirname);
use Cwd qw(getcwd);

my $LIVE_WINDOW_SECONDS   = 4 * 3600;  # heartbeat fallback only; see owner_of()
my $MAX_UNATTRIBUTED_LOG  = 10;
my $WINDOW_SLACK_SECONDS  = 2;         # clock granularity on the start stamp
my $NO_MARKER_FALLBACK    = 300;       # window used when the pre-stamp is lost

my $IS_WIN = ($^O =~ /^(MSWin32|msys|cygwin)$/i) ? 1 : 0;

# --------------------------------------------------------------------------
# paths
# --------------------------------------------------------------------------

# Returns undef rather than falling back to getcwd(). A cwd-derived home drifts
# with wherever the shell happened to be, which produces a different ledger
# every time and therefore a permanent, confident, wrong "nothing is running".
sub home_dir {
    return $ENV{WSE_TEST_HOME} if $ENV{WSE_TEST_HOME};
    return $ENV{HOME} if $ENV{HOME};
    return $ENV{USERPROFILE} if $ENV{USERPROFILE};
    return undef;
}

# The ledger is deliberately NOT in the workspace and NOT in a temp dir.
# A crashed session never reaches closeout, which is exactly how multi-day
# survivors happen, so this has to outlive both the session and a reboot.
sub ledger_home {
    return $ENV{WORKSPACE_SUPERENGINE_LEDGER_HOME}
        if $ENV{WORKSPACE_SUPERENGINE_LEDGER_HOME};
    my $h = home_dir();
    # Unreachable in practice: ledger_unusable() refuses before anything reads
    # this. The literal is here only so an undef cannot silently build a path.
    $h = '/NO-HOME-DIRECTORY' unless defined $h;
    return join('/', $h, '.claude', 'workspace-superengine', 'process-ledger');
}

# The single question every entry point must ask before it says anything about
# what is or is not running: can this ledger actually be read AND written?
# Returns a human-readable reason when it cannot, undef when it can.
#
# "The ledger was read and it is empty" is the most dangerous sentence this
# tool can print. It may only be printed after this returns undef.
sub ledger_unusable {
    if (!$ENV{WORKSPACE_SUPERENGINE_LEDGER_HOME} && !defined home_dir()) {
        return "neither HOME nor USERPROFILE is set, so there is no stable place to keep the ledger";
    }
    my $d = ws_dir();
    if (!ensure_dirs()) {
        return "the ledger folder could not be created at $d ($!)";
    }
    my $probe = $d . '/.writable';
    if (open my $fh, '>', $probe) {
        print $fh "ok\n";
        close $fh;
        drain_fallback();
        return undef;
    }
    return "the ledger folder at $d cannot be written to ($!)";
}

sub unavailable_banner {
    my ($reason, $what) = @_;
    print "PROCESS LEDGER UNAVAILABLE\n";
    print "$reason.\n";
    print "So $what. This is NOT the same as 'no background processes are running'.\n";
    print "Nothing was recorded and nothing can be stopped until this is fixed.\n";
}

# The hook side gets CLAUDE_PROJECT_DIR (Windows style, "C:/x"). The CLI side,
# run from a skill's Bash call, does NOT: verified unset there, so it falls back
# to getcwd(), which under msys perl returns "/c/x". Those two strings hash to
# two different workspace slugs, which would point `list` at an empty directory
# and make it report a confident "nothing is running" while the real ledger sat
# untouched next door. Normalise both spellings to one.
our $WS_ROOT;
our $WS_ROOT_VIA;

sub normalise_path {
    my ($w) = @_;
    $w =~ s{\\}{/}g;
    if ($IS_WIN) {
        $w =~ s{^/cygdrive/([A-Za-z])(/|$)}{\u$1:/};
        $w =~ s{^/([A-Za-z])(/|$)}{\u$1:/};
    }
    $w =~ s{/+$}{};
    return $w;
}

# cwd is not the workspace. Running the CLI from a subdirectory used to hash to
# a different slug, so `list` read an empty folder and reported a clean machine
# while the populated ledger sat one slug over. Walk up for a real marker
# instead, and when there is no marker, say so rather than guessing.
sub find_workspace_root {
    my ($start) = @_;
    my $dir = normalise_path($start);
    my @markers = ('.claude/workspace.yml', 'CLAUDE.md', 'RULES.md', '.git');
    my $hops = 0;
    while (length $dir && $hops++ < 40) {
        for my $m (@markers) {
            return ($dir, "workspace marker $m found by walking up from the current directory")
                if -e "$dir/$m";
        }
        last unless $dir =~ m{/};
        my $up = $dir;
        $up =~ s{/[^/]+$}{};
        last if $up eq $dir || $up =~ m{^[A-Za-z]:$};
        $dir = $up;
    }
    return (normalise_path($start), 'UNRESOLVED');
}

sub workspace_root {
    return $WS_ROOT if defined $WS_ROOT;
    my $env = $ENV{CLAUDE_PROJECT_DIR};
    if (defined $env && $env =~ /\S/) {
        $WS_ROOT     = normalise_path($env);
        $WS_ROOT_VIA = 'CLAUDE_PROJECT_DIR';
    }
    else {
        ($WS_ROOT, $WS_ROOT_VIA) = find_workspace_root(getcwd());
    }
    return $WS_ROOT;
}

sub workspace_root_via {
    workspace_root();
    return $WS_ROOT_VIA;
}

# Names the sibling ledgers that exist under the same root. This is what makes
# the "you are looking at the wrong workspace" failure visible instead of
# reading as a clean machine.
sub sibling_ledgers {
    my $home = ledger_home();
    my $mine = workspace_slug();
    return () unless -d $home;
    opendir my $dh, $home or return ();
    my @out;
    for my $e (sort readdir $dh) {
        next if $e =~ /^\.\.?$/;
        next if $e eq $mine;
        next unless -f "$home/$e/ledger.jsonl";
        push @out, $e;
    }
    closedir $dh;
    return @out;
}

sub workspace_slug {
    my $w = workspace_root();
    my $key = $IS_WIN ? lc($w) : $w;
    my $name = basename($w);
    $name =~ s/[^A-Za-z0-9._-]/_/g;
    $name = substr($name, 0, 40);
    $name = 'workspace' if $name eq '';
    return $name . '-' . substr(md5_hex($key), 0, 8);
}

sub ws_dir      { return ledger_home() . '/' . workspace_slug(); }
sub ledger_file { return ws_dir() . '/ledger.jsonl'; }
sub pending_dir { return ws_dir() . '/pending'; }
sub session_dir { return ws_dir() . '/sessions'; }
sub degraded_file { return ws_dir() . '/DEGRADED.txt'; }

sub hook_dir {
    return $ENV{WSE_LEDGER_HOOK_DIR} if $ENV{WSE_LEDGER_HOOK_DIR};
    my $d = dirname(__FILE__);
    return $d;
}

sub ensure_dirs {
    for my $d (ws_dir(), pending_dir(), session_dir()) {
        next if -d $d;
        eval { make_path($d); 1 } or return 0;
    }
    return 1;
}

sub safe_name {
    my ($s) = @_;
    $s = '' unless defined $s;
    $s =~ s/[^A-Za-z0-9._-]/_/g;
    $s = 'unknown' if $s eq '';
    return substr($s, 0, 80);
}

sub now_iso {
    my @t = gmtime(time);
    return sprintf('%04d-%02d-%02dT%02d:%02d:%02dZ',
        $t[5] + 1900, $t[4] + 1, $t[3], $t[2], $t[1], $t[0]);
}

# --------------------------------------------------------------------------
# degradation reporting -- a broken ledger must be loud, never silent
# --------------------------------------------------------------------------

# The report that the ledger is broken must not live inside the ledger. When
# the ledger folder is unwritable, writing DEGRADED.txt there fails too, and a
# silent eval turns a broken install into a machine that looks clean. So this
# writes to the system temp directory as well, and to stderr, every time.
# Named per workspace, so one broken workspace cannot make every other
# workspace on the machine look broken.
sub fallback_degraded_file {
    my $t = $ENV{TEMP} || $ENV{TMP} || '/tmp';
    $t = normalise_path($t);
    return "$t/workspace-superengine-ledger-DEGRADED-" . workspace_slug() . ".txt";
}

# Once the real ledger is writable again, move anything the out-of-band file
# collected into it and delete the out-of-band copy. Without this the marker
# outlives the fault and nags every session forever, which trains the user to
# ignore the one message this feature most needs them to read.
sub drain_fallback {
    my $fb = fallback_degraded_file();
    return unless -f $fb;
    eval {
        if (open my $in, '<', $fb) {
            my @lines = <$in>;
            close $in;
            if (open my $out, '>>', degraded_file()) {
                print $out @lines;
                close $out;
            }
        }
        unlink $fb;
        1;
    };
    return;
}

sub iso_to_epoch {
    my ($s) = @_;
    return undef unless defined $s && $s =~ /^(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)Z$/;
    require Time::Local;
    my $e = eval { Time::Local::timegm($6, $5, $4, $3, $2 - 1, $1) };
    return $e;
}

# Splits recorded degradation into "still worth shouting about" and "history".
# A fault from last week is a fact for the record, not a banner on every
# session start.
sub read_degraded_split {
    my @recent;
    my $older  = 0;
    my $cutoff = time - 86400;
    for my $f (degraded_file(), fallback_degraded_file()) {
        next unless -f $f;
        next unless open my $fh, '<', $f;
        while (my $l = <$fh>) {
            chomp $l;
            next unless $l =~ /\S/;
            my $when = ($l =~ /^(\S+)/) ? iso_to_epoch($1) : undef;
            if (defined $when && $when < $cutoff) { $older++ }
            else                                  { push @recent, $l }
        }
        close $fh;
    }
    return (\@recent, $older);
}

sub note_degraded {
    my ($stage, $reason) = @_;
    my $line = now_iso() . "  [$stage] $reason";
    print STDERR "workspace-superengine process ledger: $line\n";
    eval {
        if (open my $fb, '>>', fallback_degraded_file()) {
            print $fb $line, "\n";
            close $fb;
        }
        1;
    };
    eval {
        ensure_dirs();
        if (open my $fh, '>>', degraded_file()) {
            print $fh $line, "\n";
            close $fh;
        }
        append_record({ type => 'degraded', at => now_iso(), stage => $stage, reason => $reason })
            if $JSON_OK;
        1;
    };
    return;
}

sub read_degraded {
    my @out;
    for my $f (degraded_file(), fallback_degraded_file()) {
        next unless -f $f;
        next unless open my $fh, '<', $f;
        my @l = <$fh>;
        close $fh;
        chomp @l;
        push @out, grep { /\S/ } @l;
    }
    return @out;
}

# --------------------------------------------------------------------------
# ledger io
# --------------------------------------------------------------------------

sub append_record {
    my ($rec) = @_;
    return 0 unless $JSON_OK;
    return 0 unless ensure_dirs();
    my $line = eval { encode_json($rec) };
    return 0 unless defined $line;
    open my $fh, '>>', ledger_file() or return 0;
    print $fh $line, "\n";
    close $fh;
    return 1;
}

# Append-only, folded on read. Never rewritten in place: two sessions can be
# appending at once, and a lost update here would mean a forgotten process.
sub load_ledger {
    my %closed;
    my @opens;
    my @errors;
    my @unattributed;
    my @degraded;
    my $f = ledger_file();
    return (\@opens, \@errors, \@unattributed, \@degraded) unless -f $f;
    open my $fh, '<', $f or do {
        push @errors, "could not open $f: $!";
        return (\@opens, \@errors, \@unattributed, \@degraded);
    };
    my $n = 0;
    while (my $line = <$fh>) {
        $n++;
        $line =~ s/\s+$//;
        next if $line eq '';
        my $rec = eval { decode_json($line) };
        if (!$rec || ref($rec) ne 'HASH') {
            push @errors, "line $n is not readable JSON (hand-edited or truncated)";
            next;
        }
        my $t = $rec->{type} || '';
        if    ($t eq 'open')         { push @opens, $rec }
        elsif ($t eq 'close')        { $closed{ $rec->{uid} || '' } = $rec }
        elsif ($t eq 'unattributed') { push @unattributed, $rec }
        elsif ($t eq 'vetoed')       { push @degraded, { %$rec, _veto => 1 } }
        elsif ($t eq 'degraded')     { push @degraded, $rec }
    }
    close $fh;
    my @live = grep { !exists $closed{ $_->{uid} || '' } } @opens;
    return (\@live, \@errors, \@unattributed, \@degraded);
}

sub close_entry {
    my ($entry, $outcome, $reason) = @_;
    append_record({
        type    => 'close',
        uid     => $entry->{uid},
        pid     => $entry->{pid},
        outcome => $outcome,
        reason  => $reason,
        at      => now_iso(),
    });
}

# --------------------------------------------------------------------------
# process probe -- ONE code path for recording and for verifying
# --------------------------------------------------------------------------

sub win_path {
    my ($p) = @_;
    return $p if $p =~ m{^[A-Za-z]:};
    my $w = `cygpath -w "$p" 2>/dev/null`;
    chomp $w if defined $w;
    return $w if defined $w && $w ne '';
    return $p;
}

sub have_cmd {
    my ($c) = @_;
    my $o = `command -v $c 2>/dev/null`;
    return (defined $o && $o =~ /\S/) ? 1 : 0;
}

sub probe_raw_windows {
    my $ps1 = hook_dir() . '/process-probe.ps1';
    return (undef, "probe script missing at $ps1") unless -f $ps1;
    my $shell = have_cmd('powershell') ? 'powershell'
              : have_cmd('pwsh')       ? 'pwsh'
              : undef;
    return (undef, 'neither powershell nor pwsh is available on this machine')
        unless $shell;
    my $win = win_path($ps1);
    my $out = `$shell -NoProfile -ExecutionPolicy Bypass -File "$win" 2>/dev/null`;
    return (undef, "$shell returned nothing") unless defined $out && $out =~ /\S/;
    return ($out, undef);
}

sub etime_to_seconds {
    my ($e) = @_;
    return undef unless defined $e;
    my ($d, $h, $m, $s) = (0, 0, 0, 0);
    if ($e =~ /^(\d+)-(\d+):(\d+):(\d+)$/) { ($d, $h, $m, $s) = ($1, $2, $3, $4) }
    elsif ($e =~ /^(\d+):(\d+):(\d+)$/)    { ($h, $m, $s) = ($1, $2, $3) }
    elsif ($e =~ /^(\d+):(\d+)$/)          { ($m, $s) = ($1, $2) }
    else { return undef }
    return $d * 86400 + $h * 3600 + $m * 60 + $s;
}

sub probe_raw_unix {
    my $out = `ps -eo pid=,ppid=,etime=,rss=,lstart=,command= 2>/dev/null`;
    return (undef, 'ps produced no output') unless defined $out && $out =~ /\S/;
    return ($out, undef);
}

# Returns ($procs_hashref_by_pid, $selfchain_hashref, $error)
sub probe {
    my $now = time;
    my (%procs, %self);
    if ($IS_WIN) {
        my ($raw, $err) = probe_raw_windows();
        return (undef, undef, $err) unless defined $raw;
        for my $line (split /\r?\n/, $raw) {
            next unless length $line;
            if ($line =~ /^#ERROR\t(.*)$/) { return (undef, undef, $1) }
            if ($line =~ /^#SELF\t(.*)$/) {
                $self{$_} = 1 for grep { /^\d+$/ } split /,/, $1;
                next;
            }
            my @f = split /\t/, $line, 6;
            next unless @f >= 5;
            my ($pid, $ppid, $epoch, $stamp, $rss, $cmd) = @f;
            next unless $pid =~ /^\d+$/;
            $cmd = '' unless defined $cmd;
            $procs{$pid} = {
                pid => $pid + 0, ppid => $ppid + 0, epoch => $epoch + 0,
                started_at => $stamp, rss_kb => $rss + 0, cmd => $cmd,
            };
        }
        return (undef, undef, 'process table came back empty') unless %procs;
    }
    else {
        my ($raw, $err) = probe_raw_unix();
        return (undef, undef, $err) unless defined $raw;
        for my $line (split /\n/, $raw) {
            next unless $line =~ /\S/;
            next unless $line =~ /^\s*(\d+)\s+(\d+)\s+(\S+)\s+(\d+)\s+(\S+\s+\S+\s+\S+\s+\S+\s+\S+)\s+(.*)$/;
            my ($pid, $ppid, $etime, $rss, $lstart, $cmd) = ($1, $2, $3, $4, $5, $6);
            my $secs = etime_to_seconds($etime);
            next unless defined $secs;
            $lstart =~ s/\s+/ /g;
            $cmd =~ s/[\t\r\n]/ /g;
            $cmd =~ s/^\s+|\s+$//g;
            $procs{$pid} = {
                pid => $pid + 0, ppid => $ppid + 0, epoch => $now - $secs,
                started_at => $lstart, rss_kb => $rss + 0, cmd => $cmd,
            };
        }
        return (undef, undef, 'ps output was not parseable on this platform')
            unless %procs;
        # self chain: this perl, its ancestors, and its own descendants
        my %kids;
        push @{ $kids{ $procs{$_}{ppid} } }, $procs{$_}{pid} for keys %procs;
        my $cur = $$;
        my $guard = 0;
        while ($cur && $guard++ < 32) {
            last if $self{$cur};
            $self{$cur} = 1;
            last unless $procs{$cur};
            $cur = $procs{$cur}{ppid};
        }
        my @q = ($$);
        while (@q) {
            my $n = shift @q;
            for my $c (@{ $kids{$n} || [] }) {
                next if $self{$c};
                $self{$c} = 1;
                push @q, $c;
            }
        }
    }
    expand_self(\%procs, \%self);
    return (\%procs, \%self, undef);
}

# On Windows the msys $$ is not the Windows pid the process table reports.
sub my_pid {
    if (-r '/proc/self/winpid') {
        if (open my $fh, '<', '/proc/self/winpid') {
            my $p = <$fh>;
            close $fh;
            chomp $p if defined $p;
            return $p if defined $p && $p =~ /^\d+$/;
        }
    }
    return $$;
}

# The probe's own ancestor walk stops dead at the first parent that has already
# exited, which happens routinely under msys (the launcher shell execs away).
# So the exclusion set is rebuilt here from pids we know for certain: this perl,
# the shim that launched it, and the harness. Their descendants go in too.
# Ancestors are excluded as individual pids only ... never with their
# descendants, because the process we are trying to record is itself a
# descendant of the harness.
sub expand_self {
    my ($procs, $self) = @_;
    my %kids;
    push @{ $kids{ $procs->{$_}{ppid} } }, $procs->{$_}{pid} for keys %$procs;

    # V1 ... pids we know for certain, plus their descendants.
    # Only these are expanded downwards. Pids already in %self (from the probe's
    # own walk) stay as flat exclusions: that set can contain the harness
    # itself, and expanding the harness downwards would exclude every candidate
    # on the machine and silently disable the whole feature.
    my @seeds = grep { defined $_ && $_ =~ /^\d+$/ } (my_pid(), $ENV{WSE_SHIM_PID});
    my @queue;
    for my $s (@seeds) {
        $self->{$s} = 1;
        push @queue, $s;
        # Ancestors, hopping over gaps. The old version stopped at the first
        # ancestor missing from the snapshot, which under msys is the immediate
        # parent (the launcher execs away), so it excluded exactly zero
        # ancestors and offered Claude's own tool shell as a kill candidate.
        my $cur  = $procs->{$s} ? $procs->{$s}{ppid} : 0;
        my $hops = 0;
        while ($cur && $hops++ < 32) {
            last if $self->{$cur};
            $self->{$cur} = 1;
            last unless $procs->{$cur};
            $cur = $procs->{$cur}{ppid};
        }
    }
    while (@queue) {
        my $n = shift @queue;
        for my $c (@{ $kids{$n} || [] }) {
            next if $self->{$c};
            $self->{$c} = 1;
            push @queue, $c;
        }
    }

    # V2 ... msys ancestry, read from /proc rather than the Windows process
    # table. This chain is intact even when the Windows parent-pid chain is
    # broken, because msys keeps its own parent links, and it reaches the
    # Claude tool shell directly. Chain pids are excluded; their descendants
    # are NOT, because the process we are trying to record is itself a
    # descendant of the tool shell.
    $self->{$_} = 1 for msys_ancestor_winpids();

    # V3 ... a direct child of the harness is harness machinery. Claude spawns
    # tool shells and hook processes as its own children; anything a command
    # actually starts sits at least one level below that shell.
    if ($ENV{CLAUDE_PID} && $ENV{CLAUDE_PID} =~ /^\d+$/) {
        my $h = $ENV{CLAUDE_PID};
        $self->{$h} = 1;
        $self->{$_} = 1 for @{ $kids{$h} || [] };
    }

    # V4 lives in is_machinery(), applied at attribution time, so that a
    # signature match is recorded as a veto rather than vanishing here.
    return;
}

# V2 helper. Walks the msys process tree via /proc and converts each ancestor
# to its Windows pid. Returns an empty list off msys, which is correct: the
# Windows-table walk in V1 does not break on Unix.
sub msys_ancestor_winpids {
    my @out;
    return @out unless -d '/proc';
    my $p     = $$;
    my $hops  = 0;
    my %seen;
    while ($p && $hops++ < 16 && !$seen{$p}++) {
        my $stat = "/proc/$p/stat";
        last unless -r $stat;
        if (open my $w, '<', "/proc/$p/winpid") {
            my $win = <$w>;
            close $w;
            chomp $win if defined $win;
            push @out, $win if defined $win && $win =~ /^\d+$/;
        }
        open my $s, '<', $stat or last;
        my $line = <$s>;
        close $s;
        last unless defined $line;
        # /proc/<pid>/stat: pid (comm) state ppid ... comm can contain spaces,
        # so split after the closing paren.
        my $tail = ($line =~ /\)\s*(.*)$/) ? $1 : '';
        my @f = split /\s+/, $tail;
        my $ppid = (defined $f[1] && $f[1] =~ /^\d+$/) ? $f[1] : 0;
        last unless $ppid && $ppid != $p;
        $p = $ppid;
    }
    return @out;
}

# V4 ... a structural veto on harness and plugin machinery, in its own right.
#
# A denylist by name or signature is the wrong tool for SELECTING a kill target
# and the right tool for REFUSING one. It can only ever prevent a stop, never
# cause one, so the worst case is a missed cleanup rather than a killed shell.
# That asymmetry is why this is safe here and unsafe everywhere else.
sub is_machinery {
    my ($cmd) = @_;
    return 'a process with no command line at all' unless defined $cmd && $cmd =~ /\S/;
    # The probe writes "(name)" when Windows refuses to hand over a command
    # line, which is the normal answer for protected and system processes. If
    # we cannot read what a process is, we cannot prove we started it, so it is
    # never ours to stop. This closes the whole class, not just conhost.
    return 'a process whose command line Windows will not disclose, so it cannot be proved to be ours'
        if $cmd =~ /^\s*\([^)]*\)\s*$/;
    my $lc = lc $cmd;
    return 'Claude tool-shell signature (shell-snapshots)' if index($lc, 'shell-snapshots') >= 0;
    return 'Claude tool-shell signature (snapshot-bash)'   if index($lc, 'snapshot-bash')   >= 0;
    return 'Claude tool-shell signature (cwd handoff)'     if $lc =~ /claude-[0-9a-f]+-cwd/;
    return 'Windows console host'                          if $lc =~ /(^|[\\\/"(\s])conhost(\.exe)?\b/;
    return 'the ledger plugin\'s own hook machinery'        if index($lc, 'run-hook.cmd')      >= 0;
    return 'the ledger plugin\'s own hook machinery'        if index($lc, 'process-ledger')    >= 0;
    return 'the ledger plugin\'s own hook machinery'        if index($lc, 'process-probe.ps1') >= 0;
    return 'the Claude binary itself'                      if $lc =~ /(^|[\\\/"])claude\.exe\b/;
    return undef;
}

# --------------------------------------------------------------------------
# hook stdin parsing
# --------------------------------------------------------------------------

sub read_stdin {
    local $/;
    my $in = <STDIN>;
    return defined $in ? $in : '';
}

# session_id is a flat top-level scalar, safe to pull with a regex even when
# JSON::PP is unavailable. Used by `pre`, which must stay cheap.
sub quick_session_id {
    my ($raw) = @_;
    return $1 if $raw =~ /"session_id"\s*:\s*"([^"]*)"/;
    return $ENV{CLAUDE_CODE_SESSION_ID} if $ENV{CLAUDE_CODE_SESSION_ID};
    return 'unknown';
}

# --------------------------------------------------------------------------
# session identity -- who owns an entry
# --------------------------------------------------------------------------

sub session_file { my ($s) = @_; return session_dir() . '/' . safe_name($s) . '.json' }

sub touch_session {
    my ($session, $extra) = @_;
    return unless $JSON_OK;
    return unless ensure_dirs();
    my $f = session_file($session);
    my $rec = {};
    if (-f $f && open my $fh, '<', $f) {
        local $/;
        my $raw = <$fh>;
        close $fh;
        my $old = eval { decode_json($raw) };
        $rec = $old if $old && ref($old) eq 'HASH';
    }
    $rec->{session}        = $session;
    $rec->{last_seen}      = now_iso();
    $rec->{last_seen_epoch} = time;
    $rec->{workspace}      = workspace_root();
    if ($extra) { $rec->{$_} = $extra->{$_} for keys %$extra }
    my $line = eval { encode_json($rec) };
    return unless defined $line;
    open my $out, '>', $f or return;
    print $out $line, "\n";
    close $out;
}

sub load_session {
    my ($session) = @_;
    return undef unless $JSON_OK;
    my $f = session_file($session);
    return undef unless -f $f;
    open my $fh, '<', $f or return undef;
    local $/;
    my $raw = <$fh>;
    close $fh;
    my $rec = eval { decode_json($raw) };
    return (ref($rec) eq 'HASH') ? $rec : undef;
}

# The harness is identified, never guessed at kill time. CLAUDE_PID is exported
# into the tool environment by Claude Code; if it is absent we fall back to the
# nearest ancestor whose command line looks like the claude binary, and if that
# is absent too we fall back to heartbeat age. Each fallback is recorded so the
# report can say which one it used.
sub current_harness {
    my ($procs, $self) = @_;
    if ($ENV{CLAUDE_PID} && $ENV{CLAUDE_PID} =~ /^\d+$/ && $procs && $procs->{ $ENV{CLAUDE_PID} }) {
        my $p = $procs->{ $ENV{CLAUDE_PID} };
        return { pid => $p->{pid}, started_at => $p->{started_at}, cmd => $p->{cmd}, via => 'CLAUDE_PID' };
    }
    if ($procs && $self) {
        for my $pid (sort { $procs->{$b}{epoch} <=> $procs->{$a}{epoch} } grep { $procs->{$_} } keys %$self) {
            my $p = $procs->{$pid};
            next unless $p->{cmd} =~ /claude(\.exe)?\b/i || $p->{cmd} =~ /cli\.js/i;
            return { pid => $p->{pid}, started_at => $p->{started_at}, cmd => $p->{cmd}, via => 'ancestry' };
        }
    }
    return undef;
}

# --------------------------------------------------------------------------
# the gate -- which Bash calls are even capable of leaving something running
# --------------------------------------------------------------------------
#
# This is the coverage boundary, stated in code. A full process snapshot costs
# roughly two seconds on Windows, so taking one on every Bash call is not
# acceptable. Gating on "could this have backgrounded something" keeps the cost
# on the calls that can actually leak.
#
# Deliberately NOT covered: MCP servers. The harness starts those, not a tool
# call, so no Bash hook ever sees them. That gap lines up exactly with the
# safety boundary: what we cannot prove we started, we must never stop.

sub gate_reason {
    my ($cmd, $bg_flag) = @_;
    return 'run_in_background' if $bg_flag;
    return undef unless defined $cmd && length $cmd;
    return 'trailing &'      if $cmd =~ /&\s*(?:#[^\n]*)?$/m;
    return 'nohup'           if $cmd =~ /\bnohup\b/;
    return 'setsid'          if $cmd =~ /\bsetsid\b/;
    return 'disown'          if $cmd =~ /\bdisown\b/;
    return 'start /b'        if $cmd =~ /\bstart\b[^\n]*\s\/b\b/i;
    return 'Start-Process'   if $cmd =~ /\bStart-Process\b/i;
    return 'Start-Job'       if $cmd =~ /\bStart-Job\b/i;
    return 'docker detached' if $cmd =~ /\bdocker\b[^\n]*\s-d\b/;
    return 'docker compose up -d' if $cmd =~ /\bdocker[- ]compose\b[^\n]*\bup\b[^\n]*\s-d\b/;
    return 'pm2 start'       if $cmd =~ /\bpm2\s+start\b/;
    return 'screen/tmux'     if $cmd =~ /\b(?:screen|tmux)\s+(?:-d|new-session|new)\b/;
    return undef;
}

# Tokens the launched process should carry if it really came from this command.
sub command_tokens {
    my ($cmd) = @_;
    return () unless defined $cmd;
    my %stop = map { $_ => 1 } qw(
        cd echo set export then else elif fi do done if while for in and or
        sudo env exec bash sh cmd powershell pwsh nohup setsid disown start
        time nice true false null dev tmp var usr bin the run npx with
    );
    my (@out, %seen);
    for my $t (split /[\s;|&()<>{}\[\]"'`,]+/, $cmd) {
        next unless defined $t && length $t;
        next if $t =~ /^-/;
        my @cands = ($t);
        if ($t =~ m{[/\\]}) {
            my $b = $t;
            $b =~ s{.*[/\\]}{};
            push @cands, $b if length $b;
        }
        for my $c (@cands) {
            $c =~ s/^\W+|\W+$//g;
            next unless length($c) >= 3;
            next if $stop{ lc $c };
            next if $seen{ lc $c }++;
            push @out, $c;
            return @out if @out >= 16;
        }
    }
    return @out;
}

# --------------------------------------------------------------------------
# subcommand: pre
# --------------------------------------------------------------------------
# Cheapest possible: one regex over stdin, one file write. No process
# enumeration here. Its only job is to bound the capture window so a survivor
# cannot be attributed to a command that did not start it.

sub cmd_pre {
    my $raw = read_stdin();
    my $session = quick_session_id($raw);
    eval {
        ensure_dirs() or die "cannot create ledger directory\n";
        my $f = pending_dir() . '/' . safe_name($session) . '.t0';
        open my $fh, '>', $f or die "cannot write $f: $!\n";
        print $fh time, "\n";
        close $fh;
        1;
    } or note_degraded('pre', "could not stamp the tool call: $@");
    exit 0;
}

# --------------------------------------------------------------------------
# subcommand: post
# --------------------------------------------------------------------------

sub cmd_post {
    my $raw = read_stdin();
    my $session = quick_session_id($raw);

    if (!$JSON_OK) {
        note_degraded('post', 'perl JSON::PP is not installed, so nothing can be recorded');
        exit 0;
    }

    if (my $bad = ledger_unusable()) {
        note_degraded('post', "nothing could be recorded: $bad");
        exit 0;
    }

    my $ok = eval { post_body($raw, $session); 1 };
    note_degraded('post', "capture failed: $@") unless $ok;
    exit 0;
}

sub post_body {
    my ($raw, $session) = @_;

    my $j = eval { decode_json($raw) };
    if (!$j || ref($j) ne 'HASH') {
        note_degraded('post', 'hook payload was not readable JSON');
        return;
    }
    my $tool = $j->{tool_name} || '';
    return if $tool ne '' && $tool ne 'Bash';

    my $ti  = (ref($j->{tool_input}) eq 'HASH') ? $j->{tool_input} : {};
    my $cmd = $ti->{command};
    my $bg  = $ti->{run_in_background};
    $bg = ($bg && $bg ne 'false') ? 1 : 0;

    my $marker = pending_dir() . '/' . safe_name($session) . '.t0';
    my $t0;
    if (-f $marker && open my $fh, '<', $marker) {
        my $l = <$fh>;
        close $fh;
        chomp $l if defined $l;
        $t0 = $l if defined $l && $l =~ /^\d+$/;
    }
    my $window_fallback = 0;
    if (!defined $t0) {
        $t0 = time - $NO_MARKER_FALLBACK;
        $window_fallback = 1;
    }
    # Consume the marker either way. A stale stamp left by a crash between pre
    # and post would silently widen the next window.
    unlink $marker if -f $marker;

    my $reason = gate_reason($cmd, $bg);
    return unless $reason;

    my ($procs, $self, $err) = probe();
    if (!$procs) {
        note_degraded('post', "could not read the process table, so a backgrounded command went unrecorded: $err");
        return;
    }

    my $harness = current_harness($procs, $self);
    touch_session($session, $harness ? {
        harness_pid        => $harness->{pid},
        harness_started_at => $harness->{started_at},
        harness_via        => $harness->{via},
    } : {});

    my $floor = $t0 - $WINDOW_SLACK_SECONDS;
    my @fresh = grep { $_->{epoch} >= $floor } values %$procs;
    return unless @fresh;

    # Vetoes are applied here, not by quietly filtering the list, so that
    # "excluded on purpose" and "never seen" stay distinguishable to a reader.
    my (@vetoed, @eligible);
    for my $p (@fresh) {
        my $why = $self->{ $p->{pid} }
                ? 'this hook, the harness, or their machinery (pid is in the exclusion set)'
                : is_machinery($p->{cmd});
        if (defined $why) { push @vetoed, [$p, $why] }
        else              { push @eligible, $p }
    }

    # Ancestry correlation walks eligible processes only. A vetoed ancestor
    # must never launder a child into the ledger, which is how conhost.exe
    # rode in behind the tool shell.
    my %eligible_by_pid = map { $_->{pid} => $_ } @eligible;
    my @tokens = command_tokens($cmd);

    my (@recorded, @unattributed);
    for my $p (sort { $a->{pid} <=> $b->{pid} } @eligible) {
        my $matched = match_token($p->{cmd}, \@tokens);
        my $via = defined $matched ? "command token '$matched'" : undef;
        if (!defined $via) {
            # in-window ancestry only: a long-lived ancestor (the harness) must
            # never launder an unrelated process into the ledger
            my $cur = $p->{ppid};
            my $hops = 0;
            while ($cur && $hops++ < 5 && $eligible_by_pid{$cur}) {
                my $m = match_token($eligible_by_pid{$cur}{cmd}, \@tokens);
                if (defined $m) { $via = "in-window ancestor pid $cur (token '$m')"; last }
                $cur = $eligible_by_pid{$cur}{ppid};
            }
        }
        if (defined $via) { push @recorded, [$p, $via] }
        else              { push @unattributed, $p }
    }

    if (@vetoed) {
        my @samples = map { { pid => $_->[0]{pid}, cmd => substr($_->[0]{cmd}, 0, 160), veto => $_->[1] } }
                      @vetoed[0 .. ($#vetoed < $MAX_UNATTRIBUTED_LOG - 1 ? $#vetoed : $MAX_UNATTRIBUTED_LOG - 1)];
        append_record({
            type         => 'vetoed',
            at           => now_iso(),
            session      => $session,
            tool_command => (defined $cmd ? substr($cmd, 0, 500) : ''),
            count        => scalar(@vetoed),
            samples      => \@samples,
            note         => 'refused as machinery before attribution ran; never eligible to be recorded or stopped',
        });
    }

    my $seq = 0;
    for my $r (@recorded) {
        my ($p, $via) = @$r;
        $seq++;
        append_record({
            type               => 'open',
            uid                => sprintf('%d-%d-%d', time, $p->{pid}, $seq),
            pid                => $p->{pid},
            started_at         => $p->{started_at},
            started_epoch      => $p->{epoch},
            cmd                => $p->{cmd},
            workspace          => workspace_root(),
            session            => $session,
            started_by         => 'bash-tool',
            ppid               => $p->{ppid},
            rss_kb_at_record   => $p->{rss_kb},
            recorded_at        => now_iso(),
            tool_command       => (defined $cmd ? substr($cmd, 0, 500) : ''),
            gate               => $reason,
            matched_on         => $via,
            window_fallback    => ($window_fallback ? JSON::PP::true() : JSON::PP::false()),
            harness_pid        => ($harness ? $harness->{pid} : undef),
            harness_started_at => ($harness ? $harness->{started_at} : undef),
        });
    }

    # Report the no-op. Processes that appeared during the window but could not
    # be tied to this command are written down and never stopped, so that
    # "nothing was recorded" is a visible fact rather than silence.
    if (@unattributed) {
        my @samples = map { { pid => $_->{pid}, cmd => substr($_->{cmd}, 0, 160) } }
                      @unattributed[0 .. ($#unattributed < $MAX_UNATTRIBUTED_LOG - 1 ? $#unattributed : $MAX_UNATTRIBUTED_LOG - 1)];
        append_record({
            type         => 'unattributed',
            at           => now_iso(),
            session      => $session,
            tool_command => (defined $cmd ? substr($cmd, 0, 500) : ''),
            gate         => $reason,
            count        => scalar(@unattributed),
            recorded     => scalar(@recorded),
            samples      => \@samples,
            note         => 'seen during the window, not attributable to this command, reported and never stopped',
        });
    }
    return;
}

# Attribution matches on the process's EXECUTABLE only, never on a substring
# of the whole command line.
#
# The loose version (`index($cmd, $token) >= 0`) matched the token "sleep" from
# `sleep 700 &` against an unrelated `perl -e "sleep 900"`, and matched every
# Claude tool shell, because the tool shell embeds the command verbatim inside
# one of its own arguments. Anything that merely contains the text is not
# evidence that this command started it.
#
# Cost of the tightening, stated honestly: an interpreter-wrapped launch whose
# child runs under a different executable (`npm run dev` spawning node) will no
# longer be attributed. It is reported as unattributed instead, which is the
# safe direction ... unrecorded means unstoppable.
sub exe_basename {
    my ($cmd) = @_;
    return undef unless defined $cmd && $cmd =~ /\S/;
    my $exe;
    if ($cmd =~ /^\s*"([^"]+)"/)      { $exe = $1 }
    elsif ($cmd =~ /^\s*\\\?\?\\(\S+)/) { $exe = $1 }
    elsif ($cmd =~ /^\s*(\S+)/)       { $exe = $1 }
    return undef unless defined $exe;
    $exe =~ s{.*[\\/]}{};
    return lc $exe;
}

sub match_token {
    my ($cmd, $tokens) = @_;
    my $base = exe_basename($cmd);
    return undef unless defined $base;
    my $noext = $base;
    $noext =~ s/\.(exe|com|bat|cmd)$//;
    for my $t (@$tokens) {
        my $lt = lc $t;
        return $t if $lt eq $base || $lt eq $noext;
        my $tb = $lt;
        $tb =~ s{.*[\\/]}{};
        next unless length $tb;
        return $t if $tb eq $base || $tb eq $noext;
    }
    return undef;
}

# --------------------------------------------------------------------------
# classification
# --------------------------------------------------------------------------
# GONE          the pid is not running. Safe to close.
# MISMATCH      the pid is running but is NOT what we recorded. NEVER touched.
# OTHER-WINDOW  identity verified, but another live Claude harness owns it.
# STOPPABLE     identity verified and either this harness owns it or the owning
#               harness is provably gone.

sub classify {
    my ($entries, $procs, $harness_now) = @_;
    my @rows;
    for my $e (@$entries) {
        my $row = { entry => $e, pid => $e->{pid} };
        my $live = $procs->{ $e->{pid} };
        if (!$live) {
            # Before retiring the entry, check whether the recorded command and
            # start time are still running under some OTHER pid. If they are,
            # the pid field was altered or corrupted and the process is very
            # much alive. Retiring it there would lose a live process for good.
            # This reads the table to REPORT only: a MISMATCH is never
            # stoppable, so no target is ever selected from it.
            my $twin = find_twin($procs, $e);
            if ($twin) {
                $row->{status} = 'MISMATCH';
                $row->{detail} = "the recorded pid $e->{pid} does not exist, but the recorded "
                    . "command and start time are running as pid $twin->{pid}. The pid in the "
                    . "ledger was altered or corrupted, so this entry stays open and is never acted on";
                push @rows, $row;
                next;
            }
            $row->{status} = 'GONE';
            $row->{detail} = 'no process with this pid is running any more, and nothing else '
                           . 'matches the recorded command and start time';
            push @rows, $row;
            next;
        }
        $row->{live} = $live;
        my @diffs;
        push @diffs, "start time: ledger has '" . (defined $e->{started_at} ? $e->{started_at} : '(missing)')
            . "', pid $e->{pid} actually started '" . $live->{started_at} . "'"
            if !defined $e->{started_at} || $e->{started_at} ne $live->{started_at};
        push @diffs, "command: ledger has '" . short(defined $e->{cmd} ? $e->{cmd} : '(missing)')
            . "', pid $e->{pid} is actually running '" . short($live->{cmd}) . "'"
            if !defined $e->{cmd} || $e->{cmd} ne $live->{cmd};
        # Windows only. On unix the epoch is derived from elapsed time, which
        # jitters by a second between reads; comparing it there would mark
        # every entry MISMATCH and silently disable the feature.
        if ($IS_WIN && defined $e->{started_epoch} && $e->{started_epoch} != $live->{epoch}) {
            push @diffs, "recorded start timestamp $e->{started_epoch} does not match the live one $live->{epoch}";
        }
        if (@diffs) {
            $row->{status} = 'MISMATCH';
            $row->{detail} = join('; ', @diffs);
            push @rows, $row;
            next;
        }
        # The machinery veto has to run HERE too, not only when recording.
        # A ledger entry whose triple honestly describes Claude's own tool
        # shell would otherwise verify perfectly and become stoppable. Every
        # other guard in this file is about whether the entry is TRUE; this one
        # is about whether the target is ours to touch at all, and truth does
        # not make a shell safe to kill.
        if (my $mach = is_machinery($live->{cmd})) {
            $row->{status} = 'MACHINERY';
            $row->{detail} = "identity verified, but this is $mach. Never stoppable from here, "
                           . "no matter what the ledger says";
            push @rows, $row;
            next;
        }
        # identity verified. now: who owns it?
        my ($own, $why) = owner_of($e, $procs, $harness_now);
        $row->{status} = $own;
        $row->{detail} = $why;
        push @rows, $row;
    }
    return \@rows;
}

sub find_twin {
    my ($procs, $e) = @_;
    return undef unless defined $e->{started_at} && defined $e->{cmd} && length $e->{cmd};
    for my $p (values %$procs) {
        return $p if $p->{started_at} eq $e->{started_at} && $p->{cmd} eq $e->{cmd};
    }
    return undef;
}

sub owner_of {
    my ($e, $procs, $harness_now) = @_;
    my $hp = $e->{harness_pid};
    if ($hp && $harness_now && $hp == $harness_now->{pid}) {
        return ('STOPPABLE', 'started by this Claude instance');
    }
    if ($hp) {
        my $live = $procs->{$hp};
        if ($live && (!defined $e->{harness_started_at} || $live->{started_at} eq $e->{harness_started_at})) {
            return ('OTHER-WINDOW', "another Claude window (pid $hp) is still running and owns this");
        }
        return ('STOPPABLE', "the Claude session that started it (pid $hp) has ended");
    }
    # No harness identity was captured. Fall back to heartbeat age, and say so.
    my $s = load_session($e->{session} || '');
    my $seen = $s ? ($s->{last_seen_epoch} || 0) : 0;
    my $age = time - $seen;
    if ($seen && $age < $LIVE_WINDOW_SECONDS) {
        my $mins = int($age / 60);
        return ('OTHER-WINDOW', "no owner pid was recorded; that session was active ${mins}m ago so it is treated as still open");
    }
    return ('STOPPABLE', 'no owner pid was recorded and that session has not been seen for hours');
}

sub short {
    my ($s) = @_;
    $s = '' unless defined $s;
    # A hand-edited ledger can contain newlines. Collapse them so a mangled
    # entry cannot break the layout of the report the user has to read.
    $s =~ s/[\r\n\t]+/ /g;
    return length($s) > 90 ? substr($s, 0, 87) . '...' : $s;
}

sub human_age {
    my ($secs) = @_;
    return '?' unless defined $secs;
    $secs = 0 if $secs < 0;
    return sprintf('%dm', int($secs / 60)) if $secs < 3600;
    return sprintf('%dh%02dm', int($secs / 3600), int(($secs % 3600) / 60)) if $secs < 86400;
    return sprintf('%dd%02dh', int($secs / 86400), int(($secs % 86400) / 3600));
}

sub human_mb {
    my ($kb) = @_;
    return '?' unless defined $kb;
    return sprintf('%.1f MB', $kb / 1024);
}

sub consent_token {
    my ($rows) = @_;
    my @c = sort { $a->{pid} <=> $b->{pid} } grep { $_->{status} eq 'STOPPABLE' } @$rows;
    return 'none' unless @c;
    my $blob = join("\n", map {
        $_->{pid} . '|' . (defined $_->{entry}{started_at} ? $_->{entry}{started_at} : '')
                  . '|' . (defined $_->{entry}{cmd}        ? $_->{entry}{cmd}        : '')
    } @c);
    return substr(md5_hex($blob), 0, 12);
}

# --------------------------------------------------------------------------
# subcommand: list
# --------------------------------------------------------------------------

sub cmd_list {
    if (!$JSON_OK) {
        print "PROCESS LEDGER UNAVAILABLE\n";
        print "perl's JSON::PP module is missing on this machine, so the background\n";
        print "process ledger cannot be read. Nothing has been recorded and nothing\n";
        print "can be stopped. This is not the same as 'no background processes'.\n";
        return 2;
    }
    print "BACKGROUND PROCESS LEDGER\n";
    print "Workspace:   " . workspace_root() . "\n";
    print "Resolved by: " . workspace_root_via() . "\n";
    print "Ledger file: " . ledger_file() . "\n";

    if (workspace_root_via() eq 'UNRESOLVED') {
        print "\n";
        unavailable_banner(
            "I could not work out which workspace this is. CLAUDE_PROJECT_DIR is not set and "
          . "there is no .claude/workspace.yml, CLAUDE.md, RULES.md or .git anywhere above the "
          . "current directory",
            "I cannot tell you what this workspace left running");
        print "Run this from the workspace root, or run /super-setup to scaffold it.\n";
        print "\nSTOPPABLE: 0\nCONSENT TOKEN: none\n";
        return 2;
    }

    if (my $bad = ledger_unusable()) {
        print "\n";
        unavailable_banner($bad, "I cannot tell you what is running");
        print "\nSTOPPABLE: 0\nCONSENT TOKEN: none\n";
        return 2;
    }

    my ($entries, $errors, $unattr, $degraded) = load_ledger();
    my ($degrecent, $degolder) = read_degraded_split();

    for my $e (@$errors)     { print "! LEDGER READ PROBLEM: $e\n" }
    for my $d (@$degrecent)  { print "! DEGRADED (last 24h): $d\n" }
    print "(note: $degolder older degraded entries in " . degraded_file() . ")\n" if $degolder;

    if (!@$entries) {
        my @sibs = sibling_ledgers();
        if (@sibs) {
            print "\nNothing is recorded for THIS workspace, but " . scalar(@sibs)
                . " other workspace(s) have ledgers here:\n";
            print "  $_\n" for @sibs;
            print "If you expected entries, check that the workspace above is the one you mean.\n";
        }
        print "\nNo background processes are recorded as still running for this workspace.\n";
        print "That is a real answer, not a skipped check: the ledger folder was read and\n";
        print "written to successfully, and it holds no open entries.\n";
        print "\nRecording covers Bash commands that background something (a trailing &,\n";
        print "nohup, docker -d, run_in_background and similar). It deliberately does not\n";
        print "cover MCP servers, which Claude starts itself.\n";
        print "\nSTOPPABLE: 0\nCONSENT TOKEN: none\n";
        return 0;
    }

    my ($procs, $self, $err) = probe();
    if (!$procs) {
        print "\n! Could not read the process table ($err).\n";
        print "There are " . scalar(@$entries) . " open ledger entries but they cannot be\n";
        print "verified right now, so NOTHING can be stopped. Reporting them unverified:\n";
        for my $e (@$entries) {
            print "  pid $e->{pid}  session " . substr($e->{session} || '?', 0, 8)
                . "  " . short($e->{cmd}) . "\n";
        }
        print "\nSTOPPABLE: 0\nCONSENT TOKEN: none\n";
        return 2;
    }

    my $harness_now = current_harness($procs, $self);
    my $rows = classify($entries, $procs, $harness_now);

    # A dead pid can be closed with certainty, so do not nag about it twice.
    for my $r (@$rows) {
        close_entry($r->{entry}, 'gone', 'process no longer exists') if $r->{status} eq 'GONE';
    }

    print "This Claude instance: " . ($harness_now ? "pid $harness_now->{pid} (found via $harness_now->{via})"
                                                   : "not identified, ownership falls back to session heartbeat") . "\n";
    print "\n";

    my $i = 0;
    my $stoppable_kb = 0;
    my $n_stop = 0;
    for my $r (sort { $a->{pid} <=> $b->{pid} } @$rows) {
        $i++;
        my $e = $r->{entry};
        my $age = $r->{live} ? human_age(time - $r->{live}{epoch}) : '-';
        my $ram = $r->{live} ? human_mb($r->{live}{rss_kb}) : '-';
        printf("%d) pid %-7s %-12s age %-8s ram %-10s\n", $i, $r->{pid}, $r->{status}, $age, $ram);
        print  "   command:   " . short($e->{cmd}) . "\n";
        print  "   recorded:  " . ($e->{recorded_at} || '?') . " by session "
             . substr($e->{session} || '?', 0, 8) . " (matched on " . ($e->{matched_on} || '?') . ")\n";
        print  "   from:      " . short($e->{tool_command} || '?') . "\n";
        print  "   status:    $r->{detail}\n";
        if ($r->{status} eq 'MISMATCH') {
            print "   ACTION:    WILL NOT BE STOPPED. Windows and Linux both reuse pid numbers,\n";
            print "              so a pid that no longer matches what we recorded is a different\n";
            print "              program now. Stopping it would kill something we never started.\n";
        }
        if ($r->{status} eq 'MACHINERY') {
            print "   ACTION:    WILL NOT BE STOPPED. This is Claude's own plumbing. It is refused\n";
            print "              even though the ledger entry is accurate, because stopping it\n";
            print "              would kill the shell every command runs in, or Claude itself.\n";
        }
        if ($r->{status} eq 'STOPPABLE') {
            $n_stop++;
            $stoppable_kb += $r->{live}{rss_kb};
        }
        print "\n";
    }

    if (@$unattr) {
        my $tot = 0;
        $tot += ($_->{count} || 0) for @$unattr;
        print "Also seen, never recorded and never stoppable: $tot process(es) started during\n";
        print "a backgrounding command but not attributable to it. They are reported here only.\n\n";
    }

    my $vetoed_total = 0;
    $vetoed_total += ($_->{count} || 0) for grep { $_->{_veto} } @$degraded;
    if ($vetoed_total) {
        print "Refused as machinery before they could ever be recorded: $vetoed_total process(es)\n";
        print "(Claude's own tool shells, console hosts, this plugin's hooks). Written down in the\n";
        print "ledger as 'vetoed' records so refused stays distinguishable from never seen.\n\n";
    }

    printf("STOPPABLE: %d (about %s)\n", $n_stop, human_mb($stoppable_kb));
    print "CONSENT TOKEN: " . consent_token($rows) . "\n";
    if ($n_stop) {
        print "To stop, after the user says yes to these specific items:\n";
        print "  process-ledger stop --token " . consent_token($rows) . " --pids "
            . join(',', map { $_->{pid} } grep { $_->{status} eq 'STOPPABLE' } @$rows) . "\n";
    }
    return 0;
}

# --------------------------------------------------------------------------
# subcommand: stop
# --------------------------------------------------------------------------

sub kill_pid {
    my ($pid, $force) = @_;
    if ($IS_WIN) {
        # The doubled slashes are deliberate. Git Bash rewrites a lone "/F"
        # into the path "F:/" before taskkill ever sees it, which fails with
        # "Invalid argument/option" and leaves the process running. Verified on
        # Windows 11 with Git for Windows.
        my $f = $force ? '//F ' : '';
        my $out = `taskkill ${f}//PID $pid 2>&1`;
        $out = '' unless defined $out;
        if ($force && $out =~ /Invalid argument|not recognized|cannot find the path/i) {
            my $ps = have_cmd('powershell') ? 'powershell' : (have_cmd('pwsh') ? 'pwsh' : undef);
            if ($ps) {
                my $out2 = `$ps -NoProfile -Command "Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue" 2>&1`;
                $out .= ' | fallback Stop-Process: ' . (defined $out2 ? $out2 : '(no output)');
            }
        }
        return $out;
    }
    my $sig = $force ? 'KILL' : 'TERM';
    kill $sig, $pid;
    return "sent SIG$sig";
}

sub still_matches {
    my ($entry) = @_;
    my ($procs, $ignore_self, $err) = probe();
    return (undef, "process table unreadable: $err") unless $procs;
    my $live = $procs->{ $entry->{pid} };
    return (0, 'process is gone') unless $live;
    return (0, 'identity no longer matches the ledger')
        if !defined $entry->{started_at} || $entry->{started_at} ne $live->{started_at}
        || !defined $entry->{cmd}        || $entry->{cmd}        ne $live->{cmd};
    # Last gate before the signal. Re-asked here so that a machinery target
    # cannot slip through between classification and the kill.
    if (my $mach = is_machinery($live->{cmd})) {
        return (0, "this is $mach and is never stoppable");
    }
    return (1, 'verified');
}

sub cmd_stop {
    my (@args) = @_;
    if (!$JSON_OK) {
        print "PROCESS LEDGER UNAVAILABLE: perl's JSON::PP module is missing, so nothing\n";
        print "can be verified and therefore nothing will be stopped.\n";
        return 2;
    }
    my ($token, $pidspec);
    while (@args) {
        my $a = shift @args;
        if    ($a eq '--token') { $token   = shift @args }
        elsif ($a eq '--pids')  { $pidspec = shift @args }
        else { print "Unknown argument '$a'. Usage: stop --token <token> --pids <pid,pid|all>\n"; return 2 }
    }
    if (!defined $token || $token eq '') {
        print "REFUSED: no consent token.\n";
        print "Run `list` first, show that list to the user, get an explicit yes for those\n";
        print "specific processes, then pass the token `list` printed. Nothing is stopped\n";
        print "without a token that matches the exact list the user approved.\n";
        return 2;
    }
    if (!defined $pidspec || $pidspec eq '') {
        print "REFUSED: no --pids given. Name the exact pids the user approved, or 'all'.\n";
        return 2;
    }
    if (workspace_root_via() eq 'UNRESOLVED') {
        print "REFUSED: I could not work out which workspace this is, so I cannot prove any\n";
        print "process belongs to it. Nothing was stopped.\n";
        return 2;
    }
    if (my $bad = ledger_unusable()) {
        print "REFUSED: $bad, so nothing can be verified. Nothing was stopped.\n";
        return 2;
    }

    my ($entries, $errors, $ignore_u, $ignore_d) = load_ledger();
    for my $e (@$errors) { print "! LEDGER READ PROBLEM: $e\n" }

    my ($procs, $self, $err) = probe();
    if (!$procs) {
        print "REFUSED: the process table could not be read ($err), so no identity can be\n";
        print "verified. Nothing was stopped.\n";
        return 2;
    }
    my $harness_now = current_harness($procs, $self);
    my $rows = classify($entries, $procs, $harness_now);
    my %by_pid = map { $_->{pid} => $_ } @$rows;

    my @want = ($pidspec eq 'all')
        ? (map { $_->{pid} } grep { $_->{status} eq 'STOPPABLE' } @$rows)
        : (grep { /^\d+$/ } split /[,\s]+/, $pidspec);

    if (!@want) {
        print "Nothing to do: no pids were selected. Nothing was stopped.\n";
        return 0;
    }

    # Per-pid verdicts are printed BEFORE the token check so the reason a
    # particular process is skipped is always legible, even when the whole
    # batch is refused.
    my $current = consent_token($rows);
    my (@go, @skipped);
    for my $pid (@want) {
        my $r = $by_pid{$pid};
        if (!$r) {
            print "pid $pid: SKIPPED ... not in the ledger. This tool only ever stops things\n";
            print "         it recorded itself. Anything else is reported, never stopped.\n";
            push @skipped, $pid;
            next;
        }
        if ($r->{status} eq 'GONE') {
            print "pid $pid: ALREADY GONE ... it exited on its own. Closing the ledger entry.\n";
            close_entry($r->{entry}, 'gone', 'process had already exited');
            next;
        }
        if ($r->{status} eq 'MISMATCH') {
            print "pid $pid: SKIPPED ... identity mismatch, NOT stopped.\n";
            print "         $r->{detail}\n";
            print "         Pid numbers get reused, so this is a different program now.\n";
            push @skipped, $pid;
            next;
        }
        if ($r->{status} eq 'OTHER-WINDOW') {
            print "pid $pid: SKIPPED ... $r->{detail}.\n";
            print "         Close that window first, or stop it from there.\n";
            push @skipped, $pid;
            next;
        }
        if ($r->{status} eq 'MACHINERY') {
            print "pid $pid: SKIPPED ... $r->{detail}.\n";
            print "         This is Claude's own plumbing. Stopping it would kill the shell\n";
            print "         every command runs in, or Claude itself.\n";
            push @skipped, $pid;
            next;
        }
        # Default is SKIP, not kill. Only an explicit STOPPABLE proceeds, so a
        # status added later cannot fall through into the kill list.
        if ($r->{status} ne 'STOPPABLE') {
            print "pid $pid: SKIPPED ... status $r->{status}: $r->{detail}\n";
            push @skipped, $pid;
            next;
        }
        push @go, $r;
    }

    if (!@go) {
        printf("\nStopped 0, skipped %d. Nothing was stopped.\n", scalar @skipped);
        return 0;
    }

    if ($token ne $current) {
        print "\nREFUSED: the consent token does not match the current list.\n";
        print "  token given:   $token\n";
        print "  token now:     $current\n";
        print "The set of stoppable processes changed since the user approved it, so the\n";
        print "approval no longer describes what would be stopped. Nothing was stopped.\n";
        print "Re-run `list`, show the new list, and ask again.\n";
        return 2;
    }

    my $stopped = 0;
    my $freed_kb = 0;
    for my $r (@go) {
        my $pid = $r->{pid};
        my $kb  = $r->{live}{rss_kb};
        # Re-verify immediately before the signal. Between `list` and here the
        # process could have exited and the pid been handed to something else.
        my ($ok, $why) = still_matches($r->{entry});
        if (!defined $ok) { print "pid $pid: SKIPPED ... $why\n"; next }
        if (!$ok) {
            if ($why eq 'process is gone') {
                print "pid $pid: ALREADY GONE ... it exited between the check and now.\n";
                close_entry($r->{entry}, 'gone', 'exited before the stop');
            } else {
                print "pid $pid: SKIPPED ... $why. Not stopped.\n";
            }
            next;
        }
        my $out = kill_pid($pid, 0);
        sleep 2;
        my ($ok2, $why2) = still_matches($r->{entry});
        if (defined $ok2 && !$ok2 && $why2 eq 'process is gone') {
            print "pid $pid: STOPPED (asked it to close).\n";
            close_entry($r->{entry}, 'stopped', 'graceful stop');
            $stopped++; $freed_kb += $kb;
            next;
        }
        if (defined $ok2 && !$ok2) {
            print "pid $pid: SKIPPED ... $why2 after the first signal. Not forcing.\n";
            next;
        }
        # Still alive and still the same process: escalate under the same consent.
        $out = kill_pid($pid, 1);
        sleep 1;
        my ($ok3, $why3) = still_matches($r->{entry});
        if (defined $ok3 && !$ok3 && $why3 eq 'process is gone') {
            print "pid $pid: STOPPED (forced ... it ignored the polite request).\n";
            close_entry($r->{entry}, 'stopped', 'forced stop');
            $stopped++; $freed_kb += $kb;
        } else {
            print "pid $pid: FAILED ... still running after a forced stop. Left alone and\n";
            print "         left in the ledger. Stop it yourself, or reboot. ($out)\n";
        }
    }

    printf("\nStopped %d, skipped %d. Freed about %s.\n", $stopped, scalar @skipped, human_mb($freed_kb));
    return 0;
}

# --------------------------------------------------------------------------
# subcommand: session-start
# --------------------------------------------------------------------------
# Closeout catches what this session started. This catches what a session that
# crashed never got to close, which is exactly how multi-day survivors happen.

sub json_escape {
    my ($s) = @_;
    $s = '' unless defined $s;
    $s =~ s/\\/\\\\/g;
    $s =~ s/"/\\"/g;
    $s =~ s/\r/\\r/g;
    $s =~ s/\n/\\n/g;
    $s =~ s/\t/\\t/g;
    return $s;
}

sub cmd_session_start {
    my $raw = read_stdin();
    my $session = quick_session_id($raw);
    eval {
        touch_session($session, {}) if $JSON_OK;
        if (!$JSON_OK) {
            emit_context("The workspace-superengine background process ledger cannot run on "
                . "this machine: perl's JSON::PP module is missing. Background processes "
                . "started by Bash commands are NOT being tracked this session. Tell the "
                . "user this plainly if they ask about background processes.");
            exit 0;
        }
        if (my $bad = ledger_unusable()) {
            emit_context("The workspace-superengine background process ledger cannot run: "
                . "$bad. Background processes started by Bash commands are NOT being tracked "
                . "this session, and any report that nothing is running would be false. Tell "
                . "the user this plainly if background processes come up.");
            exit 0;
        }
        # Read AFTER ledger_unusable(), which drains the out-of-band marker once
        # the ledger is healthy again. Only the last 24 hours is worth a banner;
        # an old fault that has since healed must not nag every session, or the
        # banner stops being read at all.
        my ($degrecent, $degolder) = read_degraded_split();
        my ($entries, $errors, $ignore_u, $ignore_d) = load_ledger();
        if (!@$entries && !@$errors && !@$degrecent) { exit 0 }

        my ($procs, $self, $err) = probe();
        my @lines;
        if (!$procs) {
            push @lines, "There are " . scalar(@$entries) . " open background-process ledger "
                . "entries for this workspace, but the process table could not be read ($err), "
                . "so none of them can be verified or stopped right now.";
        }
        else {
            my $harness_now = current_harness($procs, $self);
            my $rows = classify($entries, $procs, $harness_now);
            for my $r (@$rows) {
                close_entry($r->{entry}, 'gone', 'process no longer exists') if $r->{status} eq 'GONE';
            }
            my @stop = grep { $_->{status} eq 'STOPPABLE' } @$rows;
            my @mis  = grep { $_->{status} eq 'MISMATCH' } @$rows;
            my $kb = 0; $kb += $_->{live}{rss_kb} for @stop;
            if (@stop) {
                push @lines, "SWEEP: " . scalar(@stop) . " background process(es) recorded by this "
                    . "workspace's earlier sessions are still running (about " . human_mb($kb) . "). "
                    . "They were recorded at the moment a Bash command started them, so ownership is "
                    . "known rather than guessed. Offer to review them in Phase 3.5 of /session-start. "
                    . "Nothing is ever stopped without the user saying yes to that specific list.";
            }
            if (@mis) {
                push @lines, "SWEEP: " . scalar(@mis) . " ledger entry(ies) no longer match the "
                    . "process running under that pid, so they will never be stopped. Report them, "
                    . "do not act on them.";
            }
        }
        push @lines, "LEDGER PROBLEM: $_" for @$errors;
        push @lines, "LEDGER DEGRADED: $_" for @$degrecent;
        exit 0 unless @lines;
        emit_context(join(' ', @lines));
        1;
    } or note_degraded('session-start', "sweep failed: $@");
    exit 0;
}

sub emit_context {
    my ($text) = @_;
    my $esc = json_escape($text);
    if ($ENV{CURSOR_PLUGIN_ROOT}) {
        print "{\n  \"additional_context\": \"$esc\"\n}\n";
    }
    elsif ($ENV{CLAUDE_PLUGIN_ROOT} && !$ENV{COPILOT_CLI}) {
        print "{\n  \"hookSpecificOutput\": {\n    \"hookEventName\": \"SessionStart\",\n    \"additionalContext\": \"$esc\"\n  }\n}\n";
    }
    else {
        print "{\n  \"additionalContext\": \"$esc\"\n}\n";
    }
}

# --------------------------------------------------------------------------
# subcommand: paths
# --------------------------------------------------------------------------

# Diagnostic. Reads candidate command lines on stdin, one per line, and reports
# how each would be treated. Exists so the machinery veto and the attribution
# rule can each be checked ON THEIR OWN, by someone who did not build this,
# without editing the file. They are meant to be independently sufficient; that
# claim is only worth something if it can be tested one at a time.
sub cmd_explain {
    my (@args) = @_;
    my $tool_cmd = '';
    while (@args) {
        my $a = shift @args;
        if ($a eq '--tool-command') { $tool_cmd = shift(@args) // '' }
        else { print "Unknown argument '$a'. Usage: explain --tool-command \"<bash command>\" < candidates\n"; return 2 }
    }
    my @tokens = command_tokens($tool_cmd);
    print "tool command: $tool_cmd\n";
    print "tokens:       " . (@tokens ? join(', ', @tokens) : '(none)') . "\n";
    print "-" x 60 . "\n";
    while (my $line = <STDIN>) {
        $line =~ s/\s+$//;
        next unless length $line;
        my $veto = is_machinery($line);
        my $exe  = exe_basename($line);
        my $tok  = match_token($line, \@tokens);
        print "candidate:  " . short($line) . "\n";
        print "  executable:      " . (defined $exe ? $exe : '(unreadable)') . "\n";
        print "  machinery veto:  " . (defined $veto ? "YES ... $veto" : 'no') . "\n";
        print "  attribution:     " . (defined $tok ? "MATCHES token '$tok'" : 'no match ... would not be recorded') . "\n";
        print "  verdict:         " . ((defined $veto || !defined $tok) ? 'NEVER RECORDED' : 'would be recorded') . "\n";
    }
    return 0;
}

sub cmd_paths {
    print "workspace:    " . workspace_root() . "\n";
    print "slug:         " . workspace_slug() . "\n";
    print "ledger dir:   " . ws_dir() . "\n";
    print "ledger file:  " . ledger_file() . "\n";
    print "cli:          " . ($ENV{WSE_LEDGER_CLI} || '(unknown)') . "\n";
    print "harness pid:  " . ($ENV{CLAUDE_PID} || '(CLAUDE_PID not set)') . "\n";
    print "JSON::PP:     " . ($JSON_OK ? 'available' : 'MISSING ... ledger cannot run') . "\n";
    print "platform:     " . ($IS_WIN ? 'windows' : 'unix') . " ($^O)\n";
    return 0;
}

# --------------------------------------------------------------------------

sub write_cli_pointer {
    return unless $ENV{WSE_LEDGER_CLI};
    eval {
        my $home = ledger_home();
        make_path($home) unless -d $home;
        open my $fh, '>', "$home/cli-path.txt" or return;
        print $fh $ENV{WSE_LEDGER_CLI}, "\n";
        close $fh;
        1;
    };
    return;
}

my $sub = shift @ARGV;
$sub = '' unless defined $sub;
write_cli_pointer();

if    ($sub eq 'pre')           { cmd_pre() }
elsif ($sub eq 'post')          { cmd_post() }
elsif ($sub eq 'session-start') { cmd_session_start() }
elsif ($sub eq 'list')          { exit(cmd_list()) }
elsif ($sub eq 'stop')          { exit(cmd_stop(@ARGV)) }
elsif ($sub eq 'paths')         { exit(cmd_paths()) }
elsif ($sub eq 'explain')       { exit(cmd_explain(@ARGV)) }
else {
    print "workspace-superengine process ledger\n";
    print "usage: process-ledger <pre|post|session-start|list|stop|paths|explain>\n";
    print "  list                              show what is recorded, verify it, print a consent token\n";
    print "  stop --token <t> --pids <a,b>     stop only verified, consented entries\n";
    print "  paths                             show where the ledger lives for this workspace\n";
    print "  explain --tool-command \"<cmd>\"    read candidate command lines on stdin and report\n";
    print "                                    how each would be treated (veto / attribution)\n";
    exit 2;
}
exit 0;
