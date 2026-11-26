# Message template

The only message this tool sends is `templates/consent_request_v1.txt`.

- **Status: pending legal review.** The text has not yet been approved by the lawyer. Live sending stays disabled until the owner confirms the lawyer has answered.
- **Do not edit the text in place.** Any change, even one character, must be saved as a new file with a bumped version in the file name (`consent_request_v2.txt`, ...), and the code that refers to the template version must be updated to match. The version string recorded in the ledger (`message_version`) is the file name without `.txt`, so every site row shows exactly which text it received.
- `{address}` is the only placeholder. It is filled from the `SENDER_ADDRESS` setting at send time. Live sending refuses to run while any sender detail still contains `TODO`.
- No personalization and no links beyond what the file contains.
