#!/usr/bin/env python3
"""
Email Message-ID Lister

Connects to an IMAP email server and prints all Message-IDs in the format:
MAILBOX MESSAGE-ID

Usage:
    python list_message_ids.py --server imap.example.com --user username [--password PASSWORD]

    # Include only specific mailboxes
    python list_message_ids.py --server imap.example.com --user username --include INBOX --include Sent

    # Exclude specific mailboxes
    python list_message_ids.py --server imap.example.com --user username --exclude Trash --exclude Spam

If password is not provided, it will be prompted securely.
"""

import imaplib
import email
import sys
import argparse
import getpass
import re
from email.header import decode_header


def decode_mailbox_name(name):
    """Decode IMAP mailbox name (handles UTF-7 encoding)."""
    try:
        # IMAP uses modified UTF-7 encoding
        return name.decode('utf-7') if isinstance(name, bytes) else name
    except:
        return name.decode('utf-8', errors='ignore') if isinstance(name, bytes) else name


def extract_message_id(msg):
    """Extract Message-ID from email message."""
    message_id = msg.get('Message-ID', '').strip()
    # Remove angle brackets if present
    if message_id.startswith('<') and message_id.endswith('>'):
        message_id = message_id[1:-1]
    return message_id


def list_mailboxes(imap_conn):
    """List all mailboxes on the server."""
    mailboxes = []
    try:
        status, mailbox_list = imap_conn.list()
        if status != 'OK':
            print(f"Error listing mailboxes: {status}", file=sys.stderr)
            return mailboxes

        for mailbox_line in mailbox_list:
            # Parse IMAP LIST response: (flags) "delimiter" "name"
            if isinstance(mailbox_line, bytes):
                mailbox_line = mailbox_line.decode('utf-8', errors='ignore')

            # Extract mailbox name (handle quoted names)
            match = re.search(r'\([^)]*\)\s+"[^"]*"\s+"?([^"]+)"?', mailbox_line)
            if match:
                mailbox_name = match.group(1)
                mailboxes.append(mailbox_name)
            else:
                # Fallback parsing
                parts = mailbox_line.split('"')
                if len(parts) >= 4:
                    mailboxes.append(parts[-2])

        return mailboxes
    except Exception as e:
        print(f"Error listing mailboxes: {e}", file=sys.stderr)
        return mailboxes


def process_mailbox(imap_conn, mailbox_name, output_file=None):
    """Process all messages in a mailbox and print their Message-IDs."""
    try:
        # Select mailbox (read-only mode)
        status, data = imap_conn.select(f'"{mailbox_name}"', readonly=True)
        if status != 'OK':
            print(f"Error selecting mailbox '{mailbox_name}': {status}", file=sys.stderr)
            return 0

        # Search for all messages
        status, message_ids = imap_conn.search(None, 'ALL')
        if status != 'OK':
            print(f"Error searching mailbox '{mailbox_name}': {status}", file=sys.stderr)
            return 0

        message_nums = message_ids[0].split()
        count = 0

        # Process each message
        for msg_num in message_nums:
            try:
                # Fetch only the Message-ID header for efficiency
                status, msg_data = imap_conn.fetch(msg_num, '(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)])')
                if status != 'OK':
                    continue

                # Parse the header
                if msg_data and msg_data[0]:
                    header_data = msg_data[0][1]
                    if isinstance(header_data, bytes):
                        header_data = header_data.decode('utf-8', errors='ignore')

                    # Extract Message-ID using email parser
                    msg = email.message_from_string(header_data)
                    message_id = extract_message_id(msg)

                    if message_id:
                        output_line = f"{mailbox_name} {message_id}"
                        if output_file:
                            output_file.write(output_line + '\n')
                        else:
                            print(output_line)
                        count += 1
                    else:
                        # Message has no Message-ID (rare but possible)
                        print(f"{mailbox_name} <NO-MESSAGE-ID:{msg_num.decode()}>", file=sys.stderr)

            except Exception as e:
                print(f"Error processing message {msg_num} in {mailbox_name}: {e}", file=sys.stderr)
                continue

        return count

    except Exception as e:
        print(f"Error processing mailbox '{mailbox_name}': {e}", file=sys.stderr)
        return 0


