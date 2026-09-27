# Blog inbox

Each FxPro email gets its own folder here. A folder holds `email.json`
(the email's details) plus the attachments from that email: the `.docx`
commentary and any chart images.

The five most recent emails already have folders with `email.json`
filled in. Each `email.json` lists the files it expects under
`expectedAttachments`. To publish them, do one of these:

- **Automatic:** run `python3 scripts/fetch_fxpro_emails.py`, which downloads
  the attachments from Gmail into the right folders.
- **By hand:** download the attachments from the email and upload them into
  the matching folder.

Then run `python3 scripts/import_commentary.py` to create the posts and
rebuild the blog.

The Weekly Market Performance email has two images, one in English and one
in Spanish. After adding them, set `includeImages` in its `email.json` to
the English file only, for example `["image (26).png"]`.
