#!/usr/bin/env bash

set -euo pipefail

script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
subject="$script_dir/flatten-recordings"
original_path=$PATH
test_root=$(mktemp -d)
background_pid=''

cleanup() {
	if [ -n "$background_pid" ]; then
		kill "$background_pid" 2>/dev/null || true
		wait "$background_pid" 2>/dev/null || true
	fi
	rm -rf "$test_root"
}
trap cleanup EXIT INT TERM HUP

fail() {
	printf 'FAIL: %s\n' "$*" >&2
	exit 1
}

assert_file() {
	[ -f "$1" ] || fail "expected file: $1"
}

assert_not_file() {
	[ ! -f "$1" ] || fail "unexpected file: $1"
}

assert_not_path() {
	[ ! -e "$1" ] && [ ! -L "$1" ] || fail "unexpected path: $1"
}

assert_eq() {
	[ "$1" = "$2" ] || fail "expected '$2', got '$1'"
}

assert_no_run_dirs() {
	local home=$1
	if [ -e "$home/Library/Logs/.flatten-recordings.run" ]; then
		fail "private run directory survived cleanup"
	fi
}

fingerprint() {
	/usr/bin/shasum -a 256 "$1" | /usr/bin/awk '{print $1}'
}

file_identity() {
	/usr/bin/stat -f '%d:%i:%B:%z' "$1"
}

create_archive_transaction() {
	local home=$1
	local base=$2
	local source="$home/Recordings/$base"
	local archive="$home/Audio/Recordings"

	CREATED_TRANSACTION="$archive/.$base.flatten-txn.fixture"
	mkdir -m 700 "$CREATED_TRANSACTION"
	cp -p "$source" "$CREATED_TRANSACTION/audio"
	printf 'recovered transcript\n' >"$CREATED_TRANSACTION/transcript"
	printf 'v4 ready %s %s %s %s %s\n' \
		"$(printf '%s' "$base" | /usr/bin/shasum -a 256 | /usr/bin/awk '{print $1}')" \
		"$(fingerprint "$source")" \
		"$(file_identity "$source")" \
		'.flatten-recordings-claim-fixture' \
		"$(fingerprint "$CREATED_TRANSACTION/transcript")" \
		>"$CREATED_TRANSACTION/manifest"
}

create_preparing_transaction() {
	local home=$1
	local base=$2
	local source="$home/Recordings/$base"
	local archive="$home/Audio/Recordings"

	CREATED_TRANSACTION="$archive/.$base.flatten-txn.preparing"
	mkdir -m 700 "$CREATED_TRANSACTION"
	cp -p "$source" "$CREATED_TRANSACTION/audio"
	printf 'v4 preparing %s %s %s %s -\n' \
		"$(printf '%s' "$base" | /usr/bin/shasum -a 256 | /usr/bin/awk '{print $1}')" \
		"$(fingerprint "$source")" \
		"$(file_identity "$source")" \
		'.flatten-recordings-claim-preparing' \
		>"$CREATED_TRANSACTION/manifest"
}

create_claiming_transaction() {
	local home=$1
	local base=$2
	local source="$home/Recordings/$base"
	local archive="$home/Audio/Recordings"

	CREATED_TRANSACTION="$archive/.$base.flatten-txn.claiming"
	mkdir -m 700 "$CREATED_TRANSACTION"
	cp -p "$source" "$CREATED_TRANSACTION/audio"
	printf 'claiming transcript from completed ASR\n' \
		>"$CREATED_TRANSACTION/transcript"
	printf 'v4 claiming %s %s %s %s %s\n' \
		"$(printf '%s' "$base" | /usr/bin/shasum -a 256 | /usr/bin/awk '{print $1}')" \
		"$(fingerprint "$source")" \
		"$(file_identity "$source")" \
		'.flatten-recordings-claim-claiming' \
		"$(fingerprint "$CREATED_TRANSACTION/transcript")" \
		>"$CREATED_TRANSACTION/manifest"
}

assert_no_transactions() {
	local home=$1
	local base=$2
	local matches=()

	shopt -s nullglob
	matches=("$home/Audio/Recordings/.$base.flatten-txn."*)
	shopt -u nullglob
	[ "${#matches[@]}" -eq 0 ] ||
		fail "archive transaction survived: ${matches[*]}"
}

write_route() {
	local home=$1
	local model=$2
	local api_key=$3
	local route="$home/.config/promptdeploy/default-llm.json"
	mkdir -p "$(dirname -- "$route")"
	printf '{"version":1,"provider":"litellm","model":"%s","base_url":"http://litellm.test/v1","api_key":"%s"}\n' \
		"$model" "$api_key" >"$route"
	chmod 600 "$route"
}

make_home() {
	local home=$1
	mkdir -p "$home/bin" "$home/Recordings" "$home/doc" "$home/test-state"
	printf 'Post-process this transcript.\n' >"$home/doc/post-process.md"
	cat >"$home/bin/transcribe" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail

state="$HOME/test-state"
config=''
output=''
request_id=''
audio=''
check=0

while [ "$#" -gt 0 ]; do
	case "$1" in
	--llm-config)
		config=$2
		shift 2
		;;
	--check-llm-config)
		check=1
		shift
		;;
	--request-id)
		request_id=$2
		shift 2
		;;
	-o)
		output=$2
		shift 2
		;;
	-p)
		shift 2
		;;
	-m | --model)
		printf 'forbidden-model-argument\n' >>"$state/events"
		exit 90
		;;
	--*)
		shift
		;;
	*)
		audio=$1
		shift
		;;
	esac
done

[ -n "$config" ] || exit 91
case "$config" in
"$HOME/Library/Logs/.flatten-recordings.run/default-llm.json") ;;
*) exit 92 ;;
esac

if [ "$check" -eq 1 ]; then
	printf 'validate\n' >>"$state/events"
	[ -s "$config" ] || exit 93
	grep -Eq '"version"[[:space:]]*:[[:space:]]*1' "$config" || exit 94
	grep -Eq '"provider"[[:space:]]*:[[:space:]]*"litellm"' "$config" || exit 95
	grep -Eq '"model"[[:space:]]*:' "$config" || exit 96
	[ "$(/usr/bin/stat -f '%Lp' "$config")" = 600 ] || exit 97
	[ "$(/usr/bin/stat -f '%Lp' "$(dirname -- "$config")")" = 700 ] || exit 102
	if [ -f "$state/mutate-published" ]; then
		cp "$state/replacement-route" \
			"$HOME/.config/promptdeploy/default-llm.json"
		rm -f "$state/mutate-published"
	fi
	exit 0
fi

