import setuptools
import os

with open('README.rst') as file:
    readme = file.read()

name = 'wrapio'

version = '2.0.0'

author = 'Exahilosys'

url = f'https://github.com/{author}/{name}'

setuptools.setup(
    name = name,
    python_requires = '>=3.5',
    version = version,
    author = author,
    url = url,
    packages = setuptools.find_packages(),
    license = 'MIT',
    description = 'Handling event-based streams.',
    long_description = readme,
    extras_require = {
        'docs': [
            'sphinx'
        ]
    }
)
