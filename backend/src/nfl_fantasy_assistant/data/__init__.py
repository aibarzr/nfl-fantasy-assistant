"""Offline/prepared-data adapters; nflverse records remain contained here.

The modules in this package deliberately expose small, stable records instead of
``nflreadpy``/Polars objects.  Live draft code consumes only a published dataset
version, never a downloader or a raw nflverse record.
"""