[ -n "$audio" ] || exit 98
[ -n "$output" ] || exit 99
[ -n "$request_id" ] || exit 100
expected_hash=$(cat "$state/expected-hash")
actual_hash=$(/usr/bin/shasum -a 256 "$config" | /usr/bin/awk '{print $1}')
[ "$actual_hash" = "$expected_hash" ] || exit 101
printf 'asr request_id=%s hash=%s config=%s audio=%s\n' \
	"$request_id" "$actual_hash" "$config" "$(basename -- "$audio")" \
	>>"$state/events"

if [ -p "$state/asr-entered" ] && [ -p "$state/asr-release" ] &&
	mkdir "$state/asr-gate-owner" 2>/dev/null; then
	printf 'entered\n' >"$state/asr-entered"
	IFS= read -r _ <"$state/asr-release"
fi

if [ -f "$state/fail-asr" ]; then
	exit 23
fi

printf 'processed transcript for %s\n' "$(basename -- "$audio")" >"$output"
STUB
	chmod +x "$home/bin/transcribe"
}

run_flatten() {
	local home=$1
	HOME="$home" PATH="$home/bin:$original_path" "$subject"
}

snapshot_home="$test_root/snapshot"
make_home "$snapshot_home"
write_route "$snapshot_home" 'hera/omlx/Qwen3.6-27B-oQ4e-mtp' 'route-secret-one'
route="$snapshot_home/.config/promptdeploy/default-llm.json"
route_hash=$(fingerprint "$route")
printf '%s\n' "$route_hash" >"$snapshot_home/test-state/expected-hash"
mkdir -p "$snapshot_home/Library/Logs/.flatten-recordings.run"
printf 'stale route credential\n' \
	>"$snapshot_home/Library/Logs/.flatten-recordings.run/default-llm.json"
write_route "$snapshot_home/replacement" 'hera/omlx/changed-model' 'route-secret-two'
cp "$snapshot_home/replacement/.config/promptdeploy/default-llm.json" \
	"$snapshot_home/test-state/replacement-route"
touch "$snapshot_home/test-state/mutate-published"
printf 'legacy audio\n' >"$snapshot_home/Recordings/legacy.m4a"
printf 'second audio\n' >"$snapshot_home/Recordings/second.m4a"
printf 'capped audio\n' >"$snapshot_home/Recordings/capped.m4a"
state_dir="$snapshot_home/Library/Logs/flatten-recordings.state"
mkdir -p "$state_dir"
printf '5\n' >"$state_dir/legacy.m4a.fail"
printf '%s %s 5\n' "$route_hash" \
	"$(fingerprint "$snapshot_home/Recordings/capped.m4a")" \
	>"$state_dir/capped.m4a.fail"
touch -t 203001010000 "$state_dir/legacy.m4a.fail" "$state_dir/capped.m4a.fail"

run_flatten "$snapshot_home" || fail "snapshot/route-aware run failed"
assert_file "$snapshot_home/Audio/Recordings/legacy.m4a.txt"
assert_file "$snapshot_home/Audio/Recordings/legacy.m4a"
assert_file "$snapshot_home/Audio/Recordings/second.m4a.txt"
assert_file "$snapshot_home/Audio/Recordings/second.m4a"
assert_eq "$(cat "$snapshot_home/.local/share/recording-transcripts/legacy.m4a.txt")" \
  "processed transcript for audio"
assert_eq "$(cat "$snapshot_home/.local/share/recording-transcripts/second.m4a.txt")" \
  "processed transcript for audio"
assert_not_file "$snapshot_home/Recordings/legacy.m4a.txt"
assert_not_file "$snapshot_home/Recordings/second.m4a.txt"
assert_file "$snapshot_home/Recordings/capped.m4a"
assert_not_file "$snapshot_home/Audio/Recordings/capped.m4a"
assert_not_file "$state_dir/legacy.m4a.fail"
assert_eq "$(cat "$state_dir/capped.m4a.fail")" \
	"$route_hash $(fingerprint "$snapshot_home/Recordings/capped.m4a") 5"
assert_eq "$(grep -c '^validate$' "$snapshot_home/test-state/events")" 1
assert_eq "$(grep -c '^asr ' "$snapshot_home/test-state/events")" 2
assert_eq "$(grep -c "hash=$route_hash" "$snapshot_home/test-state/events")" 2
grep -Eq 'request_id=[^ ]+:legacy\.m4a ' "$snapshot_home/test-state/events" ||
	fail "legacy request id was not passed"
grep -Eq 'request_id=[^ ]+:second\.m4a ' "$snapshot_home/test-state/events" ||
	fail "second request id was not passed"
grep -Eq 'transcribe begin request_id=[^ ]+:legacy\.m4a ' \
	"$snapshot_home/Library/Logs/flatten-recordings.log" ||
	fail "begin log lacks recording request id"
grep -Eq 'transcribe ok request_id=[^ ]+:legacy\.m4a ' \
	"$snapshot_home/Library/Logs/flatten-recordings.log" ||
	fail "success log lacks recording request id"
grep -q 'transcribe gave_up attempts=5' \
	"$snapshot_home/Library/Logs/flatten-recordings.log" ||
	fail "matching capped route was not skipped"
if grep -q 'route-secret-one' "$snapshot_home/Library/Logs/flatten-recordings.log"; then
	fail "API key leaked into the log"
fi
[ "$(fingerprint "$route")" != "$route_hash" ] ||
	fail "validation stub did not replace the published route"
assert_no_run_dirs "$snapshot_home"

concurrent_home="$test_root/concurrent"
make_home "$concurrent_home"
write_route "$concurrent_home" 'hera/omlx/Qwen3.6-27B-oQ4e-mtp' 'concurrent-secret'
concurrent_route="$concurrent_home/.config/promptdeploy/default-llm.json"
printf '%s\n' "$(fingerprint "$concurrent_route")" \
	>"$concurrent_home/test-state/expected-hash"
printf 'concurrent audio\n' >"$concurrent_home/Recordings/concurrent.m4a"
mkfifo "$concurrent_home/test-state/asr-entered" \
	"$concurrent_home/test-state/asr-release"
run_flatten "$concurrent_home" &
first_pid=$!
background_pid=$first_pid
IFS= read -r entered <"$concurrent_home/test-state/asr-entered"
assert_eq "$entered" entered
contender_rc=0
run_flatten "$concurrent_home" || contender_rc=$?
asr_count=$(grep -c '^asr ' "$concurrent_home/test-state/events")
printf 'release\n' >"$concurrent_home/test-state/asr-release"
owner_rc=0
wait "$first_pid" || owner_rc=$?
background_pid=''
assert_eq "$contender_rc" 0
assert_eq "$owner_rc" 0
assert_eq "$asr_count" 1
grep -q 'skip reason=already_running' \
	"$concurrent_home/Library/Logs/flatten-recordings.log" ||
	fail "contending run was not logged as skipped"
