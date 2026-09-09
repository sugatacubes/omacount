# Security policy

## Sensitive capability

Omacount's collector reads Linux input event devices. This capability can
observe system-wide keyboard and pointer events, so changes to the collector,
installer, service definition, persistence schema, or input permissions should
be treated as security-sensitive.

The supported installer does not add the login account to the `input` group and
does not install a broad udev ACL. It grants the supplementary group only to a
hardened, per-user-session systemd service. The collector opens input devices
read-only, stores aggregate counters rather than text or ordered keystrokes, and
cannot open IPv4 or IPv6 sockets under the supplied service policy.

## Reporting a vulnerability

Please do not include passwords, typed text, input-event recordings, private
configuration, or other sensitive data in a public issue. Contact me privately through the security-reporting channel configured on the GitHub repository. Include the affected version, a concise reproduction, and the security impact.

## Supported version

Security fixes are applied to the latest released version.
