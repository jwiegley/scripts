#!/usr/bin/env python3
"""
Email Message Deleter

Connects to an IMAP email server and deletes messages by UID.

Usage:
    python delete_message.py --server imap.example.com --user username --mailbox INBOX --uid 8133

    # Delete multiple messages
    python delete_message.py --server imap.example.com --user username --mailbox INBOX --uid 8133 --uid 8134

    # Dry run (preview without deleting)
    python delete_message.py --server imap.example.com --user username --mailbox INBOX --uid 8133 --dry-run

    # Verbose mode (shows full message content before deletion)
    python delete_message.py --server imap.example.com --user username --mailbox INBOX --uid 8133 --verbose

If password is not provided, it will be prompted securely.
"""

import imaplib
import email
import sys
import argparse
import getpass
from email.header import decode_header


def decode_mime_header(header):
    """Decode MIME encoded email header."""
    if not header:
        return ""

    decoded_parts = decode_header(header)
    result = []

    for content, encoding in decoded_parts:
        if isinstance(content, bytes):
            if encoding:
                try:
                    result.append(content.decode(encoding))
                except:
                    result.append(content.decode('utf-8', errors='ignore'))
            else:
                result.append(content.decode('utf-8', errors='ignore'))
        else:
            result.append(str(content))

    return ''.join(result)


def get_message_body(msg):
    """Extract the message body (text/plain preferred, or text/html)."""
    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))

            # Skip attachments
            if "attachment" in content_disposition:
                continue

            if content_type == "text/plain":
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body = payload.decode('utf-8', errors='ignore')
                        break  # Prefer plain text
                except:
                    continue
            elif content_type == "text/html" and not body:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body = payload.decode('utf-8', errors='ignore')
                except:
                    continue
    else:
        # Not multipart - just get the payload
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode('utf-8', errors='ignore')
        except:
            body = str(msg.get_payload())

    return body


def print_message_details(msg, uid):
    """Print formatted message details."""
    print(f"\n{'='*80}")
    print(f"Message UID: {uid}")
    print(f"{'-'*80}")

    # Extract and decode headers
    subject = decode_mime_header(msg.get('Subject', '(No Subject)'))
    from_addr = decode_mime_header(msg.get('From', '(Unknown)'))
    to_addr = decode_mime_header(msg.get('To', '(Unknown)'))
    date = msg.get('Date', '(Unknown)')
    message_id = msg.get('Message-ID', '(No Message-ID)')

    print(f"From: {from_addr}")
    print(f"To: {to_addr}")
    print(f"Date: {date}")
    print(f"Subject: {subject}")
    print(f"Message-ID: {message_id}")

    # Get message size
    if hasattr(msg, '__len__'):
        size = len(str(msg))
        print(f"Size: {size:,} bytes")

    print(f"{'-'*80}")

    # Get and print body
    body = get_message_body(msg)
    if body:
        # Print first 2000 characters of body
        if len(body) > 2000:
            print(body[:2000])
            print(f"\n... (truncated, {len(body) - 2000} more characters)")
        else:
            print(body)
    else:
        print("(No readable body content)")

    print(f"{'='*80}\n")


def delete_messages(server, port, username, password, mailbox, uids,
                   use_ssl=True, dry_run=False, verbose=False):
    """
    Delete messages from an IMAP mailbox by UID.

    Args:
        server: IMAP server address
        port: IMAP server port
        username: Email username
        password: Email password
        mailbox: Mailbox/folder name
        uids: List of message UIDs to delete
        use_ssl: Use SSL/TLS connection
        dry_run: Preview without actually deleting
        verbose: Print detailed progress

    Returns:
        Number of messages successfully deleted
    """
    deleted_count = 0

    try:
        # Connect to server
        if verbose:
            print(f"Connecting to {server}:{port}...", file=sys.stderr)

        if use_ssl:
            mail = imaplib.IMAP4_SSL(server, port)
        else:
            mail = imaplib.IMAP4(server, port)

        if verbose:
            print(f"Logging in as {username}...", file=sys.stderr)

        # Login
        mail.login(username, password)

        if verbose:
            print(f"Successfully authenticated.", file=sys.stderr)
            print(f"Selecting mailbox: {mailbox}", file=sys.stderr)

        # Select mailbox (read-write mode)
        status, data = mail.select(f'"{mailbox}"')
        if status != 'OK':
            print(f"Error: Could not select mailbox '{mailbox}': {status}", file=sys.stderr)
            mail.logout()
            return 0

        if verbose:
            print(f"Mailbox selected. Processing {len(uids)} message(s)...", file=sys.stderr)

        # Process each UID
        for uid in uids:
            try:
                # Fetch the full message
                status, msg_data = mail.uid('FETCH', uid, '(RFC822 FLAGS)')
                if status != 'OK' or not msg_data or msg_data[0] is None:
                    print(f"Warning: Message UID {uid} not found in {mailbox}", file=sys.stderr)
                    continue

                # Parse the message
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                if verbose:
                    # Display the full message
                    print_message_details(msg, uid)
                else:
                    print(f"Found message UID {uid}", file=sys.stderr)

                if dry_run:
                    if verbose:
                        print(f"[DRY RUN] Would delete this message\n", file=sys.stderr)
                    else:
                        print(f"[DRY RUN] Would delete message UID {uid} from {mailbox}")
                    deleted_count += 1
                else:
                    # Mark message as deleted
                    status, response = mail.uid('STORE', uid, '+FLAGS', '(\\Deleted)')
                    if status != 'OK':
                        print(f"Error: Could not mark UID {uid} as deleted: {status}", file=sys.stderr)
                        continue

                    if verbose:
                        print(f"✓ Marked UID {uid} as deleted\n", file=sys.stderr)
                    else:
                        print(f"Deleted message UID {uid} from {mailbox}")

                    deleted_count += 1

            except Exception as e:
                print(f"Error processing UID {uid}: {e}", file=sys.stderr)
                continue

        if not dry_run and deleted_count > 0:
            # Permanently remove messages marked as deleted
            if verbose:
                print("Expunging deleted messages...", file=sys.stderr)

            status, response = mail.expunge()
            if status != 'OK':
                print(f"Warning: Expunge may have failed: {status}", file=sys.stderr)
            elif verbose:
                print("Successfully expunged deleted messages.", file=sys.stderr)

        # Logout
        if verbose:
            print("Logging out...", file=sys.stderr)

        mail.logout()

        return deleted_count

    except imaplib.IMAP4.error as e:
        print(f"IMAP error: {e}", file=sys.stderr)
        return deleted_count
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return deleted_count


