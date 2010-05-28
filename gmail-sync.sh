#!/bin/sh

imapsync $1 \
    --syncinternaldates \
    --useheader 'Message-Id' \
    --allowsizemismatch \
    \
    --exclude 'Starred' \
    \
    --host1 imap.gmail.com \
    --port1 993 \
    --ssl1 \
    --user1 jwiegley@gmail.com \
    --passfile1 $PWD/gmail.secret \
    --authmech1 LOGIN \
    --prefix1 '[Gmail]/' \
    --sep1 '/' \
    \
    --host2 mail.johnwiegley.com \
    --port2 993 \
    --ssl2 \
    --user2 johnw \
    --passfile2 $PWD/vps.secret \
    --authmech2 LOGIN \
    --prefix2 'INBOX.' \
    --sep2 '.' \
    \
    --regextrans2 's/Sent Mail/Sent/' \
    \
    --regextrans2 's/CEG/Contracts.CEG/' \
    --regextrans2 's/ABC/Contracts.CEG.ABC/' \
    --regextrans2 's/Jobvite/Contracts.Jobvite/' \
    --regextrans2 's/TI/Contracts.TI/' \
    \
    --regextrans2 's/Emacs/Mailing Lists.Emacs/' \
    --regextrans2 's/Ledger/Mailing Lists.Ledger/' \
    --regextrans2 's/org-mode/Mailing Lists.Org-mode/' \
    --regextrans2 's/Quran9/Mailing Lists.Quran9/' \
    --regextrans2 's/Tarjuman/Mailing Lists.Tarjuman/'