def main():
    parser = argparse.ArgumentParser(
        description='List all Message-IDs from an IMAP email server',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--server', '-s', required=True, help='IMAP server address')
    parser.add_argument('--port', '-p', type=int, default=993, help='IMAP port (default: 993 for SSL)')
    parser.add_argument('--user', '-u', required=True, help='Email username')
    parser.add_argument('--password', '-P', help='Email password (will prompt if not provided)')
    parser.add_argument('--no-ssl', action='store_true', help='Disable SSL/TLS (use plain IMAP on port 143)')
    parser.add_argument('--include', '-i', action='append', dest='includes', metavar='MAILBOX',
                        help='Include only specific mailbox (can be specified multiple times)')
    parser.add_argument('--exclude', '-e', action='append', dest='excludes', metavar='MAILBOX',
                        help='Exclude specific mailbox (can be specified multiple times)')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    # Get password if not provided
    password = args.password
    if not password:
        password = getpass.getpass(f"Password for {args.user}: ")

    # Connect to IMAP server
    try:
        if args.verbose:
            print(f"Connecting to {args.server}:{args.port}...", file=sys.stderr)

        if args.no_ssl:
            imap_conn = imaplib.IMAP4(args.server, args.port)
        else:
            imap_conn = imaplib.IMAP4_SSL(args.server, args.port)

        if args.verbose:
            print(f"Logging in as {args.user}...", file=sys.stderr)

        imap_conn.login(args.user, password)

        if args.verbose:
            print("Successfully connected and authenticated.", file=sys.stderr)

    except Exception as e:
        print(f"Error connecting to server: {e}", file=sys.stderr)
        sys.exit(1)

    # Open output file if specified
    output_file = None
    if args.output:
        try:
            output_file = open(args.output, 'w', encoding='utf-8')
        except Exception as e:
            print(f"Error opening output file: {e}", file=sys.stderr)
            sys.exit(1)

    try:
        # Get list of mailboxes
        if args.includes:
            # If includes specified, only use those mailboxes
            mailboxes = args.includes
            if args.verbose:
                print(f"Using included mailboxes: {', '.join(mailboxes)}", file=sys.stderr)
        else:
            # Get all mailboxes from server
            if args.verbose:
                print("Listing mailboxes...", file=sys.stderr)
            mailboxes = list_mailboxes(imap_conn)
            if args.verbose:
                print(f"Found {len(mailboxes)} mailboxes.", file=sys.stderr)

        # Apply exclusions if specified
        if args.excludes:
            original_count = len(mailboxes)
            mailboxes = [mb for mb in mailboxes if mb not in args.excludes]
            if args.verbose:
                excluded_count = original_count - len(mailboxes)
                print(f"Excluded {excluded_count} mailbox(es): {', '.join(args.excludes)}", file=sys.stderr)
                print(f"Processing {len(mailboxes)} mailbox(es) after exclusions.", file=sys.stderr)

        # Process each mailbox
        total_messages = 0
        for mailbox in mailboxes:
            if args.verbose:
                print(f"Processing mailbox: {mailbox}", file=sys.stderr)

            count = process_mailbox(imap_conn, mailbox, output_file)
            total_messages += count

            if args.verbose:
                print(f"  Found {count} messages with Message-IDs", file=sys.stderr)

        if args.verbose:
            print(f"\nTotal: {total_messages} messages processed from {len(mailboxes)} mailboxes", file=sys.stderr)

    finally:
        # Cleanup
        if output_file:
            output_file.close()

        try:
            imap_conn.logout()
        except:
            pass


if __name__ == '__main__':
    main()
