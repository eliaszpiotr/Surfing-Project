import os
import subprocess
import sys


VALID_SECRET_KEY = "test-production-secret-key-with-enough-length-1234567890"


def run_production_settings_check(extra_env):
    env = os.environ.copy()
    env.update(extra_env)
    env.pop("DJANGO_SETTINGS_MODULE", None)

    return subprocess.run(
        [
            sys.executable,
            "manage.py",
            "check",
            "--deploy",
            "--settings=surfingproject.production_settings",
        ],
        cwd=os.getcwd(),
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def test_production_settings_require_secret_key():
    result = run_production_settings_check(
        {
            "SECRET_KEY": "",
            "ALLOWED_HOSTS": "example.com",
            "CSRF_TRUSTED_ORIGINS": "https://example.com",
        }
    )

    assert result.returncode != 0
    assert "SECRET_KEY is required in production" in result.stderr


def test_production_settings_require_allowed_hosts():
    result = run_production_settings_check(
        {
            "SECRET_KEY": VALID_SECRET_KEY,
            "ALLOWED_HOSTS": "",
            "CSRF_TRUSTED_ORIGINS": "https://example.com",
        }
    )

    assert result.returncode != 0
    assert "ALLOWED_HOSTS must contain at least one value in production" in result.stderr


def test_production_settings_reject_wildcard_allowed_hosts():
    result = run_production_settings_check(
        {
            "SECRET_KEY": VALID_SECRET_KEY,
            "ALLOWED_HOSTS": "*",
            "CSRF_TRUSTED_ORIGINS": "https://example.com",
        }
    )

    assert result.returncode != 0
    assert "ALLOWED_HOSTS cannot contain '*'" in result.stderr


def test_production_settings_require_csrf_trusted_origins():
    result = run_production_settings_check(
        {
            "SECRET_KEY": VALID_SECRET_KEY,
            "ALLOWED_HOSTS": "example.com",
            "CSRF_TRUSTED_ORIGINS": "",
        }
    )

    assert result.returncode != 0
    assert "CSRF_TRUSTED_ORIGINS must contain at least one value in production" in result.stderr


def test_production_settings_require_https_csrf_origins():
    result = run_production_settings_check(
        {
            "SECRET_KEY": VALID_SECRET_KEY,
            "ALLOWED_HOSTS": "example.com",
            "CSRF_TRUSTED_ORIGINS": "http://example.com",
        }
    )

    assert result.returncode != 0
    assert "CSRF_TRUSTED_ORIGINS must use https://" in result.stderr


def test_production_settings_pass_django_deployment_checks():
    result = run_production_settings_check(
        {
            "SECRET_KEY": VALID_SECRET_KEY,
            "ALLOWED_HOSTS": "example.com,www.example.com",
            "CSRF_TRUSTED_ORIGINS": "https://example.com,https://www.example.com",
            "SECURE_HSTS_SECONDS": "31536000",
            "SECURE_HSTS_INCLUDE_SUBDOMAINS": "True",
            "SECURE_HSTS_PRELOAD": "True",
        }
    )

    assert result.returncode == 0, result.stderr
    assert "System check identified no issues" in result.stdout + result.stderr
