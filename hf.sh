#!/usr/bin/env bash

SERVER=192.168.50.5

XDG_LOCAL=$HOME/.local/share

GGUF_MODELS=$HOME/Models
MLX_MODELS=$HOME/.cache/huggingface/hub
LMSTUDIO_MODELS=$XDG_LOCAL/lmstudio/models
OLLAMA_MODELS=$XDG_LOCAL/ollama/models

lookup_csv() {
    local csv_file="$1"        # CSV filename
    local search_key="$2"      # Key to search for
    local key_column="${3:-1}" # Default to first column as key

    while IFS="," read -r col1 col2 col3 col4 col5 col6 col7 col8
    do
        # Check if key column matches our search key
        if [[ "${!key_column}" && \
              "$(eval echo \$col$((key_column)))" == "$search_key" ]]; then
            # Found match - variables are already set by 'read'
            return 0
        fi
    done < "$csv_file"

    return 1  # No match found
}

find_model() {
    find $1 -name '*.gguf' -type f -size +100M | sort | grep -m 1 "$2"
}

list_remote_only() {
    host="$1"
    local="$2"
    remote="$3"
    comm -13 <(ls -1 "$local" | sort) <(ssh $host ls -1 "$remote" | sort)
}

cmd=$1
shift 1

case $cmd in
    download)
        for entry in "$@"; do
            model=$(echo $entry | cut -d'/' -f1-2)
            name=$(echo $model | sed -e 's%/%_%')
            mkdir -p $name
            git clone hf.co:$model $name
            # git config lfs.storage ~/Athena/LFS
        done
        ;;

    download-cd)
        entry="$1"
        $0 download "$entry"
        model=$(echo $entry | cut -d'/' -f1-2)
        name=$(echo $model | sed -e 's%/%_%')
        cd $name
        ;;

    checkout)
        for model in "$@"; do
            if [[ -f $model ]]; then
                dir=$(dirname $model)
                base=$(basename $model)
                (cd $dir ; git lfs fetch --include $base)
                (cd $dir ; git lfs checkout $base)
                (cd $dir ; git lfs dedup)
                # linkdups -v $dir
            fi
        done
        ;;

    import-lmstudio)
        for model in "$@"; do
            if [[ -f $model ]]; then
                file=$(realpath $model)
                base=$(echo "$file" | sed -e "s%$GGUF_MODELS/%%")
                name=$(echo $base | sed -e 's%_%/%')
                target=$LMSTUDIO_MODELS/$name
                mkdir -p $(dirname $target)
                ln -f $file $target
            fi
        done
        ;;

    import-ollama)
        for model in "$@"; do
            dir=$(dirname $model)
            base=$(basename $model)
            file=$(realpath $model)
            if [[ -f $model ]]; then
                echo "FROM $file" > ${base%.gguf}.modelfile
                ollama create ${base%.gguf} -f ${base%.gguf}.modelfile
                rm -f ${base%.gguf}.modelfile
                linkdups -v $OLLAMA_MODELS/blobs $dir
            fi
        done
        ;;

    gguf)
        model="$1"

        fp32=$(find_model $model "fp32[_-]")
        fp16=$(find_model $model "fp16[_-]")
        f16=$(find_model $model "f16")
        q8=$(find_model $model "[Qq]8_")
        q6=$(find_model $model "[Qq]6_")
        q5=$(find_model $model "[Qq]5_")
        q4xl=$(find_model $model "[Qq]4_.*XL")
        q4=$(find_model $model "[Qq]4_")

        gguf=""
        if [[ -f $fp32 ]]; then
            gguf=$fp32
        elif [[ -f $fp16 ]]; then
            gguf=$fp16
        elif [[ -f $f16 ]]; then
            gguf=$f16
        elif [[ -f $q8 ]]; then
            gguf=$q8
        elif [[ -f $q6 ]]; then
            gguf=$q6
        elif [[ -f $q5 ]]; then
            gguf=$q5
        elif [[ -f $q4xl ]]; then
            gguf=$q4xl
        elif [[ -f $q4 ]]; then
            gguf=$q4
        fi

        echo $gguf
        ;;

    show)
        model="$1"
        gguf=$($0 gguf $model)
        gguf-tools show $gguf
        ;;

    ctx-size)
        model="$1"
        gguf=$($0 gguf $model)
        gguf-tools show $gguf | grep '\.context_length' \
            | perl -ne 'print $1, "\n" if /\[uint32\] ([0-9]+)/'
        ;;

    json)
        model=$1
        gguf=$($0 gguf $model)
        if [[ -d $model && -f $gguf ]]; then
            name=$(echo $model | sed -e 's/.*_//' -e 's/-GGUF//')

            if lookup_csv "$GGUF_MODELS/models.csv" $name 1; then
                draft=$col2
                context=$col3
                temp=$col4
                topk=$col5
                topp=$col6
            else
                context=$($0 ctx-size $gguf)
            fi
            cat <<EOF
{
  "title": "Hera → ${name}",
  "description": "",
  "iconUrl": "",
  "endpoint": "https://${SERVER}:8443/v1/chat/completions",
  "modelID": "${name}",
  "apiType": "openai",
  "contextLength": ${context:-4096},
  "headerRows": [],
  "bodyRows": [],
  "skipAPIKey": true,
  "pluginSupported": ${tooluse:-false},
  "visionSupported": false,
  "systemMessageSupported": ${sysprompt:-true},
  "streamOutputSupported": ${streaming:-true}
}
EOF
        fi
        ;;

    model-config)
        for model in "$@"
        do
            gguf=$($0 gguf $model)

            if [[ -d $model && -f $gguf ]]; then
                name=$(echo $model | sed -e 's/.*_//' -e 's/-[Gg][Gg][Uu][Ff]//')

                draft=""
                context=""
                temp=""
                topk=""
                topp=""
                aliases=""
                args=""
                if lookup_csv "$GGUF_MODELS/models.csv" $name 1; then
                    draft=$col2
                    context=$col3
                    temp=$col4
                    topk=$col5
                    topp=$col6
                    aliases=$col7
                    args=" $col8"
                fi
                if [[ -n "$draft" ]]; then
                    args="$args --model-draft $draft"
                fi
                if [[ -z "$context" ]]; then
                    context=$($0 ctx-size $gguf)
                fi
                if [[ -n "$context" ]]; then
                    args="$args --ctx-size $context"
                fi
                if [[ -n "$temp" ]]; then
                    args="$args --temp $temp"
                fi
                if [[ -n "$topk" ]]; then
                    args="$args --top-k $topk"
                fi
                if [[ -n "$topp" ]]; then
                    args="$args --top-p $topp"
                fi

                cat <<EOF
  "${name}":
    proxy: "http://127.0.0.1:\${PORT}"
    cmd: >
      $(which llama-server)
      --threads 24
      --jinja
      --port \${PORT}${args}
      --model ${gguf}
    checkEndpoint: /health
