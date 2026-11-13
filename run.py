#!/usr/bin/env python3
"""Start the Persian Voice Chat server."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8765,
        reload=False,
        log_level="info",
    )
