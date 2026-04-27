# Contributing to Midnight Rider 🌊

Thank you for interest in contributing! This is an open-source marine instrumentation project, and contributions are welcome.

## Guidelines

### Before You Start

1. **Check existing issues** — avoid duplicates
2. **Fork the repo** on GitHub
3. **Create a feature branch** — use a descriptive name
   ```bash
   git checkout -b feature/your-feature-name
   ```

### Code Standards

- **Never commit credentials** — use `.env.example` as a template
- Follow **PEP 8** for Python code
- Add **docstrings** to functions
- Test your changes locally before pushing
- Write clear **commit messages**

### Security

- **No hardcoded tokens, passwords, or API keys** in code or config files
- Use `.env.local` (which is gitignored) for local credentials
- If you discover a security issue, please report it privately to the maintainers

### Testing

Before submitting a PR:
1. Test your changes locally
2. Run `pytest` if tests exist
3. Verify no errors in logs

### Pull Request Process

1. Update documentation if you change functionality
2. Reference any related issues (`Fixes #123`)
3. Provide a clear description of changes
4. Submit PR against `main` branch

### Documentation

- Update relevant markdown files in `docs/`
- Keep `README.md` in sync with major changes
- Document hardware connections and configuration steps

## Questions?

Open an issue on GitHub and describe your question. We're here to help!

---

**Thank you for helping make Midnight Rider better!** ⛵