assert_file "$concurrent_home/Audio/Recordings/concurrent.m4a.txt"
assert_file "$concurrent_home/Audio/Recordings/concurrent.m4a"
assert_not_file "$concurrent_home/Recordings/concurrent.m4a.txt"
assert_no_run_dirs "$concurrent_home"

collision_home="$test_root/collision"
make_home "$collision_home"
write_route "$collision_home" 'hera/omlx/Qwen3.6-27B-oQ4e-mtp' 'collision-secret'
collision_route="$collision_home/.config/promptdeploy/default-llm.json"
printf '%s\n' "$(fingerprint "$collision_route")" \
	>"$collision_home/test-state/expected-hash"
printf 'collision audio\n' >"$collision_home/Recordings/collision.m4a"
mkdir -p "$collision_home/Audio/Recordings"
printf 'existing transcript\n' \
	>"$collision_home/Audio/Recordings/collision.m4a.txt"
if run_flatten "$collision_home"; then
	fail "pre-existing transcript target unexpectedly succeeded"
fi
assert_file "$collision_home/Recordings/collision.m4a"
assert_not_file "$collision_home/Audio/Recordings/collision.m4a"
assert_eq "$(cat "$collision_home/Audio/Recordings/collision.m4a.txt")" \
	"existing transcript"
if grep -q '^asr ' "$collision_home/test-state/events"; then
	fail "archive collision reached ASR"
fi
grep -q 'ERROR archive reason=target_exists' \
	"$collision_home/Library/Logs/flatten-recordings.log" ||
	fail "archive collision was not logged"
assert_no_run_dirs "$collision_home"

for race_kind in transcript audio; do
	race_home="$test_root/race-$race_kind"
	make_home "$race_home"
	write_route "$race_home" 'hera/omlx/Qwen3.6-27B-oQ4e-mtp' \
		"race-$race_kind-secret"
	race_route="$race_home/.config/promptdeploy/default-llm.json"
	printf '%s\n' "$(fingerprint "$race_route")" \
		>"$race_home/test-state/expected-hash"
	printf '%s race audio\n' "$race_kind" \
		>"$race_home/Recordings/race.m4a"
	mkfifo "$race_home/test-state/asr-entered" \
		"$race_home/test-state/asr-release"
	run_flatten "$race_home" &
	race_pid=$!
	background_pid=$race_pid
	IFS= read -r entered <"$race_home/test-state/asr-entered"
	assert_eq "$entered" entered
	mkdir -p "$race_home/Audio/Recordings"
	if [ "$race_kind" = transcript ]; then
		printf 'external transcript\n' \
			>"$race_home/Audio/Recordings/race.m4a.txt"
	else
		printf 'external audio\n' \
			>"$race_home/Audio/Recordings/race.m4a"
	fi
	printf 'release\n' >"$race_home/test-state/asr-release"
	race_rc=0
	wait "$race_pid" || race_rc=$?
	background_pid=''
	[ "$race_rc" -ne 0 ] ||
		fail "$race_kind archive race unexpectedly succeeded"
	assert_not_path "$race_home/Recordings/race.m4a"
	shopt -s nullglob
	race_transactions=(
		"$race_home/Audio/Recordings/.race.m4a.flatten-txn."*
	)
	shopt -u nullglob
	[ "${#race_transactions[@]}" -eq 1 ] ||
		fail "$race_kind archive race lost its transaction"
	race_claim_name=$(awk '{print $6}' "${race_transactions[0]}/manifest")
	race_claim="$race_home/Recordings/$race_claim_name/source"
	assert_eq "$(cat "$race_claim")" "$race_kind race audio"
	if [ "$race_kind" = transcript ]; then
		assert_eq "$(cat "$race_home/Audio/Recordings/race.m4a.txt")" \
			"external transcript"
		assert_not_path "$race_home/Audio/Recordings/race.m4a"
	else
		assert_eq "$(cat "$race_home/Audio/Recordings/race.m4a")" \
			"external audio"
		assert_not_path "$race_home/Audio/Recordings/race.m4a.txt"
	fi
	assert_not_path "$race_home/Audio/Recordings/.race.m4a.part"
	assert_not_path "$race_home/Audio/Recordings/.race.m4a.txt.part"
	assert_no_run_dirs "$race_home"
done

for recovery_phase in \
	transcript-published \
	pair-published \
	source-unlinked \
	source-unlinked-audio-stage-gone \
	source-unlinked-transcript-stage-gone \
	source-unlinked-org-imported
do
	recovery_home="$test_root/recovery-$recovery_phase"
	make_home "$recovery_home"
	write_route "$recovery_home" 'hera/omlx/Qwen3.6-27B-oQ4e-mtp' \
		"recovery-$recovery_phase-secret"
	recovery_route="$recovery_home/.config/promptdeploy/default-llm.json"
	printf '%s\n' "$(fingerprint "$recovery_route")" \
		>"$recovery_home/test-state/expected-hash"
	mkdir -p "$recovery_home/Audio/Recordings"
	recovery_source="$recovery_home/Recordings/recovery.m4a"
	recovery_audio_dest="$recovery_home/Audio/Recordings/recovery.m4a"
	recovery_transcript_dest="$recovery_home/Audio/Recordings/recovery.m4a.txt"
	printf 'recovery audio\n' >"$recovery_source"
	create_archive_transaction "$recovery_home" recovery.m4a
	recovery_transaction=$CREATED_TRANSACTION
	recovery_audio_stage="$recovery_transaction/audio"
	recovery_transcript_stage="$recovery_transaction/transcript"
	/bin/ln "$recovery_transcript_stage" "$recovery_transcript_dest"
	if [ "$recovery_phase" != transcript-published ]; then
		/bin/ln "$recovery_audio_stage" "$recovery_audio_dest"
	fi
	case "$recovery_phase" in
	source-unlinked*)
		/bin/rm "$recovery_source"
		;;
	esac
	if [ "$recovery_phase" = source-unlinked-audio-stage-gone ]; then
		/bin/rm "$recovery_audio_stage"
	elif [ "$recovery_phase" = source-unlinked-transcript-stage-gone ]; then
		/bin/rm "$recovery_transcript_stage"
	elif [ "$recovery_phase" = source-unlinked-org-imported ]; then
		receipt_dir="$recovery_home/.local/share/recording-transcripts/.imported"
		mkdir -p "$receipt_dir"
		fingerprint "$recovery_transcript_stage" \
			>"$receipt_dir/recovery.m4a.txt.sha256"
	fi

	run_flatten "$recovery_home" ||
		fail "$recovery_phase transaction recovery failed"
	assert_not_path "$recovery_source"
	assert_file "$recovery_audio_dest"
	assert_file "$recovery_transcript_dest"
	assert_eq "$(cat "$recovery_audio_dest")" "recovery audio"
	assert_eq "$(cat "$recovery_transcript_dest")" "recovered transcript"
	if [ "$recovery_phase" = source-unlinked-org-imported ]; then
		assert_not_path "$recovery_home/.local/share/recording-transcripts/recovery.m4a.txt"
	else
		assert_eq "$(cat "$recovery_home/.local/share/recording-transcripts/recovery.m4a.txt")" \
			"recovered transcript"
	fi
	assert_not_path "$recovery_home/Recordings/recovery.m4a.txt"
	assert_not_path "$recovery_transaction"
	assert_no_transactions "$recovery_home" recovery.m4a
	if grep -q '^asr ' "$recovery_home/test-state/events"; then
		fail "$recovery_phase recovery repeated ASR"
	fi
	assert_no_run_dirs "$recovery_home"
