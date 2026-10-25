# Privacy Policy

Last updated: 2025.

## Summary

EON is a local application (a command-line tool and an optional web
interface that runs on your own computer). It does not collect, transmit,
sell, or share any personal information.

## What EON actually does with data

- EON generates and stores simulation data: procedurally generated world
  grids, simulated organism records, species records, and event logs.
  All of this is synthetic data produced by the simulation itself. None
  of it is personal information about you.
- When you use `--save` or the `resume` command, EON writes this
  simulation data to a JSON file at the path you specify, on your own
  filesystem. Nothing is uploaded anywhere.
- The web interface (`python3 serve.py`) runs a small server bound to
  127.0.0.1, so only your own computer can reach it. When the page
  opens, your browser asks Google Fonts (fonts.googleapis.com) for the
  Space Grotesk, JetBrains Mono and Reenie Beanie fonts, which Google
  can see as a normal web request from your browser. EON itself sends
  nothing there. Offline, the page falls back to system fonts.
- The EON program does not make network requests. It does not phone home, check for
  updates automatically, report usage analytics, or contact any
  Anthropic or third-party server.
- EON does not ask for, store, or process your name, email address,
  location, device identifiers, or any other personal information.

## Third-party services

EON does not integrate with any third-party analytics, advertising, or
tracking service. It has no accounts, no login, and no telemetry.

## Changes

If a future version of EON adds a network feature, an API, analytics, or
any other component that changes this, this document will be updated to
describe exactly what is collected and why, rather than making a blanket
claim that nothing changed.

## Contact

This is an independent, experimental software project. There is no
dedicated support address; use the project's issue tracker if one is
provided alongside this copy of EON.
