#!/bin/bash

debug=false
if [[ "$1" == "-v" ]]; then
    debug=true
    shift 1
fi

taking=false

SNAPSHOTS="/Volumes/My Book/Archive/Snapshots"

if [[ -d "$SNAPSHOTS" ]]; then
    # Make a monthly backup if the last monthly snapshot is equal to or older
    # than 27 days, or if no monthly snapshot has yet been made.

    if [[ -d "$SNAPSHOTS/monthly.0" ]]; then
	secs_since_monthly=$(( $(stat -f %m "$SNAPSHOTS/weekly.3") - \
	                       $(stat -f %m "$SNAPSHOTS/monthly.0") ))
	days_since_monthly=$(( secs_since_monthly / 86400 ))
    fi

    if [[ -z "$days_since_monthly" || $days_since_monthly -ge 27 ]]; then
	rsnapshot -c ~/.rsnapshotrc monthly "$@"
        if [[ $debug == true ]]; then
	    echo Taking a monthly snapshot \($days_since_monthly days \>\= 27\).
	fi
	taking=true
    elif [[ $debug == true ]]; then
	echo Not time yet for a monthly snapshot \($days_since_monthly days \< 27\).
    fi

    # Make a weekly backup if the last monthly snapshot is equal to or older
    # than 6 days (since 6.9 days will be seen as 6 days), or if no weekly
    # snapshot has yet been made.

    if [[ -d "$SNAPSHOTS/weekly.0" ]]; then
	secs_since_weekly=$(( $(stat -f %m "$SNAPSHOTS/daily.6") - \
	                      $(stat -f %m "$SNAPSHOTS/weekly.0") ))
	days_since_weekly=$(( secs_since_weekly / 86400 ))
    fi

    if [[ -z "$days_since_weekly" || $days_since_weekly -ge 6 ]]; then
	rsnapshot -c ~/.rsnapshotrc weekly "$@"
        if [[ $debug == true ]]; then
	    echo Taking a weekly snapshot \($days_since_weekly days \>\= 6\).
	fi
	taking=true
    elif [[ $debug == true ]]; then
	echo Not time yet for a weekly snapshot \($days_since_weekly days \< 6\).
    fi

    # Make a daily snapshot every time this script is run, which should be
    # once nightly.

    if [[ -d "$SNAPSHOTS/daily.0" ]]; then
	secs_since_daily=$(( $(date +%s) - $(stat -f %m "$SNAPSHOTS/daily.0") ))
	hours_since_daily=$(( secs_since_daily / 3600 ))
    fi

    if [[ -z "$hours_since_daily" || $hours_since_daily -ge 23 ]]; then
	rsnapshot -c ~/.rsnapshotrc daily "$@"
        if [[ $debug == true ]]; then
	    echo Taking a daily snapshot \($hours_since_daily hours \>\= 23\).
	fi
	taking=true
    elif [[ $debug == true ]]; then
	echo Not time yet for a daily snapshot \($hours_since_daily hours \< 23\).
    fi
fi

if [[ $debug == true && $taking == true ]]; then
    echo Waiting for all snapshots to complete...
    wait
    echo System snapshot is finished.
fi
