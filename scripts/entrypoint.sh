#!/bin/sh
set -eu

password="${EXAM_PASSWORD:-exam}"
printf 'exam:%s\n' "$password" | chpasswd

mkdir -p /run/sshd /var/lib/examshell/git /var/lib/examshell/sessions
chown -R git:git /var/lib/examshell/git
chmod 2775 /var/lib/examshell/git
chown exam:exam /var/lib/examshell/sessions
chmod 0700 /var/lib/examshell/sessions

if [ ! -f /etc/ssh/ssh_host_ed25519_key ]; then
    ssh-keygen -q -t ed25519 -N '' -f /etc/ssh/ssh_host_ed25519_key
fi
if [ ! -f /etc/ssh/ssh_host_rsa_key ]; then
    ssh-keygen -q -t rsa -b 3072 -N '' -f /etc/ssh/ssh_host_rsa_key
fi

if [ ! -d /var/lib/examshell/git/exam.git ]; then
    git init --bare --initial-branch=master /var/lib/examshell/git/exam.git
    git init --initial-branch=master /tmp/exam-seed
    git -C /tmp/exam-seed config user.name 'ExamShell subjects'
    git -C /tmp/exam-seed config user.email 'examshell@localhost'
    mkdir -p /tmp/exam-seed/subjects/subject /tmp/exam-seed/rendu/exam
    cp -R /opt/examshell/subjects/ft_strlen /tmp/exam-seed/subjects/subject/ft_strlen
    touch /tmp/exam-seed/rendu/exam/.gitkeep
    git -C /tmp/exam-seed add subjects rendu
    git -C /tmp/exam-seed commit -m 'Initialize Rank 02 exam repository'
    git -C /tmp/exam-seed push /var/lib/examshell/git/exam.git master
    git --git-dir=/var/lib/examshell/git/exam.git config daemon.export true
    git --git-dir=/var/lib/examshell/git/exam.git config daemon.receivepack true
    git --git-dir=/var/lib/examshell/git/exam.git config receive.denyNonFastForwards true
    git --git-dir=/var/lib/examshell/git/exam.git config receive.denyDeletes true
    git --git-dir=/var/lib/examshell/git/exam.git config core.sharedRepository group
    chown -R git:git /var/lib/examshell/git/exam.git
    chmod -R g+rwX /var/lib/examshell/git/exam.git
    rm -rf /tmp/exam-seed
fi

find /var/lib/examshell/git -type d -exec chmod 2775 {} \;
find /var/lib/examshell/git -type f -exec chmod g+rw {} \;
find /var/lib/examshell/git -name git-daemon-export-ok -exec chmod 664 {} \;

git daemon --reuseaddr --base-path=/var/lib/examshell/git --export-all \
    --listen=0.0.0.0 --port=9418 \
    --user=git --group=git /var/lib/examshell/git &

exec /usr/sbin/sshd -D -e

