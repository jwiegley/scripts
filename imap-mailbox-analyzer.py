#!/usr/bin/env python3
"""
IMAP Mailbox Analyzer
Scans all mailboxes in an IMAP account and generates a PostgreSQL script with detailed message metadata.
Supports incremental mode to only process new messages.
"""

import argparse
import email
from email.message import Message
import getpass
import imaplib
import json
import os
import re
import sys
from datetime import datetime
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional, Tuple, Any, Set

# Optional PostgreSQL support - only import when needed
try:
    import psycopg2
    import psycopg2.extras
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    psycopg2 = None


def decode_mime_header(header_value: str) -> Optional[str]:
    """Decode MIME-encoded header values.

    Args:
        header_value: Raw header value to decode

    Returns:
        Decoded string or None if empty
    """
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


def connect_postgres(db_host: str, db_port: int, db_name: str,
                     db_user: str, db_password: Optional[str] = None):
    """Connect to PostgreSQL database.

    Args:
        db_host: Database host
        db_port: Database port
        db_name: Database name
        db_user: Database username
        db_password: Database password (optional, will prompt if needed)

    Returns:
        Database connection object
    """
    if not PSYCOPG2_AVAILABLE:
        print("Error: psycopg2 is not installed. Install it with:", file=sys.stderr)
        print("  pip install psycopg2-binary", file=sys.stderr)
        sys.exit(1)

    # Get password if not provided
    if not db_password:
        db_password = os.environ.get('PGPASSWORD')
        if not db_password:
            db_password = getpass.getpass(f"PostgreSQL password for {db_user}@{db_host}: ")

    try:
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password
        )
        print(f"Connected to PostgreSQL: {db_user}@{db_host}:{db_port}/{db_name}", file=sys.stderr)
        return conn
    except psycopg2.Error as e:
        print(f"PostgreSQL connection failed: {e}", file=sys.stderr)
        sys.exit(1)


def get_known_uids(conn, mailbox: str) -> Set[str]:
    """Get set of known UIDs for a mailbox from the database.

    Args:
        conn: Database connection
        mailbox: Mailbox name

    Returns:
        Set of known UIDs
    """
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT uid FROM email_messages WHERE mailbox = %s",
                (mailbox,)
            )
            return {row[0] for row in cur.fetchall()}
    except psycopg2.Error as e:
        print(f"Warning: Error querying known UIDs for {mailbox}: {e}", file=sys.stderr)
        return set()


def table_exists(conn, table_name: str = 'email_messages') -> bool:
    """Check if table exists in the database.

    Args:
        conn: Database connection
        table_name: Name of table to check

    Returns:
        True if table exists
    """
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s)",
                (table_name,)
            )
            return cur.fetchone()[0]
    except psycopg2.Error as e:
        print(f"Error checking if table exists: {e}", file=sys.stderr)
        return False


def create_table_if_needed(conn, out) -> bool:
    """Create email_messages table if it doesn't exist.

    Args:
        conn: Database connection
        out: Output file handle for SQL

    Returns:
        True if table was created, False if it already existed
    """
    if table_exists(conn):
        return False

    print("Table email_messages doesn't exist, creating it...", file=sys.stderr)

    # Define CREATE TABLE statement
    create_table_sql = """CREATE TABLE IF NOT EXISTS email_messages (
    mailbox TEXT NOT NULL,
    uid TEXT NOT NULL,
    message_id TEXT NOT NULL,
    flags TEXT[],
    internal_date TIMESTAMP,
    rfc822_size BIGINT,
    headers JSONB NOT NULL,
    body_length INTEGER NOT NULL DEFAULT 0,
    attachment_count INTEGER NOT NULL DEFAULT 0,
    attachment_total_size BIGINT NOT NULL DEFAULT 0,
    scan_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (mailbox, uid)
);"""

    # Define index creation statements
    index_statements = [
        "CREATE INDEX IF NOT EXISTS idx_email_messages_message_id ON email_messages(message_id);",
        "CREATE INDEX IF NOT EXISTS idx_email_messages_mailbox ON email_messages(mailbox);",
        "CREATE INDEX IF NOT EXISTS idx_email_messages_internal_date ON email_messages(internal_date);",
        "CREATE INDEX IF NOT EXISTS idx_email_messages_flags ON email_messages USING GIN(flags);",
        "CREATE INDEX IF NOT EXISTS idx_email_messages_scan_date ON email_messages(scan_date);",
        "CREATE INDEX IF NOT EXISTS idx_email_messages_headers ON email_messages USING GIN(headers);"
    ]

    # Execute CREATE TABLE and indexes against the database
    try:
        with conn.cursor() as cur:
            # Create table
            cur.execute(create_table_sql)
            print("  Created table in database", file=sys.stderr)

            # Create indexes
            for idx_sql in index_statements:
                cur.execute(idx_sql)
            print("  Created indexes in database", file=sys.stderr)

        # Commit the transaction
        conn.commit()
        print("  Table creation committed to database", file=sys.stderr)
    except psycopg2.Error as e:
        print(f"Error creating table in database: {e}", file=sys.stderr)
        conn.rollback()
        sys.exit(1)

    # Also write to SQL output file for documentation
    out.write("-- Creating email_messages table\n")
    out.write(create_table_sql)
    out.write("\n\n")
    out.write("-- Create indexes for common queries\n")
    for idx_sql in index_statements:
        out.write(idx_sql)
        out.write("\n")
    out.write("\n")

    return True


