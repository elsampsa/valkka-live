from setuptools import setup, Extension, find_packages
import sys

# modified by setver.bash
version = '0.4.1'

# # https://setuptools.readthedocs.io/en/latest/setuptools.html#basic-use
setup(
    name = "valkka_live",
    version = version,
    
    # python packaging is in a state of mess, as usual (**)
    # https://github.com/pypa/pip/issues/5384
    
    install_requires = [
        'PySide2 >=5.11.1',
        'cute_mongo_forms >=0.2.1',
        'imutils >= 0.4.6',
        'pypng >= 0.0.18'
        # 'cute_mongo_forms@git+https://github.com/elsampsa/cute_mongo_forms.git@master' # (**) won't work at the moment
    ],
    
    #dependency_links = [ # install dependencies from git
    #    'git+https://github.com/elsampsa/cute_mongo_forms.git' # (**) works, but is deprecated.  Must use --process-dependency_links with pip3
    #],
    
    scripts=[
        "bin/valkka-live", # sets env variables, uses run-valkka-live entry point
        "bin/install-valkka-core",
        "bin/update-valkka-core",
        "bin/valkka-move-ps",
        "bin/valkka-tune",
        "bin/valkka-kill",
        "bin/valkka-bionic-install"
    ],

    #
    entry_points={
        'console_scripts': [
            'run-valkka-live = valkka.live.gui:main'
    ]
    },

    # packages = find_packages(), # # includes python code from every directory that has an "__init__.py" file in it.  If no "__init__.py" is found, the directory is omitted.  Other directories / files to be included, are defined in the MANIFEST.in file

    # this is needed for namespace packages:
    packages=[
        'valkka.live',
        'valkka.live.container',
        'valkka.mvision',
        'valkka.mvision.movement',
        'valkka.mvision.alpr',
        'valkka.mvision.nix'
        ],

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

