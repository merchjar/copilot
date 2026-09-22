# Deliver the report that was actually written

The shell's working directory and the chat client's project root may differ. This
happens in a full Copilot as well as a standalone skill, especially after running a
helper inside `skills/branded-review`. A relative link can point to a nonexistent
file even though report generation succeeded.

1. Choose the output location within the user's accessible workspace. Resolve it
   to an absolute path before generation and retain that path across commands.
   Folder changes do not change the saved report location.
2. Read `report_artifact` from the upload, connected or privacy report helper's
   output. It verifies the file is readable and nonempty and returns its absolute
   path, byte count, hash and a ready-to-use local Markdown link. This is a file
   check, not proof that the client's preview rendered.
3. For a native attachment or local presentation tool, pass
   `report_artifact.absolute_path` exactly. Use any tool-returned attachment URI
   unchanged. For local Markdown file links, use `report_artifact.markdown_link`
   exactly. Do not shorten the target to a filename, infer a project-relative
   prefix, add `file://`, or invent a sandbox URL.
4. Verify the presentation tool's result when one is available. Provide the report
   link and headline values in the same response. If preview cannot be checked,
   do not claim it opened. If the client cannot preview HTML, offer the supported
   attachment/download and keep the concise result readable in chat. Never upload
   private account data to an external service to obtain a preview.

For a report created outside the bundled helpers, or to repair an existing link,
run `scripts/report_delivery.py` with the **absolute path to that existing file**.
The helper reads the file and returns the same delivery record without changing it.
It deliberately rejects relative paths so a changed working directory cannot
silently select the wrong file. Use the saved output path; if it was lost, locate
the specific report within authorized workspace files and confirm its identity.

An unreadable preview is not by itself evidence that the report is missing. Check
the exact linked target against the actual file first. Redeliver the same file by
its verified absolute path. Regenerate only if the report itself is missing,
invalid or the user requested changed data. Do not make the user ask again to get
the file, and do not rely on a client-specific memory note for this behavior.

Keep delivery records private. A privacy report masks report content; its absolute
path may still identify a customer through folder or file names. Do not claim that
privacy export sanitizes chat, paths or prior attachments.
