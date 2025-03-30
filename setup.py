from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="linkedin-job-automation",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="LinkedIn job application automation tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/linkedin-job-automation",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "playwright>=1.40.0",
        "python-dotenv>=1.0.0",
        "google-generativeai>=0.3.0",
        "weasyprint>=60.1",
        "markdown>=3.5.1",
        "beautifulsoup4>=4.12.2",
        "pytest>=7.4.0",
        "pypandoc>=1.12",
        "nltk>=3.8.1",
        "Levenshtein>=0.27.1"
    ],
    entry_points={
        "console_scripts": [
            "linkedin-apply=main:main",
        ],
    },
)