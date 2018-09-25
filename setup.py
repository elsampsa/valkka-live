from setuptools import setup, Extension, find_packages
import sys

# modified by setver.bash
version = '0.1.1'

# # https://setuptools.readthedocs.io/en/latest/setuptools.html#basic-use
setup(
    name = "valkka_live",
    version = version,
    install_requires = [
        'PySide2 >=5.11.1',
        'cute_mongo_forms >=0.2.0',
    ],

    scripts=[
        "bin/valkka-live", # sets env variables, uses run-valkka-live entry point
        "bin/install-valkka-core",
        "bin/update-valkka-core"
    ],

    #
    entry_points={
        'console_scripts': [
            'run-valkka-live = valkka_live.gui:main'
    ]
    },

    packages = find_packages(), # # includes python code from every directory that has an "__init__.py" file in it.  If no "__init__.py" is found, the directory is omitted.  Other directories / files to be included, are defined in the MANIFEST.in file

    include_package_data=True, # # conclusion: NEVER forget this : files get included but not installed
    # # "package_data" keyword is a practical joke: use MANIFEST.in instead

    # metadata for upload to PyPI
    author = "Sampsa Riikonen",
    author_email = "sampsa.riikonen@iki.fi",
    description = "Valkka Live video surveillance program",
    license = "AGPL",
    keywords = "valkka video surveillance",
    url = "https://elsampsa.github.io/valkka-live/",

    long_description ="""
    Valkka Live is modular, hackable and customizable OpenSource approach to modern video surveillance and management solutions in local area networks
    """,
    long_description_content_type='text/plain',

    classifiers = [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Operating System :: POSIX :: Linux',
        'Topic :: Multimedia :: Video',
        'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
        'Programming Language :: Python :: 3'
    ],
    project_urls={
        'Valkka library': 'https://elsampsa.github.io/valkka-examples/'
    }
)

