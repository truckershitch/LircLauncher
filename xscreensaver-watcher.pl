#!/usr/bin/perl
# exit when xscreensaver unblanks screen
# run.py watches for this process to exit

# my $wid = $ARGV[0];

# Listen for SIGTERM


my $pid = open (IN, "xscreensaver-command -watch |");
$SIG{TERM} = sub { kill 9, $pid; die "Caught a sigterm $!" };

while (<IN>) {
    if (m/^UNBLANK/) {
        # xscreensaver unblanked screen
        kill 9, $pid;
        exit (0);
    }
}
