# Contributing to VALKYRIE

Thank you for your interest in contributing to VALKYRIE! This document provides guidelines for contributing.

## Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/madhavmadupu/valkyrie-mcp.git
   cd valkyrie-mcp
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install in development mode:**
   ```bash
   pip install -e ".[all]"
   ```

4. **Install pre-commit hooks:**
   ```bash
   pre-commit install
   ```

## Code Quality

We maintain high code quality standards:

- **Type hints:** All functions must have complete type hints
- **Docstrings:** Google-style docstrings for all public APIs
- **Testing:** 90%+ test coverage target
- **Linting:** Code must pass `ruff check`
- **Type checking:** Code must pass `mypy --strict`

### Running checks locally:

```bash
# Format and lint
ruff check src tests --fix
ruff format src tests

# Type check
mypy src --strict

# Run tests
pytest tests/ -v --cov=valkyrie
```

## Testing Guidelines

1. **Unit tests** go in `tests/unit/`
2. **Integration tests** go in `tests/integration/`
3. **Validation tests** (against external data) go in `tests/validation/`; reference numbers live in
   `tests/validation/validation_cases.py`, each with its source. Heavier studies go in
   `validation/run_validation.py`, which regenerates `docs/validation.md` — rerun it after any
   change to the physics.
4. Use descriptive test names: `test_loiter_bmf_increases_with_endurance`
5. Include docstrings explaining what the test validates
6. Use fixtures from `conftest.py` for common test data
7. Prefer checks against an independent calculation (energy balance, published data) over loose ranges

## Contributing Data

The most valuable contribution right now is **flight data** to validate endurance end to end.
Useful logs have: takeoff mass, wing area and span, battery energy used (Wh, from a power module),
airspeed, altitude and wind, and the propulsion setup. Open an issue with the log and its source;
it becomes a case in `tests/validation/` and a section in `docs/validation.md`.

Every physics change must cite its source in the docstring and in `docs/references.md`.

## Pull Request Process

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** with clear, atomic commits

3. **Write tests** for new functionality

4. **Update documentation** if you changed APIs

5. **Run all checks:**
   ```bash
   pytest tests/ -v
   ruff check src tests
   mypy src --strict
   ```

6. **Submit PR** with:
   - Clear description of changes
   - Link to related issue (if applicable)
   - Screenshots/output for examples

## Areas for Contribution

### Good First Issues
- Add propeller database entries (APC, Master Airscrew)
- Implement additional empty-weight regression models
- Create example UAV designs
- Improve error messages

### Advanced Contributions
- Multi-objective optimization (Pareto fronts)
- Wind/gust response modeling
- Structural weight estimation improvements
- Integration with CAD tools

### Documentation
- Tutorial notebooks
- Video walkthroughs
- Theory deep-dives
- Integration guides

## Reporting Issues

When reporting bugs, include:
- VALKYRIE version (`python -c "import valkyrie; print(valkyrie.__version__)"`)
- Python version
- Operating system
- Minimal reproducible example
- Expected vs. actual behavior

## Code of Conduct

- Be respectful and constructive
- Focus on the technical merit of ideas
- Help newcomers learn
- Give credit where due

## Questions?

- Open a GitHub issue with the `question` label
- Start a discussion in GitHub Discussions
- Tag @madhavmadupu for urgent matters

---

**Thank you for helping make VALKYRIE better!**
