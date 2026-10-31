# Privacy

In 0.5.0 command-only mode (the default), the model receives the request, shell,
cwd, bounded filename/context metadata, permission flags and verified source paths.
It generates a command; file contents are not sent to it for command translation.
The optional structured planner retains bounded inspection, now gated by read
permission. Full/Developer profiles permit arbitrary commands/scripts with the
user's Windows rights, including network access; this is intentionally broader
than Balanced. The inference transport still stays on Ollama loopback, without
cloud fallback. Glass rendering uses only the application's own backdrop pixels;
upstream desktop/screen capture code is not shipped.

In 0.3.0, factual file answers can request bounded read-only inspection in the current directory or known user directories. Up to eight tool observations enter model context within a 12,000-character budget; text is redacted and capped at 6,000 characters per read, and listings are capped at 20 rows in model context. Reads support UTF-8 and UTF-16 BOM; binary files are rejected. Results identify truncation, partial listings and errors. Observations remain in request memory and are not saved as permanent history. Strict mode disables automatic inspection.

No cloud API, API keys, analytics or telemetry. Ollama requests go to fixed loopback `127.0.0.1:11434`, with proxies disabled. External networking occurs only during explicitly consented installation/model download and user-clicked terminal links or directly executed user programs.

Saved by default: configuration, install ownership/hashes, GUI preferences and bounded technical rotating logs. Permanent prompt/output history is off. The GUI holds a 4096-character recent-output tail and six context items in memory; ANSI control sequences are removed and at most 600 visible characters enter model context. The model sees up to four recent items capped at 400 characters, 40 directory entries and only relevant executable paths. External sessions persist at most six redactable AI summaries/requests in runtime files, validated against process creation time, expire after 30 minutes and are purged on later invocation. They never collect output from normal commands typed in external shells.

`Save AI history` opts into local JSONL history. Settings can clear permanent history and temporary sessions. Runtime ACL limits access to the current user and SYSTEM; profile backups can contain original user configuration and retain the user's existing permissions. Logs rotate at 1 MB with three backups; INFO logs never record terminal output, prompts or environment. Explicit debug can reveal technical tracebacks. Secret redaction covers common key/token/password assignments, Authorization headers and PEM private keys; it cannot guarantee detecting all secrets.

Ollama itself is separate software. Before sending any prompt, Chameleon checks `/api/show` and rejects remote model aliases or models without local metadata. Settings reject cloud tags. When Setup starts the local server it sets `OLLAMA_NO_CLOUD=1` and binds loopback. Chameleon's backend endpoint cannot be changed to a cloud address through settings. Downloads still require Internet; inference with an installed local model does not.