def connect_imap(host: Optional[str] = None,
                 port: int = 993,
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 use_ssl: bool = True,
                 process: Optional[str] = None) -> imaplib.IMAP4:
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


def parse_mailbox_list(list_response: List[bytes]) -> List[Tuple[List[str], str]]:
    r"""Parse IMAP LIST response to extract flags and mailbox names.

    Args:
        list_response: Raw LIST response from IMAP server

    Returns:
        List of tuples: [(flags, mailbox_name), ...]
        where flags is a list of flag strings (e.g., ['\\Noselect', '\\HasChildren'])

    Examples:
        b'(\\HasNoChildren \\UnMarked) "/" Good' -> (['\\HasNoChildren', '\\UnMarked'], 'Good')
        b'(\\HasNoChildren) "/" INBOX' -> (['\\HasNoChildren'], 'INBOX')
        b'(\\Noselect) "/" Archive/2024' -> (['\\Noselect'], 'Archive/2024')
    """
    mailboxes = []

    for mailbox_line in list_response:
        # Handle both bytes and string responses
        if isinstance(mailbox_line, bytes):
            mailbox_line = mailbox_line.decode('utf-8', errors='replace')

        # IMAP LIST response format: (flags) "delimiter" mailbox_name
        # Note: mailbox_name is typically UNQUOTED (unless it contains special characters)
        # Examples:
        #   b'(\\HasNoChildren \\UnMarked) "/" Good'
        #   b'(\\HasNoChildren) "/" INBOX'
        #   b'(\\Noselect) "/" Archive/2024'

        # Extract flags - they're in parentheses at the start
        flags = []
        flags_match = re.search(r'\(([^)]*)\)', mailbox_line)
        if flags_match:
            flags_content = flags_match.group(1).strip()
            if flags_content:
                flags = [f.strip() for f in flags_content.split() if f.strip()]

        # Extract mailbox name - it comes after the delimiter (quoted string)
        # Pattern: (flags) "delimiter" mailbox_name
        # Use regex to capture everything after the closing parenthesis and delimiter
        #
        # Match pattern: ) "X" mailbox_name  where X is the delimiter (usually "/")
        # The mailbox name can be quoted or unquoted
        mailbox_name_match = re.match(r'\([^)]*\)\s+"[^"]*"\s+(.+)$', mailbox_line)
        if mailbox_name_match:
            mailbox_name = mailbox_name_match.group(1).strip()

            # If the name is quoted, remove the quotes
            if mailbox_name.startswith('"') and mailbox_name.endswith('"'):
                mailbox_name = mailbox_name[1:-1]
        else:
            # Fallback: try alternate format with NIL delimiter (no quoted delimiter)
            # Format: (flags) NIL mailbox_name
            nil_match = re.match(r'\([^)]*\)\s+NIL\s+(.+)$', mailbox_line)
            if nil_match:
                mailbox_name = nil_match.group(1).strip()
                if mailbox_name.startswith('"') and mailbox_name.endswith('"'):
                    mailbox_name = mailbox_name[1:-1]
            else:
                # Can't parse this line, skip it
                continue

        mailboxes.append((flags, mailbox_name))

    return mailboxes


def get_mailbox_list(imap: imaplib.IMAP4, limit_mailbox: Optional[str] = None) -> List[str]:
    r"""Get list of all mailboxes to scan.

    Args:
        imap: IMAP connection object
        limit_mailbox: Optional mailbox name to limit scanning to

    Returns:
        List of selectable mailbox names (filtered to exclude \Noselect and invalid names)
    """
    try:
        if limit_mailbox:
            return [limit_mailbox]

        status, mailboxes = imap.list()
        if status != 'OK':
            print("Failed to retrieve mailbox list", file=sys.stderr)
            sys.exit(1)

        # Parse the LIST response
        parsed_mailboxes = parse_mailbox_list(mailboxes)

        # Filter to only include valid, selectable mailboxes
        mailbox_names = []
        for flags, mailbox_name in parsed_mailboxes:
            # Skip mailboxes with \Noselect flag (these are hierarchy placeholders)
            if '\\Noselect' in flags or '\\NoSelect' in flags:
                print(f"  Skipping \\Noselect mailbox: {mailbox_name}", file=sys.stderr)
                continue

            # Skip invalid mailbox names
            if not mailbox_name or len(mailbox_name.strip()) == 0:
                print(f"  Skipping empty mailbox name", file=sys.stderr)
                continue

            # Skip single-character names that are likely delimiters
            if len(mailbox_name) == 1 and mailbox_name in ['/', '.', '\\']:
                print(f"  Skipping delimiter: {mailbox_name}", file=sys.stderr)
                continue

            mailbox_names.append(mailbox_name)

        return sorted(mailbox_names)
    except Exception as e:
        print(f"Error getting mailbox list: {e}", file=sys.stderr)
        sys.exit(1)