done

source_change_home="$test_root/source-change"
make_home "$source_change_home"
write_route "$source_change_home" 'hera/omlx/Qwen3.6-27B-oQ4e-mtp' \
	'source-change-secret'
source_change_route="$source_change_home/.config/promptdeploy/default-llm.json"
printf '%s\n' "$(fingerprint "$source_change_route")" \
	>"$source_change_home/test-state/expected-hash"
source_change_source="$source_change_home/Recordings/source-change.m4a"
printf 'original source audio\n' >"$source_change_source"
mkfifo "$source_change_home/test-state/asr-entered" \
	"$source_change_home/test-state/asr-release"
run_flatten "$source_change_home" &
source_change_pid=$!
background_pid=$source_change_pid
IFS= read -r entered <"$source_change_home/test-state/asr-entered"
assert_eq "$entered" entered
/bin/rm "$source_change_source"
printf 'replacement source audio\n' >"$source_change_source"
printf 'release\n' >"$source_change_home/test-state/asr-release"
source_change_rc=0
wait "$source_change_pid" || source_change_rc=$?
background_pid=''
[ "$source_change_rc" -ne 0 ] ||
	fail "source replacement during ASR unexpectedly succeeded"
assert_eq "$(cat "$source_change_source")" "replacement source audio"
assert_eq "$(cat "$source_change_home/Audio/Recordings/source-change.m4a")" \
	"original source audio"
assert_file "$source_change_home/Audio/Recordings/source-change.m4a.txt"
assert_no_transactions "$source_change_home" source-change.m4a
assert_no_run_dirs "$source_change_home"

deleted_during_home="$test_root/deleted-during-asr"
make_home "$deleted_during_home"
write_route "$deleted_during_home" 'hera/omlx/Qwen3.6-27B-oQ4e-mtp' \
	'deleted-during-asr-secret'
deleted_during_route="$deleted_during_home/.config/promptdeploy/default-llm.json"
printf '%s\n' "$(fingerprint "$deleted_during_route")" \
	>"$deleted_during_home/test-state/expected-hash"
deleted_during_source="$deleted_during_home/Recordings/deleted-during.m4a"
printf 'mistaken recording deleted during ASR\n' >"$deleted_during_source"
mkfifo "$deleted_during_home/test-state/asr-entered" \
	"$deleted_during_home/test-state/asr-release"
run_flatten "$deleted_during_home" &
deleted_during_pid=$!
background_pid=$deleted_during_pid
IFS= read -r entered <"$deleted_during_home/test-state/asr-entered"
assert_eq "$entered" entered
/bin/rm "$deleted_during_source"
printf 'release\n' >"$deleted_during_home/test-state/asr-release"
wait "$deleted_during_pid" ||
	fail "deletion during ASR did not cancel cleanly"
background_pid=''
assert_not_file "$deleted_during_home/Audio/Recordings/deleted-during.m4a"
assert_not_file "$deleted_during_home/Audio/Recordings/deleted-during.m4a.txt"
assert_no_transactions "$deleted_during_home" deleted-during.m4a
assert_eq "$(grep -c '^asr ' "$deleted_during_home/test-state/events")" 1
assert_no_run_dirs "$deleted_during_home"

failed_replace_home="$test_root/failed-replacement"
make_home "$failed_replace_home"
write_route "$failed_replace_home" 'hera/omlx/Qwen3.6-27B-oQ4e-mtp' \
	'failed-replacement-secret'
failed_replace_route="$failed_replace_home/.config/promptdeploy/default-llm.json"
printf '%s\n' "$(fingerprint "$failed_replace_route")" \
	>"$failed_replace_home/test-state/expected-hash"
failed_replace_source="$failed_replace_home/Recordings/failed-replacement.m4a"
printf 'original before failed ASR\n' >"$failed_replace_source"
touch "$failed_replace_home/test-state/fail-asr"
mkfifo "$failed_replace_home/test-state/asr-entered" \
	"$failed_replace_home/test-state/asr-release"
run_flatten "$failed_replace_home" &
failed_replace_pid=$!
background_pid=$failed_replace_pid
IFS= read -r entered <"$failed_replace_home/test-state/asr-entered"
assert_eq "$entered" entered
/bin/rm "$failed_replace_source"
printf 'replacement after failed ASR\n' >"$failed_replace_source"
printf 'release\n' >"$failed_replace_home/test-state/asr-release"
failed_replace_rc=0
wait "$failed_replace_pid" || failed_replace_rc=$?
background_pid=''
[ "$failed_replace_rc" -ne 0 ] ||
	fail "replacement plus ASR failure unexpectedly succeeded"
shopt -s nullglob
failed_replace_transactions=(
	"$failed_replace_home/Audio/Recordings/.failed-replacement.m4a.flatten-txn."*
)
shopt -u nullglob
[ "${#failed_replace_transactions[@]}" -eq 1 ] ||
	fail "verified stage was not retained after ASR failure"
assert_eq "$(cat "${failed_replace_transactions[0]}/audio")" \
	"original before failed ASR"
assert_eq "$(cat "$failed_replace_source")" "replacement after failed ASR"
/bin/rm "$failed_replace_home/test-state/fail-asr"
if run_flatten "$failed_replace_home"; then
	fail "resumed failed-replacement transaction unexpectedly succeeded"
fi
assert_eq "$(cat "$failed_replace_home/Audio/Recordings/failed-replacement.m4a")" \
	"original before failed ASR"
assert_file "$failed_replace_home/Audio/Recordings/failed-replacement.m4a.txt"
assert_eq "$(cat "$failed_replace_source")" "replacement after failed ASR"
assert_no_transactions "$failed_replace_home" failed-replacement.m4a
assert_no_run_dirs "$failed_replace_home"

