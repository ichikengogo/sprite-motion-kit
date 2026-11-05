# Security and privacy

The HTTP editor is a development-only loopback service, with bounded request size, PNG checks, a fixed static-file allowlist, Host/Origin checks on mutations and no remote binding option. Do not deploy it publicly or reverse-proxy it to the internet. This is not a multi-user or hardened production service.

Imported artwork stays on the local computer unless you separately choose to share it. Saved browser JSON embeds images and can contain private material. Keep it outside the repository. Rendering and parsing untrusted files still carry dependency/parser and resource-exhaustion risks; use trusted inputs and supported dependencies.

Do not put security reports containing secrets or private images in public issues. Report a minimal synthetic reproduction privately to the repository maintainers if a private channel is available. Never include live credentials.
