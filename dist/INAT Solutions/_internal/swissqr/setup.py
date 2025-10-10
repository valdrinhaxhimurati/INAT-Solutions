import pathlib
from distutils.core import setup
from setuptools import find_packages


here = pathlib.Path(__file__).parent.resolve()
long_description = (here / 'README.md').read_text(encoding='utf-8')
install_requires = [
    line.strip()
    for line in (here / "requirements.txt").read_text(encoding="utf-8").splitlines()
    if line.strip() and not line.startswith("#")
]


setup(
    name='swissqr',
    version='0.2.0',
    description='Generator for Swiss QR bill qr codes',
    long_description=long_description,
    long_description_content_type='text/markdown',
    license="MIT",
    author='Martin Obrist',
    author_email='dev@obrist.email',
    url='https://gitlab.com/dinuthehuman/swissqr',
    project_urls={
        'Source Code': 'https://gitlab.com/dinuthehuman/swissqr',
        'Issue Tracker': 'https://gitlab.com/dinuthehuman/swissqr/-/issues'
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Topic :: Office/Business :: Financial",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only"
    ],
    keywords="Switzerland, payment, qrcode",
    packages=find_packages(where='.', exclude=['tests', 'tasks']),
    python_requires='>=3.9, <4',
    include_package_data=True,
    install_requires=[
        "beautifulsoup4",
        "iso4217",
        "lxml",
        "pyban",
        "pyban-swift",
        "pycountry",
        "pydantic",
        "qrcode"
    ],
    extras_require={
        "dev": ["invoke", "twine"]
    }
)