def extract_all_headers(msg: Message) -> Dict[str, List[str]]:
    """Extract all headers from a message, preserving duplicates.

    Args:
        msg: Email message object

    Returns:
        Dictionary mapping header names to lists of values
    """
    headers = {}

    for header_name in msg.keys():
        if header_name not in headers:
            headers[header_name] = []

        # Get all values for this header (handles duplicates like Received)
        for value in msg.get_all(header_name, []):
            try:
                decoded_value = decode_mime_header(value)
                if decoded_value:
                    headers[header_name].append(decoded_value)
            except Exception as e:
                # Fallback to raw value if decoding fails
                print(f"Warning: Failed to decode header {header_name}: {e}", file=sys.stderr)
                headers[header_name].append(str(value))

    return headers


def calculate_body_length(msg: Message) -> int:
    """Calculate total length of text and HTML body parts.

    Args:
        msg: Email message object

    Returns:
        Total body length in bytes
    """
    total_length = 0

    try:
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type in ('text/plain', 'text/html'):
                    payload = part.get_payload(decode=True)
                    if payload:
                        total_length += len(payload)
        else:
            # Single part message
            content_type = msg.get_content_type()
            if content_type in ('text/plain', 'text/html'):
                payload = msg.get_payload(decode=True)
                if payload:
                    total_length += len(payload)
    except Exception as e:
        print(f"Warning: Error calculating body length: {e}", file=sys.stderr)

    return total_length


def get_attachment_info(msg: Message) -> Tuple[int, int]:
    """Get attachment count and total size.

    Args:
        msg: Email message object

    Returns:
        Tuple of (attachment_count, total_attachment_size)
    """
    attachment_count = 0
    total_size = 0

    try:
        if msg.is_multipart():
            for part in msg.walk():
                # Skip multipart containers
                if part.get_content_maintype() == 'multipart':
                    continue

                # Check for attachment disposition
                # Convert Header object to string before using string methods
                disposition = str(part.get('Content-Disposition', ''))
                filename = part.get_filename()

                # Count as attachment if:
                # 1. Has attachment disposition, OR
                # 2. Has inline disposition with filename, OR
                # 3. Has filename but no disposition (common pattern)
                is_attachment = (
                    'attachment' in disposition.lower() or
                    ('inline' in disposition.lower() and filename) or
                    (filename and not disposition and part.get_content_type() not in ('text/plain', 'text/html'))
                )

                if is_attachment:
                    attachment_count += 1
                    payload = part.get_payload(decode=True)
                    if payload:
                        total_size += len(payload)
    except Exception as e:
        print(f"Warning: Error processing attachments: {e}", file=sys.stderr)

    return attachment_count, total_size


def parse_imap_flags(flags_bytes: bytes) -> List[str]:
    """Parse IMAP flags from FETCH response.

    Args:
        flags_bytes: Raw flags data from IMAP

    Returns:
        List of flag strings
    """
    try:
        # Convert bytes to string
        if isinstance(flags_bytes, bytes):
            flags_str = flags_bytes.decode('utf-8', errors='replace')
        else:
            flags_str = str(flags_bytes)

        # Extract flags from parentheses: (\\Seen \\Flagged) -> ['\\Seen', '\\Flagged']
        match = re.search(r'\(([^)]*)\)', flags_str)
        if match:
            flags_content = match.group(1).strip()
            if flags_content:
                return [f.strip() for f in flags_content.split() if f.strip()]
        return []
    except Exception as e:
        print(f"Warning: Error parsing flags: {e}", file=sys.stderr)
        return []


def parse_imap_internaldate(date_bytes: bytes) -> Optional[str]:
    """Parse IMAP INTERNALDATE to ISO format.

    Args:
        date_bytes: Raw INTERNALDATE from IMAP

    Returns:
        ISO formatted timestamp string or None
    """
    try:
        # Convert bytes to string
        if isinstance(date_bytes, bytes):
            date_str = date_bytes.decode('utf-8', errors='replace')
        else:
            date_str = str(date_bytes)

        # Extract date from quotes: "17-Jul-1996 02:44:25 -0700"
        match = re.search(r'"([^"]+)"', date_str)
        if match:
            date_str = match.group(1)

        # Parse to datetime object
        dt = parsedate_to_datetime(date_str)
        return dt.isoformat()
    except Exception as e:
        print(f"Warning: Error parsing INTERNALDATE '{date_bytes}': {e}", file=sys.stderr)
        return None


