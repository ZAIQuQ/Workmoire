# Contributing

Keep changes small, documented, and easy to review.

Before opening a pull request:

1. Run make compile.
2. Run make test.
3. Check that no runtime data, credentials, server addresses, or generated
   files are included in the diff.
4. Explain the user-facing behavior and how it was verified.

The application intentionally uses Python's standard library and a small
browser client so it can run on a modest single-user server.

For frontend changes, also run the optional browser smoke test in a development
environment with Python 3.12 and Playwright:

```sh
python -m pip install playwright
python -m playwright install chromium
python tests/browser_smoke.py
```

The test starts its own loopback server and uses only temporary, synthetic data.
Playwright is a development dependency; production needs no browser packages.