crash_replace_home="$test_root/crash-replacement"
make_home "$crash_replace_home"
write_route "$crash_replace_home" 'hera/omlx/Qwen3.6-27B-oQ4e-mtp' \
	'crash-replacement-secret'
crash_replace_route="$crash_replace_home/.config/promptdeploy/default-llm.json"
printf '%s\n' "$(fingerprint "$crash_replace_route")" \
	>"$crash_replace_home/test-state/expected-hash"
mkdir -p "$crash_replace_home/Audio/Recordings"
crash_replace_source="$crash_replace_home/Recordings/crash-replacement.m4a"
printf 'original before crash\n' >"$crash_replace_source"
create_preparing_transaction "$crash_replace_home" crash-replacement.m4a
crash_replace_transaction=$CREATED_TRANSACTION
/bin/rm "$crash_replace_source"
printf 'replacement after crash\n' >"$crash_replace_source"
if run_flatten "$crash_replace_home"; then
	fail "resumed crash-replacement transaction unexpectedly succeeded"
fi
assert_eq "$(cat "$crash_replace_home/Audio/Recordings/crash-replacement.m4a")" \
	"original before crash"
assert_file "$crash_replace_home/Audio/Recordings/crash-replacement.m4a.txt"
assert_eq "$(cat "$crash_replace_source")" "replacement after crash"
assert_not_path "$crash_replace_transaction"
assert_no_transactions "$crash_replace_home" crash-replacement.m4a
assert_no_run_dirs "$crash_replace_home"

absent_home="$test_root/absent-source"
make_home "$absent_home"
write_route "$absent_home" 'hera/omlx/Qwen3.6-27B-oQ4e-mtp' \
	'absent-source-secret'
absent_route="$absent_home/.config/promptdeploy/default-llm.json"
printf '%s\n' "$(fingerprint "$absent_route")" \
	>"$absent_home/test-state/expected-hash"
mkdir -p "$absent_home/Audio/Recordings"
absent_source="$absent_home/Recordings/absent.m4a"
printf 'staged before source disappeared\n' >"$absent_source"
create_preparing_transaction "$absent_home" absent.m4a
absent_transaction=$CREATED_TRANSACTION
printf 'partial transcript from killed run\n' >"$absent_transaction/transcript"
printf 'partial manifest\n' >"$absent_transaction/manifest.next"
/bin/rm "$absent_source"
run_flatten "$absent_home" || fail "deleted preparing transaction did not cancel"
assert_not_file "$absent_home/Audio/Recordings/absent.m4a"
assert_not_file "$absent_home/Audio/Recordings/absent.m4a.txt"
assert_not_path "$absent_transaction"
if grep -q '^asr ' "$absent_home/test-state/events"; then
	fail "deleted preparing transaction reached ASR"
fi
assert_no_run_dirs "$absent_home"

claimed_home="$test_root/claimed-preparing"
make_home "$claimed_home"
write_route "$claimed_home" 'hera/omlx/Qwen3.6-27B-oQ4e-mtp' \
	'claimed-preparing-secret'
claimed_route="$claimed_home/.config/promptdeploy/default-llm.json"
printf '%s\n' "$(fingerprint "$claimed_route")" \
	>"$claimed_home/test-state/expected-hash"
mkdir -p "$claimed_home/Audio/Recordings"
claimed_source="$claimed_home/Recordings/claimed.m4a"
printf 'claimed before ready crash\n' >"$claimed_source"
create_claiming_transaction "$claimed_home" claimed.m4a
claimed_transaction=$CREATED_TRANSACTION
claimed_claim_name=$(awk '{print $6}' "$claimed_transaction/manifest")
claimed_claim_dir="$claimed_home/Recordings/$claimed_claim_name"
mkdir -m 700 "$claimed_claim_dir"
/bin/mv "$claimed_source" "$claimed_claim_dir/source"
run_flatten "$claimed_home" ||
	fail "claimed preparing transaction did not resume"
assert_eq "$(cat "$claimed_home/Audio/Recordings/claimed.m4a")" \
	"claimed before ready crash"
assert_file "$claimed_home/Audio/Recordings/claimed.m4a.txt"
assert_eq "$(cat "$claimed_home/Audio/Recordings/claimed.m4a.txt")" \
	"claiming transcript from completed ASR"
if grep -q '^asr ' "$claimed_home/test-state/events"; then
	fail "claiming transaction repeated ASR"
fi
assert_not_path "$claimed_claim_dir"
assert_not_path "$claimed_transaction"
assert_no_run_dirs "$claimed_home"

mismatched_claim_home="$test_root/mismatched-claiming"
make_home "$mismatched_claim_home"
write_route "$mismatched_claim_home" 'hera/omlx/Qwen3.6-27B-oQ4e-mtp' \
	'mismatched-claiming-secret'
mismatched_claim_route="$mismatched_claim_home/.config/promptdeploy/default-llm.json"
printf '%s\n' "$(fingerprint "$mismatched_claim_route")" \
	>"$mismatched_claim_home/test-state/expected-hash"
mkdir -p "$mismatched_claim_home/Audio/Recordings"
mismatched_claim_source="$mismatched_claim_home/Recordings/mismatched.m4a"
printf 'original staged before mismatched claim\n' >"$mismatched_claim_source"
create_claiming_transaction "$mismatched_claim_home" mismatched.m4a
mismatched_claim_transaction=$CREATED_TRANSACTION
mismatched_claim_name=$(awk '{print $6}' \
	"$mismatched_claim_transaction/manifest")
mismatched_claim_dir="$mismatched_claim_home/Recordings/$mismatched_claim_name"
/bin/rm "$mismatched_claim_source"
mkdir -m 700 "$mismatched_claim_dir"
printf 'replacement stranded in claim\n' >"$mismatched_claim_dir/source"
run_flatten "$mismatched_claim_home" ||
	fail "mismatched claiming transaction did not recover"
assert_eq "$(cat "$mismatched_claim_home/Audio/Recordings/mismatched.m4a")" \
	"original staged before mismatched claim"
assert_eq "$(cat "$mismatched_claim_home/Audio/Recordings/mismatched.m4a.txt")" \
	"claiming transcript from completed ASR"
