#!/usr/bin/env python3
"""
IMAP List-Id Scanner
Scans a Dovecot IMAP mailbox and reports Message-ID and List-Id headers for all messages.
"""

import argparse
import email
import getpass
import imaplib
import os
import sys
from email.header import decode_header


def decode_mime_header(header_value):
    """Decode MIME-encoded header values."""
    if not header_value:
        return None

    decoded_parts = decode_header(header_value)
    decoded_string = ""

    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            decoded_string += part.decode(encoding or 'utf-8', errors='replace')
        else:
            decoded_string += part

    return decoded_string.strip()


def connect_imap(host=None, port=993, username=None, password=None, use_ssl=True, process=None):
    """Connect to IMAP server and login.

    Args:
        host: IMAP server hostname (for network mode)
        port: IMAP server port (for network mode)
        username: IMAP username (for network mode)
        password: IMAP password (for network mode)
        use_ssl: Use SSL/TLS (for network mode)
        process: Path to IMAP process to spawn (for local mode)

    Returns:
        IMAP connection object
    """
    try:
        if process:
            # Local process mode (e.g., Dovecot)
            print(f"Spawning local IMAP process: {process}", file=sys.stderr)
            imap = imaplib.IMAP4_stream(process)
            print("Connected to local IMAP process (authentication handled by process)", file=sys.stderr)
        else:
            # Network mode
            if use_ssl:
                imap = imaplib.IMAP4_SSL(host, port)
            else:
                imap = imaplib.IMAP4(host, port)

            imap.login(username, password)
            print(f"Connected to {host}:{port} as {username}", file=sys.stderr)

        return imap
    except imaplib.IMAP4.error as e:
        print(f"IMAP login failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Connection failed: {e}", file=sys.stderr)
        sys.exit(1)


def scan_mailbox(imap, mailbox="INBOX", output_format="table", dest_mailbox=None):
    """Scan mailbox and extract Message-ID and List-Id headers.

    Args:
        imap: IMAP connection object
        mailbox: Source mailbox to scan
        output_format: Output format (table, csv, summary)
        dest_mailbox: Optional destination mailbox to move messages with List-Id
    """
    try:
        # Select mailbox (read-write if moving, otherwise readonly)
        readonly = dest_mailbox is None
        status, messages = imap.select(mailbox, readonly=readonly)
        if status != 'OK':
            print(f"Failed to select mailbox: {mailbox}", file=sys.stderr)
            return

        # Get all message IDs
        status, message_ids = imap.search(None, 'ALL')
        if status != 'OK':
            print("Failed to search messages", file=sys.stderr)
            return

        msg_id_list = message_ids[0].split()
        total_messages = len(msg_id_list)

        print(f"Scanning {total_messages} messages in {mailbox}...\n", file=sys.stderr)

        results = []
        messages_to_move = []
        moved_count = 0
        move_errors = 0

        for idx, msg_id in enumerate(msg_id_list, 1):
            # Fetch headers only for efficiency
            status, msg_data = imap.fetch(msg_id, '(BODY.PEEK[HEADER])')

            if status != 'OK':
                print(f"Failed to fetch message {msg_id}", file=sys.stderr)
                continue

            # Parse email headers
            email_message = email.message_from_bytes(msg_data[0][1])

            message_id = email_message.get('Message-ID', '<no-message-id>')
            list_id_raw = email_message.get('List-Id')
            list_id = decode_mime_header(list_id_raw) if list_id_raw else None

            result = {
                'seq_num': msg_id.decode(),
                'message_id': message_id,
                'list_id': list_id,
                'has_list_id': list_id is not None
            }
            results.append(result)

            # Track messages to move if dest is specified
            if dest_mailbox and list_id:
                messages_to_move.append(msg_id)

            # Progress indicator
            if idx % 100 == 0:
                print(f"Processed {idx}/{total_messages} messages...", file=sys.stderr)

        # Move messages if destination specified
        if dest_mailbox and messages_to_move:
            print(f"\nMoving {len(messages_to_move)} messages with List-Id to {dest_mailbox}...", file=sys.stderr)

            for idx, msg_id in enumerate(messages_to_move, 1):
                try:
                    # Copy message to destination
                    status, response = imap.copy(msg_id, dest_mailbox)
                    if status != 'OK':
                        print(f"Failed to copy message {msg_id.decode()}: {response}", file=sys.stderr)
                        move_errors += 1
                        continue

                    # Mark original as deleted
                    status, response = imap.store(msg_id, '+FLAGS', '\\Deleted')
                    if status != 'OK':
                        print(f"Failed to mark message {msg_id.decode()} as deleted: {response}", file=sys.stderr)
                        move_errors += 1
                        continue

                    moved_count += 1

                    # Progress indicator
                    if idx % 100 == 0:
                        print(f"Moved {idx}/{len(messages_to_move)} messages...", file=sys.stderr)

                except Exception as e:
                    print(f"Error moving message {msg_id.decode()}: {e}", file=sys.stderr)
                    move_errors += 1

            # Expunge to permanently remove moved messages
            if moved_count > 0:
                print(f"Expunging {moved_count} moved messages...", file=sys.stderr)
                imap.expunge()
                print(f"Successfully moved {moved_count} messages to {dest_mailbox}", file=sys.stderr)

            if move_errors > 0:
                print(f"Encountered {move_errors} errors during move operation", file=sys.stderr)

        # Output results
        if output_format == "table":
            print()  # Blank line before results
            print_table(results)
        elif output_format == "csv":
            print_csv(results)
        elif output_format == "summary":
            print()  # Blank line before results
            print_summary(results)

    except Exception as e:
        print(f"Error scanning mailbox: {e}", file=sys.stderr)
        raise


