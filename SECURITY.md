# Security policy

The release candidate is under active validation. No security audit or hostile-code
sandbox certification is claimed. See [the threat model](docs/SECURITY_MODEL.md).

Report suspected vulnerabilities using GitHub's private vulnerability reporting
on this repository when available. Otherwise contact the repository owner through
their published GitHub contact details to arrange private disclosure. Do not post
credentials, exploit payloads targeting third parties or confidential repository
contents in public issues. If no private channel is available, open an issue
requesting a private contact without exploit details.

Include the affected version, OS/Python/runtime versions, a minimal synthetic
reproduction, expected boundary and observed behavior. No response-time SLA is
promised. Patch support is currently focused on the latest release candidate;
maintainers will assess backports after stable releases exist.

Analysis does not execute source. Approved verification executes code with host
permissions unless the operator separately provides isolation. Do not run unknown
code merely to reproduce a report on a normal workstation.