assert_not_path "$mismatched_claim_dir"
assert_not_path "$mismatched_claim_transaction"
shopt -s nullglob
mismatched_requeued=(
	"$mismatched_claim_home/Recordings/.flatten-recordings-recovery."*/*.m4a
)
shopt -u nullglob
[ "${#mismatched_requeued[@]}" -eq 1 ] ||
	fail "mismatched claiming replacement was not requeued"
assert_eq "$(cat "${mismatched_requeued[0]}")" \
	"replacement stranded in claim"
if grep -q '^asr ' "$mismatched_claim_home/test-state/events"; then
	fail "mismatched claiming transaction repeated ASR"
fi
assert_no_run_dirs "$mismatched_claim_home"

absent_fail_home="$test_root/absent-source-failure"
make_home "$absent_fail_home"
write_route "$absent_fail_home" 'hera/omlx/Qwen3.6-27B-oQ4e-mtp' \
	'absent-source-failure-secret'
absent_fail_route="$absent_fail_home/.config/promptdeploy/default-llm.json"
printf '%s\n' "$(fingerprint "$absent_fail_route")" \
	>"$absent_fail_home/test-state/expected-hash"
mkdir -p "$absent_fail_home/Audio/Recordings"
absent_fail_source="$absent_fail_home/Recordings/absent-failure.m4a"
printf 'staged before absent failure\n' >"$absent_fail_source"
touch "$absent_fail_home/test-state/fail-asr"
if run_flatten "$absent_fail_home"; then
	fail "absent-source ASR failure unexpectedly succeeded"
fi
shopt -s nullglob
absent_fail_transactions=(
	"$absent_fail_home/Audio/Recordings/.absent-failure.m4a.flatten-txn."*
)
shopt -u nullglob
[ "${#absent_fail_transactions[@]}" -eq 1 ] ||
	fail "failed ASR did not retain its preparing transaction"
absent_fail_transaction=${absent_fail_transactions[0]}
assert_file "$absent_fail_transaction/audio"
assert_eq "$(cat "$absent_fail_transaction/audio")" \
	"staged before absent failure"
/bin/rm "$absent_fail_source"
run_flatten "$absent_fail_home" ||
	fail "deleted failed transaction did not cancel"
assert_not_file "$absent_fail_home/Audio/Recordings/absent-failure.m4a"
assert_not_file "$absent_fail_home/Audio/Recordings/absent-failure.m4a.txt"
assert_not_path "$absent_fail_transaction"
assert_eq "$(grep -c '^asr ' "$absent_fail_home/test-state/events")" 1
assert_no_run_dirs "$absent_fail_home"

retry_isolation_home="$test_root/retry-isolation"
make_home "$retry_isolation_home"
write_route "$retry_isolation_home" 'hera/omlx/Qwen3.6-27B-oQ4e-mtp' \
	'retry-isolation-secret'
retry_isolation_route="$retry_isolation_home/.config/promptdeploy/default-llm.json"
retry_isolation_route_hash=$(fingerprint "$retry_isolation_route")
printf '%s\n' "$retry_isolation_route_hash" \
	>"$retry_isolation_home/test-state/expected-hash"
mkdir -p "$retry_isolation_home/Audio/Recordings" \
	"$retry_isolation_home/Library/Logs/flatten-recordings.state"
retry_isolation_source="$retry_isolation_home/Recordings/isolation.m4a"
printf 'new source identity\n' >"$retry_isolation_source"
printf '%s %s 5\n' "$retry_isolation_route_hash" \
	'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' \
	>"$retry_isolation_home/Library/Logs/flatten-recordings.state/isolation.m4a.fail"
run_flatten "$retry_isolation_home" ||
	fail "different source hash inherited retry exhaustion"
assert_file "$retry_isolation_home/Audio/Recordings/isolation.m4a"
assert_file "$retry_isolation_home/Audio/Recordings/isolation.m4a.txt"
assert_not_file \
	"$retry_isolation_home/Library/Logs/flatten-recordings.state/isolation.m4a.fail"
assert_no_run_dirs "$retry_isolation_home"

duplicate_home="$test_root/duplicate-transactions"
make_home "$duplicate_home"
write_route "$duplicate_home" 'hera/omlx/Qwen3.6-27B-oQ4e-mtp' \
	'duplicate-transactions-secret'
duplicate_route="$duplicate_home/.config/promptdeploy/default-llm.json"
printf '%s\n' "$(fingerprint "$duplicate_route")" \
	>"$duplicate_home/test-state/expected-hash"
mkdir -p "$duplicate_home/Audio/Recordings"
duplicate_source="$duplicate_home/Recordings/duplicate.m4a"
printf 'duplicate-protected source\n' >"$duplicate_source"
create_preparing_transaction "$duplicate_home" duplicate.m4a
duplicate_transaction_one=$CREATED_TRANSACTION
duplicate_transaction_two="$duplicate_home/Audio/Recordings/.duplicate.m4a.flatten-txn.second"
/bin/cp -R "$duplicate_transaction_one" "$duplicate_transaction_two"
if run_flatten "$duplicate_home"; then
	fail "duplicate owned transactions unexpectedly succeeded"
fi
assert_eq "$(cat "$duplicate_source")" "duplicate-protected source"
assert_file "$duplicate_transaction_one/audio"
assert_file "$duplicate_transaction_two/audio"
assert_not_file "$duplicate_home/Audio/Recordings/duplicate.m4a"
if grep -q '^asr ' "$duplicate_home/test-state/events"; then
	fail "duplicate transaction conflict reached ASR"
fi
assert_no_run_dirs "$duplicate_home"

renamed_home="$test_root/renamed-transaction"
make_home "$renamed_home"
write_route "$renamed_home" 'hera/omlx/Qwen3.6-27B-oQ4e-mtp' \
	'renamed-transaction-secret'
renamed_route="$renamed_home/.config/promptdeploy/default-llm.json"
printf '%s\n' "$(fingerprint "$renamed_route")" \
	>"$renamed_home/test-state/expected-hash"
mkdir -p "$renamed_home/Audio/Recordings"
renamed_source="$renamed_home/Recordings/original-name.m4a"
printf 'source with bound basename\n' >"$renamed_source"
create_preparing_transaction "$renamed_home" original-name.m4a
renamed_original_transaction=$CREATED_TRANSACTION
renamed_transaction="$renamed_home/Audio/Recordings/.wrong-name.m4a.flatten-txn.renamed"
/bin/mv "$renamed_original_transaction" "$renamed_transaction"
run_flatten "$renamed_home" || fail "renamed foreign transaction blocked source"
assert_file "$renamed_transaction/manifest"
assert_eq "$(cat "$renamed_home/Audio/Recordings/original-name.m4a")" \
	"source with bound basename"
assert_file "$renamed_home/Audio/Recordings/original-name.m4a.txt"
assert_no_run_dirs "$renamed_home"

replacement_home="$test_root/recovery-replacement"
make_home "$replacement_home"
write_route "$replacement_home" 'hera/omlx/Qwen3.6-27B-oQ4e-mtp' \
	'recovery-replacement-secret'
replacement_route="$replacement_home/.config/promptdeploy/default-llm.json"
printf '%s\n' "$(fingerprint "$replacement_route")" \
	>"$replacement_home/test-state/expected-hash"
mkdir -p "$replacement_home/Audio/Recordings"
replacement_source="$replacement_home/Recordings/replacement.m4a"
replacement_audio_dest="$replacement_home/Audio/Recordings/replacement.m4a"
replacement_transcript_dest="$replacement_home/Audio/Recordings/replacement.m4a.txt"
printf 'old source audio\n' >"$replacement_source"
create_archive_transaction "$replacement_home" replacement.m4a
replacement_transaction=$CREATED_TRANSACTION
/bin/ln "$replacement_transaction/audio" "$replacement_audio_dest"
/bin/ln "$replacement_transaction/transcript" "$replacement_transcript_dest"
/bin/rm "$replacement_source"
printf 'new source audio\n' >"$replacement_source"
if run_flatten "$replacement_home"; then
	fail "replacement source archive collision unexpectedly succeeded"
fi
assert_eq "$(cat "$replacement_source")" "new source audio"
assert_eq "$(cat "$replacement_audio_dest")" "old source audio"
assert_eq "$(cat "$replacement_transcript_dest")" "recovered transcript"
assert_not_path "$replacement_transaction"
if grep -q '^asr ' "$replacement_home/test-state/events"; then
	fail "replacement source collision reached ASR"
fi
assert_no_run_dirs "$replacement_home"

restoration_home="$test_root/recovery-restoration"
make_home "$restoration_home"
write_route "$restoration_home" 'hera/omlx/Qwen3.6-27B-oQ4e-mtp' \
	'recovery-restoration-secret'
restoration_route="$restoration_home/.config/promptdeploy/default-llm.json"
printf '%s\n' "$(fingerprint "$restoration_route")" \
	>"$restoration_home/test-state/expected-hash"
mkdir -p "$restoration_home/Audio/Recordings"
restoration_source="$restoration_home/Recordings/restoration.m4a"
restoration_claim_dir="$restoration_home/Recordings/.flatten-recordings-claim-fixture"
restoration_claim="$restoration_claim_dir/source"
restoration_audio_dest="$restoration_home/Audio/Recordings/restoration.m4a"
restoration_transcript_dest="$restoration_home/Audio/Recordings/restoration.m4a.txt"
printf 'old source audio\n' >"$restoration_source"
create_archive_transaction "$restoration_home" restoration.m4a
restoration_transaction=$CREATED_TRANSACTION
/bin/ln "$restoration_transaction/audio" "$restoration_audio_dest"
/bin/ln "$restoration_transaction/transcript" "$restoration_transcript_dest"
/bin/rm "$restoration_source"
mkdir -m 700 "$restoration_claim_dir"
printf 'replacement after restore\n' >"$restoration_claim"
run_flatten "$restoration_home" ||
	fail "claim-only replacement recovery failed"
assert_not_path "$restoration_source"
assert_not_path "$restoration_claim_dir"
assert_eq "$(cat "$restoration_audio_dest")" "old source audio"
assert_eq "$(cat "$restoration_transcript_dest")" "recovered transcript"
assert_not_path "$restoration_transaction"
shopt -s nullglob
restoration_requeued=(
	"$restoration_home/Recordings/.flatten-recordings-recovery."*/*.m4a
)
shopt -u nullglob
[ "${#restoration_requeued[@]}" -eq 1 ] ||
	fail "claim-only replacement was not requeued exactly once"