EOF
                if [[ -n "$aliases" ]]; then
                    cat <<EOF
    aliases:
      - ${aliases}
EOF
                fi
            fi
        done
        ;;

    build-yaml)
        cat <<EOF > $GGUF_MODELS/llama-swap.yaml
healthCheckTimeout: 7200
startPort: 9200

models:
EOF
        for model in $GGUF_MODELS/*
        do
            $0 model-config $model \
               >> $GGUF_MODELS/llama-swap.yaml
        done

        for model in $($0 huggingface-models)
        do
            draft=""
            context=""
            temp=""
            topk=""
            topp=""
            aliases=""
            args=""
            if lookup_csv "$GGUF_MODELS/models.csv" $model 1; then
                draft=$col2
                context=$col3
                temp=$col4
                topk=$col5
                topp=$col6
                aliases=$col7
                args=" $col8"
            fi
            if [[ -n "$draft" ]]; then
                args="$args --draft-model $draft"
            fi
            # if [[ -z "$context" ]]; then
            #     context=$($0 ctx-size $gguf)
            # fi
            # if [[ -n "$context" ]]; then
            #     args="$args --ctx-size $context"
            # fi
            if [[ -n "$temp" ]]; then
                args="$args --temp $temp"
            fi
            if [[ -n "$topk" ]]; then
                args="$args --top-k $topk"
            fi
            if [[ -n "$topp" ]]; then
                args="$args --top-p $topp"
            fi

            cat <<EOF >> $GGUF_MODELS/llama-swap.yaml
  "${model}":
    proxy: "http://127.0.0.1:\${PORT}"
    cmd: >
      $(which mlx-lm) server
      --host 127.0.0.1 --port \${PORT}
      --max-tokens 8192
      --model ${model}${args}
    checkEndpoint: /health
EOF
            if [[ -n "$aliases" ]]; then
                cat <<EOF >> $GGUF_MODELS/llama-swap.yaml
    aliases:
      - ${aliases}
EOF
            fi
        done

        cat $GGUF_MODELS/llama-swap-extra.yaml >> $GGUF_MODELS/llama-swap.yaml

        killall llama-swap
        ;;

    llama-swap)
        llama-swap --config $GGUF_MODELS/llama-swap.yaml
        ;;

    models)
        curl -s http://${SERVER}:8080/v1/models | jq -r '.data.[] | .id' | sort
        ;;

    huggingface-models)
        huggingface-cli scan-cache | grep model | awk '{print $1}'
        ;;

    model-files)
        for model in $GGUF_MODELS/*
        do
            $0 gguf $model
        done
        ;;

    gptel)
        cat <<EOF
    (gptel-make-openai "llama-swap"
      :host "${SERVER}:8080"
      :protocol "http"
      ;; :stream t
      :models '(
EOF
        $0 models
        cat <<EOF
                ))
EOF
        ;;

    status)
        curl -s http://${SERVER}:8080/running | jq -r
        ;;

    unload)
        curl -s http://${SERVER}:8080/unload
        ;;

    logs)
        curl -Ns http://${SERVER}:8080/logs/stream
        ;;

    status)
        for model in $(find $GGUF_MODELS -maxdepth 1 -type d)
        do
            (cd $model ; git status)
        done
        ;;

    pull)
        for model in $(find $GGUF_MODELS -maxdepth 1 -type d)
        do
            (cd $model ; git pull)
        done
        ;;

    sizes)
        cd $GGUF_MODELS
        sizes -a -x .git
        ;;

    all-sizes)
        sizes -a -x .git                        \
              $OLLAMA_MODELS                    \
              $LMSTUDIO_MODELS                  \
              $MLX_MODELS                       \
              $GGUF_MODELS
        ;;

    sizes-org)
        cd $GGUF_MODELS
        sizes -a -x .git \
            | sed -e 's/_/ | /' -e 's/\.\///' -e 's/-GGUF\///' \
            | awk '{print "|", $1, "|", $5, "|", $3}'
        ;;

    pending)
        cd $GGUF_MODELS
        for model in $(find . -maxdepth 1 -type d)
        do
            gguf=$(find $model -name '*.gguf' -type f -size +100M | sort | egrep -m 1 '([Qq][8654]_|fp?(16|32))' | head -1)
            if [[ -f $gguf ]]; then
                part=$(find $model \( -name '*.part1of*' -o -name '*-00001-of-*' -o -name '*.split*' \) -type f -size +100M | head -1)
                if [[ ! -f $part ]]; then
                    linked=$(find $gguf -links +1)
                    if [[ "$linked" != "$gguf" ]]; then
                        echo "LINK $model $gguf"
                    fi
                fi
            else
                part=$(find $model \( -name '*.part1of*' -o -name '*-00001-of-*' -o -name '*.split*' \) -type f -size +100M | head -1)
                if [[ -f $part ]]; then
                    echo "MERGE $model $part"
                else
                    echo "FETCH $model"
                fi
            fi
        done
        ;;

    files)
        cd $GGUF_MODELS
        cat <(find . -maxdepth 1 -type d)                               \
            <(find . \( -name .git -prune -o -type f -size +100M \)     \
                  | grep -v '\.git')                                    \
            | sed -e 's%./%%' | sort
        ;;

    remote-only)
        echo "==== GGUF ===="
        list_remote_only vulcan $GGUF_MODELS /tank/Models
        echo "==== MLX ===="
        list_remote_only vulcan $MLX_MODELS /tank/HuggingFace
        ;;

    all-models)
        find $MLX_MODELS $GGUF_MODELS -mindepth 1 -maxdepth 1 \
             \( -name .locks -prune -o -type d -printf '%f\n' \) \
            | sed -e 's/^models--//' -e 's/--/_/g' \
            | sort
        ;;

    duplicates)
        $0 all-models | uniq -c | grep -v "    1"
        ;;

    add-submodules)
        for i in "$@"
        do
            git submodule add $(git --git-dir=${i}/.git remote get-url origin) ./$i
        done
        ;;

    help)
        echo "Usage: $0 COMMAND [ARGUMENT...]"
        echo ""
        echo "Available commands:"
        echo "  get              Download and import models"
        echo "  download         Download models from HuggingFace"
        echo "  download-cd      Download and change directory to model"
        echo "  checkout         Checkout models using Git LFS"
        echo "  import-lmstudio  Import models to LMStudio"
        echo "  import-ollama    Import models to Ollama"
        echo "  gguf             Get the GGUF file path for a model"
        echo "  show             Show model details using gguf-tools"
        echo "  ctx-size         Get the context size of a model"
        echo "  json             Generate JSON config for a model"
        echo "  model-config     Generate model config for llama-swap"
        echo "  build-yaml       Build llama-swap.yaml config file"
        echo "  llama-swap       Start llama-swap with the generated config"
        echo "  models           List available models"
        echo "  gptel            Generate GPTel configuration"
        echo "  status           Check current status of llama-swap"
        echo "  logs             Stream llama-swap logs"
        echo "  status           Show git status of all models"
        echo "  pull             Pull updates for all models"
        echo "  sizes            Show sizes of all models"
        echo "  pending          Show pending actions for all models"
        echo "  files            List all checked out model files"
        ;;

    *)
        echo "Unknown command"
        exit 1
esac
