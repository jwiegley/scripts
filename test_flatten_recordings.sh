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
printf '%s 5\n' "$route_hash" >"$state_dir/capped.m4a.fail"
touch -t 203001010000 "$state_dir/legacy.m4a.fail" "$state_dir/capped.m4a.fail"

run_flatten "$snapshot_home" || fail "snapshot/route-aware run failed"
assert_file "$snapshot_home/Recordings/legacy.m4a.txt"
assert_file "$snapshot_home/Audio/Recordings/legacy.m4a"
assert_file "$snapshot_home/Recordings/second.m4a.txt"
assert_file "$snapshot_home/Audio/Recordings/second.m4a"
assert_file "$snapshot_home/Recordings/capped.m4a"
assert_not_file "$snapshot_home/Audio/Recordings/capped.m4a"
assert_not_file "$state_dir/legacy.m4a.fail"
assert_eq "$(cat "$state_dir/capped.m4a.fail")" "$route_hash 5"
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
assert_file "$concurrent_home/Recordings/concurrent.m4a.txt"
assert_file "$concurrent_home/Audio/Recordings/concurrent.m4a"
assert_no_run_dirs "$concurrent_home"

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
failure_state="$failure_home/Library/Logs/flatten-recordings.state/failure.m4a.fail"

if run_flatten "$failure_home"; then
	fail "failing transcription unexpectedly succeeded"
fi
assert_eq "$(cat "$failure_state")" "$failure_hash 1"
if run_flatten "$failure_home"; then
	fail "second failing transcription unexpectedly succeeded"
fi
assert_eq "$(cat "$failure_state")" "$failure_hash 2"

write_route "$failure_home" 'hera/omlx/Qwen3.6-27B-oQ4e-mtp-v2' 'failure-secret-two'
new_failure_hash=$(fingerprint "$failure_route")
printf '%s\n' "$new_failure_hash" >"$failure_home/test-state/expected-hash"
if run_flatten "$failure_home"; then
	fail "changed-route failing transcription unexpectedly succeeded"
fi
assert_eq "$(cat "$failure_state")" "$new_failure_hash 1"

printf '%s 4\n' "$new_failure_hash" >"$failure_state"
if run_flatten "$failure_home"; then
	fail "fourth matching-route failure unexpectedly succeeded"
fi
assert_eq "$(cat "$failure_state")" "$new_failure_hash 5"

printf '%s 08\n' "$new_failure_hash" >"$failure_state"
if run_flatten "$failure_home"; then
	fail "leading-zero retry state unexpectedly succeeded"
fi
assert_eq "$(cat "$failure_state")" "$new_failure_hash 1"

printf '%s 4\n' "$new_failure_hash" >"$failure_state"
touch -t 202001010000 "$failure_state"
touch -t 203001010000 "$failure_home/Recordings/failure.m4a"
if run_flatten "$failure_home"; then
	fail "newer-recording failing transcription unexpectedly succeeded"
fi
assert_eq "$(cat "$failure_state")" "$new_failure_hash 1"
grep -Eq 'ERROR transcribe rc=23 request_id=[^ ]+:failure\.m4a ' \
	"$failure_home/Library/Logs/flatten-recordings.log" ||
	fail "failure log lacks recording request id"
assert_not_file "$failure_home/Recordings/failure.m4a.txt"
assert_not_file "$failure_home/Audio/Recordings/failure.m4a"
assert_no_run_dirs "$failure_home"

printf 'flatten-recordings route regression: PASS\n'