assert_eq "$(cat "${restoration_requeued[0]}")" "replacement after restore"
restoration_recovery_base=$(basename "${restoration_requeued[0]}")
if grep -q '^asr ' "$restoration_home/test-state/events"; then
	fail "interrupted replacement restoration reached ASR"
fi
assert_no_run_dirs "$restoration_home"
run_flatten "$restoration_home" ||
	fail "requeued claim-only replacement was not processed"
assert_eq "$(cat "$restoration_home/Audio/Recordings/$restoration_recovery_base")" \
	"replacement after restore"
assert_file \
	"$restoration_home/Audio/Recordings/$restoration_recovery_base.txt"
assert_no_run_dirs "$restoration_home"

claim_collision_home="$test_root/recovery-claim-collision"
make_home "$claim_collision_home"
write_route "$claim_collision_home" 'hera/omlx/Qwen3.6-27B-oQ4e-mtp' \
	'recovery-claim-collision-secret'
claim_collision_route="$claim_collision_home/.config/promptdeploy/default-llm.json"
printf '%s\n' "$(fingerprint "$claim_collision_route")" \
	>"$claim_collision_home/test-state/expected-hash"
mkdir -p "$claim_collision_home/Audio/Recordings"
claim_collision_source="$claim_collision_home/Recordings/claim-collision.m4a"
claim_collision_path="$claim_collision_home/Recordings/.flatten-recordings-claim-fixture"
claim_collision_audio_dest="$claim_collision_home/Audio/Recordings/claim-collision.m4a"
claim_collision_transcript_dest="$claim_collision_home/Audio/Recordings/claim-collision.m4a.txt"
printf 'source protected from claim collision\n' >"$claim_collision_source"
create_archive_transaction "$claim_collision_home" claim-collision.m4a
claim_collision_transaction=$CREATED_TRANSACTION
/bin/ln "$claim_collision_transaction/audio" "$claim_collision_audio_dest"
/bin/ln "$claim_collision_transaction/transcript" \
	"$claim_collision_transcript_dest"
mkdir -m 700 "$claim_collision_path"
printf 'foreign claim collision\n' >"$claim_collision_path/sentinel"
if run_flatten "$claim_collision_home"; then
	fail "foreign claim collision unexpectedly succeeded"
fi
assert_eq "$(cat "$claim_collision_source")" \
	"source protected from claim collision"
assert_eq "$(cat "$claim_collision_path/sentinel")" "foreign claim collision"
assert_file "$claim_collision_transaction/manifest"
assert_eq "$(cat "$claim_collision_audio_dest")" \
	"source protected from claim collision"
assert_eq "$(cat "$claim_collision_transcript_dest")" \
	"recovered transcript"
if grep -q '^asr ' "$claim_collision_home/test-state/events"; then
	fail "foreign claim collision reached ASR"
fi
assert_no_run_dirs "$claim_collision_home"

