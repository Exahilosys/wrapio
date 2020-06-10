import setuptools

with open('README.rst') as file:

    readme = file.read()

name = 'wrapio'

version = '0.3.2'

author = 'Exahilosys'

url = f'https://github.com/{author}/{name}'

setuptools.setup(
    name = name,
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
