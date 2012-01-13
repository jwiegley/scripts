#!/usr/sbin/dtrace -s

#pragma D option quiet
#pragma D option switchrate=10hz

dtrace:::BEGIN
{
	/*
	 * These are some of over 500 NT_STATES_* error codes defined in
	 * uts/common/smbsrv/ntstatus.h.  For more detail see MSDN and
	 * ntstatus.h in the MS DDK.
	 */
	ntstatus[0] = "SUCCESS";
	ntstatus[1] = "UNSUCCESSFUL";
	ntstatus[2] = "NOT_IMPLEMENTED";
	ntstatus[5] = "ACCESS_VIOLATION";
	ntstatus[15] = "NO_SUCH_FILE";
	ntstatus[17] = "END_OF_FILE";
	ntstatus[23] = "NO_MEMORY";
	ntstatus[29] = "ILLEGAL_INSTRUCTION";
	ntstatus[34] = "ACCESS_DENIED";
	ntstatus[50] = "DISK_CORRUPT_ERROR";
	ntstatus[61] = "DATA_ERROR";
	ntstatus[62] = "CRC_ERROR";
	ntstatus[68] = "QUOTA_EXCEEDED";
	ntstatus[127] = "DISK_FULL";
	ntstatus[152] = "FILE_INVALID";
	ntstatus[186] = "FILE_IS_A_DIRECTORY";
	ntstatus[258] = "FILE_CORRUPT_ERROR";
	ntstatus[259] = "NOT_A_DIRECTORY";
	ntstatus[291] = "FILE_DELETED";
	/* ...etc... */

	printf(" %-24s %3s %-19s %-16s %s\n", "CIFS EVENT", "ERR", "CODE",
	    "CLIENT", "PATHNAME");
}

smb:::op-*-start, smb:::op-*-done
/(this->sr = (struct smb_request *)arg0) && this->sr->smb_error.status != 0/
{
	this->err = this->sr->smb_error.status;
	this->str = ntstatus[this->err] != NULL ? ntstatus[this->err] : "?";
	    printf(" %-24s %3d %-19s %-16s %s\n", probename, this->err,
	this->str, args[0]->ci_remote, args[1]->soi_curpath);
}