def analyze_message(msg_data: bytes, mailbox: str, uid: str, flags: List[str],
                    internal_date: Optional[str], rfc822_size: Optional[int]) -> Optional[Dict[str, Any]]:
    """Parse and analyze a single email message.

    Args:
        msg_data: Raw message data
        mailbox: Name of the mailbox containing the message
        uid: IMAP UID of the message
        flags: List of IMAP flags
        internal_date: IMAP INTERNALDATE in ISO format
        rfc822_size: RFC822.SIZE from IMAP

    Returns:
        Dictionary with message metadata or None on error
    """
    try:
        msg = email.message_from_bytes(msg_data)

        # Extract Message-ID
        message_id = msg.get('Message-ID', '<no-message-id>')

        # Extract all headers
        headers = extract_all_headers(msg)

        # Calculate body length
        body_length = calculate_body_length(msg)

        # Get attachment info
        attachment_count, attachment_size = get_attachment_info(msg)

        return {
            'message_id': message_id,
            'mailbox': mailbox,
            'uid': uid,
            'flags': flags,
            'internal_date': internal_date,
            'rfc822_size': rfc822_size,
            'headers': headers,
            'body_length': body_length,
            'attachment_count': attachment_count,
            'attachment_total_size': attachment_size
        }
    except Exception as e:
        print(f"Warning: Error analyzing message: {e}", file=sys.stderr)
        return None


def escape_sql_string(value: Optional[str]) -> str:
    """Escape a string for PostgreSQL.

    Args:
        value: String to escape

    Returns:
        SQL-safe escaped string with quotes or NULL
    """
    if value is None:
        return 'NULL'

    # Escape single quotes by doubling them
    escaped = value.replace("'", "''")
    # Escape backslashes
    escaped = escaped.replace("\\", "\\\\")

    return f"'{escaped}'"


def format_json_for_sql(data: Dict) -> str:
    """Format a dictionary as JSONB for PostgreSQL.

    Args:
        data: Dictionary to convert

    Returns:
        SQL-safe JSONB string
    """
    # Create valid JSON (backslashes are already properly escaped by json.dumps)
    json_str = json.dumps(data, ensure_ascii=False)

    # For SQL string literals, we only need to escape single quotes
    # Do NOT escape backslashes - they're already correct in the JSON!
    escaped = json_str.replace("'", "''")
    return f"'{escaped}'"


def format_array_for_sql(values: List[str]) -> str:
    """Format a list of strings as a PostgreSQL array.

    Args:
        values: List of strings to convert

    Returns:
        SQL-safe array string
    """
    if not values:
        return "ARRAY[]::TEXT[]"

    # Escape each value and quote it
    escaped_values = [escape_sql_string(v) for v in values]
    return f"ARRAY[{', '.join(escaped_values)}]"