for foreign_phase in preexisting mid-asr; do
	foreign_home="$test_root/foreign-$foreign_phase"
	make_home "$foreign_home"
	write_route "$foreign_home" 'hera/omlx/Qwen3.6-27B-oQ4e-mtp' \
		"foreign-$foreign_phase-secret"
	foreign_route="$foreign_home/.config/promptdeploy/default-llm.json"
	printf '%s\n' "$(fingerprint "$foreign_route")" \
		>"$foreign_home/test-state/expected-hash"
	printf 'foreign stage audio\n' >"$foreign_home/Recordings/foreign.m4a"
	mkdir -p "$foreign_home/Audio/Recordings"
	foreign_transaction="$foreign_home/Audio/Recordings/.foreign.m4a.flatten-txn.foreign"
	if [ "$foreign_phase" = mid-asr ]; then
		mkfifo "$foreign_home/test-state/asr-entered" \
			"$foreign_home/test-state/asr-release"
		run_flatten "$foreign_home" &
		foreign_pid=$!
		background_pid=$foreign_pid
		IFS= read -r entered <"$foreign_home/test-state/asr-entered"
		assert_eq "$entered" entered
	fi
	mkdir -m 700 "$foreign_transaction"
	printf 'foreign content\n' >"$foreign_transaction/do-not-touch"
	if [ "$foreign_phase" = mid-asr ]; then
		printf 'release\n' >"$foreign_home/test-state/asr-release"
		foreign_rc=0
		wait "$foreign_pid" || foreign_rc=$?
		background_pid=''
		assert_eq "$foreign_rc" 0
	else
		run_flatten "$foreign_home" ||
			fail "foreign transaction path blocked independent staging"
	fi
	assert_eq "$(cat "$foreign_transaction/do-not-touch")" "foreign content"
	assert_file "$foreign_home/Audio/Recordings/foreign.m4a"
	assert_file "$foreign_home/Audio/Recordings/foreign.m4a.txt"
	assert_no_run_dirs "$foreign_home"
done

no_recordings_home="$test_root/no-recordings"
make_home "$no_recordings_home"
rm -rf "$no_recordings_home/Recordings"
run_flatten "$no_recordings_home" ||
	fail "missing recordings directory should not require an LLM route"
[ ! -e "$no_recordings_home/test-state/events" ] ||
	fail "missing recordings directory invoked transcribe"

invalid_home="$test_root/invalid"
make_home "$invalid_home"
mkdir -p "$invalid_home/.config/promptdeploy" "$invalid_home/Recordings/nested"
printf 'not json\n' >"$invalid_home/.config/promptdeploy/default-llm.json"
printf 'nested audio\n' >"$invalid_home/Recordings/nested/invalid.m4a"
if run_flatten "$invalid_home"; then
	fail "invalid managed route unexpectedly succeeded"
fi
assert_file "$invalid_home/Recordings/nested/invalid.m4a"
assert_not_file "$invalid_home/Recordings/invalid.m4a"
[ ! -d "$invalid_home/Library/Logs/flatten-recordings.state" ] ||
	fail "invalid preflight created retry state"
assert_eq "$(grep -c '^validate$' "$invalid_home/test-state/events")" 1
if grep -q '^asr ' "$invalid_home/test-state/events"; then
	fail "invalid preflight reached ASR"
fi

missing_home="$test_root/missing"
make_home "$missing_home"
mkdir -p "$missing_home/Recordings/nested"
printf 'nested audio\n' >"$missing_home/Recordings/nested/missing.m4a"
if run_flatten "$missing_home"; then
	fail "missing managed route unexpectedly succeeded"
fi
assert_file "$missing_home/Recordings/nested/missing.m4a"
assert_not_file "$missing_home/Recordings/missing.m4a"
[ ! -e "$missing_home/test-state/events" ] ||
	fail "missing route invoked transcribe"
[ ! -d "$missing_home/Library/Logs/flatten-recordings.state" ] ||
	fail "missing preflight created retry state"

failure_home="$test_root/failure"
make_home "$failure_home"
write_route "$failure_home" 'hera/omlx/Qwen3.6-27B-oQ4e-mtp' 'failure-secret-one'
failure_route="$failure_home/.config/promptdeploy/default-llm.json"
failure_hash=$(fingerprint "$failure_route")
printf '%s\n' "$failure_hash" >"$failure_home/test-state/expected-hash"
touch "$failure_home/test-state/fail-asr"
printf 'failing audio\n' >"$failure_home/Recordings/failure.m4a"
failure_source_hash=$(fingerprint "$failure_home/Recordings/failure.m4a")
failure_state="$failure_home/Library/Logs/flatten-recordings.state/failure.m4a.fail"

if run_flatten "$failure_home"; then
	fail "failing transcription unexpectedly succeeded"
fi
assert_eq "$(cat "$failure_state")" "$failure_hash $failure_source_hash 1"
if run_flatten "$failure_home"; then
	fail "second failing transcription unexpectedly succeeded"
fi
assert_eq "$(cat "$failure_state")" "$failure_hash $failure_source_hash 2"

write_route "$failure_home" 'hera/omlx/Qwen3.6-27B-oQ4e-mtp-v2' 'failure-secret-two'
new_failure_hash=$(fingerprint "$failure_route")
printf '%s\n' "$new_failure_hash" >"$failure_home/test-state/expected-hash"
if run_flatten "$failure_home"; then
	fail "changed-route failing transcription unexpectedly succeeded"
fi
assert_eq "$(cat "$failure_state")" \
	"$new_failure_hash $failure_source_hash 1"

printf '%s %s 4\n' "$new_failure_hash" "$failure_source_hash" \
	>"$failure_state"
if run_flatten "$failure_home"; then
	fail "fourth matching-route failure unexpectedly succeeded"
fi
assert_eq "$(cat "$failure_state")" \
	"$new_failure_hash $failure_source_hash 5"

printf '%s %s 08\n' "$new_failure_hash" "$failure_source_hash" \
	>"$failure_state"
if run_flatten "$failure_home"; then
	fail "leading-zero retry state unexpectedly succeeded"
fi
assert_eq "$(cat "$failure_state")" \
	"$new_failure_hash $failure_source_hash 1"

printf '%s %s 4\n' "$new_failure_hash" "$failure_source_hash" \
	>"$failure_state"
touch -t 202001010000 "$failure_state"
touch -t 203001010000 "$failure_home/Recordings/failure.m4a"
if run_flatten "$failure_home"; then
	fail "newer-path retry unexpectedly succeeded"
fi
assert_eq "$(cat "$failure_state")" \
	"$new_failure_hash $failure_source_hash 5"
grep -Eq 'ERROR transcribe rc=23 request_id=[^ ]+:failure\.m4a ' \
	"$failure_home/Library/Logs/flatten-recordings.log" ||
	fail "failure log lacks recording request id"
assert_not_file "$failure_home/Recordings/failure.m4a.txt"
assert_not_file "$failure_home/Audio/Recordings/failure.m4a"
assert_not_file "$failure_home/Audio/Recordings/failure.m4a.txt"
assert_no_run_dirs "$failure_home"

printf 'flatten-recordings route regression: PASS\n'
