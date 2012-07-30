group { puppet: ensure => present }

define port_install(variants = "installed") {
  package { $title:
    provider => macports,
    ensure   => $variants;
  }
}

$emacs_deps = [
    'xml2'
  , 'ncurses'
  , 'gnutls'
  , 'aspell'
  , 'aspell-dict-en'
  , 'lisp-hyperspec'
  , 'MPlayer'
  , 'taglib'
]

port_install { $emacs_deps: }

$shell_pkgs = [
    'coreutils'
  , 'diffutils'
  , 'findutils'
  , 'gnutar'
  , 'gawk'
  , 'grep'
  , 'gsed'
]

port_install { 'zsh-devel':
  variants => '+doc+examples+mp_completion+pcre';
}
port_install { $shell_pkgs: }

$sysadmin_pkgs = [
    'stow'
  , 'xz'
  , 'p7zip'
  , 'flip'
  , 'parallel'
  , 'watch'
  , 'pv'
  , 'screen'
    # These last two are needed by ~/Library/MacPorts/cpan2port
  , 'p5-module-depends'
  , 'p5-list-moreutils'
]

port_install { $sysadmin_pkgs: }

$lang_pkgs = [
    'python27'
]

port_install { $lang_pkgs: }
port_install { 'ruby19':
  variants => '+c_api_docs+nosuffix';
}
port_install { 'sbcl':
  variants => '+html';
}

$mail_pkgs = [
    'pflogsumm'
  , 'fetchmail'
  , 'procmail'
  , 'mairix'
]

port_install { 'postfix':
  variants => '-mysql55+pcre+sasl+tls';
}
port_install { 'logrotate':
  variants => '+bzip2';
}
port_install { 'mutt':
  variants => '-ssl';
}
port_install { 'bitlbee':
  variants => '+otr';
}
port_install { $mail_pkgs: }

$spam_pkgs = [
    'p5-mail-spamassassin'
  , 'p5-razor-agents'
  , 'clamav-server'
  , 'p5-mail-clamav'
  , 'milter-greylist'
    # These are needed by MailScanner
  , 'p5-mime-base64'
  , 'p5-compress-raw-zlib'
  , 'p5-filesys-df'
  , 'p5-net-cidr'
  , 'p5-ole-storage_lite'
  , 'p5-sys-sigaction'
  , 'p5-mime-encwords'
]

port_install { 'clamav':
  variants => '+clamav_milter';
}
port_install { $spam_pkgs: }

$net_pkgs = [
    'rsync'
  , 'mtr'
  , 'nmap'
  , 'socat'
  , 'bmon'
  , 'autossh'
  , 'tcpdump'
  , 'httrack'
  , 'wget'
  , 'boehmgc-devel'
  , 'apg'
]

port_install { $net_pkgs: }
port_install { 'w3m':
  variants => '+inline_image_gtk2';
}

$vc_pkgs = [
    'subversion'
  , 'cvsps'
  , 'gc-utils'
  , 'bzr'
  , 'bzr-fastimport'
  , 'bzrtools'
  , 'mercurial'
]

port_install { 'git-core':
  variants => '+svn';
}
port_install { $vc_pkgs: }

$devel_pkgs = [
    'm4'
  , 'libtool'
  , 'autoconf'
  , 'automake'
  , 'autogen'
  , 'cmake'
  , 'ccache'
  , 'distcc'
  , 'doxygen'
  , 'gmake'
  , 'gperf'
  , 'lcov'
  , 'valgrind'
  , 'sloccount'
  , 'highlight'
  , 'patchutils'
  , 'diffstat'
  , 'tidy'
  , 'gmp'
  , 'mpfr'
  , 'xmlstarlet'
]

port_install { $devel_pkgs: }

$comp_pkgs = [
    'gcc47'
  , 'gcc48'
]

port_install { $comp_pkgs: }

$ti_pkgs = [
    'p5-ipc-run'
  , 'p5-list-compare'
  , 'p5-dbd-mysql'
  , 'p5-mime-lite'
]

port_install { $ti_pkgs: }

$misc_pkgs = [
    'graphviz'
  , 'aquaterm'
  , 'cotvnc'
]

port_install { $misc_pkgs: }

$db_pkgs = [
    'sqlite3'
  , 'mysql55-server'
  , 'postgresql92-server'
]

port_install { $db_pkgs: }

$tex_pkgs = [
    'texinfo'
  , 'texlive-xetex'
  , 'texlive-documentation-english'
  , 'texlive-fonts-extra'
  , 'texlive-fonts-recommended'
  , 'texlive-fontutils'
  , 'texlive-generic-extra'
  , 'texlive-lang-english'
  , 'texlive-latex-extra'
  , 'texlive-math-extra'
  , 'texlive-metapost'
  , 'texlive-pictures'
  , 'texlive-plain-extra'
  , 'texlive-pstricks'
]

port_install { $tex_pkgs: }

### macports.pp ends here
