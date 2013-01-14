# Path to your oh-my-zsh configuration.
ZSH=$HOME/.oh-my-zsh

# Set name of the theme to load.
# Look in ~/.oh-my-zsh/themes/
# Optionally, if you set this to "random", it'll load a random theme each
# time that oh-my-zsh is loaded.
ZSH_THEME="johnw"

# Example aliases
# alias zshconfig="mate ~/.zshrc"
# alias ohmyzsh="mate ~/.oh-my-zsh"

# Set to this to use case-sensitive completion
# CASE_SENSITIVE="true"

# Comment this out to disable weekly auto-update checks
DISABLE_AUTO_UPDATE="true"

# Uncomment following line if you want to disable colors in ls
# DISABLE_LS_COLORS="true"

# Uncomment following line if you want to disable autosetting terminal title.
# DISABLE_AUTO_TITLE="true"

# Uncomment following line if you want red dots to be displayed while waiting for completion
# COMPLETION_WAITING_DOTS="true"

# Which plugins would you like to load? (plugins can be found in ~/.oh-my-zsh/plugins/*)
# Custom plugins may be added to ~/.oh-my-zsh/custom/plugins/
# Example format: plugins=(rails git textmate ruby lighthouse)
plugins=(git git-flow osx brew zsh-syntax-highlighting)

source $ZSH/oh-my-zsh.sh
#export PS1="%m %~ %(!.#.\$) "

# Customize to your needs...

# Setup options

bindkey -e                      # set to Emacs line-editing mode

setopt AUTO_PUSHD
setopt PUSHD_IGNORE_DUPS
setopt PUSHD_SILENT
setopt DVORAK

setopt HIST_IGNORE_ALL_DUPS     # drop duplicates from history, oldest first
setopt HIST_FCNTL_LOCK
setopt HIST_NO_STORE
setopt HIST_REDUCE_BLANKS
setopt HIST_SAVE_NO_DUPS
setopt EXTENDED_HISTORY
setopt SHARE_HISTORY

# Setup environment for all terminal types

export HISTFILE=~/.zsh_history
export HISTSIZE=50000
export SAVEHIST=50000

# Setup aliases

function E() {
    emacsclient "/sudo:root@localhost:$(abspath $1)"
}

alias rm=rmtrash
alias gerp=grep
alias l="git log --graph --pretty=format:'%Cred%h%Creset —%Cblue%d%Creset %s %Cgreen(%cr)%Creset' --abbrev-commit --date=relative"
alias b='git branch --color -v'
alias w='git status -sb'
unalias ga
alias ga=git-annex
alias visudo=E
alias hist='history -Dd'
#alias ssh=ssh-ride
alias scp='rsync -aP --inplace'
#alias cab='cabal-meta --dev'

eval `gdircolors`
alias ls='gls --color=auto'
alias find=gfind
alias tar=gtar

autoload -U compinit && compinit

zstyle ':completion:*' auto-description 'specify: %d'
#zstyle ':completion:*' completer _expand _complete _correct _approximate
zstyle ':completion:*' completer _expand _complete
zstyle ':completion:*' format 'Completing %d'
zstyle ':completion:*' group-name ''
zstyle ':completion:*' menu select=2 eval "$(gdircolors -b)"
zstyle ':completion:*:default' list-colors ${(s.:.)LS_COLORS}
zstyle ':completion:*' list-colors ''
zstyle ':completion:*' list-prompt %SAt %p: Hit TAB for more, or the character to insert%s
zstyle ':completion:*' matcher-list '' 'm:{a-z}={A-Z}' 'm:{a-zA-Z}={A-Za-z}' 'r:|[._-]=* r:|=* l:|=*'
zstyle ':completion:*' menu select=long
zstyle ':completion:*' select-prompt %SScrolling active: current selection at %p%s
zstyle ':completion:*' use-compctl false
zstyle ':completion:*' verbose true

zstyle ':completion:*:*:kill:*:processes' list-colors '=(#b) #([0-9]#)*=0=01;31'
zstyle ':completion:*:kill:*' command 'ps -u $USER -o pid,%cpu,cputime,command'

autoload -Uz chpwd_recent_dirs cdr add-zsh-hook
add-zsh-hook chpwd chpwd_recent_dirs

# Customize environment for particular terminals

function output_env_escaped() {
    print -P "PAnSiTu %n\\"
    print -P "PAnSiTc %d\\"
}

function output_env() {
    print -P "AnSiTu %n"
    print -P "AnSiTc %d"
}

case $TERM in
    dumb)
        unsetopt zle
        unsetopt prompt_cr
        unsetopt prompt_subst
        ;;

    # The following will also apply to the host I ssh to within screen, if it
    # has a copy of my .zshrc, and the SHELL is set to zsh.

    eterm-color)
        export PS1="%m %~ %(!.#.$) "

        if [ -n "$INSIDE_EMACS" ]; then
            export INSIDE_EMACS

            chpwd() { output_env }
            output_env

            alias pwd='pwd ; output_env'
        else
            stty erase 
        fi
        ;;

    screen|screen-256color)
        export PS1="%m %~ %(!.#.$) "

        if [ -n "$INSIDE_EMACS" ]; then
            export INSIDE_EMACS

            chpwd() { output_env_escaped }
            output_env_escaped

            alias pwd='pwd ; output_env'
        else
            stty erase 
        fi
        ;;
esac

### .zshrc ends here
