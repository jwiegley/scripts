#!/usr/bin/env bash

function rename_mbox() {
    mv ${1}/mbox /tmp/x.$$
    rm -fr ${1}
    mv /tmp/x.$$ ${1}
}

rename_mbox Drafts.mbox
rename_mbox mail/spam/report.mbox
rename_mbox mail/archive.mbox
rename_mbox mail/gmail.mbox
rename_mbox mail/trash.mbox
rename_mbox mail/quantum.mbox
rename_mbox mail/sent.mbox
rename_mbox mail/pending.mbox
rename_mbox mail/gmail/sent.mbox
rename_mbox mail/gmail/c2g.mbox
rename_mbox mail/spam.mbox
rename_mbox list/coq.mbox
rename_mbox list/misc.mbox
rename_mbox list/types.mbox
rename_mbox list/coq-devs.mbox
rename_mbox list/bahai/study.mbox
rename_mbox list/bahai/assembly.mbox
rename_mbox list/bahai/ror.mbox
rename_mbox list/bahai/andf.mbox
rename_mbox list/bahai/ctg/sunday.mbox
rename_mbox list/bahai/ctg/admin.mbox
rename_mbox list/bahai/tarjuman.mbox
rename_mbox list/bahai/anti-racism.mbox
rename_mbox list/bahai/srp.mbox
rename_mbox list/bahai/ctg.mbox
rename_mbox list/haskell/cafe.mbox
rename_mbox list/haskell/cabal.mbox
rename_mbox list/haskell/cloud.mbox
rename_mbox list/haskell/prime.mbox
rename_mbox list/haskell/committee.mbox
rename_mbox list/haskell/ghc.mbox
rename_mbox list/haskell/commercial.mbox
rename_mbox list/haskell/hackage-trustees.mbox
rename_mbox list/haskell/ghc/linker.mbox
rename_mbox list/haskell/libraries.mbox
rename_mbox list/haskell/announce.mbox
rename_mbox list/haskell/admin.mbox
rename_mbox list/haskell/community.mbox
rename_mbox list/haskell/beginners.mbox
rename_mbox list/haskell/infrastructure.mbox
rename_mbox list/emacs/conf.mbox
rename_mbox list/emacs/devel/owner.mbox
rename_mbox list/emacs/orgmode.mbox
rename_mbox list/emacs/sources.mbox
rename_mbox list/emacs/manual.mbox
rename_mbox list/emacs/org-mode.mbox
rename_mbox list/emacs/bugs.mbox
rename_mbox list/emacs/devel.mbox
rename_mbox list/emacs/tangents.mbox
rename_mbox list/emacs/elpa/diffs.mbox
rename_mbox list/emacs/announce.mbox
rename_mbox list/emacs/help.mbox
rename_mbox list/emacs/proofgeneral.mbox
rename_mbox list/gnu/prog.mbox
rename_mbox list/gnu/prog/discuss.mbox
rename_mbox list/gnu/debbugs.mbox
rename_mbox list/gsoc/mentors.mbox
rename_mbox list/gnu.mbox
rename_mbox list/notifications.mbox
rename_mbox list/github.mbox
rename_mbox list/bahai.mbox
rename_mbox list/coq/fiat.mbox
rename_mbox list/coq/ssreflect.mbox
rename_mbox list/coq/devel.mbox
rename_mbox list/coq/deepspec.mbox
rename_mbox list/finance.mbox
rename_mbox list/ledger.mbox
