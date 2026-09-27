# Contributing

Suggestions, bug reports, and pull requests are welcome when they improve the checker without making unsupported claims about search-engine behavior.

## Before opening a change

- Explain the problem and expected behavior.
- Add or update tests for changed logic.
- Keep network behavior bounded and predictable.
- Document meaningful changes to output or exit codes.
- Do not add tracking, hidden links, or ranking guarantees.

## Local tests

```bash
python -m unittest discover -s tests -v
```
