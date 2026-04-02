import subprocess


def _run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def commit_and_push():
    """
    Deterministic commit + push of generated artefacts.
    Safe to run repeatedly.
    """

    # Configure bot identity
    _run(["git", "config", "user.name", "meta-bot"])
    _run(["git", "config", "user.email", "bot@meta.ai"])

    # Add all changes
    _run(["git", "add", "."])

    # Commit (ignore if nothing to commit)
    code, out, err = _run(["git", "commit", "-m", "Auto-generated system update"])
    if code != 0:
        print("No changes to commit")

    # Push
    code, out, err = _run(["git", "push"])
    if code != 0:
        print("Push failed:", err)
    else:
        print("Push successful")
