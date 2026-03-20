from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="codeless-api-framework",
    version="1.0.0",
    author="Codeless API Framework Team",
    author_email="team@codeless-api.com",
    description="A powerful framework for writing API tests in natural language",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/codeless-api-framework",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Testing",
        "Topic :: Internet :: WWW/HTTP",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
        ],
        "performance": [
            "locust>=2.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "codeless-api=main:cli",
        ],
    },
    include_package_data=True,
    package_data={
        "src": ["reporter/templates/*.html"],
    },
)
