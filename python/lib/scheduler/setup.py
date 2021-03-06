from setuptools import setup, find_namespace_packages

try:
    with open('README.md', 'r') as readme:
        long_description = readme.read()
except:
    long_description = ''

exec(open('nwmaas/scheduler/_version.py').read())

setup(
    name='nwmaas-scheduler',
    version=__version__,
    description='',
    long_description=long_description,
    author='',
    author_email='',
    url='',
    license='',
    install_requires=['docker', 'Faker', 'nwmaas-communication>=0.2.0', 'nwmaas-redis>=0.0.1'],
    packages=find_namespace_packages(exclude=('test', 'src'))
)