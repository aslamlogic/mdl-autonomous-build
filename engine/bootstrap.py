name: Bootstrap MBH

on:
  push:
    paths:
      - 'specs/**'

jobs:
  bootstrap:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Install deps
        run: pip install requests

      - name: Run bootstrap
        env:
          CLAUDE_API_KEY: ${{ secrets.CLAUDE_API_KEY }}
        run: python engine/bootstrap.py