def scan_all_mailboxes(imap: imaplib.IMAP4,
                       mailbox_names: List[str],
                       output_file: Optional[str] = None,
                       incremental: bool = False,
                       db_conn=None) -> Dict[str, Any]:
    """Scan all mailboxes and generate PostgreSQL script.

    Args:
        imap: IMAP connection object
        mailbox_names: List of mailboxes to scan
        output_file: Optional output file path (None for stdout)
        incremental: Enable incremental mode (only process new messages)
        db_conn: Database connection (required for incremental mode)

    Returns:
        Dictionary with scan statistics
    """
    # Open output file or use stdout
    if output_file:
        try:
            out = open(output_file, 'w', encoding='utf-8')
            print(f"Writing SQL output to: {output_file}", file=sys.stderr)
        except Exception as e:
            print(f"Error opening output file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        out = sys.stdout

    try:
        # Write SQL header
        out.write("-- IMAP Mailbox Analysis\n")
        out.write(f"-- Generated: {datetime.now().isoformat()}\n")
        if incremental:
            out.write("-- Mode: Incremental (only new messages)\n")
        else:
            out.write("-- Mode: Full scan\n")
        out.write("-- \n\n")

        out.write("BEGIN;\n\n")

        # Handle table creation based on mode
        if incremental:
            # In incremental mode, create table if needed
            if db_conn:
                create_table_if_needed(db_conn, out)
        else:
            # In full mode, drop and recreate table
            out.write("DROP TABLE IF EXISTS email_messages CASCADE;\n\n")
            out.write("CREATE TABLE email_messages (\n")
            out.write("    mailbox TEXT NOT NULL,\n")
            out.write("    uid TEXT NOT NULL,\n")
            out.write("    message_id TEXT NOT NULL,\n")
            out.write("    flags TEXT[],\n")
            out.write("    internal_date TIMESTAMP,\n")
            out.write("    rfc822_size BIGINT,\n")
            out.write("    headers JSONB NOT NULL,\n")
            out.write("    body_length INTEGER NOT NULL DEFAULT 0,\n")
            out.write("    attachment_count INTEGER NOT NULL DEFAULT 0,\n")
            out.write("    attachment_total_size BIGINT NOT NULL DEFAULT 0,\n")
            out.write("    scan_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,\n")
            out.write("    PRIMARY KEY (mailbox, uid)\n")
            out.write(");\n\n")
            out.write("-- Create indexes for common queries\n")
            out.write("CREATE INDEX idx_email_messages_message_id ON email_messages(message_id);\n")
            out.write("CREATE INDEX idx_email_messages_mailbox ON email_messages(mailbox);\n")
            out.write("CREATE INDEX idx_email_messages_internal_date ON email_messages(internal_date);\n")
            out.write("CREATE INDEX idx_email_messages_flags ON email_messages USING GIN(flags);\n")
            out.write("CREATE INDEX idx_email_messages_scan_date ON email_messages(scan_date);\n")
            out.write("CREATE INDEX idx_email_messages_headers ON email_messages USING GIN(headers);\n\n")

        # Statistics
        stats = {
            'total_mailboxes': len(mailbox_names),
            'total_messages': 0,
            'total_body_bytes': 0,
            'total_attachments': 0,
            'total_attachment_bytes': 0,
            'errors': 0,
            'duplicates': 0,
            'already_in_db': 0,
            'new_messages': 0,
            'skipped_messages': 0
        }

        seen_message_keys = set()  # Track (mailbox, uid) pairs
        scan_date = datetime.now().isoformat()

        # Scan each mailbox
        for mailbox_idx, mailbox in enumerate(mailbox_names, 1):
            print(f"\nScanning mailbox {mailbox_idx} of {stats['total_mailboxes']}: {mailbox}",
                  file=sys.stderr)

            try:
                # Get known UIDs for this mailbox if in incremental mode
                known_uids = set()
                if incremental and db_conn:
                    known_uids = get_known_uids(db_conn, mailbox)
                    print(f"  Found {len(known_uids)} existing messages in database", file=sys.stderr)

                # Select mailbox (readonly)
                status, messages = imap.select(mailbox, readonly=True)
                if status != 'OK':
                    print(f"  Failed to select mailbox: {mailbox}", file=sys.stderr)
                    stats['errors'] += 1
                    continue

                # Get all message IDs
                status, message_ids = imap.search(None, 'ALL')
                if status != 'OK':
                    print(f"  Failed to search messages in {mailbox}", file=sys.stderr)
                    stats['errors'] += 1
                    continue

                msg_id_list = message_ids[0].split()
                total_in_mailbox = len(msg_id_list)

                print(f"  Found {total_in_mailbox} messages", file=sys.stderr)

                # Count messages to process and skip
                messages_to_process = []
                messages_to_skip = 0

                # First pass: identify which messages to process
                for idx, msg_id in enumerate(msg_id_list, 1):
                    try:
                        # Fetch UID only first to check if we need to process this message
                        status, msg_data = imap.fetch(msg_id, '(UID)')

                        if status != 'OK' or not msg_data or not msg_data[0]:
                            stats['errors'] += 1
                            continue

                        # Extract UID
                        fetch_str = msg_data[0].decode('utf-8', errors='replace') if isinstance(msg_data[0], bytes) else str(msg_data[0])
                        uid_match = re.search(r'UID (\d+)', fetch_str)
                        uid = uid_match.group(1) if uid_match else msg_id.decode()

                        # Check if we should skip this message (incremental mode)
                        if incremental and uid in known_uids:
                            messages_to_skip += 1
                            stats['already_in_db'] += 1
                            continue

                        messages_to_process.append(msg_id)

                    except Exception as e:
                        print(f"  Warning: Error checking message {msg_id.decode()}: {e}",
                              file=sys.stderr)
                        stats['errors'] += 1
                        continue

                # Show skip/process summary
                if incremental:
                    print(f"  Skipping {messages_to_skip} known messages, processing {len(messages_to_process)} new messages...",
                          file=sys.stderr)

                # Second pass: process messages
                for idx, msg_id in enumerate(messages_to_process, 1):
                    try:
                        # Fetch complete message with metadata
                        # Use BODY.PEEK to avoid marking messages as seen
                        status, msg_data = imap.fetch(msg_id, '(UID FLAGS INTERNALDATE RFC822.SIZE BODY.PEEK[HEADER])')

                        if status != 'OK' or not msg_data or not msg_data[0]:
                            print(f"  Warning: Failed to fetch message {msg_id.decode()}",
                                  file=sys.stderr)
                            stats['errors'] += 1
                            continue

                        # Parse the FETCH response
                        # The response is a tuple like: (b'1 (UID 1234 FLAGS (\\Seen) ...)', b'header data')
                        fetch_response = msg_data[0]
                        if isinstance(fetch_response, tuple):
                            fetch_parts = fetch_response[0]
                            header_data = fetch_response[1]
                        else:
                            # Sometimes the response format is different
                            fetch_parts = fetch_response
                            header_data = None

                        # Convert to string for parsing
                        if isinstance(fetch_parts, bytes):
                            fetch_str = fetch_parts.decode('utf-8', errors='replace')
                        else:
                            fetch_str = str(fetch_parts)

                        # Extract UID
                        uid_match = re.search(r'UID (\d+)', fetch_str)
                        uid = uid_match.group(1) if uid_match else msg_id.decode()

                        # Extract FLAGS
                        flags_match = re.search(r'FLAGS \(([^)]*)\)', fetch_str)
                        flags = []
                        if flags_match:
                            flags_content = flags_match.group(1).strip()
                            if flags_content:
                                flags = [f.strip() for f in flags_content.split() if f.strip()]

                        # Extract INTERNALDATE
                        internaldate_match = re.search(r'INTERNALDATE "([^"]+)"', fetch_str)
                        internal_date = None
                        if internaldate_match:
                            try:
                                dt = parsedate_to_datetime(internaldate_match.group(1))
                                internal_date = dt.isoformat()
                            except Exception as e:
                                print(f"  Warning: Failed to parse INTERNALDATE: {e}", file=sys.stderr)

                        # Extract RFC822.SIZE
                        size_match = re.search(r'RFC822\.SIZE (\d+)', fetch_str)
                        rfc822_size = int(size_match.group(1)) if size_match else None

                        # Check for duplicate (mailbox, uid) pair
                        message_key = (mailbox, uid)
                        if message_key in seen_message_keys:
                            stats['duplicates'] += 1
                            continue

                        seen_message_keys.add(message_key)

                        # Now fetch the full message body for analysis
                        status, body_data = imap.fetch(msg_id, '(BODY.PEEK[])')
                        if status != 'OK' or not body_data or not body_data[0]:
                            print(f"  Warning: Failed to fetch message body {uid}",
                                  file=sys.stderr)
                            stats['errors'] += 1
                            continue

                        # Extract the raw message
                        if isinstance(body_data[0], tuple):
                            raw_message = body_data[0][1]
                        else:
                            raw_message = body_data[0]

                        # Parse message
                        message_info = analyze_message(raw_message, mailbox, uid, flags,
                                                      internal_date, rfc822_size)

                        if not message_info:
                            stats['errors'] += 1
                            continue

                        # Write INSERT statement
                        out.write("INSERT INTO email_messages (mailbox, uid, message_id, flags, ")
                        out.write("internal_date, rfc822_size, headers, body_length, ")
                        out.write("attachment_count, attachment_total_size, scan_date)\n")
                        out.write("VALUES (")
                        out.write(f"{escape_sql_string(message_info['mailbox'])}, ")
                        out.write(f"{escape_sql_string(message_info['uid'])}, ")
                        out.write(f"{escape_sql_string(message_info['message_id'])}, ")
                        out.write(f"{format_array_for_sql(message_info['flags'])}, ")
                        if message_info['internal_date']:
                            out.write(f"'{message_info['internal_date']}', ")
                        else:
                            out.write("NULL, ")
                        if message_info['rfc822_size'] is not None:
                            out.write(f"{message_info['rfc822_size']}, ")
                        else:
                            out.write("NULL, ")
                        out.write(f"{format_json_for_sql(message_info['headers'])}::jsonb, ")
                        out.write(f"{message_info['body_length']}, ")
                        out.write(f"{message_info['attachment_count']}, ")
                        out.write(f"{message_info['attachment_total_size']}, ")
                        out.write(f"'{scan_date}'")
                        out.write(");\n")

                        # Update statistics
                        stats['total_messages'] += 1
                        stats['new_messages'] += 1
                        stats['total_body_bytes'] += message_info['body_length']
                        stats['total_attachments'] += message_info['attachment_count']
                        stats['total_attachment_bytes'] += message_info['attachment_total_size']

                    except Exception as e:
                        print(f"  Warning: Error processing message {msg_id.decode()}: {e}",
                              file=sys.stderr)
                        stats['errors'] += 1
                        continue

                    # Progress indicator
                    if idx % 100 == 0:
                        print(f"  Processed {idx}/{len(messages_to_process)} messages...",
                              file=sys.stderr)

                print(f"  Completed: {len(messages_to_process)} messages processed",
                      file=sys.stderr)

                # Update skipped messages stat
                stats['skipped_messages'] += messages_to_skip

            except Exception as e:
                print(f"  Error processing mailbox {mailbox}: {e}", file=sys.stderr)
                stats['errors'] += 1
                continue

        # Write commit
        out.write("\nCOMMIT;\n\n")

        # Write statistics as comments
        out.write("-- Scan Statistics\n")
        out.write(f"-- Total mailboxes scanned: {stats['total_mailboxes']}\n")
        out.write(f"-- Total messages processed: {stats['total_messages']}\n")
        if incremental:
            out.write(f"-- Messages already in DB: {stats['already_in_db']}\n")
            out.write(f"-- New messages processed: {stats['new_messages']}\n")
            out.write(f"-- Skipped messages: {stats['skipped_messages']}\n")
        out.write(f"-- Duplicate messages skipped: {stats['duplicates']}\n")
        out.write(f"-- Total body size: {stats['total_body_bytes']:,} bytes ({stats['total_body_bytes']/1024/1024:.2f} MB)\n")
        out.write(f"-- Total attachments: {stats['total_attachments']}\n")
        out.write(f"-- Total attachment size: {stats['total_attachment_bytes']:,} bytes ({stats['total_attachment_bytes']/1024/1024:.2f} MB)\n")
        out.write(f"-- Errors encountered: {stats['errors']}\n")

        return stats

    finally:
        if output_file:
            out.close()


def print_summary(stats: Dict[str, Any], incremental: bool = False):
    """Print scan summary to stderr.

    Args:
        stats: Statistics dictionary from scan
        incremental: Whether this was an incremental scan
    """
    print("\n" + "="*60, file=sys.stderr)
    print("SCAN SUMMARY", file=sys.stderr)
    print("="*60, file=sys.stderr)
    print(f"Mailboxes scanned:        {stats['total_mailboxes']}", file=sys.stderr)
    print(f"Messages processed:       {stats['total_messages']}", file=sys.stderr)

    if incremental:
        print(f"Messages already in DB:   {stats['already_in_db']}", file=sys.stderr)
        print(f"New messages processed:   {stats['new_messages']}", file=sys.stderr)
        print(f"Skipped messages:         {stats['skipped_messages']}", file=sys.stderr)

    print(f"Duplicate messages:       {stats['duplicates']}", file=sys.stderr)
    print(f"Total body size:          {stats['total_body_bytes']:,} bytes ({stats['total_body_bytes']/1024/1024:.2f} MB)",
          file=sys.stderr)
    print(f"Total attachments:        {stats['total_attachments']}", file=sys.stderr)
    print(f"Total attachment size:    {stats['total_attachment_bytes']:,} bytes ({stats['total_attachment_bytes']/1024/1024:.2f} MB)",
          file=sys.stderr)

    if stats['errors'] > 0:
        print(f"Errors encountered:       {stats['errors']}", file=sys.stderr)

    print("="*60, file=sys.stderr)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze all IMAP mailboxes and generate PostgreSQL import script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full scan - Network mode with prompted password
  %(prog)s -H mail.example.com -u john@example.com -o mailbox_data.sql

  # Full scan - Scan with environment variable password
  export IMAP_PASSWORD="mypassword"
  %(prog)s -H mail.example.com -u john@example.com -o output.sql

  # Local process mode - Access Dovecot directly
  sudo -u johnw %(prog)s --process "/nix/store/.../libexec/dovecot/imap" -o output.sql

  # Incremental mode - Only process new messages
  %(prog)s -H localhost -u johnw --incremental --db-name maildb --db-user postgres -o new_messages.sql
  psql -d maildb -f new_messages.sql

  # First incremental run (creates table automatically)
  %(prog)s -H localhost -u johnw --incremental --db-name maildb --db-user postgres -o initial.sql

  # Scan only specific mailbox
  %(prog)s -H localhost -u johnw --limit-mailbox INBOX -o inbox.sql

  # Output to stdout (redirect to file)
  %(prog)s -H localhost -u johnw > mailbox_data.sql

  # Import into PostgreSQL
  %(prog)s -H localhost -u johnw -o data.sql
  psql -d mydb -f data.sql

Incremental Mode:
  - Use --incremental to only process messages not already in the database
  - Requires --db-name and --db-user to query existing messages
  - If table doesn't exist, it will be created automatically
  - Generates INSERT statements only (no DROP/CREATE)
  - Subsequent runs add only new messages to the database
  - Use environment variables for credentials: PGPASSWORD, PGHOST, PGPORT, PGUSER

Usage Notes:
  - The script scans ALL mailboxes unless --limit-mailbox is specified
  - Primary key is (mailbox, uid) to capture each message instance
  - Captures IMAP metadata: UID, FLAGS, INTERNALDATE, RFC822.SIZE
  - All headers are stored as JSONB for flexible querying
  - Progress is shown on stderr, SQL output on stdout (or -o file)
  - Use transactions for safe import (included in generated SQL)
  - BODY.PEEK is used to avoid marking messages as seen
        """
    )

    # IMAP connection options
    imap_group = parser.add_argument_group('IMAP Connection')
    imap_group.add_argument('-H', '--host',
                            help='IMAP server hostname (network mode)')
    imap_group.add_argument('-p', '--port', type=int, default=993,
                            help='IMAP server port (network mode, default: 993)')
    imap_group.add_argument('-u', '--username',
                            help='IMAP username (network mode)')
    imap_group.add_argument('-P', '--password',
                            help='IMAP password (network mode, will prompt if not provided)')
    imap_group.add_argument('--process',
                            help='IMAP process to spawn for local access (e.g., /usr/libexec/dovecot/imap)')
    imap_group.add_argument('--no-ssl', action='store_true',
                            help='Disable SSL/TLS (network mode, not recommended)')

    # Database options for incremental mode
    db_group = parser.add_argument_group('PostgreSQL Database (for incremental mode)')
    db_group.add_argument('--incremental', action='store_true',
                          help='Enable incremental mode (only process new messages)')
    db_group.add_argument('--db-host', default=None,
                          help='Database host (default: from PGHOST or localhost)')
    db_group.add_argument('--db-port', type=int, default=None,
                          help='Database port (default: from PGPORT or 5432)')
    db_group.add_argument('--db-name',
                          help='Database name (required for incremental mode, or use PGDATABASE)')
    db_group.add_argument('--db-user',
                          help='Database username (required for incremental mode, or use PGUSER)')
    db_group.add_argument('--db-password',
                          help='Database password (optional, will use PGPASSWORD or prompt)')

    # Output options
    output_group = parser.add_argument_group('Output Options')
    output_group.add_argument('-o', '--output',
                              help='Output SQL file (default: stdout)')
    output_group.add_argument('--limit-mailbox',
                              help='Scan only this specific mailbox (default: scan all mailboxes)')

    args = parser.parse_args()

    # Validate incremental mode requirements
    if args.incremental:
        # Get database name from args or environment
        db_name = args.db_name or os.environ.get('PGDATABASE')
        db_user = args.db_user or os.environ.get('PGUSER')

        if not db_name:
            print("Error: --db-name is required for incremental mode (or set PGDATABASE environment variable)",
                  file=sys.stderr)
            sys.exit(1)

        if not db_user:
            print("Error: --db-user is required for incremental mode (or set PGUSER environment variable)",
                  file=sys.stderr)
            sys.exit(1)

        # Get database connection parameters
        db_host = args.db_host or os.environ.get('PGHOST') or 'localhost'
        db_port = args.db_port or (int(os.environ.get('PGPORT')) if os.environ.get('PGPORT') else 5432)
        db_password = args.db_password  # Will be fetched later if needed

    # Validate IMAP mode selection
    if args.process:
        # Local process mode
        if args.host or args.username or args.password:
            print("Warning: --host, --username, and --password are ignored when using --process",
                  file=sys.stderr)
        password = None
        host = None
        username = None
    else:
        # Network mode - host and username required
        if not args.host:
            args.host = 'localhost'
        if not args.username:
            print("Error: --username is required for network mode (or use --process for local mode)",
                  file=sys.stderr)
            sys.exit(1)

        # Get password for network mode
        password = args.password or os.environ.get('IMAP_PASSWORD')
        if not password:
            password = getpass.getpass(f"IMAP password for {args.username}: ")

        host = args.host
        username = args.username

    # Connect to database if in incremental mode
    db_conn = None
    if args.incremental:
        print("\n=== Incremental Mode Enabled ===", file=sys.stderr)
        db_conn = connect_postgres(
            db_host=db_host,
            db_port=db_port,
            db_name=db_name,
            db_user=db_user,
            db_password=db_password
        )

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
        # Get mailbox list
        print("\nRetrieving mailbox list...", file=sys.stderr)
        mailbox_names = get_mailbox_list(imap, args.limit_mailbox)
        print(f"Found {len(mailbox_names)} mailbox(es) to scan", file=sys.stderr)

        # Scan all mailboxes
        stats = scan_all_mailboxes(
            imap,
            mailbox_names,
            args.output,
            incremental=args.incremental,
            db_conn=db_conn
        )

        # Print summary
        print_summary(stats, incremental=args.incremental)

        if args.output:
            print(f"\nSQL script written to: {args.output}", file=sys.stderr)
            print(f"Import with: psql -d {db_name if args.incremental else 'your_database'} -f {args.output}", file=sys.stderr)

    finally:
        # Cleanup
        try:
            imap.close()
            imap.logout()
        except:
            pass

        if db_conn:
            try:
                db_conn.close()
            except:
                pass


if __name__ == '__main__':
    main()