def print_table(results):
    """Print results in table format."""
    # Header
    print(f"{'SEQ':<6} | {'HAS LIST-ID':<12} | {'MESSAGE-ID':<50} | LIST-ID")
    print("-" * 150)

    for r in results:
        has_list = "Yes" if r['has_list_id'] else "No"
        msg_id = r['message_id'][:47] + "..." if len(r['message_id']) > 50 else r['message_id']
        list_id = r['list_id'] if r['list_id'] else ""

        print(f"{r['seq_num']:<6} | {has_list:<12} | {msg_id:<50} | {list_id}")


def print_csv(results):
    """Print results in CSV format."""
    import csv
    import sys

    writer = csv.DictWriter(sys.stdout, fieldnames=['seq_num', 'has_list_id', 'message_id', 'list_id'])
    writer.writeheader()

    for r in results:
        writer.writerow({
            'seq_num': r['seq_num'],
            'has_list_id': 'Yes' if r['has_list_id'] else 'No',
            'message_id': r['message_id'],
            'list_id': r['list_id'] or ''
        })


def print_summary(results):
    """Print summary statistics."""
    total = len(results)
    with_list_id = sum(1 for r in results if r['has_list_id'])
    without_list_id = total - with_list_id

    print(f"Total messages: {total}")
    print(f"Messages with List-Id: {with_list_id} ({with_list_id/total*100:.1f}%)")
    print(f"Messages without List-Id: {without_list_id} ({without_list_id/total*100:.1f}%)")

    if with_list_id > 0:
        print("\nUnique List-Id values:")
        list_ids = set(r['list_id'] for r in results if r['list_id'])
        for lid in sorted(list_ids):
            count = sum(1 for r in results if r['list_id'] == lid)
            print(f"  {count:4d} messages: {lid}")


def main():
    parser = argparse.ArgumentParser(
        description="Scan Dovecot IMAP mailbox for List-Id headers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Network mode - Scan INBOX with prompted password
  %(prog)s -H vulcan.lan -u john@example.com

  # Network mode - Scan with environment variable password
  export IMAP_PASSWORD="mypassword"
  %(prog)s -H vulcan.lan -u john@example.com -m "Sent Items"

  # Network mode - Output CSV format
  %(prog)s -H vulcan.lan -u john@example.com -f csv > results.csv

  # Network mode - Show summary only
  %(prog)s -H vulcan.lan -u john@example.com -f summary

  # Local process mode - Access Dovecot directly (authentication handled by process)
  # Must run as the mail user whose mailbox you want to access
  sudo -u johnw %(prog)s --process "/nix/store/.../libexec/dovecot/imap" -m INBOX

  # Local process mode - Show summary
  sudo -u johnw %(prog)s --process "/nix/store/.../libexec/dovecot/imap" -m INBOX -f summary

  # Move messages with List-Id to a destination mailbox
  %(prog)s -H localhost -u johnw -m INBOX --dest "Lists" -f summary

  # Local process mode - Move messages
  sudo -u johnw %(prog)s --process "/nix/store/.../libexec/dovecot/imap" -m INBOX --dest "MailingLists"
        """
    )

    parser.add_argument('-H', '--host',
                        help='IMAP server hostname (network mode, default: localhost)')
    parser.add_argument('-p', '--port', type=int, default=993,
                        help='IMAP server port (network mode, default: 993)')
    parser.add_argument('-u', '--username',
                        help='IMAP username (network mode)')
    parser.add_argument('-P', '--password',
                        help='IMAP password (network mode, will prompt if not provided)')
    parser.add_argument('--process',
                        help='IMAP process to spawn for local access (e.g., /usr/libexec/dovecot/imap)')
    parser.add_argument('-m', '--mailbox', default='INBOX',
                        help='Mailbox to scan (default: INBOX)')
    parser.add_argument('-f', '--format', choices=['table', 'csv', 'summary'],
                        default='table',
                        help='Output format (default: table)')
    parser.add_argument('--dest',
                        help='Destination mailbox to move messages with List-Id headers')
    parser.add_argument('--no-ssl', action='store_true',
                        help='Disable SSL/TLS (network mode, not recommended)')

    args = parser.parse_args()

    # Validate mode selection
    if args.process:
        # Local process mode - server/username/password not required
        if args.host or args.username or args.password:
            print("Warning: --host, --username, and --password are ignored when using --process", file=sys.stderr)
        password = None
        host = None
        username = None
    else:
        # Network mode - host and username required
        if not args.host:
            args.host = 'localhost'
        if not args.username:
            print("Error: --username is required for network mode (or use --process for local mode)", file=sys.stderr)
            sys.exit(1)

        # Get password for network mode
        password = args.password or os.environ.get('IMAP_PASSWORD')
        if not password:
            password = getpass.getpass(f"Password for {args.username}: ")

        host = args.host
        username = args.username

    # Connect to IMAP
    imap = connect_imap(
        host=host,
        port=args.port,
        username=username,
        password=password,
        use_ssl=not args.no_ssl,
        process=args.process
    )

    try:
        # Scan mailbox
        scan_mailbox(imap, args.mailbox, args.format, args.dest)
    finally:
        # Cleanup
        try:
            imap.close()
            imap.logout()
        except:
            pass


if __name__ == '__main__':
    main()