def main():
    parser = argparse.ArgumentParser(
        description='Delete messages from an IMAP email server by UID',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Delete a single message
  %(prog)s --server imap.gmail.com --user you@gmail.com --mailbox INBOX --uid 8133

  # Delete multiple messages
  %(prog)s --server imap.gmail.com --user you@gmail.com --mailbox INBOX --uid 8133 --uid 8134 --uid 8135

  # Preview deletion without actually deleting (dry run)
  %(prog)s --server imap.gmail.com --user you@gmail.com --mailbox INBOX --uid 8133 --dry-run

  # Delete from a specific folder with verbose output
  %(prog)s --server imap.gmail.com --user you@gmail.com --mailbox "Archive/2024" --uid 8133 --verbose
        """
    )

    # Connection settings
    parser.add_argument('--server', '-s', required=True,
                       help='IMAP server address (e.g., imap.gmail.com)')
    parser.add_argument('--port', '-p', type=int, default=993,
                       help='IMAP port (default: 993 for SSL)')
    parser.add_argument('--user', '-u', required=True,
                       help='Email username')
    parser.add_argument('--password', '-P',
                       help='Email password (will prompt if not provided)')
    parser.add_argument('--no-ssl', action='store_true',
                       help='Disable SSL/TLS (use plain IMAP on port 143)')

    # Message selection
    parser.add_argument('--mailbox', '-m', required=True,
                       help='Mailbox/folder name (e.g., INBOX, Sent, "Archive/2024")')
    parser.add_argument('--uid', action='append', dest='uids', required=True,
                       metavar='UID',
                       help='Message UID to delete (can be specified multiple times)')

    # Operation settings
    parser.add_argument('--dry-run', '-n', action='store_true',
                       help='Preview deletion without actually deleting')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output (prints full message content including headers and body)')
    parser.add_argument('--yes', '-y', action='store_true',
                       help='Skip confirmation prompt')

    args = parser.parse_args()

    # Get password if not provided
    password = args.password
    if not password:
        password = getpass.getpass(f"Password for {args.user}: ")

    # Confirmation prompt (unless --yes or --dry-run)
    if not args.yes and not args.dry_run:
        uid_list = ', '.join(args.uids)
        print(f"\nYou are about to DELETE {len(args.uids)} message(s) from '{args.mailbox}':", file=sys.stderr)
        print(f"  UIDs: {uid_list}", file=sys.stderr)
        print(f"  Server: {args.server}", file=sys.stderr)
        print(f"  User: {args.user}", file=sys.stderr)

        response = input("\nAre you sure you want to proceed? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("Deletion cancelled.", file=sys.stderr)
            sys.exit(0)

    # Perform deletion
    deleted_count = delete_messages(
        server=args.server,
        port=args.port,
        username=args.user,
        password=password,
        mailbox=args.mailbox,
        uids=args.uids,
        use_ssl=not args.no_ssl,
        dry_run=args.dry_run,
        verbose=args.verbose
    )

    # Summary
    if args.dry_run:
        print(f"\n[DRY RUN] Would have deleted {deleted_count} message(s)", file=sys.stderr)
    else:
        print(f"\nSuccessfully deleted {deleted_count} message(s)", file=sys.stderr)

    sys.exit(0 if deleted_count == len(args.uids) else 1)


if __name__ == '__main__':
    main()
